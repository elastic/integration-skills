# Severity rubric -- fields domain

> **Not for single-pass reviews.** This file is one domain's slice of
> `../../severity-rubric.md`, written for a reviewer that owns only this
> domain within a larger, domain-split review. If you are running the
> `review-integration` skill end to end, read the monolith instead -- it
> carries every domain's rows and is the authoritative copy.

Severity definitions and the new-vs-existing calibration note live in
`../severity-core.md`. Read that file first, then the rows below.
Conflicts for this domain: `../conflicts-core.md` plus
`conflict-resolutions.md` in this directory.

> **Maintenance:** these rows mirror the fields rows in
> `../../severity-rubric.md`. A PR that changes a row must change both
> files in the same PR.

## Universal rules (same severity regardless of package age)

| Domain | Finding | Severity |
|--------|---------|----------|
| Fields | Pipeline field not in ecs.yml (non-dynamic-mapped type) | HIGH |
| Fields | Wrong field type | HIGH |
| Fields | Missing field description | LOW |
| Fields | build.yml ECS pin mismatches pipeline ecs.version | HIGH |

## Rules with new-vs-existing severity adjustment

| Domain | Finding | New package | Existing package |
|--------|---------|------------|-----------------|
| Fields | base-fields.yml wrong entry count | HIGH | MEDIUM (verify minimum entries present) |
| Fields | beats.yml absent | HIGH (file-based inputs) | MEDIUM for file-based; N/A for CEL/HTTPJSON |

## ECS field declarations

- Only flag missing `external: ecs` declarations when `elastic-package` would fail validation or the field type genuinely requires it (e.g., `geo_point`, `geo_shape`, `nested`, `flattened`)
- Standard keyword/date ECS fields that work via dynamic mapping do NOT need explicit declaration — do not flag their absence
