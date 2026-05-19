# Conflict resolutions

Build skills (loaded in Step 3) are prescriptive — they teach the current recommended way to build integrations. The review skill must accept a broader range of valid patterns, including older approaches that predate current standards. This file documents where the review interpretation diverges from the build prescription and why.

## state.with() absence

**Conflict**: The `cel-programs` skill teaches `state.with()` as the standard pattern for state construction. Review guidance historically rated its absence as HIGH.

**Resolution**: `state.with()` is the recommended pattern for new code, but if a program constructs a complete state map without it, this is valid. Only flag as HIGH if state construction is incomplete (missing cursor, missing want_more, missing events).

## ECS field declarations vs dynamic mapping

**Conflict**: The `ecs-field-mappings` skill says pipeline fields must be declared in `fields/ecs.yml`. But standard ECS keyword/date fields work via dynamic mapping and don't require explicit `external: ecs` declarations.

**Resolution**: Only flag when the field type genuinely requires explicit declaration (geo_point, geo_shape, nested, flattened) or when `elastic-package` would fail validation. Standard keyword/date ECS fields are not findings.

## rate_limit() in CEL programs

**Conflict**: The `cel-programs` skill says "Do NOT implement rate limiting in the CEL program" and directs authors to use YAML-level `resource.rate_limit.*` instead. But many existing integrations call `rate_limit()` directly in the program, and this is a valid, functioning pattern.

**Resolution**: Do not flag `rate_limit()` usage in existing integrations. Only flag when ALL of: (1) API docs show rate limit headers, (2) the integration does not handle rate limiting at all, (3) `rate_limit()` is called with incorrect arguments. Ignoring the return value is valid. From v9.3.0, the return no longer needs to be placed in state for the limit to be applied.

## Build-skill authoring process vs product correctness

**Conflict**: Build skills include both runtime requirements and authoring-process guidance. Runtime requirements (e.g., mito compatibility — mito is the library Elastic CEL programs execute on, not generic CEL) are product correctness concerns. Authoring-process rules (e.g., "write no more than 10-15 lines before testing," reference loading order, incremental development methodology) guide how to produce code, not what correct code looks like.

**Resolution**: Runtime requirements from build skills are valid review concerns — a CEL program that doesn't work on mito is defective. Authoring methodology and workflow sequencing are not review findings. Review evaluates the product artifact, not how it was produced.
