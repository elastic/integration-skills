# Severity rubric — dashboard

Apply the [shared severity guidance](../severity-core.md) and
[shared conflict resolutions](../conflicts-core.md).

Dashboard-specific rules live in the `dashboard-review` skill's
`references/review-procedure.md` and the `dashboard-guidelines` skill. This
file gives severities only; the rules themselves stay in those skills.

Severities for the Kibana 9.x checks in `dashboard-review/SKILL.md`:

| Finding | Severity |
|---------|----------|
| Dashboards API request body committed in `kibana/dashboard/` instead of a saved object | HIGH |
| ES\|QL `FROM` hard-codes a namespace (for example `-default`) | HIGH |
| ES\|QL-sourced control values (`values_source: esql`) on a package whose Kibana floor is below 9.5 -- the controls are silently dropped | MEDIUM |
| ES\|QL metric trend background on a package whose Kibana floor is below 9.5, or below 9.6 when the trendline layer is not stored (no time filter in the query) -- cosmetic only | LOW |
| Gradient area fill on a package whose Kibana floor is below 9.6 -- ignored, cosmetic only | LOW |
| All-ES\|QL dashboard with `lens` panels and no dashboard-level `data_stream.dataset` filter (fails `SVR00002`), or a new `SVR00002` exclusion without a documented reason | MEDIUM |
| All-ES\|QL dashboard with `vis` panels and no dashboard-level `data_stream.dataset` filter (passes CI, unscoped) | LOW |
| New dashboard title does not follow `[<Logs\|Metrics> <Package>] <Name>` (or `[<Product> OTel] <Name>` in OTel content packages) | LOW |
| New dashboard on a 9.4+ package without a description, or without sections at roughly 6+ visualization panels | LOW |
