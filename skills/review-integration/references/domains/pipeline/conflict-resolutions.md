# Conflict resolutions -- pipeline domain

> **Not for single-pass reviews.** This file is one domain's slice of
> `../../conflict-resolutions.md`, written for a reviewer that owns only
> this domain within a larger, domain-split review. If you are running the
> `review-integration` skill end to end, read the monolith instead -- it
> carries every entry and is the authoritative copy.

Read `../conflicts-core.md` first: it carries the build-skill preamble and
the conflicts that apply to every domain. Among those, "ECS field
declarations vs dynamic mapping" is cross-domain and applies here — the
pipeline reviewer judges the ECS fields its pipelines set against it. The
entry below is specific to the pipeline domain.

> **Maintenance:** this entry mirrors the matching entry in
> `../../conflict-resolutions.md`. A PR that changes it must change both
> files in the same PR.

## geoip/user_agent if-guards vs ignore_missing

**Conflict**: The pipeline review checklist historically demanded an `if` existence guard on geoip and user_agent processors, while the `ingest-pipelines` canonical examples historically showed bare `ignore_missing: true` (the geoip examples now carry the guard). Many shipped integrations follow the older unguarded pattern.

**Resolution**: The guard is a performance improvement, not a correctness rule. New pipelines should guard geoip (the expensive database-lookup case) — flag MEDIUM. Missing guards on geoip in existing pipelines are not findings. user_agent never requires the guard; bare `ignore_missing: true` is always acceptable there.
