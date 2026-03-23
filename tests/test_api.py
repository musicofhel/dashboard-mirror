"""Tests for dashboard_mirror.api"""

import json
from unittest.mock import patch, MagicMock
import urllib.error

from dashboard_mirror.api import (
    api_get, api_get_v2, api_post, api_get_noauth, api_get_root,
    search, is_error, _creds,
)


class TestCreds:
    def test_returns_base64_string(self):
        with patch("dashboard_mirror.api.cfg") as mock_cfg:
            mock_cfg.OO_USER = "admin"
            mock_cfg.OO_PASS = "secret"
            result = _creds()
            assert isinstance(result, str)
            assert len(result) > 0


class TestIsError:
    def test_string_is_error(self):
        assert is_error("HTTP 401: Unauthorized") is True

    def test_dict_is_not_error(self):
        assert is_error({"list": []}) is False

    def test_list_is_not_error(self):
        assert is_error([]) is False

    def test_connection_error(self):
        assert is_error("CONNECTION_ERROR: refused") is True


class TestApiGet:
    @patch("dashboard_mirror.api.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"list": [1, 2]}).encode()
        mock_urlopen.return_value = mock_resp

        with patch("dashboard_mirror.api.cfg") as mock_cfg:
            mock_cfg.OO_URL = "http://localhost:5080"
            mock_cfg.OO_ORG = "default"
            mock_cfg.OO_USER = "admin"
            mock_cfg.OO_PASS = "pass"
            result = api_get("streams")

        assert result == {"list": [1, 2]}

    @patch("dashboard_mirror.api.urllib.request.urlopen")
    def test_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://test", 401, "Unauthorized", {}, MagicMock(read=lambda: b"denied")
        )
        with patch("dashboard_mirror.api.cfg") as mock_cfg:
            mock_cfg.OO_URL = "http://localhost:5080"
            mock_cfg.OO_ORG = "default"
            mock_cfg.OO_USER = "admin"
            mock_cfg.OO_PASS = "pass"
            result = api_get("streams")

        assert is_error(result)
        assert "401" in result

    @patch("dashboard_mirror.api.urllib.request.urlopen")
    def test_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        with patch("dashboard_mirror.api.cfg") as mock_cfg:
            mock_cfg.OO_URL = "http://localhost:5080"
            mock_cfg.OO_ORG = "default"
            mock_cfg.OO_USER = "admin"
            mock_cfg.OO_PASS = "pass"
            result = api_get("streams")

        assert is_error(result)
        assert "CONNECTION_ERROR" in result

    @patch("dashboard_mirror.api.urllib.request.urlopen")
    def test_custom_org(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_urlopen.return_value = mock_resp

        with patch("dashboard_mirror.api.cfg") as mock_cfg:
            mock_cfg.OO_URL = "http://localhost:5080"
            mock_cfg.OO_ORG = "default"
            mock_cfg.OO_USER = "admin"
            mock_cfg.OO_PASS = "pass"
            api_get("cluster/info", org="_meta")

        call_args = mock_urlopen.call_args[0][0]
        assert "/api/_meta/" in call_args.full_url


class TestApiGetV2:
    @patch("dashboard_mirror.api.urllib.request.urlopen")
    def test_v2_url_prefix(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"list": []}'
        mock_urlopen.return_value = mock_resp

        with patch("dashboard_mirror.api.cfg") as mock_cfg:
            mock_cfg.OO_URL = "http://localhost:5080"
            mock_cfg.OO_ORG = "default"
            mock_cfg.OO_USER = "admin"
            mock_cfg.OO_PASS = "pass"
            api_get_v2("alerts")

        call_args = mock_urlopen.call_args[0][0]
        assert "/v2/default/alerts" in call_args.full_url
        assert "/api/" not in call_args.full_url


class TestApiGetNoauth:
    @patch("dashboard_mirror.api.urllib.request.urlopen")
    def test_no_auth_header(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"status": "ok"}'
        mock_urlopen.return_value = mock_resp

        with patch("dashboard_mirror.api.cfg") as mock_cfg:
            mock_cfg.OO_URL = "http://localhost:5080"
            api_get_noauth("healthz")

        call_args = mock_urlopen.call_args[0][0]
        assert call_args.get_header("Authorization") is None


class TestApiGetRoot:
    @patch("dashboard_mirror.api.urllib.request.urlopen")
    def test_root_path_with_auth(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"key": "value"}'
        mock_urlopen.return_value = mock_resp

        with patch("dashboard_mirror.api.cfg") as mock_cfg:
            mock_cfg.OO_URL = "http://localhost:5080"
            mock_cfg.OO_USER = "admin"
            mock_cfg.OO_PASS = "pass"
            result = api_get_root("config/runtime")

        call_args = mock_urlopen.call_args[0][0]
        assert call_args.full_url == "http://localhost:5080/config/runtime"
        assert call_args.get_header("Authorization") is not None
        assert result == {"key": "value"}


class TestSearch:
    @patch("dashboard_mirror.api.api_post")
    def test_search_passes_time_range(self, mock_post):
        mock_post.return_value = {"hits": [], "total": 0}
        with patch("dashboard_mirror.api.cfg") as mock_cfg:
            mock_cfg.OO_ORG = "default"
            result = search("SELECT * FROM default")

        assert mock_post.called
        call_data = mock_post.call_args[0][1]
        assert "start_time" in call_data["query"]
        assert "end_time" in call_data["query"]
        assert call_data["query"]["start_time"] < call_data["query"]["end_time"]

    @patch("dashboard_mirror.api.api_post")
    def test_search_default_stream_type(self, mock_post):
        mock_post.return_value = {"hits": []}
        with patch("dashboard_mirror.api.cfg") as mock_cfg:
            mock_cfg.OO_ORG = "default"
            search("SELECT * FROM default")

        path = mock_post.call_args[0][0]
        assert "type=traces" in path

    @patch("dashboard_mirror.api.api_post")
    def test_search_custom_stream_type(self, mock_post):
        mock_post.return_value = {"hits": []}
        with patch("dashboard_mirror.api.cfg") as mock_cfg:
            mock_cfg.OO_ORG = "default"
            search("SELECT * FROM logs", stream_type="logs")

        path = mock_post.call_args[0][0]
        assert "type=logs" in path
