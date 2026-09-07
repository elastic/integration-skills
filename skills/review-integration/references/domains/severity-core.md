# Shared severity and package calibration

This is the canonical shared rubric for standalone and hosted reviewers. Load it
once, then use the domain references selected by the existing skill routing table
or by the host. Domain-specific rules and explicit new-versus-existing exceptions
take precedence over the broad severity examples below.

## Severity definitions

**CRITICAL**: Broken functionality, security vulnerabilities (hardcoded secrets, leaked credentials), missing required files that cause elastic-package build/lint/check failures, infinite loops (pagination without termination, want_more true on error paths).

**HIGH**: Quality standard violations that should be fixed before merge -- missing error handling, wrong ECS categorization values, no test coverage, prohibited patterns (event.ingested in pipeline, preserve_duplicate_custom_fields, trailing event.original remove), missing ASN enrichment alongside geo enrichment, secrets not redacted, version compatibility violations.

**MEDIUM**: Suboptimal patterns that should be fixed when possible -- .as() nesting depth 6-7, set instead of rename for ECS mapping, missing grok anchoring, wrong Mustache syntax (double braces instead of triple), missing edge case coverage, documentation gaps, tracer at wrong level.

**LOW**: Style issues and minor improvements -- variable naming, field description wording, sprintf vs concatenation preference, informational notes about first-version leniency.

## New versus existing packages

Read the package's `changelog.yml`:
- **One entry** (version `0.0.1` or `1.0.0`): this is a new package. Apply new-package standards.
- **Multiple entries**: this is an existing package. Apply the existing-package adjustments in the relevant domain rubric.

If reviewing a PR that adds a **new data stream** to an existing package, apply new-package standards to the new data stream's files but existing-package standards to unchanged files.

Use the new/existing adjustments in the relevant domain rubric. Version-related
standards live with the fields and package-structure rubrics, not in a second
table in the skill entrypoint.

"Could be newer" or "below current standard" is not sufficient evidence of a
compatibility defect. Verify the required feature, configuration option, field,
or mismatch instead of inferring a failure from age alone.
