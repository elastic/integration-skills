# Conflict resolutions — pipeline

Canonical review exceptions for standalone and hosted reviewers. Read the
[shared conflict resolutions](../conflicts-core.md) first.

## geoip/user_agent if-guards vs ignore_missing

**Conflict**: The pipeline review checklist historically demanded an `if` existence guard on geoip and user_agent processors, while the `ingest-pipelines` canonical examples historically showed bare `ignore_missing: true` (the geoip examples now carry the guard). Many shipped integrations follow the older unguarded pattern.

**Resolution**: The guard is a performance improvement, not a correctness rule. New pipelines should guard geoip (the expensive database-lookup case) — flag MEDIUM. Missing guards on geoip in existing pipelines are not findings. user_agent never requires the guard; bare `ignore_missing: true` is always acceptable there.
