"""Deep trace structure analysis for dashboard-mirror.

Captures service inventory, operation catalog, attribute coverage, trace
hierarchy validation, DAG structure, and duration distributions.

Usage:
    uv run dm-traces
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from . import config as cfg
from .api import api_get, search, is_error


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def fetch_service_inventory() -> list[dict]:
    """Get all services and their span counts."""
    result = search(
        "SELECT service_name, COUNT(*) as span_count FROM default GROUP BY service_name"
    )
    if is_error(result):
        print(f"  Failed to fetch services: {result}")
        return []
    return result.get("hits", [])


def fetch_operation_catalog() -> list[dict]:
    """Get all operations per service with counts."""
    result = search(
        "SELECT service_name, operation_name, COUNT(*) as cnt "
        "FROM default "
        "GROUP BY service_name, operation_name "
        "ORDER BY service_name, cnt DESC",
        size=500,
    )
    if is_error(result):
        print(f"  Failed to fetch operations: {result}")
        return []
    return result.get("hits", [])


def fetch_attribute_sample(service_name: str, operation_name: str) -> dict | None:
    """Fetch one sample span for attribute coverage analysis."""
    # Escape single quotes in names
    svc = service_name.replace("'", "''")
    op = operation_name.replace("'", "''")
    result = search(
        f"SELECT * FROM default "
        f"WHERE service_name = '{svc}' AND operation_name = '{op}' "
        f"ORDER BY _timestamp DESC LIMIT 1",
        size=1,
    )
    if is_error(result):
        return None
    hits = result.get("hits", [])
    return hits[0] if hits else None


def fetch_latest_traces(count: int = 3) -> list[dict]:
    """Fetch latest trace summaries using traces endpoint."""
    now_us = int(time.time() * 1_000_000)
    ago_30d_us = int((time.time() - 86400 * 30) * 1_000_000)
    result = api_get(
        f"default/traces/latest?start_time={ago_30d_us}&end_time={now_us}&size={count}"
    )
    if is_error(result):
        print(f"  Failed to fetch latest traces: {result}")
        return []
    return result.get("hits", []) if isinstance(result, dict) else []


def fetch_trace_spans(trace_id: str) -> list[dict]:
    """Fetch all spans for a specific trace."""
    tid = trace_id.replace("'", "''")
    result = search(
        f"SELECT trace_id, span_id, parent_span_id, operation_name, "
        f"service_name, duration, status_code "
        f"FROM default WHERE trace_id = '{tid}' "
        f"ORDER BY _timestamp ASC",
        size=500,
    )
    if is_error(result):
        return []
    return result.get("hits", [])


def fetch_trace_dag(trace_id: str) -> dict | str:
    """Fetch DAG for a trace using the traces endpoint."""
    now_us = int(time.time() * 1_000_000)
    ago_30d_us = int((time.time() - 86400 * 30) * 1_000_000)
    return api_get(
        f"default/traces/{trace_id}/dag?start_time={ago_30d_us}&end_time={now_us}"
    )


def validate_trace_tree(spans: list[dict]) -> dict:
    """Validate parent-child relationships in a trace."""
    span_ids = {s.get("span_id") for s in spans}
    issues = []
    root_spans = []

    for span in spans:
        parent = span.get("parent_span_id", "")
        if not parent or parent == "0" * len(parent) if parent else True:
            root_spans.append(span)
        elif parent not in span_ids:
            issues.append({
                "span_id": span.get("span_id"),
                "operation": span.get("operation_name"),
                "parent_span_id": parent,
                "issue": "parent_not_found",
            })

    return {
        "span_count": len(spans),
        "root_spans": [{"span_id": s.get("span_id"), "operation": s.get("operation_name")} for s in root_spans],
        "orphan_issues": issues,
        "valid": len(issues) == 0,
    }


def fetch_duration_distribution() -> list[dict]:
    """Get duration stats for key operation patterns."""
    result = search(
        "SELECT operation_name, "
        "COUNT(*) as cnt, "
        "ROUND(MIN(CAST(duration AS DOUBLE)), 0) as min_us, "
        "ROUND(AVG(CAST(duration AS DOUBLE)), 0) as avg_us, "
        "ROUND(MAX(CAST(duration AS DOUBLE)), 0) as max_us "
        "FROM default "
        "WHERE service_name = 'dev-loop' "
        "AND (operation_name LIKE 'tb%.run' "
        "OR operation_name LIKE 'tb%.phase.%' "
        "OR operation_name LIKE 'gates.%' "
        "OR operation_name = 'runtime.spawn_agent' "
        "OR operation_name = 'runtime.heartbeat') "
        "GROUP BY operation_name "
        "ORDER BY operation_name",
        size=200,
    )
    if is_error(result):
        print(f"  Failed to fetch durations: {result}")
        return []
    return result.get("hits", [])


def main():
    parser = argparse.ArgumentParser(description="Deep trace structure analysis")
    parser.add_argument("--output", type=Path, default=None, help="Output directory")
    args = parser.parse_args()

    output_dir = args.output or (cfg.OUTPUT_DIR / "_baseline")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Analyzing traces from {cfg.OO_URL}...")

    # 1. Service inventory
    print("  Fetching service inventory...")
    services = fetch_service_inventory()
    _write_json(output_dir / "trace-services.json", {
        "services": services,
        "count": len(services),
    })
    for svc in services:
        print(f"    {svc.get('service_name', '?')}: {svc.get('span_count', 0)} spans")

    # 2. Operation catalog
    print("  Fetching operation catalog...")
    operations = fetch_operation_catalog()
    _write_json(output_dir / "trace-operations.json", {
        "operations": operations,
        "count": len(operations),
    })
    print(f"    {len(operations)} distinct operations")

    # 3. Attribute coverage per operation (sample up to 30 unique ops)
    print("  Sampling attribute coverage...")
    seen_ops = set()
    attributes = []
    for op in operations:
        svc = op.get("service_name", "")
        opname = op.get("operation_name", "")
        key = f"{svc}:{opname}"
        if key in seen_ops or len(seen_ops) >= 30:
            continue
        seen_ops.add(key)

        sample = fetch_attribute_sample(svc, opname)
        if sample:
            non_null = {k: type(v).__name__ for k, v in sample.items() if v is not None}
            attributes.append({
                "service_name": svc,
                "operation_name": opname,
                "non_null_attributes": non_null,
                "attribute_count": len(non_null),
            })
    _write_json(output_dir / "trace-attributes.json", {
        "operations_sampled": len(attributes),
        "attributes": attributes,
    })
    print(f"    Sampled {len(attributes)} operations")

    # 4. Trace structure samples
    print("  Fetching trace structure samples...")
    latest = fetch_latest_traces(3)
    trace_structures = []
    for trace_summary in latest:
        trace_id = trace_summary.get("trace_id", "")
        if not trace_id:
            continue
        spans = fetch_trace_spans(trace_id)
        validation = validate_trace_tree(spans)
        trace_structures.append({
            "trace_id": trace_id,
            "summary": trace_summary,
            "spans": spans,
            "validation": validation,
        })
    _write_json(output_dir / "trace-structure.json", {
        "traces_sampled": len(trace_structures),
        "traces": trace_structures,
    })

    # 5. Trace DAGs
    print("  Fetching trace DAGs...")
    dags = []
    for ts in trace_structures:
        trace_id = ts["trace_id"]
        dag = fetch_trace_dag(trace_id)
        if is_error(dag):
            dags.append({"trace_id": trace_id, "error": dag})
        else:
            dags.append({"trace_id": trace_id, "dag": dag})
    _write_json(output_dir / "trace-dag.json", {
        "traces": len(dags),
        "dags": dags,
    })

    # 6. Duration distribution
    print("  Fetching duration distribution...")
    durations = fetch_duration_distribution()
    _write_json(output_dir / "trace-durations.json", {
        "operations": durations,
        "count": len(durations),
    })
    for d in durations:
        avg = d.get("avg_us", 0)
        unit = "µs" if avg < 1000 else "ms" if avg < 1_000_000 else "s"
        val = avg if avg < 1000 else avg / 1000 if avg < 1_000_000 else avg / 1_000_000
        print(f"    {d.get('operation_name', '?')}: avg={val:.0f}{unit}")

    svc_names = [s.get("service_name", "?") for s in services]
    print(f"\nTrace analysis: {len(services)} services ({', '.join(svc_names)}), "
          f"{len(operations)} operations")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
