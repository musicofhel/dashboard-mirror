"""Tests for dashboard_mirror.traces"""

from dashboard_mirror.traces import validate_trace_tree


class TestValidateTraceTree:
    def test_valid_tree(self):
        spans = [
            {"span_id": "root", "parent_span_id": "", "operation_name": "tb1.run"},
            {"span_id": "child1", "parent_span_id": "root", "operation_name": "tb1.phase.a"},
            {"span_id": "child2", "parent_span_id": "root", "operation_name": "tb1.phase.b"},
        ]
        result = validate_trace_tree(spans)
        assert result["valid"] is True
        assert result["span_count"] == 3
        assert len(result["root_spans"]) == 1
        assert result["root_spans"][0]["operation"] == "tb1.run"

    def test_orphan_span(self):
        spans = [
            {"span_id": "root", "parent_span_id": "", "operation_name": "tb1.run"},
            {"span_id": "orphan", "parent_span_id": "nonexistent", "operation_name": "orphan.op"},
        ]
        result = validate_trace_tree(spans)
        assert result["valid"] is False
        assert len(result["orphan_issues"]) == 1
        assert result["orphan_issues"][0]["issue"] == "parent_not_found"

    def test_empty_trace(self):
        result = validate_trace_tree([])
        assert result["valid"] is True
        assert result["span_count"] == 0

    def test_multiple_roots(self):
        spans = [
            {"span_id": "root1", "parent_span_id": "", "operation_name": "op1"},
            {"span_id": "root2", "parent_span_id": "", "operation_name": "op2"},
        ]
        result = validate_trace_tree(spans)
        assert result["valid"] is True
        assert len(result["root_spans"]) == 2

    def test_zero_parent_id(self):
        """Parent span ID of all zeros should be treated as root."""
        spans = [
            {"span_id": "root", "parent_span_id": "0000000000000000", "operation_name": "root.op"},
        ]
        result = validate_trace_tree(spans)
        assert len(result["root_spans"]) == 1
