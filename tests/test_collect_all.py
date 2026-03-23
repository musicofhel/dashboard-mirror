"""Tests for dashboard_mirror.collect_all"""

import json
import tempfile
from pathlib import Path

from dashboard_mirror.collect_all import _count_output_files, _load_summary_data


class TestCountOutputFiles:
    def test_counts_json_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline = Path(tmpdir) / "_baseline"
            baseline.mkdir()
            (baseline / "alerts.json").write_text("{}")
            (baseline / "health.json").write_text("{}")
            (baseline / "report.md").write_text("# Report")
            assert _count_output_files(Path(tmpdir)) == 2

    def test_missing_baseline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert _count_output_files(Path(tmpdir)) == 0


class TestLoadSummaryData:
    def test_loads_oo_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline = Path(tmpdir) / "_baseline"
            baseline.mkdir()
            (baseline / "oo-config.json").write_text(json.dumps({
                "config": {"version": "v0.12.1"}
            }))
            summary = _load_summary_data(Path(tmpdir))
            assert summary["oo_version"] == "v0.12.1"

    def test_loads_health_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline = Path(tmpdir) / "_baseline"
            baseline.mkdir()
            (baseline / "oo-health.json").write_text(json.dumps({"status": "ok"}))
            summary = _load_summary_data(Path(tmpdir))
            assert summary["health"] == "ok"

    def test_health_unreachable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline = Path(tmpdir) / "_baseline"
            baseline.mkdir()
            (baseline / "oo-health.json").write_text(json.dumps({"error": "CONNECTION_ERROR"}))
            summary = _load_summary_data(Path(tmpdir))
            assert summary["health"] == "UNREACHABLE"

    def test_loads_alert_counts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline = Path(tmpdir) / "_baseline"
            baseline.mkdir()
            (baseline / "alerts.json").write_text(json.dumps({
                "list": [
                    {"name": "a", "enabled": True},
                    {"name": "b", "enabled": False},
                    {"name": "c", "enabled": True},
                ]
            }))
            summary = _load_summary_data(Path(tmpdir))
            assert summary["alert_count"] == 3
            assert summary["alerts_enabled"] == 2
            assert summary["alerts_disabled"] == 1

    def test_handles_missing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline = Path(tmpdir) / "_baseline"
            baseline.mkdir()
            summary = _load_summary_data(Path(tmpdir))
            assert isinstance(summary, dict)

    def test_enterprise_incident_404(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline = Path(tmpdir) / "_baseline"
            baseline.mkdir()
            (baseline / "alert-incidents.json").write_text(json.dumps({
                "incidents": {"error": "not_found_in_this_version"},
                "stats": {"error": "not_found_in_this_version"},
            }))
            summary = _load_summary_data(Path(tmpdir))
            assert summary.get("active_incidents") is None or summary.get("active_incidents") == "N/A"
