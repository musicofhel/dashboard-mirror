# Environment & Commands

## Quick Reference

| Command | Purpose | Time |
|---|---|---|
| `uv run dm-health` | OO instance health + config | ~2s |
| `uv run dm-schema` | Fetch OO stream schemas | ~10s |
| `uv run dm-alerts` | Capture alert configs + drift check | ~5s |
| `uv run dm-functions` | Capture functions & pipelines | ~3s |
| `uv run dm-traces` | Deep trace structure analysis | ~15s |
| `uv run dm-supplementary` | Views, reports, annotations, folders | ~5s |
| `uv run dm-chain` | Trace config transformations | ~5s |
| `uv run dm-collect` | Full Playwright mirror capture | ~3-5 min |
| `uv run dm-collect-all` | Run ALL collectors in sequence | ~4-6 min |

## Environment Variables

| Variable | Default |
|---|---|
| `OPENOBSERVE_URL` | `http://localhost:5080` |
| `OPENOBSERVE_USER` | `admin@dev-loop.local` |
| `OPENOBSERVE_PASS` | `devloop123` |
| `OPENOBSERVE_ORG` | `default` |
| `DM_OUTPUT` | `./output` |
| `DM_CONFIG_DIR` | `~/dev-loop/config/dashboards` |
| `DM_ALERTS_CONFIG` | `~/dev-loop/config/alerts/rules.yaml` |

## Prompt Templates

All in `prompts/`:
- `baseline.md` — baseline cross-dashboard validation
- `analyst-structure.md` — layout, sizing, config drift
- `analyst-data.md` — queries, schema, labels, time ranges
- `analyst-ux.md` — readability, errors, chart fitness
- `synthesizer.md` — grounding document synthesis
