"""Capture OpenObserve VRL functions and pipeline configuration.

Fetches all functions, pipelines, pipeline-stream associations, and
pipeline modification history. Performs basic VRL field analysis.

Usage:
    uv run dm-functions
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from . import config as cfg
from .api import api_get, is_error


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def fetch_functions() -> dict | list | str:
    """Fetch all VRL functions."""
    return api_get("functions")


def fetch_pipelines() -> dict | list | str:
    """Fetch all pipelines."""
    return api_get("pipelines")


def fetch_pipeline_streams() -> dict | list | str:
    """Fetch stream-to-pipeline associations."""
    return api_get("pipelines/streams")


def fetch_pipeline_history() -> dict | list | str:
    """Fetch pipeline modification history."""
    return api_get("pipelines/history")


def analyze_vrl(source: str) -> dict:
    """Extract field read/write/delete patterns from VRL source code.

    This is pattern matching, not a full VRL parser. It catches common patterns
    but may miss complex expressions.
    """
    fields_read = set()
    fields_written = set()
    fields_deleted = set()

    # Fields read: .field_name (but not after del( or as assignment target)
    for m in re.finditer(r'(?<!del\()\.([a-zA-Z_][a-zA-Z0-9_.]*)', source):
        fields_read.add(m.group(1))

    # Fields written: .field_name = ... (single =, not == or !=)
    for m in re.finditer(r'\.([a-zA-Z_][a-zA-Z0-9_.]*)\s*(?<!=)=(?!=)', source):
        fields_written.add(m.group(1))

    # Fields deleted: del(.field_name)
    for m in re.finditer(r'del\(\s*\.([a-zA-Z_][a-zA-Z0-9_.]*)\s*\)', source):
        fields_deleted.add(m.group(1))

    # Fields renamed = deleted + written with different name
    fields_renamed = []
    for deleted in fields_deleted:
        for written in fields_written:
            if deleted != written:
                fields_renamed.append({"from": deleted, "to": written})

    # Remove write targets from read set (they may appear as both)
    pure_reads = fields_read - fields_written - fields_deleted

    return {
        "fields_read": sorted(pure_reads),
        "fields_written": sorted(fields_written),
        "fields_deleted": sorted(fields_deleted),
        "possible_renames": fields_renamed,
    }


def main():
    parser = argparse.ArgumentParser(description="Capture OO functions & pipelines")
    parser.add_argument("--output", type=Path, default=None, help="Output directory")
    args = parser.parse_args()

    output_dir = args.output or (cfg.OUTPUT_DIR / "_baseline")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching functions & pipelines from {cfg.OO_URL}...")

    # 1. Functions
    functions_result = fetch_functions()
    if is_error(functions_result):
        print(f"  Failed to fetch functions: {functions_result}")
        _write_json(output_dir / "functions.json", {"error": functions_result})
    else:
        func_list = functions_result.get("list", []) if isinstance(functions_result, dict) else functions_result
        # Analyze VRL for each function
        for func in func_list:
            source = func.get("function", func.get("source", ""))
            if source:
                func["_vrl_analysis"] = analyze_vrl(source)
        _write_json(output_dir / "functions.json", functions_result)
        print(f"  Found {len(func_list)} functions.")

    # 2. Pipelines
    pipelines_result = fetch_pipelines()
    if is_error(pipelines_result):
        print(f"  Failed to fetch pipelines: {pipelines_result}")
        _write_json(output_dir / "pipelines.json", {"error": pipelines_result})
    else:
        pipe_list = pipelines_result.get("list", []) if isinstance(pipelines_result, dict) else pipelines_result
        _write_json(output_dir / "pipelines.json", pipelines_result)
        print(f"  Found {len(pipe_list)} pipelines.")

    # 3. Pipeline-stream associations
    streams_result = fetch_pipeline_streams()
    if is_error(streams_result):
        _write_json(output_dir / "pipeline-streams.json", {"error": streams_result})
    else:
        _write_json(output_dir / "pipeline-streams.json", streams_result)
        print(f"  Pipeline-stream associations captured.")

    # 4. Pipeline history
    history_result = fetch_pipeline_history()
    if is_error(history_result):
        _write_json(output_dir / "pipeline-history.json", {"error": history_result})
    else:
        _write_json(output_dir / "pipeline-history.json", history_result)
        hits = history_result.get("hits", []) if isinstance(history_result, dict) else []
        print(f"  Pipeline history: {len(hits)} entries.")

    print(f"\nOutput: {output_dir}")


if __name__ == "__main__":
    main()
