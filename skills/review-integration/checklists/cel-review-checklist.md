# CEL review checklist

Severity-tagged checklist for reviewing CEL input programs. Use for self-review before submitting a PR, or for formal review. Items are grouped by domain. For systematic version compatibility verification, load the `review-integration` skill's version check references.

## Structure

- [ ] `interval: {{interval}}` uses Handlebars variable, not hardcoded -- **HIGH** if hardcoded
- [ ] Request tracer path matches input type: `../../logs/cel/http-request-trace-*.ndjson`. Two formats: conditional `{{#if enable_request_tracer}}` (any version) or block `resource.tracer:` with `enabled:` field (v8.15.0+). Tracer should be at data stream level, not input level -- **MEDIUM** if wrong path or wrong level
- [ ] `state` initializes all fields the program reads -- **HIGH** if program reads uninitialized state
- [ ] `redact.fields` lists every secret key in state. Use `redact.fields: ~` if none. Cross-check against any `secret_fields` in manifest -- **HIGH** if secrets not redacted
- [ ] `max_executions` defaults to 1000 if not specified. Only flag if the default is inappropriate for the specific API (e.g., API with known infinite pagination bugs). Do NOT flag absence as a routine finding -- **LOW** if missing with no evidence of need

## State and cursor

- [ ] `want_more` is explicitly set on ALL execution paths (success, error, empty response, pagination complete) -- **HIGH** if any path omits want_more
- [ ] `want_more` derives from API response (next cursor present, has_more field, etc.), NOT from `size(events) > 0` or event count -- **HIGH** if gated on event count (causes missed pages)
- [ ] Cursor values only persist when at least one event is published. If empty pages with new cursors are expected, emit a placeholder event and drop it in the pipeline -- **MEDIUM** if empty-page cursor scenario not handled
- [ ] Optional access patterns: use `.?field`, `.orValue(default)`, `has(obj.field)` for fields that may be absent -- **MEDIUM** if direct access on optional fields
- [ ] On error paths, cursor handling must match the error shape:
  - Single-object `{"events": {"error": {...}}}` — cursor is intentionally NOT preserved (agent retries from last known good state). Do NOT flag cursor absence here.
  - Array `{"events": [{"error": {...}}]}` — cursor MUST be preserved (event indexed, processing continues). **HIGH** if cursor lost with array error shape.

## Error handling

- [ ] HTTP status code checked after every request (`resp.StatusCode != 200` or similar) -- **HIGH** if no status check
- [ ] Error shape: single-object `{"events": {"error": {"code": "...", "id": "...", "message": "..."}}, "want_more": false}` = retry/halt semantics (cursor deleted, agent retries). Array `{"events": [{"error": {"code": "...", "id": "...", "message": "..."}}], "want_more": false}` = advance semantics (cursor preserved, event indexed). Choose shape based on whether the error is recoverable -- **HIGH** if error events use wrong shape for the scenario
- [ ] `want_more` is false on all error paths -- **CRITICAL** if want_more true on error (causes infinite error loop)

## Pagination

- [ ] Pagination terminates: there must be a condition that sets `want_more: false` (empty response, no next cursor, max page reached) -- **CRITICAL** if no termination condition
- [ ] Pagination continuation uses API response fields (next_cursor, has_more, etc.), not event count -- **HIGH** if `want_more: size(events) > 0`
- [ ] For timestamp-based cursors, cursor defaults use `now` global for upper bound, not `now()` function -- **MEDIUM** if using `now()` (unstable within evaluation)

## Authentication transport

- [ ] Config-level auth (`auth.oauth2`, `auth.digest`, `auth.aws`, `auth.file`, `auth.custom`) applies to direct HTTP calls (`get()`, `post()`) AND `do_request()` calls
- [ ] If using `do_request()` with `auth.basic` or `auth.token` config: these are NOT applied to `do_request()` calls (only to direct calls). Must set auth headers manually in the request map for `do_request()` -- **HIGH** if relying on config auth that is not applied
- [ ] For new integrations targeting v8.19.0+: prefer `auth.custom` for static Bearer/Token auth over manual header construction -- **LOW** informational

## Type safety

- [ ] All CEL numbers are float64 (IEEE 754 double). Integers >= 10^7 will appear in scientific notation. Integers >= 2^53 lose precision -- **HIGH** if large integer IDs not handled
- [ ] Pipeline must use `convert` processor for fields that need specific types (long, double). CEL delivers everything as JSON numbers which Elasticsearch may interpret differently -- **MEDIUM** if numeric fields lack convert processor
- [ ] String IDs that look numeric (e.g., Snowflake IDs, large event IDs) should be kept as strings in CEL using `.string()` or extracted from the string representation -- **HIGH** if precision-sensitive IDs treated as numbers

## Code quality

- [ ] `.as()` nesting depth does not exceed 5 levels from `state.with()` inward. HTTP core should be 2 levels: `do_request().as(resp, decode_json().as(body, {...}))` inside `state.with()` -- **HIGH** if exceeds 5
- [ ] Cursor defaults and window/time-range bounds extracted as pre-bindings BEFORE `state.with()`, not stacked inside the HTTP chain -- **MEDIUM** if pre-bindings inside HTTP chain
- [ ] Single-use values (e.g., `int(state.batch_size)` used once) are inlined at the call site, not wrapped in their own `.as()` binding -- **LOW**

## Configuration

- [ ] `redact.fields` and `secret_fields` (if present in manifest) are consistent. Every secret in manifest should be redacted in CEL config -- **HIGH** if mismatch
- [ ] No Handlebars `{{` syntax inside the `program:` block. Use `state` to pass manifest variables into the CEL program -- **CRITICAL** if Handlebars in program (breaks CEL compilation)
- [ ] Request tracer: prefer data stream level `enable_request_tracer` variable over input-level. Default value should be `false` -- **MEDIUM** if at wrong level

## Formatting

- [ ] celfmt output is the canonical formatting authority. Do not flag or "fix" formatting that celfmt produces. If unsure about syntax, run `celfmt -agent -i cel.yml.hbs -o cel.yml.hbs` -- informational

## Rate limiting

- [ ] It is valid to call `rate_limit()` and ignore the return value (for logging/diagnostics). Only flag rate limiting issues when: API docs show rate limit headers AND the integration does not handle them AND incorrect arguments are passed to `rate_limit()` -- **MEDIUM** if genuinely wrong, do not over-flag
- [ ] Before v9.3.0: `rate_limit()` return must be placed in `state.rate_limit` for the limit to take effect (next cycle only). From v9.3.0: immediate apply, state placement optional -- **HIGH** if targeting pre-v9.3.0 and return not in state

## Version awareness

If the program uses a function or config option introduced after v8.6.0, verify that `conditions.kibana.version` in the root manifest allows a high enough beats version. See `cel-polymorphic-patterns.md` for version-tagged patterns. For systematic version verification during formal reviews, use the `review-integration` skill's version check references.
