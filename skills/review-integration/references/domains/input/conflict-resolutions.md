# Conflict resolutions — input

Canonical review exceptions for standalone and hosted reviewers. Read the
[shared conflict resolutions](../conflicts-core.md) first.

## state.with() absence

**Conflict**: The `cel-programs` skill teaches `state.with()` as the standard pattern for state construction. Review guidance historically rated its absence as HIGH.

**Resolution**: `state.with()` is the recommended pattern for new code, but if a program constructs a complete state map without it, this is valid. Only flag as HIGH if state construction is incomplete (missing cursor, missing want_more, missing events).

## rate_limit() in CEL programs

**Conflict**: The `cel-programs` skill says "Do NOT implement rate limiting in the CEL program" and directs authors to use YAML-level `resource.rate_limit.*` instead. But many existing integrations call `rate_limit()` directly in the program, and this is a valid, functioning pattern.

**Resolution**: Do not flag `rate_limit()` usage in existing integrations. Only flag when ALL of: (1) API docs show rate limit headers, (2) the integration does not handle rate limiting at all, (3) `rate_limit()` is called with incorrect arguments. Ignoring the return value is valid. From v9.3.0, the return no longer needs to be placed in state for the limit to be applied.

## Additional review exceptions

The following exceptions apply to CEL inputs.

- CEL `state.with()` **merges** keys into state — keys not in the map are preserved.
  Do NOT claim cursor is lost on error paths unless the error path explicitly sets
  `cursor` to null. Omitting `cursor` from the map preserves the previous value.
