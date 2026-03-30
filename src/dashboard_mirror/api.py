"""Shared OpenObserve API client for dashboard-mirror."""

from __future__ import annotations

import base64
import json
import time
import urllib.request
from typing import Any

from . import config as cfg

# IMPORTANT: Use cfg.OO_URL (module attribute access), NOT `from .config import OO_URL`.
# collect.py patches cfg.OO_URL/cfg.OO_USER/cfg.OO_PASS at runtime when CLI args
# override defaults. If we used `from .config import OO_URL`, we'd capture the value
# at import time and miss the runtime patches.


def _creds() -> str:
    return base64.b64encode(f"{cfg.OO_USER}:{cfg.OO_PASS}".encode()).decode()


def api_get(path: str, org: str | None = None) -> dict | list | str:
    """Authenticated GET to OO API. Returns parsed JSON or error string."""
    org = org or cfg.OO_ORG
    url = f"{cfg.OO_URL}/api/{org}/{path}"
    req = urllib.request.Request(url, method="GET", headers={
        "Content-Type": "application/json",
        "Authorization": f"Basic {_creds()}",
    })
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode()[:200]}"
    except urllib.error.URLError as e:
        return f"CONNECTION_ERROR: {e.reason}"


def api_get_v2(path: str, org: str | None = None) -> dict | list | str:
    """Authenticated GET to OO v2 API (/api/v2/{org}/{path})."""
    org = org or cfg.OO_ORG
    url = f"{cfg.OO_URL}/api/v2/{org}/{path}"
    req = urllib.request.Request(url, method="GET", headers={
        "Content-Type": "application/json",
        "Authorization": f"Basic {_creds()}",
    })
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode()[:200]}"
    except urllib.error.URLError as e:
        return f"CONNECTION_ERROR: {e.reason}"


def api_post(path: str, data: dict, org: str | None = None) -> dict | str:
    """Authenticated POST to OO API."""
    org = org or cfg.OO_ORG
    url = f"{cfg.OO_URL}/api/{org}/{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Basic {_creds()}",
    })
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode()[:200]}"
    except urllib.error.URLError as e:
        return f"CONNECTION_ERROR: {e.reason}"


def api_get_noauth(path: str) -> dict | str:
    """Unauthenticated GET (for /healthz, /config only — NOT /config/runtime)."""
    url = f"{cfg.OO_URL}/{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode()[:200]}"
    except urllib.error.URLError as e:
        return f"CONNECTION_ERROR: {e.reason}"


def api_get_root(path: str) -> dict | str:
    """Authenticated GET to a non-org-scoped path (e.g., /config/runtime).

    Unlike api_get which builds /api/{org}/{path}, this builds /{path} directly
    with Basic auth. Use for endpoints like /config/runtime that need auth but
    aren't under the /api/{org}/ prefix.
    """
    url = f"{cfg.OO_URL}/{path}"
    req = urllib.request.Request(url, method="GET", headers={
        "Content-Type": "application/json",
        "Authorization": f"Basic {_creds()}",
    })
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode()[:200]}"
    except urllib.error.URLError as e:
        return f"CONNECTION_ERROR: {e.reason}"


def search(sql: str, stream_type: str = "traces", size: int = 100) -> dict | str:
    """Run an OO SQL search. Handles start_time/end_time automatically (30d window).

    NOTE: stream_type defaults to "traces" for dev-loop's current setup.
    Callers querying logs or metrics streams MUST pass stream_type explicitly.
    """
    now_us = int(time.time() * 1_000_000)
    ago_30d_us = int((time.time() - 86400 * 30) * 1_000_000)
    return api_post("_search?type=" + stream_type, {
        "query": {
            "sql": sql,
            "start_time": ago_30d_us,
            "end_time": now_us,
            "from": 0,
            "size": size,
        }
    })


def is_error(result: Any) -> bool:
    """Check if an API result is an error string."""
    return isinstance(result, str)
