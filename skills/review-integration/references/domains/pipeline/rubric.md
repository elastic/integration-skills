# Severity rubric -- pipeline domain

> **Not for single-pass reviews.** This file is one domain's slice of
> `../../severity-rubric.md`, written for a reviewer that owns only this
> domain within a larger, domain-split review. If you are running the
> `review-integration` skill end to end, read the monolith instead -- it
> carries every domain's rows and is the authoritative copy.

Severity definitions and the new-vs-existing calibration note live in
`../severity-core.md`. Read that file first, then the rows below.
Conflicts for this domain: `../conflicts-core.md` plus
`conflict-resolutions.md` in this directory.

> **Maintenance:** these rows mirror the pipeline rows in
> `../../severity-rubric.md`. A PR that changes a row must change both
> files in the same PR.

## Universal rules (same severity regardless of package age)

| Domain | Finding | Severity |
|--------|---------|----------|
| Pipeline | event.ingested set in pipeline | HIGH |
| Pipeline | Trailing remove of event.original PRESENT (deprecated pattern; never ask for one to be added) | HIGH |
| Pipeline | Double-brace Mustache instead of triple | MEDIUM |
| Pipeline | Unanchored grok pattern | MEDIUM |

## Rules with new-vs-existing severity adjustment

| Domain | Finding | New package | Existing package |
|--------|---------|------------|-----------------|
| Pipeline | Missing pipeline-level on_failure | HIGH | Missing entirely: HIGH. Wrong structure/order: LOW |
| Pipeline | preserve_duplicate_custom_fields tag | HIGH | MEDIUM (technical debt; was officially recommended before deprecation) |
| Pipeline | Missing processor tag | MEDIUM | LOW (only enforced from format_version 3.6.0) |
| Pipeline | CEL-only opening processors (`remove_agentless_tags` + terminate) missing on a NEW CEL stream in an agentless-enabled package (`deployment_modes.agentless.enabled: true`), or where sibling pipelines already carry the block | MEDIUM | LOW at most (Agentless-era additions; pre-Agentless integrations don't have them — absence there is not a finding) |
| Pipeline | JSE00001 pattern differs from current standard | HIGH | MEDIUM (if event.original is preserved by alternate means) |
| Pipeline | Geo enrichment without ASN companion | HIGH | MEDIUM (newer standard) |

## ECS field declarations

Judge the fields a pipeline sets against the "ECS field declarations"
section in `../fields/rubric.md`.
