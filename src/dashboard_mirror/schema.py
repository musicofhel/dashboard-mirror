"""Capture OpenObserve stream schema — the ground truth for query validation.

Fetches all streams and their field definitions, producing a schema file
that analysts use to verify whether dashboard queries reference real columns.

Usage:
    uv run dm-schema
    uv run dm-schema --output ./output/_baseline/stream-schema.json
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from . import config as cfg
from .api import api_get, api_post, is_error


def fetch_streams() -> list[dict]:
    """Fetch all streams and their types."""
    result = api_get("streams")
    if is_error(result):
        print(f"  Failed to list streams: {result}")
        return []
    return result.get("list", [])


def fetch_stream_schema(stream_name: str, stream_type: str) -> dict:
    """Fetch full schema for a specific stream."""
    result = api_get(f"streams/{stream_name}/schema?type={stream_type}")
    if is_error(result):
        print(f"  Failed to get schema for {stream_name}: {result}")
        return {}
    return result


def fetch_sample_data(stream_name: str, stream_type: str, limit: int = 5) -> list[dict]:
    """Fetch a few sample rows to show real column values."""
    now_us = int(time.time() * 1_000_000)
    ago_30d_us = int((time.time() - 86400 * 30) * 1_000_000)

    query = {
        "query": {
            "sql": f"SELECT * FROM \"{stream_name}\" LIMIT {limit}",
            "start_time": ago_30d_us,
            "end_time": now_us,
            "from": 0,
            "size": limit,
        },
    }
    result = api_post(f"_search?type={stream_type}", query)
    if is_error(result):
        print(f"  Failed to sample {stream_name}: {result}")
        return []
    return result.get("hits", [])


def main():
    parser = argparse.ArgumentParser(description="Capture OO stream schema")
    parser.add_argument("--output", type=Path, default=None, help="Output file path")
    args = parser.parse_args()

    output_path = args.output or (cfg.OUTPUT_DIR / "_baseline" / "stream-schema.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Fetching stream schema from {cfg.OO_URL}...")

    streams = fetch_streams()
    print(f"  Found {len(streams)} streams.")

    schema_data = {
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "oo_url": cfg.OO_URL,
        "org": cfg.OO_ORG,
        "streams": [],
    }

    for stream in streams:
        name = stream.get("name", "")
        stype = stream.get("stream_type", "")
        doc_count = stream.get("stats", {}).get("doc_count", 0)

        print(f"  [{name}] type={stype}, docs={doc_count}")

        # Fetch full schema
        full_schema = fetch_stream_schema(name, stype)
        fields = []
        for field in full_schema.get("fields", full_schema.get("schema", [])):
            fname = field.get("name", field.get("field", ""))
            ftype = field.get("type", field.get("field_type", ""))
            fields.append({"name": fname, "type": ftype})

        # Fetch sample data
        samples = fetch_sample_data(name, stype, limit=3)

        schema_data["streams"].append({
            "name": name,
            "type": stype,
            "doc_count": doc_count,
            "field_count": len(fields),
            "fields": fields,
            "sample_rows": samples,
        })

    with open(output_path, "w") as f:
        json.dump(schema_data, f, indent=2, default=str)

    print(f"\nSchema saved to: {output_path}")
    print(f"  {len(schema_data['streams'])} streams, "
          f"{sum(s['field_count'] for s in schema_data['streams'])} total fields.")

    # Build cross-dashboard map
    from .cross_map import save_cross_map
    save_cross_map(output_dir=output_path.parent.parent)


if __name__ == "__main__":
    main()
