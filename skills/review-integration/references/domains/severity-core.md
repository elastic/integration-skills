# Severity rubric -- shared core

> **Not for single-pass reviews.** This file exists for reviewers that own
> a single domain within a larger, domain-split review. If you are running
> the `review-integration` skill end to end, read `../severity-rubric.md` instead --
> it is the authoritative copy.

Severity definitions and calibration shared by every domain reviewer. A
domain-scoped reviewer reads this file plus the `rubric.md` for its own
domain; a single-pass review reads `references/severity-rubric.md`
instead, which carries the same content whole.

> **Maintenance:** this file mirrors the definitions and calibration notes
> in `../severity-rubric.md`. A PR that changes a definition or note must
> change both files in the same PR.

## Severity definitions

**CRITICAL**: Broken functionality, security vulnerabilities (hardcoded secrets, leaked credentials), missing required files that cause elastic-package build/lint/check failures, infinite loops (pagination without termination, want_more true on error paths).

**HIGH**: Quality standard violations that should be fixed before merge -- missing error handling, wrong ECS categorization values, no test coverage, prohibited patterns (event.ingested in pipeline, preserve_duplicate_custom_fields, trailing event.original remove), missing ASN enrichment alongside geo enrichment, secrets not redacted, version compatibility violations.

**MEDIUM**: Suboptimal patterns that should be fixed when possible -- .as() nesting depth 6-7, set instead of rename for ECS mapping, missing grok anchoring, wrong Mustache syntax (double braces instead of triple), missing edge case coverage, documentation gaps, tracer at wrong level.

**LOW**: Style issues and minor improvements -- variable naming, field description wording, sprintf vs concatenation preference, informational notes about first-version leniency.

## Domain-specific calibration

These severities apply to **new packages**. For existing packages, see the "Reviewing new vs existing integrations" section in `review-integration/SKILL.md` for adjustments.

> **Note:** "Could be newer" or "below current standard" is never a finding by itself. Only flag version fields when a feature in the package requires a higher version than declared.
