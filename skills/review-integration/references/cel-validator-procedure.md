# CEL validator procedure

Review-time validation checks beyond the public checklist. Apply these during every formal CEL PR review.

## celfmt formatting authority

celfmt output is canonical. Never flag formatting that celfmt produces as incorrect. If a reviewer is unsure about CEL syntax or formatting, the correct action is to run celfmt, not to manually reformat. The formatted output IS the standard.

Consequences:
- If the PR's CEL program matches celfmt output, formatting is correct regardless of how it looks.
- If the PR's CEL program differs from celfmt output, request the author run celfmt.
- Do not suggest manual formatting changes that contradict celfmt.

## Type conversion audit

All CEL numbers are IEEE 754 float64:
- Integers >= 10^7 appear in scientific notation in JSON output (e.g., `10000000` becomes `1e+07`)
- Integers with magnitude >= 2^53 (9,007,199,254,740,992) lose integer round-trip precision (both positive and negative)
- This affects any numeric value that passes through `encode_json` or appears in the output event

Check for:
- Large integer IDs (Snowflake IDs, Discord IDs, Twitter/X IDs, Box IDs)
- Timestamps in milliseconds (13-digit epoch values)
- Large counters, sequence numbers, or offsets
- Fields destined for ES `long` or `keyword` mappings

### Pattern table for suspicious type usage

| Pattern | Risk | Action |
|---------|------|--------|
| `int(value)` used as ID | Precision loss if > 2^53 | Flag HIGH if ID can exceed 2^53 |
| Timestamp as int (ms since epoch) | Scientific notation | Flag MEDIUM, recommend string format |
| Counter > 10^7 | Scientific notation in JSON | Flag MEDIUM, ensure pipeline handles it |
| String ID converted to int | Unnecessary precision risk | Flag MEDIUM, keep as string |
| Float arithmetic for currency | Rounding errors | Flag HIGH, recommend integer cents or string |

Recommendation: String IDs should stay strings. Numeric fields that may exceed safe integer range need either string representation in CEL or a convert processor in the ingest pipeline.

## Error shape validation

CEL programs return events to the agent via the `events` field. The shape of the error event determines recovery behavior:

**Object shape (retry semantics):**
```
{"events": {"error": {"code": "...", "id": "...", "message": "error text"}}, "want_more": false}
```
- Cursor is deleted. The agent retries from the last known good cursor on the next evaluation.
- Use for transient errors: HTTP 429, 500, 502, 503, network timeouts.

**Array shape (advance semantics):**
```
{"events": [{"error": {"code": "...", "id": "...", "message": "error text"}}], "want_more": false}
```
- Cursor is preserved. The error event is indexed as a document and the cursor advances.
- Use when the pipeline has a terminate processor that drops error events, or when error events should be visible in the index.

Validation checks:
- Verify the shape matches the intended recovery behavior.
- If the integration has a terminate processor in the ingest pipeline for error events, the CEL program should use array shape so the event reaches the pipeline.
- If the integration wants the agent to retry on transient errors (429, 500), use object shape.
- A program that uses object shape for 4xx client errors (other than 429) is likely a bug -- client errors are not transient and will retry forever.
- Check that `want_more` is set to `false` in error paths.

## secret_fields vs redact cross-check

If the data stream manifest declares `secret: true` for any variable, that variable's value in state must be listed in `redact.fields` in the CEL config.

Procedure:
1. Read the data stream `manifest.yml`. Find all `vars` entries with `secret: true`.
2. Read the CEL config (`cel.yml.hbs`). Find the `redact.fields` list.
3. For each secret variable, verify its state path appears in `redact.fields`.
4. If `redact.fields` is `~` (null/empty), verify that no secret variables exist in state.
5. If a secret variable is in state but not in `redact.fields`, flag it.

Common state paths for secrets:
- `state.header.Authorization` (for auth tokens passed via state)
- `state.api_key`, `state.secret_key`, `state.password`
- Any state field populated from a `secret: true` manifest variable

## Handlebars-in-program detection

The `program: |` block in `cel.yml.hbs` must NOT contain `{{` or `}}` Handlebars template syntax.

Manifest variables should be passed into the initial `state` map via Handlebars in the `state` block, then accessed as `state.*` fields within the CEL program. Handlebars inside the program block causes:
- CEL parse errors when the template renders unexpected types
- Difficulty testing the program outside the integration context
- Security issues if user-controlled values are interpolated into the program text

Detection:
- If `{{` appears inside the `program: |` block: flag as CRITICAL.
- The `state:` block and other config fields may legitimately use `{{` -- only the `program` block is restricted.
- False positive: `{{` inside a CEL string literal that is not Handlebars (extremely rare). Verify by checking if the surrounding context is a Handlebars expression (`{{variable_name}}`).
