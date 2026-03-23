"""Capture OpenObserve alert configuration and firing state.

Fetches alert rules, history, incidents, templates, destinations, and dedup
config. Cross-references against source YAML and stream schema for drift
detection and schema coverage validation.

Usage:
    uv run dm-alerts
    uv run dm-alerts --alerts-config ~/dev-loop/config/alerts/rules.yaml
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from . import config as cfg
from .api import api_get, api_get_v2, is_error


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def fetch_alerts() -> dict | str:
    """Fetch all alert rules from v2 API."""
    return api_get_v2("alerts")


def fetch_alert_history() -> dict | str:
    """Fetch alert firing history (last 30 days)."""
    now_us = int(time.time() * 1_000_000)
    ago_30d_us = int((time.time() - 86400 * 30) * 1_000_000)
    return api_get_v2(f"alerts/history?start_time={ago_30d_us}&end_time={now_us}&size=1000")


def fetch_incidents() -> dict:
    """Fetch active incidents + stats. Enterprise-only — handles 404 gracefully."""
    incidents = api_get_v2("alerts/incidents?limit=50")
    stats = api_get_v2("alerts/incidents/stats")

    result = {}
    if is_error(incidents) and "404" in str(incidents):
        result["incidents"] = {"error": "not_found_in_this_version", "note": "incidents require OO enterprise"}
    elif is_error(incidents):
        result["incidents"] = {"error": incidents}
    else:
        result["incidents"] = incidents

    if is_error(stats) and "404" in str(stats):
        result["stats"] = {"error": "not_found_in_this_version", "note": "incident stats require OO enterprise"}
    elif is_error(stats):
        result["stats"] = {"error": stats}
    else:
        result["stats"] = stats

    return result


def fetch_templates() -> dict | list | str:
    """Fetch alert templates (v1 path)."""
    return api_get("alerts/templates")


def fetch_destinations() -> dict | list | str:
    """Fetch alert notification destinations (v1 path)."""
    return api_get("alerts/destinations")


def fetch_dedup() -> dict:
    """Fetch dedup config (v1) and summary (v2)."""
    config = api_get("alerts/deduplication/config")
    summary = api_get_v2("alerts/dedup/summary")
    return {
        "config": config if not is_error(config) else {"error": config},
        "summary": summary if not is_error(summary) else {"error": summary},
    }


def load_source_alerts(config_path: Path) -> list[dict]:
    """Load alert definitions from source YAML config."""
    if not config_path.exists():
        return []
    try:
        import yaml
        with open(config_path) as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("alerts", data.get("rules", []))
        return []
    except ImportError:
        # PyYAML not available — try basic parsing
        print("  Warning: PyYAML not available, skipping source alert comparison")
        return []
    except Exception as e:
        print(f"  Warning: Could not parse alerts config: {e}")
        return []


def detect_drift(source_alerts: list[dict], live_alerts: list[dict]) -> dict:
    """Compare source-defined alerts against live OO alerts."""
    # Build lookup by name
    live_by_name = {}
    for alert in live_alerts:
        name = alert.get("name", "")
        if name:
            live_by_name[name] = alert

    source_by_name = {}
    for alert in source_alerts:
        name = alert.get("name", "")
        if name:
            source_by_name[name] = alert

    missing_in_oo = []
    extra_in_oo = []
    drift = []

    for name, src in source_by_name.items():
        if name not in live_by_name:
            missing_in_oo.append({"name": name, "source": src})
        else:
            live = live_by_name[name]
            diffs = []
            # Compare key fields
            src_enabled = src.get("enabled", True)
            live_enabled = live.get("enabled", True)
            if src_enabled != live_enabled:
                diffs.append({"field": "enabled", "source": src_enabled, "live": live_enabled})

            src_sql = src.get("sql", src.get("query", ""))
            live_sql = live.get("query_condition", {}).get("sql", "") if isinstance(live.get("query_condition"), dict) else ""
            if src_sql and live_sql and _normalize_sql(src_sql) != _normalize_sql(live_sql):
                diffs.append({"field": "sql", "source": src_sql, "live": live_sql})

            if diffs:
                drift.append({"name": name, "differences": diffs})

    for name in live_by_name:
        if name not in source_by_name:
            extra_in_oo.append({"name": name})

    return {
        "missing_in_oo": missing_in_oo,
        "extra_in_oo": extra_in_oo,
        "drift": drift,
        "source_count": len(source_by_name),
        "live_count": len(live_by_name),
    }


def _normalize_sql(sql: str) -> str:
    """Normalize SQL for comparison (strip whitespace, lowercase)."""
    return re.sub(r"\s+", " ", sql.strip().lower())


def _extract_columns_from_sql(sql: str) -> set[str]:
    """Extract column names referenced in an alert SQL query."""
    columns = set()
    skip_words = {
        "select", "as", "from", "and", "or", "where", "group", "by", "order",
        "having", "limit", "offset", "case", "when", "then", "else", "end",
        "null", "true", "false", "count", "sum", "avg", "min", "max", "round",
        "cast", "date_trunc", "to_timestamp", "interval", "now", "bigint",
        "double", "varchar", "int", "asc", "desc", "between", "not", "in",
        "like", "is", "distinct",
    }
    for token in re.findall(r"\b([a-z_][a-z0-9_]*)\b", sql, re.I):
        if token.lower() not in skip_words:
            columns.add(token)
    return columns


def check_schema_coverage(alerts: list[dict], schema_path: Path) -> list[dict]:
    """Cross-reference alert SQL columns against stream schema."""
    if not schema_path.exists():
        return [{"error": "stream-schema.json not found — run dm-schema first"}]

    with open(schema_path) as f:
        schema = json.load(f)

    # Build set of all known columns across all streams
    known_columns = set()
    for stream in schema.get("streams", []):
        for field in stream.get("fields", []):
            known_columns.add(field.get("name", "").lower())

    results = []
    for alert in alerts:
        name = alert.get("name", "")
        sql = ""
        qc = alert.get("query_condition", {})
        if isinstance(qc, dict):
            sql = qc.get("sql", "")
        if not sql:
            continue

        columns = _extract_columns_from_sql(sql)
        coverage = []
        for col in sorted(columns):
            exists = col.lower() in known_columns
            coverage.append({"column": col, "exists": exists})

        missing = [c for c in coverage if not c["exists"]]
        results.append({
            "alert_name": name,
            "sql": sql,
            "columns": coverage,
            "missing_columns": [c["column"] for c in missing],
            "all_columns_valid": len(missing) == 0,
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="Capture OO alert configuration")
    parser.add_argument("--alerts-config", type=Path, default=cfg.ALERTS_CONFIG,
                        help="Path to source alert rules YAML")
    parser.add_argument("--output", type=Path, default=None, help="Output directory")
    args = parser.parse_args()

    output_dir = args.output or (cfg.OUTPUT_DIR / "_baseline")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching alerts from {cfg.OO_URL}...")

    # 1. Alert rules
    alerts_result = fetch_alerts()
    if is_error(alerts_result):
        print(f"  Failed to fetch alerts: {alerts_result}")
        _write_json(output_dir / "alerts.json", {"error": alerts_result})
        return
    _write_json(output_dir / "alerts.json", alerts_result)
    alerts_list = alerts_result.get("list", [])
    print(f"  Found {len(alerts_list)} alert rules.")

    # 2. Alert history
    print("  Fetching alert history...")
    history = fetch_alert_history()
    _write_json(output_dir / "alert-history.json",
                history if not is_error(history) else {"error": history})

    # 3. Incidents (enterprise-only)
    print("  Fetching incidents...")
    incidents = fetch_incidents()
    _write_json(output_dir / "alert-incidents.json", incidents)

    # 4. Templates
    print("  Fetching alert templates...")
    templates = fetch_templates()
    _write_json(output_dir / "alert-templates.json",
                templates if not is_error(templates) else {"error": templates})

    # 5. Destinations
    print("  Fetching alert destinations...")
    destinations = fetch_destinations()
    _write_json(output_dir / "alert-destinations.json",
                destinations if not is_error(destinations) else {"error": destinations})

    # 6. Dedup
    print("  Fetching dedup config...")
    dedup = fetch_dedup()
    _write_json(output_dir / "alert-dedup.json", dedup)

    # 7. Drift detection
    print(f"  Checking drift against {args.alerts_config}...")
    source_alerts = load_source_alerts(args.alerts_config)
    drift = detect_drift(source_alerts, alerts_list)
    _write_json(output_dir / "alert-drift.json", drift)
    if drift["missing_in_oo"]:
        print(f"    {len(drift['missing_in_oo'])} alerts missing in OO")
    if drift["extra_in_oo"]:
        print(f"    {len(drift['extra_in_oo'])} extra alerts in OO")
    if drift["drift"]:
        print(f"    {len(drift['drift'])} alerts with config drift")

    # 8. Schema coverage
    schema_path = output_dir / "stream-schema.json"
    print("  Checking alert SQL schema coverage...")
    coverage = check_schema_coverage(alerts_list, schema_path)
    _write_json(output_dir / "alert-schema-coverage.json", coverage)
    invalid = [c for c in coverage if isinstance(c, dict) and not c.get("all_columns_valid", True)]
    if invalid:
        print(f"    {len(invalid)} alerts reference missing columns")

    enabled = sum(1 for a in alerts_list if a.get("enabled", True))
    disabled = len(alerts_list) - enabled
    print(f"\nAlerts: {len(alerts_list)} rules ({enabled} enabled, {disabled} disabled)")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
