# Output Structure

```
output/
├── _baseline/
│   ├── stream-schema.json         ← All OO columns, types, samples
│   ├── cross-dashboard-map.json   ← Metrics in 2+ dashboards
│   └── baseline-report.md         ← Baseline agent output
│
├── <dashboard-slug>/
│   ├── screenshots/               ← full-page.png, viewport-*.png, panel-*.png
│   ├── screenshots-1h/            ← Same at 1h time range
│   ├── screenshots-7d/            ← Same at 7d time range
│   ├── dom/
│   │   ├── text-content.json      ← Panel text, legends, axes
│   │   ├── layout-metrics.json    ← Pixel dims, grid coords
│   │   └── chart-data.json        ← SVG/canvas data, colors
│   ├── api/
│   │   ├── queries-executed.json  ← Intercepted search queries + results
│   │   └── errors.json            ← Console errors/warnings
│   ├── config/
│   │   ├── source.json            ← Raw config
│   │   ├── transformed.json       ← After import script
│   │   ├── sent.json              ← POST payload to OO
│   │   ├── stored.json            ← What OO returns
│   │   └── chain-diff.txt         ← Unified diffs
│   ├── timing.json                ← Per-panel load times
│   ├── meta.json                  ← Panel count, URL, timestamp
│   ├── analyst-structure.md       ← Analyst A output
│   ├── analyst-data.md            ← Analyst B output
│   ├── analyst-ux.md              ← Analyst C output
│   └── grounding.md               ← Final grounding document
```
