# Output Structure

```
output/
├── _baseline/
│   ├── stream-schema.json         ← All OO columns, types, samples
│   ├── cross-dashboard-map.json   ← Metrics in 2+ dashboards
│   ├── alerts.json                ← Alert rule configs from OO (v2 API)
│   ├── alert-history.json         ← Alert firing history
│   ├── alert-incidents.json       ← Active incidents + stats
│   ├── alert-templates.json       ← All alert templates
│   ├── alert-destinations.json    ← Notification destinations with config
│   ├── alert-dedup.json           ← Deduplication config + stats
│   ├── alert-drift.json           ← Source vs live alert diff
│   ├── alert-schema-coverage.json ← Column existence check per alert SQL
│   ├── functions.json             ← VRL functions with analysis
│   ├── pipelines.json             ← Pipeline configs
│   ├── pipeline-streams.json      ← Stream-to-pipeline associations
│   ├── pipeline-history.json      ← Pipeline modification history
│   ├── trace-services.json        ← Service names + span counts
│   ├── trace-operations.json      ← Operation names per service + counts
│   ├── trace-attributes.json      ← Non-null attributes per operation (sample)
│   ├── trace-structure.json       ← Sample trace trees with parent-child validation
│   ├── trace-dag.json             ← Service dependency graphs for sample traces
│   ├── trace-durations.json       ← Duration distributions per operation
│   ├── oo-health.json             ← OO healthz response
│   ├── oo-config.json             ← OO config (noauth) + runtime config (auth)
│   ├── oo-org-settings.json       ← Org settings
│   ├── oo-org-summary.json        ← Org stats (stream counts, data size)
│   ├── oo-cluster.json            ← Cluster info + node list
│   ├── saved-views.json           ← All saved views
│   ├── enrichment-tables.json     ← Enrichment table statuses
│   ├── reports.json               ← All reports
│   ├── annotations.json           ← Per-dashboard annotations
│   ├── folders.json               ← Dashboard + alert folder structure
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
