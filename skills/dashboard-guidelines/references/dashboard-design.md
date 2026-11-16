# dashboard-design

Layout and chart rules for integration dashboards on Kibana 9.4+. They follow
the design guidance of the `kibana-dashboards` skill in `elastic/agent-skills`,
adapted for packages: titles follow the package naming convention, queries are
scoped to the package's data streams, and settings are limited by the package's
Kibana floor (see `../SKILL.md`).

## Layout

- 48-column grid. Use widths that divide 48. Fill rows left to right; panels in
  a row share the same height; `x + w ≤ 48`.
- Aim for 8–12 panels in the first 20–24 rows (what is visible on open).
- Kibana compacts panels upward, so blank rows do not survive. Separate groups
  with sections, not gaps.
- Panels inside a section use coordinates relative to that section.

| Panel | Width (`w`) | Height (`h`) |
|---|---|---|
| Metric | 6, 8 or 12 | 5–6 |
| Gauge | 12 | 8 |
| XY, heatmap, tag cloud | 24 (48 for the primary time series) | 10 |
| Treemap / waffle / mosaic | 24 | 10 |
| Pie / donut | 12 | 10 |
| Markdown | 24–48 | 4–9 |
| Data table | 24–48 | 12–16 |

Never make a metric or gauge full width.

## Sections

Use collapsible sections when a dashboard has roughly 6 or more visualization
panels. Each section holds only panels that match its purpose. A typical
security dashboard:

1. Key metrics — 4–6 metric tiles (totals, critical/high counts, open items)
2. Trends over time — the primary time series, then a breakdown over time
3. Breakdowns and distributions — by severity, status, category, source
4. Domain section — for example MITRE ATT&CK coverage, CVEs, affected packages
5. Resources and context — accounts, regions, hosts, users, top-N tables

## Controls

Add 3–5 options-list controls for the fields users filter by most. On a 9.4
floor, back them with a data view field. ES|QL-sourced control values need 9.5
(see `../SKILL.md`).

## Charts

- Pick the chart for the question: time series for trends, horizontal bars for
  ranked categories, pies only for fewer than about 7 slices, tables for top-N
  detail with several columns.
- No panel title on metric, gauge, tag cloud and waffle panels. Elsewhere use a
  self-explanatory title and hide axis titles; do not repeat the same
  information in title, axes and labels.
- Show a legend (bottom, list layout) on charts with a breakdown or more than
  one series; hide it on single-series charts.
- Use natural units (percent, bytes, duration) when the field has one; leave
  plain counts unformatted.
- Use default palettes. Add color only where it carries meaning, and keep the
  same color for the same category across charts.
- Data tables: sort by the measure, limit rows (top 10/20), and say so in the
  title ("Top 20 CVEs by count").

## ES|QL patterns

Always read the package's data streams with a namespace wildcard:

```esql
FROM logs-<package>.<dataset>-*
| STATS `Total findings` = COUNT()
```

Time series bucketed on the dashboard time range (`?_tstart` / `?_tend` are
supplied by Kibana):

```esql
FROM logs-<package>.<dataset>-*
| WHERE @timestamp <= ?_tend AND @timestamp > ?_tstart
| STATS `Findings` = COUNT() BY BUCKET(@timestamp, 75, ?_tstart, ?_tend)
```

Ranked breakdown:

```esql
FROM logs-<package>.<dataset>-*
| STATS `Findings` = COUNT() BY `Severity` = <package>.<dataset>.severity
| SORT `Findings` DESC
| LIMIT 10
```

Name output columns with readable aliases; chart axes and table headers use
them. Before committing, run each query against test data, replacing
`?_tstart` / `?_tend` with fixed expressions such as `NOW() - 7 days`.

Every field a query references must be declared in the package's
`fields/*.yml` or be an ECS field the pipeline sets.
