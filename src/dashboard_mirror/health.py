"""Capture OpenObserve instance health and configuration.

Fetches healthz, config, runtime config, org settings, org summary,
and cluster information.

Usage:
    uv run dm-health
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import config as cfg
from .api import api_get, api_get_noauth, api_get_root, is_error


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def fetch_health() -> dict | str:
    """Fetch /healthz (no auth)."""
    return api_get_noauth("healthz")


def fetch_config() -> dict | str:
    """Fetch /config (no auth)."""
    return api_get_noauth("config")


def fetch_runtime_config() -> dict | str:
    """Fetch /config/runtime (requires auth)."""
    return api_get_root("config/runtime")


def fetch_org_settings() -> dict | str:
    """Fetch org settings."""
    return api_get("settings")


def fetch_org_summary() -> dict | str:
    """Fetch org summary/stats."""
    return api_get("summary")


def fetch_cluster_info() -> dict:
    """Fetch cluster info and node list (requires _meta org)."""
    cluster = api_get("cluster/info", org="_meta")
    nodes = api_get("node/list", org="_meta")
    return {
        "cluster": cluster if not is_error(cluster) else {"error": cluster},
        "nodes": nodes if not is_error(nodes) else {"error": nodes},
    }


def main():
    parser = argparse.ArgumentParser(description="Capture OO health & config")
    parser.add_argument("--output", type=Path, default=None, help="Output directory")
    args = parser.parse_args()

    output_dir = args.output or (cfg.OUTPUT_DIR / "_baseline")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Checking OO health at {cfg.OO_URL}...")

    # 1. Health check
    health = fetch_health()
    _write_json(output_dir / "oo-health.json",
                health if not is_error(health) else {"error": health, "url": cfg.OO_URL})
    if is_error(health):
        print(f"  Health check failed: {health}")
        if "CONNECTION_ERROR" in str(health):
            print(f"  OpenObserve not reachable at {cfg.OO_URL}. Is the container running?")
    else:
        status = health.get("status", "unknown") if isinstance(health, dict) else health
        print(f"  Health: {status}")

    # 2. OO config (noauth)
    print("  Fetching OO config...")
    oo_config = fetch_config()

    # 3. Runtime config (auth required)
    print("  Fetching runtime config...")
    runtime_config = fetch_runtime_config()

    _write_json(output_dir / "oo-config.json", {
        "config": oo_config if not is_error(oo_config) else {"error": oo_config},
        "runtime": runtime_config if not is_error(runtime_config) else {"error": runtime_config},
    })

    if not is_error(oo_config) and isinstance(oo_config, dict):
        version = oo_config.get("version", "unknown")
        print(f"  OO version: {version}")

    # 4. Org settings
    print(f"  Fetching org settings for '{cfg.OO_ORG}'...")
    settings = fetch_org_settings()
    _write_json(output_dir / "oo-org-settings.json",
                settings if not is_error(settings) else {"error": settings})

    # 5. Org summary
    print("  Fetching org summary...")
    summary = fetch_org_summary()
    _write_json(output_dir / "oo-org-summary.json",
                summary if not is_error(summary) else {"error": summary})
    if not is_error(summary) and isinstance(summary, dict):
        streams = summary.get("streams", "?")
        print(f"  Org summary: {streams} streams")

    # 6. Cluster info
    print("  Fetching cluster info...")
    cluster = fetch_cluster_info()
    _write_json(output_dir / "oo-cluster.json", cluster)

    print(f"\nOutput: {output_dir}")


if __name__ == "__main__":
    main()
