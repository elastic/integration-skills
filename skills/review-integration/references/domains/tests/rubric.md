# Severity rubric -- tests domain

> **Not for single-pass reviews.** This file is one domain's slice of
> `../../severity-rubric.md`, written for a reviewer that owns only this
> domain within a larger, domain-split review. If you are running the
> `review-integration` skill end to end, read the monolith instead -- it
> carries every domain's rows and is the authoritative copy.

Severity definitions and the new-vs-existing calibration note live in
`../severity-core.md`. Read that file first, then the rows below.
Conflicts for this domain: core only (`../conflicts-core.md`); there is no
tests-specific conflict file.

> **Maintenance:** these rows mirror the tests rows in
> `../../severity-rubric.md`. A PR that changes a row must change both
> files in the same PR.

## Universal rules (same severity regardless of package age)

| Domain | Finding | Severity |
|--------|---------|----------|
| Tests | No pipeline test fixtures | HIGH |
| Tests | Missing test-common-config.yml | HIGH |

## Rules with new-vs-existing severity adjustment

| Domain | Finding | New package | Existing package |
|--------|---------|------------|-----------------|
| Tests | source.geo in dynamic_fields | MEDIUM | LOW (acceptable workaround if version bump not in scope) |
