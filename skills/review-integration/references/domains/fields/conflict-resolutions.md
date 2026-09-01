# Conflict resolutions -- fields domain

> **Not for single-pass reviews.** This file is one domain's slice of
> `../../conflict-resolutions.md`, written for a reviewer that owns only
> this domain within a larger, domain-split review. If you are running the
> `review-integration` skill end to end, read the monolith instead -- it
> carries every entry and is the authoritative copy.

Read `../conflicts-core.md` first: it carries the build-skill preamble and
the conflicts that apply to every domain.

The fields domain has no conflict entries of its own. Its one live
conflict, "ECS field declarations vs dynamic mapping", is cross-domain and
lives in `../conflicts-core.md`: the fields reviewer judges the
declarations in `fields/ecs.yml`, the pipeline reviewer judges the fields
its pipelines set. Apply the core resolution as written.

> **Maintenance:** this file holds pointers only. Rule text lives in
> `../conflicts-core.md` and `../../conflict-resolutions.md`.
