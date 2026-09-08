# Severity rubric — input

Canonical review guidance for standalone and hosted reviewers. Apply the
[shared definitions and calibration](../severity-core.md) and
[shared conflict resolutions](../conflicts-core.md).
Also read the [relevant conflict resolutions](conflict-resolutions.md).

CEL-specific rows apply only when a CEL input is in scope.

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

## Additional review exceptions

The following exceptions apply to CEL inputs.

- `max_executions` in CEL — defaults to 1000 if not specified. Do not flag its absence.
- CEL error shape: single-object `{"events": {"error": {...}}}` is intentional —
  it signals retry/halt semantics where the agent handles cursor. Do NOT flag this
  as 'cursor lost'. The single-object shape is the correct pattern for non-recoverable errors.
