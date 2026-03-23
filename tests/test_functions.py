"""Tests for dashboard_mirror.functions"""

from dashboard_mirror.functions import analyze_vrl


class TestAnalyzeVrl:
    def test_field_read(self):
        result = analyze_vrl('.service_name == "dev-loop"')
        assert "service_name" in result["fields_read"]

    def test_field_write(self):
        result = analyze_vrl('.new_field = "value"')
        assert "new_field" in result["fields_written"]

    def test_field_delete(self):
        result = analyze_vrl('del(.old_field)')
        assert "old_field" in result["fields_deleted"]

    def test_possible_rename(self):
        result = analyze_vrl('del(.old_name)\n.new_name = .some_source')
        assert "old_name" in result["fields_deleted"]
        assert "new_name" in result["fields_written"]
        renames = result["possible_renames"]
        assert any(r["from"] == "old_name" and r["to"] == "new_name" for r in renames)

    def test_empty_source(self):
        result = analyze_vrl("")
        assert result["fields_read"] == []
        assert result["fields_written"] == []
        assert result["fields_deleted"] == []
        assert result["possible_renames"] == []

    def test_nested_field(self):
        result = analyze_vrl('.metadata.trace_id = "abc"')
        assert "metadata.trace_id" in result["fields_written"]

    def test_read_not_in_write(self):
        """Fields that are both read and written should only appear in written."""
        result = analyze_vrl('.x = .x + 1')
        assert "x" in result["fields_written"]
        assert "x" not in result["fields_read"]
