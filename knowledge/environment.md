# Environment & Commands

## Quick Reference

| Command | Purpose | Time |
|---|---|---|
| `uv run dm-schema` | Fetch OO stream schemas | ~10s |
| `uv run dm-chain` | Trace config transformations | ~5s |
| `uv run dm-collect` | Full Playwright mirror capture | ~3-5 min |

## Environment Variables

| Variable | Default |
|---|---|
| `OPENOBSERVE_URL` | `http://localhost:5080` |
| `OPENOBSERVE_USER` | `admin@dev-loop.local` |
| `OPENOBSERVE_PASS` | `devloop123` |
| `OPENOBSERVE_ORG` | `default` |
| `DM_OUTPUT` | `./output` |
| `DM_CONFIG_DIR` | `~/dev-loop/config/dashboards` |

## Prompt Templates

All in `prompts/`:
- `baseline.md` — baseline cross-dashboard validation
- `analyst-structure.md` — layout, sizing, config drift
- `analyst-data.md` — queries, schema, labels, time ranges
- `analyst-ux.md` — readability, errors, chart fitness
- `synthesizer.md` — grounding document synthesis
