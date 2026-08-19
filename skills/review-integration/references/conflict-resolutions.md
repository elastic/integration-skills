# Conflict resolutions

Build skills (loaded in Step 3) are prescriptive — they teach the current recommended way to build integrations. The review skill must accept a broader range of valid patterns, including older approaches that predate current standards. This file documents where the review interpretation diverges from the build prescription and why.

## state.with() absence

**Conflict**: The `cel-programs` skill teaches `state.with()` as the standard pattern for state construction. Review guidance historically rated its absence as HIGH.

**Resolution**: `state.with()` is the recommended pattern for new code, but if a program constructs a complete state map without it, this is valid. Only flag as HIGH if state construction is incomplete (missing cursor, missing want_more, missing events).

## ECS field declarations vs dynamic mapping

**Conflict**: The `ecs-field-mappings` skill says pipeline fields must be declared in `fields/ecs.yml`. But standard ECS keyword/date fields work via dynamic mapping and don't require explicit `external: ecs` declarations.

**Resolution**: On packages whose `conditions.kibana.version` floor is >= 8.13.0, only flag when the field type genuinely requires explicit declaration (`geo_point` on non-standard parent prefixes, `geo_shape`, `nested`, `flattened`) or when `elastic-package` would fail validation — standard keyword/date and standard-prefix geo ECS fields are not findings. If the constraint admits stacks below 8.13 (which never apply `ecs@mappings`, regardless of package-spec version), pipeline-set ECS fields still need declarations.

## rate_limit() in CEL programs

**Conflict**: The `cel-programs` skill says "Do NOT implement rate limiting in the CEL program" and directs authors to use YAML-level `resource.rate_limit.*` instead. But many existing integrations call `rate_limit()` directly in the program, and this is a valid, functioning pattern.

**Resolution**: Do not flag `rate_limit()` usage in existing integrations. Only flag when ALL of: (1) API docs show rate limit headers, (2) the integration does not handle rate limiting at all, (3) `rate_limit()` is called with incorrect arguments. Ignoring the return value is valid. From v9.3.0, the return no longer needs to be placed in state for the limit to be applied.

## Build-skill authoring process vs product correctness

**Conflict**: Build skills include both runtime requirements and authoring-process guidance. Runtime requirements (e.g., mito compatibility — mito is the library Elastic CEL programs execute on, not generic CEL) are product correctness concerns. Authoring-process rules (e.g., "write no more than 10-15 lines before testing," reference loading order, incremental development methodology) guide how to produce code, not what correct code looks like.

**Resolution**: Runtime requirements from build skills are valid review concerns — a CEL program that doesn't work on mito is defective. Authoring methodology and workflow sequencing are not review findings. Review evaluates the product artifact, not how it was produced.

## geoip/user_agent if-guards vs ignore_missing

**Conflict**: The pipeline review checklist historically demanded an `if` existence guard on geoip and user_agent processors, while the `ingest-pipelines` canonical examples historically showed bare `ignore_missing: true` (the geoip examples now carry the guard). Many shipped integrations follow the older unguarded pattern.

**Resolution**: The guard is a performance improvement, not a correctness rule. New pipelines should guard geoip (the expensive database-lookup case) — flag MEDIUM. Missing guards on geoip in existing pipelines are not findings. user_agent never requires the guard; bare `ignore_missing: true` is always acceptable there.

## First-version leniency

**Conflict**: Strict changelog-link and asset rules would flag every first-version package for placeholders that are expected during initial development.

**Resolution**: For first-version packages (`0.0.1`/`1.0.0` with a single changelog entry), placeholder changelog links and placeholder logos/icons are informational notes only, not findings. The sanctioned development placeholder is `pull/99999` — `elastic-package lint` REJECTS `pull/0`, so never grant leniency to that value. Review tooling and CI keep flagging any placeholder link until it is replaced with the real PR link before merge; that is expected behavior, not noise.
