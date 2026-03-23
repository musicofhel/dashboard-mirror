"""Tests for dashboard_mirror.health"""

from unittest.mock import patch

from dashboard_mirror.health import (
    fetch_health, fetch_config, fetch_runtime_config,
    fetch_org_settings, fetch_org_summary, fetch_cluster_info,
)


class TestFetchHealth:
    @patch("dashboard_mirror.health.api_get_noauth")
    def test_calls_noauth(self, mock_noauth):
        mock_noauth.return_value = {"status": "ok"}
        result = fetch_health()
        mock_noauth.assert_called_once_with("healthz")
        assert result == {"status": "ok"}


class TestFetchConfig:
    @patch("dashboard_mirror.health.api_get_noauth")
    def test_calls_noauth(self, mock_noauth):
        mock_noauth.return_value = {"version": "v0.12.1"}
        result = fetch_config()
        mock_noauth.assert_called_once_with("config")
        assert result["version"] == "v0.12.1"


class TestFetchRuntimeConfig:
    @patch("dashboard_mirror.health.api_get_root")
    def test_uses_root_with_auth(self, mock_root):
        mock_root.return_value = {"key": "value"}
        result = fetch_runtime_config()
        mock_root.assert_called_once_with("config/runtime")
        assert result == {"key": "value"}


class TestFetchOrgSettings:
    @patch("dashboard_mirror.health.api_get")
    def test_calls_api_get(self, mock_get):
        mock_get.return_value = {"data": {}}
        result = fetch_org_settings()
        mock_get.assert_called_once_with("settings")


class TestFetchOrgSummary:
    @patch("dashboard_mirror.health.api_get")
    def test_calls_api_get(self, mock_get):
        mock_get.return_value = {"streams": 4}
        result = fetch_org_summary()
        mock_get.assert_called_once_with("summary")
        assert result["streams"] == 4


class TestFetchClusterInfo:
    @patch("dashboard_mirror.health.api_get")
    def test_uses_meta_org(self, mock_get):
        mock_get.return_value = {"nodes": []}
        fetch_cluster_info()
        calls = mock_get.call_args_list
        assert any(call[1].get("org") == "_meta" or (len(call[0]) > 1 and call[0][1] == "_meta") for call in calls)
