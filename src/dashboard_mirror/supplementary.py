"""Capture supplementary OpenObserve objects for grounding context.

Fetches saved views, enrichment tables, reports, dashboard annotations,
and folder structure.

Usage:
    uv run dm-supplementary
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from . import config as cfg
from .api import api_get, api_get_v2, is_error


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def fetch_saved_views() -> dict | list | str:
    """Fetch all saved views."""
    return api_get("savedviews")


def fetch_enrichment_tables() -> dict | str:
    """Fetch enrichment table statuses."""
    return api_get("enrichment_tables/status")


def fetch_reports() -> dict | list | str:
    """Fetch all reports."""
    return api_get("reports")


def fetch_dashboard_annotations(dashboard_id: str) -> dict | list | str:
    """Fetch annotations for a specific dashboard."""
    now_us = int(time.time() * 1_000_000)
    ago_30d_us = int((time.time() - 86400 * 30) * 1_000_000)
    return api_get(
        f"dashboards/{dashboard_id}/annotations?start_time={ago_30d_us}&end_time={now_us}"
    )


def fetch_folders() -> dict:
    """Fetch dashboard and alert folder structure (v2 API)."""
    dash_folders = api_get_v2("folders/dashboards")
    alert_folders = api_get_v2("folders/alerts")
    return {
        "dashboard_folders": dash_folders if not is_error(dash_folders) else {"error": dash_folders},
        "alert_folders": alert_folders if not is_error(alert_folders) else {"error": alert_folders},
    }


def _list_dashboard_ids() -> list[dict]:
    """Get dashboard IDs from the dashboards API for annotation fetching."""
    result = api_get("dashboards")
    if is_error(result):
        return []
    dashboards = []
    for d in result.get("dashboards", []):
        v8 = d.get("v8") or {}
        dash_id = v8.get("dashboardId", "")
        title = v8.get("title", "")
        if dash_id:
            dashboards.append({"id": dash_id, "title": title})
    return dashboards


def main():
    parser = argparse.ArgumentParser(description="Capture supplementary OO objects")
    parser.add_argument("--output", type=Path, default=None, help="Output directory")
    args = parser.parse_args()

    output_dir = args.output or (cfg.OUTPUT_DIR / "_baseline")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching supplementary data from {cfg.OO_URL}...")

    # 1. Saved views
    print("  Fetching saved views...")
    views = fetch_saved_views()
    _write_json(output_dir / "saved-views.json",
                views if not is_error(views) else {"error": views})
    if not is_error(views):
        view_list = views.get("views", []) if isinstance(views, dict) else views
        print(f"    {len(view_list)} saved views")

    # 2. Enrichment tables
    print("  Fetching enrichment tables...")
    tables = fetch_enrichment_tables()
    _write_json(output_dir / "enrichment-tables.json",
                tables if not is_error(tables) else {"error": tables})
    if not is_error(tables) and isinstance(tables, dict):
        print(f"    {len(tables)} enrichment tables")

    # 3. Reports
    print("  Fetching reports...")
    reports = fetch_reports()
    _write_json(output_dir / "reports.json",
                reports if not is_error(reports) else {"error": reports})
    if not is_error(reports):
        report_list = reports if isinstance(reports, list) else []
        print(f"    {len(report_list)} reports")

    # 4. Dashboard annotations
    print("  Fetching dashboard annotations...")
    dashboards = _list_dashboard_ids()
    all_annotations = {}
    for dash in dashboards:
        annotations = fetch_dashboard_annotations(dash["id"])
        if is_error(annotations):
            all_annotations[dash["id"]] = {"title": dash["title"], "error": annotations}
        else:
            ann_list = annotations if isinstance(annotations, list) else annotations.get("annotations", []) if isinstance(annotations, dict) else []
            all_annotations[dash["id"]] = {
                "title": dash["title"],
                "annotations": ann_list,
                "count": len(ann_list),
            }
    _write_json(output_dir / "annotations.json", all_annotations)
    total_annotations = sum(
        v.get("count", 0) for v in all_annotations.values() if isinstance(v, dict)
    )
    print(f"    {total_annotations} annotations across {len(dashboards)} dashboards")

    # 5. Folders
    print("  Fetching folder structure...")
    folders = fetch_folders()
    _write_json(output_dir / "folders.json", folders)

    print(f"\nOutput: {output_dir}")


if __name__ == "__main__":
    main()
