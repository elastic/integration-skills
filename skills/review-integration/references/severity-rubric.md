# Severity rubric

This file is the authoritative rubric and is complete on its own -- reading
it is all a review needs. Do not also load the fragments under `domains/`;
they are a per-domain split of this same content, for callers that dispatch
one reviewer per domain.

> **Maintenance:** the fragments under `domains/` mirror this file. A PR
> that changes a rule here must update the matching fragment in the same
> PR, and vice versa.

## Severity definitions

**CRITICAL**: Broken functionality, security vulnerabilities (hardcoded secrets, leaked credentials), missing required files that cause elastic-package build/lint/check failures, infinite loops (pagination without termination, want_more true on error paths).

**HIGH**: Quality standard violations that should be fixed before merge -- missing error handling, wrong ECS categorization values, no test coverage, prohibited patterns (event.ingested in pipeline, preserve_duplicate_custom_fields, trailing event.original remove), missing ASN enrichment alongside geo enrichment, secrets not redacted, version compatibility violations.

**MEDIUM**: Suboptimal patterns that should be fixed when possible -- .as() nesting depth 6-7, set instead of rename for ECS mapping, missing grok anchoring, wrong Mustache syntax (double braces instead of triple), missing edge case coverage, documentation gaps, tracer at wrong level.

**LOW**: Style issues and minor improvements -- variable naming, field description wording, sprintf vs concatenation preference, informational notes about first-version leniency.

## Domain-specific calibration

These severities apply to **new packages**. For existing packages, see the "Reviewing new vs existing integrations" section in `review-integration/SKILL.md` for adjustments.

> **Note:** "Could be newer" or "below current standard" is never a finding by itself. Only flag version fields when a feature in the package requires a higher version than declared.

### Universal rules (same severity regardless of package age)

| Domain | Finding | Severity |
|--------|---------|----------|
| Pipeline | event.ingested set in pipeline | HIGH |
| Pipeline | Trailing remove of event.original PRESENT (deprecated pattern; never ask for one to be added) | HIGH |
| Pipeline | Double-brace Mustache instead of triple | MEDIUM |
| Pipeline | Unanchored grok pattern | MEDIUM |
| CEL | want_more true on error path | CRITICAL |
| CEL | No pagination termination | CRITICAL |
| CEL | Handlebars in program block | CRITICAL |
| CEL | Secrets not in redact.fields | HIGH |
| CEL | Verify error shape matches intended recovery behavior | MEDIUM |
| CEL | .as() depth exceeds 5 (hard cap) | HIGH |
| CEL | Single-use .as() binding | LOW |
| Fields | Pipeline field not in ecs.yml (non-dynamic-mapped type) | HIGH |
| Fields | Wrong field type | HIGH |
| Fields | Missing field description | LOW |
| Fields | build.yml ECS pin mismatches pipeline ecs.version | HIGH |
| Manifest | format_version too low for features used | HIGH |
| Manifest | conditions.kibana.version too low for agent features used | HIGH |
| Manifest | Data stream duplicates root manifest fields | MEDIUM |
| Tests | No pipeline test fixtures | HIGH |
| Tests | Missing test-common-config.yml | HIGH |
| Input | Hardcoded credentials | CRITICAL |
| Input | Hardcoded URL | MEDIUM |
| Input | Missing forwarded/disable_host coupling | MEDIUM |

### Rules with new-vs-existing severity adjustment

| Domain | Finding | New package | Existing package |
|--------|---------|------------|-----------------|
| Pipeline | Missing pipeline-level on_failure | HIGH | Missing entirely: HIGH. Wrong structure/order: LOW |
| Pipeline | preserve_duplicate_custom_fields tag | HIGH | MEDIUM (technical debt; was officially recommended before deprecation) |
| Pipeline | Missing processor tag | MEDIUM | LOW (only enforced from format_version 3.6.0) |
| Pipeline | CEL-only opening processors (`remove_agentless_tags` + terminate) missing on a NEW CEL stream in an agentless-enabled package (`deployment_modes.agentless.enabled: true`), or where sibling pipelines already carry the block | MEDIUM | LOW at most (Agentless-era additions; pre-Agentless integrations don't have them — absence there is not a finding) |
| Pipeline | JSE00001 pattern differs from current standard | HIGH | MEDIUM (if event.original is preserved by alternate means) |
| Pipeline | Geo enrichment without ASN companion | HIGH | MEDIUM (newer standard) |
| Fields | base-fields.yml wrong entry count | HIGH | MEDIUM (verify minimum entries present) |
| Fields | beats.yml absent | HIGH (file-based inputs) | MEDIUM for file-based; N/A for CEL/HTTPJSON |
| Tests | source.geo in dynamic_fields | MEDIUM | LOW (acceptable workaround if version bump not in scope) |
| Changelog | Changelog link does not point at the PR or issue that introduces the change (a placeholder was left in; there is no placeholder value to match on -- see `conflict-resolutions.md`) | Informational note only (first-version leniency) | LOW (`check_changelog_entries.sh` enforces this on every link the PR adds; flag only what that check cannot see -- an entry this PR did not touch, or a review with no PR context) |

## ECS field declarations

- Only flag missing `external: ecs` declarations when `elastic-package` would fail validation or the field type genuinely requires it (e.g., `geo_point`, `geo_shape`, `nested`, `flattened`)
- Standard keyword/date ECS fields that work via dynamic mapping do NOT need explicit declaration — do not flag their absence
