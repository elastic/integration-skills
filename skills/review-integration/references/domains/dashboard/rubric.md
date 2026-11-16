# Severity rubric — dashboard

Apply the [shared severity guidance](../severity-core.md) and
[shared conflict resolutions](../conflicts-core.md).

Dashboard-specific calibration remains in the `dashboard-review` skill's
`references/review-procedure.md` and the `dashboard-guidelines` skill. Use those
references directly; do not copy their rules into a second rubric here.

Severities for the Kibana 9.x checks in `dashboard-review/SKILL.md`:

| Finding | Severity |
|---------|----------|
| Dashboards API request body committed in `kibana/dashboard/` instead of a saved object | HIGH |
| ES\|QL `FROM` hard-codes a namespace (for example `-default`) | HIGH |
| Setting needs a Kibana version above the package's floor (ES\|QL-sourced control values, ES\|QL metric trend background, gradient area fill) | MEDIUM |
| All-ES\|QL dashboard without a dashboard-level `data_stream.dataset` filter, or a new `SVR00002` exclusion without a documented reason | MEDIUM |
| Dashboard title does not follow `[<Logs\|Metrics> <Package>] <Name>` | LOW |
| New dashboard on a 9.4+ package without a description, or without sections at roughly 6+ visualization panels | LOW |
