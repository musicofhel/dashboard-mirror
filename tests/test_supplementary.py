"""Tests for dashboard_mirror.supplementary"""

from unittest.mock import patch

from dashboard_mirror.supplementary import (
    fetch_saved_views, fetch_enrichment_tables, fetch_reports,
    fetch_folders, fetch_dashboard_annotations,
)


class TestFetchSavedViews:
    @patch("dashboard_mirror.supplementary.api_get")
    def test_calls_api_get(self, mock_get):
        mock_get.return_value = {"views": [{"id": "1", "name": "test"}]}
        result = fetch_saved_views()
        mock_get.assert_called_once_with("savedviews")
        assert len(result["views"]) == 1


class TestFetchEnrichmentTables:
    @patch("dashboard_mirror.supplementary.api_get")
    def test_calls_api_get(self, mock_get):
        mock_get.return_value = {"my_table": []}
        result = fetch_enrichment_tables()
        mock_get.assert_called_once_with("enrichment_tables/status")


class TestFetchReports:
    @patch("dashboard_mirror.supplementary.api_get")
    def test_returns_list(self, mock_get):
        mock_get.return_value = [{"name": "daily_report"}]
        result = fetch_reports()
        assert isinstance(result, list)
        assert len(result) == 1


class TestFetchFolders:
    @patch("dashboard_mirror.supplementary.api_get_v2")
    def test_uses_v2_api(self, mock_v2):
        mock_v2.return_value = {"list": []}
        result = fetch_folders()
        calls = [c[0][0] for c in mock_v2.call_args_list]
        assert "folders/dashboards" in calls
        assert "folders/alerts" in calls


class TestFetchDashboardAnnotations:
    @patch("dashboard_mirror.supplementary.api_get")
    def test_includes_time_params(self, mock_get):
        mock_get.return_value = []
        fetch_dashboard_annotations("dash123")
        path = mock_get.call_args[0][0]
        assert "annotations" in path
        assert "start_time=" in path
        assert "end_time=" in path
