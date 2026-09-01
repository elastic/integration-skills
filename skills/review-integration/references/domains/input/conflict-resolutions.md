# Conflict resolutions -- input domain

> **Not for single-pass reviews.** This file is one domain's slice of
> `../../conflict-resolutions.md`, written for a reviewer that owns only
> this domain within a larger, domain-split review. If you are running the
> `review-integration` skill end to end, read the monolith instead -- it
> carries every entry and is the authoritative copy.

Read `../conflicts-core.md` first: it carries the build-skill preamble and
the conflicts that apply to every domain. The entries below are specific
to the input domain.

> **Maintenance:** these entries mirror the matching entries in
> `../../conflict-resolutions.md`. A PR that changes an entry must change
> both files in the same PR.

## state.with() absence

**Conflict**: The `cel-programs` skill teaches `state.with()` as the standard pattern for state construction. Review guidance historically rated its absence as HIGH.

**Resolution**: `state.with()` is the recommended pattern for new code, but if a program constructs a complete state map without it, this is valid. Only flag as HIGH if state construction is incomplete (missing cursor, missing want_more, missing events).

## rate_limit() in CEL programs

**Conflict**: The `cel-programs` skill says "Do NOT implement rate limiting in the CEL program" and directs authors to use YAML-level `resource.rate_limit.*` instead. But many existing integrations call `rate_limit()` directly in the program, and this is a valid, functioning pattern.

**Resolution**: Do not flag `rate_limit()` usage in existing integrations. Only flag when ALL of: (1) API docs show rate limit headers, (2) the integration does not handle rate limiting at all, (3) `rate_limit()` is called with incorrect arguments. Ignoring the return value is valid. From v9.3.0, the return no longer needs to be placed in state for the limit to be applied.
