---
name: collect
description: "Capture mirror bundles from OpenObserve dashboards — screenshots, DOM text, API responses, config chains, layout metrics, alerts, traces, functions, health."
license: MIT
metadata:
  author: musicofhel
  version: "0.2.0"
  category: collection
---

# When to Use

Use this skill when you need to capture or refresh the raw mirror data from OpenObserve dashboards. This is Phase 1 of the pipeline — it produces the data that analysis agents consume.

# Prerequisites

- OpenObserve running and accessible (default: `http://localhost:5080`)
- Python 3.11+ with `uv`
- Playwright chromium installed: `uv run playwright install chromium`
- Dashboard configs in `DM_CONFIG_DIR` (default: `~/dev-loop/config/dashboards`)

# Commands

Run from the `~/dashboard-mirror` directory.

## Recommended: Full Collection

Run ALL collectors in sequence (API collectors + Playwright):

```bash
uv run dm-collect-all
```

To skip the slow Playwright step (API data only):

```bash
uv run dm-collect-all --skip-playwright
```

## Individual Collectors

### 1. OO Health & Config

Check OO instance health, version, config, and cluster state:

```bash
uv run dm-health
```

Output: `output/_baseline/oo-health.json`, `oo-config.json`, `oo-org-settings.json`, `oo-org-summary.json`, `oo-cluster.json`

### 2. Schema Capture

Fetch all stream field definitions and sample data:

```bash
uv run dm-schema
```

Output: `output/_baseline/stream-schema.json`, `cross-dashboard-map.json`

### 3. Alerts

Capture alert rules, history, incidents, destinations, and drift check:

```bash
uv run dm-alerts
uv run dm-alerts --alerts-config ~/dev-loop/config/alerts/rules.yaml
```

Output: `output/_baseline/alerts.json`, `alert-history.json`, `alert-incidents.json`, `alert-templates.json`, `alert-destinations.json`, `alert-dedup.json`, `alert-drift.json`, `alert-schema-coverage.json`

### 4. Functions & Pipelines

Capture VRL functions, pipelines, and modification history:

```bash
uv run dm-functions
```

Output: `output/_baseline/functions.json`, `pipelines.json`, `pipeline-streams.json`, `pipeline-history.json`

### 5. Deep Trace Analysis

Analyze trace structure, operations, durations, and attribute coverage:

```bash
uv run dm-traces
```

Output: `output/_baseline/trace-services.json`, `trace-operations.json`, `trace-attributes.json`, `trace-structure.json`, `trace-dag.json`, `trace-durations.json`

### 6. Supplementary Data

Capture saved views, reports, annotations, enrichment tables, and folders:

```bash
uv run dm-supplementary
```

Output: `output/_baseline/saved-views.json`, `enrichment-tables.json`, `reports.json`, `annotations.json`, `folders.json`

### 7. Config Chain

Trace dashboard configs through 4 transformation stages and generate diffs:

```bash
uv run dm-chain --config-dir ~/dev-loop/config/dashboards
```

Output per dashboard: `output/<slug>/config/{source,transformed,sent,stored}.json` + `chain-diff.txt`

### 8. Full Mirror Collection (Playwright)

Launch Playwright to capture screenshots, DOM text, API responses, layout metrics, and timing:

```bash
uv run dm-collect
uv run dm-collect --dashboard dora-metrics-proxy --dashboard loop-health
```

Output per dashboard: `screenshots/`, `dom/`, `api/`, `timing.json`, `meta.json`

# Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `OPENOBSERVE_URL` | `http://localhost:5080` | OO base URL |
| `OPENOBSERVE_USER` | `admin@dev-loop.local` | Login username |
| `OPENOBSERVE_PASS` | `devloop123` | Login password |
| `OPENOBSERVE_ORG` | `default` | OO organization |
| `DM_OUTPUT` | `./output` | Output directory |
| `DM_CONFIG_DIR` | `~/dev-loop/config/dashboards` | Source config directory |
| `DM_ALERTS_CONFIG` | `~/dev-loop/config/alerts/rules.yaml` | Source alert rules YAML |

# Typical Flow

```bash
cd ~/dashboard-mirror
uv run dm-collect-all                # Full pipeline (~4-6 min)
# OR for API-only (no screenshots):
uv run dm-collect-all --skip-playwright  # ~30-40s
```
