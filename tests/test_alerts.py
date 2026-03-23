"""Tests for dashboard_mirror.alerts"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from dashboard_mirror.alerts import (
    detect_drift,
    check_schema_coverage,
    _extract_columns_from_sql,
    _normalize_sql,
    load_source_alerts,
)


class TestExtractColumnsFromSql:
    def test_simple_select(self):
        cols = _extract_columns_from_sql("SELECT service_name, duration FROM default")
        assert "service_name" in cols
        assert "duration" in cols

    def test_where_clause(self):
        cols = _extract_columns_from_sql(
            "SELECT COUNT(*) FROM default WHERE status_code = 'ERROR'"
        )
        assert "status_code" in cols

    def test_group_by(self):
        cols = _extract_columns_from_sql(
            "SELECT operation_name, COUNT(*) FROM default GROUP BY operation_name"
        )
        assert "operation_name" in cols

    def test_skips_sql_keywords(self):
        cols = _extract_columns_from_sql("SELECT COUNT(*) as cnt FROM default WHERE x = 1")
        assert "count" not in cols
        assert "select" not in cols
        assert "from" not in cols


class TestNormalizeSql:
    def test_strips_whitespace(self):
        assert _normalize_sql("  SELECT  *  FROM  default  ") == "select * from default"

    def test_lowercases(self):
        assert _normalize_sql("SELECT X FROM Y") == "select x from y"


class TestDetectDrift:
    def test_missing_in_oo(self):
        source = [{"name": "alert_a"}, {"name": "alert_b"}]
        live = [{"name": "alert_a"}]
        result = detect_drift(source, live)
        assert len(result["missing_in_oo"]) == 1
        assert result["missing_in_oo"][0]["name"] == "alert_b"

    def test_extra_in_oo(self):
        source = [{"name": "alert_a"}]
        live = [{"name": "alert_a"}, {"name": "alert_c"}]
        result = detect_drift(source, live)
        assert len(result["extra_in_oo"]) == 1
        assert result["extra_in_oo"][0]["name"] == "alert_c"

    def test_enabled_drift(self):
        source = [{"name": "alert_a", "enabled": True}]
        live = [{"name": "alert_a", "enabled": False}]
        result = detect_drift(source, live)
        assert len(result["drift"]) == 1
        assert result["drift"][0]["differences"][0]["field"] == "enabled"

    def test_no_drift(self):
        source = [{"name": "alert_a", "enabled": True}]
        live = [{"name": "alert_a", "enabled": True}]
        result = detect_drift(source, live)
        assert len(result["drift"]) == 0
        assert len(result["missing_in_oo"]) == 0
        assert len(result["extra_in_oo"]) == 0

    def test_empty_inputs(self):
        result = detect_drift([], [])
        assert result["source_count"] == 0
        assert result["live_count"] == 0


class TestCheckSchemaCoverage:
    def test_all_columns_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "stream-schema.json"
            schema_path.write_text(json.dumps({
                "streams": [{"fields": [
                    {"name": "service_name", "type": "Utf8"},
                    {"name": "duration", "type": "Int64"},
                    {"name": "default", "type": "Utf8"},
                ]}]
            }))

            alerts = [{"name": "test", "query_condition": {
                "sql": "SELECT service_name, duration FROM default"
            }}]
            result = check_schema_coverage(alerts, schema_path)
            assert len(result) == 1
            assert result[0]["all_columns_valid"] is True

    def test_missing_column(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "stream-schema.json"
            schema_path.write_text(json.dumps({
                "streams": [{"fields": [
                    {"name": "service_name", "type": "Utf8"},
                    {"name": "default", "type": "Utf8"},
                ]}]
            }))

            alerts = [{"name": "test", "query_condition": {
                "sql": "SELECT nonexistent_col FROM default"
            }}]
            result = check_schema_coverage(alerts, schema_path)
            assert len(result) == 1
            assert result[0]["all_columns_valid"] is False
            assert "nonexistent_col" in result[0]["missing_columns"]

    def test_schema_file_missing(self):
        result = check_schema_coverage([], Path("/nonexistent/path.json"))
        assert len(result) == 1
        assert "error" in result[0]


class TestLoadSourceAlerts:
    def test_file_not_found(self):
        result = load_source_alerts(Path("/nonexistent/path.yaml"))
        assert result == []

    def test_yaml_list(self):
        try:
            import yaml
        except ImportError:
            return  # skip if no pyyaml

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump([{"name": "alert_a"}], f)
            f.flush()
            result = load_source_alerts(Path(f.name))
            assert len(result) == 1
            assert result[0]["name"] == "alert_a"
