"""Run ALL dashboard-mirror collectors in sequence.

Orchestrates the full collection pipeline:
  1. OO health & config
  2. Stream schemas + cross-dashboard map
  3. Alerts, incidents, destinations
  4. Functions & pipelines
  5. Deep trace analysis
  6. Supplementary (views, reports, annotations, folders)
  7. Config transformation chain diffs
  8. Playwright screenshots + DOM capture

Usage:
    uv run dm-collect-all
    uv run dm-collect-all --skip-playwright
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from . import config as cfg


def _run_step(name: str, module_main, **kwargs) -> tuple[bool, float]:
    """Run a collector step, return (success, duration_seconds)."""
    start = time.time()
    try:
        module_main(**kwargs)
        return True, time.time() - start
    except SystemExit:
        # argparse may call sys.exit(0) on success
        return True, time.time() - start
    except Exception as e:
        print(f"  ERROR in {name}: {e}")
        return False, time.time() - start


def _run_cli(name: str, cmd: list[str]) -> tuple[bool, float]:
    """Run a collector as a subprocess, return (success, duration_seconds)."""
    start = time.time()
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0, time.time() - start
    except Exception as e:
        print(f"  ERROR in {name}: {e}")
        return False, time.time() - start


def _count_output_files(output_dir: Path) -> int:
    """Count JSON files in _baseline."""
    baseline = output_dir / "_baseline"
    if not baseline.exists():
        return 0
    return len(list(baseline.glob("*.json")))


def _load_summary_data(output_dir: Path) -> dict:
    """Load key data from output files for the summary."""
    baseline = output_dir / "_baseline"
    summary = {}

    # OO version from config
    config_path = baseline / "oo-config.json"
    if config_path.exists():
        with open(config_path) as f:
            data = json.load(f)
        cfg_data = data.get("config", {})
        if isinstance(cfg_data, dict):
            summary["oo_version"] = cfg_data.get("version", "unknown")

    # Health
    health_path = baseline / "oo-health.json"
    if health_path.exists():
        with open(health_path) as f:
            data = json.load(f)
        if isinstance(data, dict) and "error" not in data:
            summary["health"] = data.get("status", "OK")
        else:
            summary["health"] = "UNREACHABLE"

    # Streams
    schema_path = baseline / "stream-schema.json"
    if schema_path.exists():
        with open(schema_path) as f:
            data = json.load(f)
        streams = data.get("streams", [])
        summary["stream_count"] = len(streams)
        total_docs = sum(s.get("doc_count", 0) for s in streams)
        summary["total_docs"] = total_docs

    # Alerts
    alerts_path = baseline / "alerts.json"
    if alerts_path.exists():
        with open(alerts_path) as f:
            data = json.load(f)
        if isinstance(data, dict) and "error" not in data:
            alerts_list = data.get("list", [])
            summary["alert_count"] = len(alerts_list)
            summary["alerts_enabled"] = sum(1 for a in alerts_list if a.get("enabled", True))
            summary["alerts_disabled"] = summary["alert_count"] - summary["alerts_enabled"]

    # Incidents
    incidents_path = baseline / "alert-incidents.json"
    if incidents_path.exists():
        with open(incidents_path) as f:
            data = json.load(f)
        stats = data.get("stats", {})
        if isinstance(stats, dict) and "error" not in stats:
            summary["active_incidents"] = stats.get("open_incidents", 0)
        else:
            summary["active_incidents"] = "N/A"

    # Destinations
    dest_path = baseline / "alert-destinations.json"
    if dest_path.exists():
        with open(dest_path) as f:
            data = json.load(f)
        if isinstance(data, list):
            summary["destination_count"] = len(data)
        elif isinstance(data, dict) and "error" not in data:
            summary["destination_count"] = len(data.get("list", data.get("destinations", [])))

    # Functions & pipelines
    func_path = baseline / "functions.json"
    if func_path.exists():
        with open(func_path) as f:
            data = json.load(f)
        if isinstance(data, dict) and "error" not in data:
            summary["function_count"] = len(data.get("list", []))

    pipe_path = baseline / "pipelines.json"
    if pipe_path.exists():
        with open(pipe_path) as f:
            data = json.load(f)
        if isinstance(data, dict) and "error" not in data:
            summary["pipeline_count"] = len(data.get("list", []))

    # Traces
    svc_path = baseline / "trace-services.json"
    if svc_path.exists():
        with open(svc_path) as f:
            data = json.load(f)
        services = data.get("services", [])
        summary["trace_services"] = [s.get("service_name", "?") for s in services]

    ops_path = baseline / "trace-operations.json"
    if ops_path.exists():
        with open(ops_path) as f:
            data = json.load(f)
        summary["operation_count"] = data.get("count", 0)

    # Saved views
    views_path = baseline / "saved-views.json"
    if views_path.exists():
        with open(views_path) as f:
            data = json.load(f)
        if isinstance(data, dict) and "error" not in data:
            summary["saved_views"] = len(data.get("views", []))
        elif isinstance(data, list):
            summary["saved_views"] = len(data)

    # Reports
    reports_path = baseline / "reports.json"
    if reports_path.exists():
        with open(reports_path) as f:
            data = json.load(f)
        if isinstance(data, list):
            summary["report_count"] = len(data)
        elif isinstance(data, dict) and "error" not in data:
            summary["report_count"] = 0

    # Dashboards (count from output dirs)
    dash_dirs = [d for d in output_dir.iterdir()
                 if d.is_dir() and d.name != "_baseline" and (d / "meta.json").exists()]
    summary["dashboard_count"] = len(dash_dirs)
    total_panels = 0
    for dd in dash_dirs:
        meta_path = dd / "meta.json"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            total_panels += meta.get("panel_count", 0)
    summary["total_panels"] = total_panels

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run ALL dashboard-mirror collectors")
    parser.add_argument("--output", type=Path, default=cfg.OUTPUT_DIR, help="Output directory")
    parser.add_argument("--skip-playwright", action="store_true",
                        help="Skip the Playwright-based collection (steps 7-8)")
    parser.add_argument("--url", default=None, help="Override OO URL")
    parser.add_argument("--user", default=None, help="Override OO username")
    parser.add_argument("--pass", dest="password", default=None, help="Override OO password")
    args = parser.parse_args()

    if args.url:
        cfg.OO_URL = args.url
    if args.user:
        cfg.OO_USER = args.user
    if args.password:
        cfg.OO_PASS = args.password

    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Dashboard Mirror — Full Collection")
    print(f"  OO: {cfg.OO_URL}")
    print(f"  Org: {cfg.OO_ORG}")
    print(f"  Output: {output_dir.resolve()}")
    print("=" * 60)

    total_start = time.time()
    results = {}

    # Step 1: Health
    print("\n[1/8] OO Health & Config")
    from .health import main as health_main
    ok, dur = _run_step("health", health_main)
    results["health"] = {"ok": ok, "duration": dur}

    # Step 2: Schema
    print("\n[2/8] Stream Schemas")
    from .schema import main as schema_main
    ok, dur = _run_step("schema", schema_main)
    results["schema"] = {"ok": ok, "duration": dur}

    # Step 3: Alerts
    print("\n[3/8] Alerts & Incidents")
    from .alerts import main as alerts_main
    ok, dur = _run_step("alerts", alerts_main)
    results["alerts"] = {"ok": ok, "duration": dur}

    # Step 4: Functions
    print("\n[4/8] Functions & Pipelines")
    from .functions import main as functions_main
    ok, dur = _run_step("functions", functions_main)
    results["functions"] = {"ok": ok, "duration": dur}

    # Step 5: Traces
    print("\n[5/8] Trace Analysis")
    from .traces import main as traces_main
    ok, dur = _run_step("traces", traces_main)
    results["traces"] = {"ok": ok, "duration": dur}

    # Step 6: Supplementary
    print("\n[6/8] Supplementary Data")
    from .supplementary import main as supplementary_main
    ok, dur = _run_step("supplementary", supplementary_main)
    results["supplementary"] = {"ok": ok, "duration": dur}

    if not args.skip_playwright:
        # Step 7: Transform chain
        print("\n[7/8] Config Transformation Chain")
        ok, dur = _run_cli("chain", [sys.executable, "-m", "dashboard_mirror.transform_chain"])
        results["chain"] = {"ok": ok, "duration": dur}

        # Step 8: Playwright collection
        print("\n[8/8] Playwright Mirror Capture")
        ok, dur = _run_cli("collect", [sys.executable, "-m", "dashboard_mirror.collect"])
        results["collect"] = {"ok": ok, "duration": dur}
    else:
        print("\n[7-8/8] Skipped (--skip-playwright)")
        results["chain"] = {"ok": True, "duration": 0, "skipped": True}
        results["collect"] = {"ok": True, "duration": 0, "skipped": True}

    total_duration = time.time() - total_start

    # Summary
    summary = _load_summary_data(output_dir)
    file_count = _count_output_files(output_dir)

    print("\n" + "=" * 60)
    print("Dashboard Mirror — Collection Complete")
    print(f"  OO Version: {summary.get('oo_version', 'unknown')}")
    print(f"  Health: {summary.get('health', 'unknown')}")
    print(f"  Org: {cfg.OO_ORG}")
    print(f"  Streams: {summary.get('stream_count', '?')} ({summary.get('total_docs', '?')} docs)")

    dash_count = summary.get("dashboard_count", 0)
    panels = summary.get("total_panels", 0)
    if dash_count:
        print(f"  Dashboards: {dash_count} ({panels} panels total)")

    alert_count = summary.get("alert_count", "?")
    enabled = summary.get("alerts_enabled", "?")
    disabled = summary.get("alerts_disabled", "?")
    incidents = summary.get("active_incidents", "?")
    print(f"  Alerts: {alert_count} rules ({enabled} enabled, {disabled} disabled), {incidents} active incidents")
    print(f"  Destinations: {summary.get('destination_count', '?')} configured")
    print(f"  Functions: {summary.get('function_count', 0)}")
    print(f"  Pipelines: {summary.get('pipeline_count', 0)}")

    svcs = summary.get("trace_services", [])
    print(f"  Trace services: {len(svcs)} ({', '.join(svcs) if svcs else 'none'})")
    print(f"  Operations: {summary.get('operation_count', '?')} distinct")
    print(f"  Saved views: {summary.get('saved_views', '?')}")
    print(f"  Reports: {summary.get('report_count', '?')}")
    print(f"  Output: {output_dir.resolve()} ({file_count} baseline files)")

    minutes = int(total_duration // 60)
    seconds = int(total_duration % 60)
    print(f"  Duration: {minutes}m {seconds}s")

    # Step status
    failed = [name for name, r in results.items() if not r["ok"]]
    if failed:
        print(f"\n  FAILED steps: {', '.join(failed)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
