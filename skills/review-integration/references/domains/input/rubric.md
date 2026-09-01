# Severity rubric -- input domain

> **Not for single-pass reviews.** This file is one domain's slice of
> `../../severity-rubric.md`, written for a reviewer that owns only this
> domain within a larger, domain-split review. If you are running the
> `review-integration` skill end to end, read the monolith instead -- it
> carries every domain's rows and is the authoritative copy.

Severity definitions and the new-vs-existing calibration note live in
`../severity-core.md`. Read that file first, then the rows below.
Conflicts for this domain: `../conflicts-core.md` plus
`conflict-resolutions.md` in this directory.

The input domain covers every input type. CEL rows are listed under their
own `CEL` domain label, as the monolith does; they apply when a CEL input
is in scope.

> **Maintenance:** these rows mirror the CEL and Input rows in
> `../../severity-rubric.md`. A PR that changes a row must change both
> files in the same PR.

## Universal rules (same severity regardless of package age)

| Domain | Finding | Severity |
|--------|---------|----------|
| CEL | want_more true on error path | CRITICAL |
| CEL | No pagination termination | CRITICAL |
| CEL | Handlebars in program block | CRITICAL |
| CEL | Secrets not in redact.fields | HIGH |
| CEL | Verify error shape matches intended recovery behavior | MEDIUM |
| CEL | .as() depth exceeds 5 (hard cap) | HIGH |
| CEL | Single-use .as() binding | LOW |
| Input | Hardcoded credentials | CRITICAL |
| Input | Hardcoded URL | MEDIUM |
| Input | Missing forwarded/disable_host coupling | MEDIUM |

## Rules with new-vs-existing severity adjustment

No input-domain rows carry a new-vs-existing adjustment today. Rows land
here when they exist in `../../severity-rubric.md`.
