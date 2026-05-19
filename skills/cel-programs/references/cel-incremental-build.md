# Incremental CEL program development

Build CEL programs in phases, validating with mito after each one. Do NOT write the full program before running mito. Do NOT proceed to the next phase until the current phase compiles and evaluates correctly.

This approach prevents the most common failure mode: writing a 200+ line program, getting a cascade of compilation errors, then rewriting from scratch repeatedly.

---

## Syntax anti-patterns — compilation failures

These mistakes cause `failed compilation` errors. They are **never valid CEL** — do not use them under any circumstances.

### Comma rules: terminated vs separated

Map and list **literals** allow a trailing comma after the last element. This works the same as Go — prefer trailing commas when elements are split across lines:

```cel
// Valid — trailing commas in map and list literals
{
  "a": 1,
  "b": 2,
}
[
  "first",
  "second",
]
```

Function and macro **calls** use comma-**separated** arguments. A trailing comma after the last argument is a syntax error:

```cel
// WRONG — trailing comma in function call
request(
  "GET",
  state.url.trim_right("/") + "/api/v1/events",  // <-- syntax error
)

// CORRECT — no trailing comma
request(
  "GET",
  state.url.trim_right("/") + "/api/v1/events"
)
```

The same applies to macros like `.map()`, `.filter()`, `.exists()`, `.as()`, and `has()`.

### Tuple / comma-separated returns

CEL does not support tuples. You cannot return multiple values separated by commas.

```cel
// WRONG — causes "Syntax error: mismatched input ','"
(savedStart, savedEnd, false)

// CORRECT — use a map
{"start": savedStart, "end": savedEnd, "done": false}
```

### `bytes()` as a method call

`bytes` is a **function**, not a method. Calling it as `.bytes()` on a string expression fails.

```cel
// WRONG — causes "no such overload for 'bytes' applied to 'string.()'"
(state.api_key + ":").bytes().base64()

// CORRECT — bytes() is a top-level function
bytes(state.api_key + ":").base64()
```

### `parse_time()` without required arguments

`parse_time` requires **two arguments**: a Go time layout string and a timezone location.

```cel
// WRONG — causes "no such overload for 'parse_time' applied to 'string.()'"
cursorLastTs.parse_time()

// WRONG — causes "no such overload for 'parse_time' applied to 'dyn.()'"
state.cursor.ts.parse_time()

// CORRECT — provide layout and timezone
cursorLastTs.parse_time("2006-01-02T15:04:05Z07:00", "UTC")
string(state.cursor.ts).parse_time("2006-01-02T15:04:05.000Z", "UTC")
```

Common Go layout strings:
- RFC 3339: `"2006-01-02T15:04:05Z07:00"`
- RFC 3339 with millis: `"2006-01-02T15:04:05.000Z07:00"`
- Date only: `"2006-01-02"`
- Epoch seconds: use `timestamp(int(value))` instead of `parse_time`

### Unbalanced parentheses from deep `.as()` nesting

Every `.as(name,` opens a scope that must be closed with `)`. In deeply nested programs this is the most common source of `mismatched input ')' expecting <EOF>` or `missing ')' at ':'` errors.

Prevention rules:
- Keep nesting depth to **5 or fewer** `.as()` levels where possible.
- Extract sub-expressions into separate `.as()` bindings rather than inlining everything.
- After writing code, mentally count: every `.as(` needs exactly one matching `)`.
- If you get a paren error, do NOT add or remove parens blindly. Instead, re-read the structure from the outermost `state.with(` inward and verify each `.as(` has its `)`.

### `has()` requires `expr.field` form

`has()` is a macro that checks field presence. It requires the outermost operation to be a regular field selection (`.field`), but the expression it operates on is unconstrained — optional chains within the expression are fine.

```cel
// Valid — outermost operation is .poll_start (regular field selection)
has(state.?cursor.poll_start)
has(state.?cursor.last_timestamp)

// Also valid — deeper optional chains in the expression
has(state.?cursor.settings.timeout)

// WRONG — outermost operation is an index, not a field selection
has(state.?cursor.items[0])

// WRONG — outermost operation is optional field selection (.?), not regular (.field)
has(result.?resp)
has(state.?cursor)
```

Both `has()` and `orValue` work for cursor field checks. Prefer `orValue` when you need the value anyway (avoids accessing the field twice):

```cel
// has() — fine when you only need the existence check
has(state.?cursor.poll_start)

// orValue — preferred when you also need the value
state.?cursor.poll_start.orValue("").as(start, ...)
```

### Null-or-absent checks

Some APIs return `null` for a field rather than omitting it. Use `orValue(null)` to collapse both cases:

```cel
// True when the field is missing OR explicitly null
state.?cursor.token.orValue(null) != null
```

### Non-empty array checks

When checking that an optional array exists and has elements, index into it and use `hasValue()`:

```cel
// True when the array exists and is non-empty
state.?cursor.items[0].hasValue()
```

This is equivalent to `has(state.?cursor.items) && size(state.cursor.items) != 0` but more concise.

### Method calls on parenthesized groups

Wrapping an expression in `()` and then calling a method works only for some types. Prefer using `.as(name, ...)` to bind intermediates.

```cel
// FRAGILE — can produce unexpected 'no such overload' on dyn values
(someExpr + otherExpr).someMethod()

// PREFERRED — explicit binding, always works
(someExpr + otherExpr).as(combined, combined.someMethod())
```

### `optMap` does not flatten nested optionals

`optMap` is `map`, not `flatMap`. When the receiver has a value, `optMap` wraps the body's result in an outer optional. If the body evaluates to `optional.none()`, the result is `optional.of(optional.none())` — which `.hasValue()` reports as `true`. When serialised, the inner none becomes `null`:

```cel
optional.of("").optMap(et,
  (et != "") ? optional.of([et]) : optional.none()
)
// → null (not absent)
```

In an optional field (`?"key": ...`), this inserts `"key": null` instead of omitting the key, silently breaking `format_query()` and other functions that expect concrete types.

```cel
// WRONG — empty string produces ?"event_types": null
?"event_types": state.?event_types.optMap(et,
  (et != "") ? optional.of([et]) : optional.none()
)

// CORRECT — ternary at the top; optional.none() omits the key
?"event_types": (state.?event_types.orValue("") != "") ?
  optional.of([state.event_types])
:
  optional.none(),
```

`optMap` is safe when the body always evaluates to a concrete value (e.g. `optMap(v, [v])`). Do not use it when the body needs to conditionally evaluate to `optional.none()`.

### Type mismatches in ternary branches — `dyn()` wrapping

A ternary has the signature `bool ? T : T` — both branches must have the same type. The type checker operates on underlying Go types, not on the CEL surface syntax. A `{"key": "str"}` is `map[string]string` in Go, while `{"key": true}` is `map[string]bool`. These are different types even though both look like single-key maps. Worse, a map that previously had mixed-type values (e.g. `{"a": "str", "b": 1}` then `"b"` was removed) may be `map[string]any`, not `map[string]string`. The exact rules are hard to predict from the source — don't try.

```cel
// FAILS — list(map(string,string)) vs list(map(string,bool))
(size(events) > 0) ? events : [{"retry": true}]
```

**Workflow:**
1. Write the expression without `dyn()`.
2. Run `celfmt -s` (or mito). If it reports `found no matching overload for '_?_:_'`, wrap each branch in `dyn()` to defer type checking to runtime.
3. After adding `dyn()`, run mito with inputs that exercise **both branches** to confirm the expression evaluates correctly at runtime. This is the actual verification — do not skip it.

```cel
// CORRECT — dyn() defers type checking to runtime
(size(events) > 0) ? dyn(events) : dyn([{"retry": true}])
```

Do not add `dyn()` preemptively. Only use it when the compiler rejects a ternary whose branches are valid at runtime.

---

## Phase 0 — Skeleton

Write the absolute minimum: `state.with()` wrapping a single HTTP request that returns an empty events array. The goal is to verify the mock is reachable and the basic structure compiles.

```cel
state.with(
  request("GET", state.url.trim_right("/") + "/api/v1/items").with({
    "Header": {
      "Authorization": ["Bearer " + state.api_key],
      "Accept": ["application/json"],
    },
  }).do_request().as(resp, {
    "events": [],
    "want_more": false,
  })
)
```

**Validate:**

```bash
mito -data state.json -log_requests program.cel
```

**Expected:** JSON output with `"events": []`. The `-log_requests` flag shows the HTTP exchange — confirm the mock responds with 200. If this fails, fix the mock or URL before proceeding.

---

## Phase 1 — Error handling

Add the `resp.StatusCode == 200` branch with error reporting.

```cel
state.with(
  request("GET", state.url.trim_right("/") + "/api/v1/items").with({
    "Header": {
      "Authorization": ["Bearer " + state.api_key],
      "Accept": ["application/json"],
    },
  }).do_request().as(resp,
    resp.StatusCode == 200 ?
      {
        "events": [],
        "want_more": false,
      }
    :
      {
        "events": {
          "error": {
            "code": string(resp.StatusCode),
            "id": string(resp.Status),
            "message": "GET /api/v1/items: " + (
              size(resp.Body) != 0 ? string(resp.Body) : string(resp.Status)
            ),
          },
        },
        "want_more": false,
      }
  )
)
```

**Validate:**

```bash
mito -data state.json -log_requests program.cel
```

**Expected:** 200 branch returns `"events": []`. To test the error path, temporarily break the auth header or URL and confirm the error object appears.

---

## Phase 2 — Event mapping

Parse the response body and map events. This is where `decode_json()` and `.map()` are introduced.

```cel
state.with(
  request("GET", state.url.trim_right("/") + "/api/v1/items").with({
    "Header": {
      "Authorization": ["Bearer " + state.api_key],
      "Accept": ["application/json"],
    },
  }).do_request().as(resp,
    resp.StatusCode == 200 ?
      resp.Body.decode_json().as(body,
        body.items.map(e, {"message": e.encode_json()}).as(events, {
          "events": events,
          "want_more": false,
        })
      )
    :
      {
        "events": {
          "error": {
            "code": string(resp.StatusCode),
            "id": string(resp.Status),
            "message": "GET /api/v1/items: " + (
              size(resp.Body) != 0 ? string(resp.Body) : string(resp.Status)
            ),
          },
        },
        "want_more": false,
      }
  )
)
```

**Validate:**

```bash
mito -data state.json -log_requests program.cel
```

**Expected:** events array contains `{"message": "<json>"}` entries matching the mock response. If the response field is not `items`, adjust to match the actual API (e.g., `body.data`, `body.results`, `body.events`).

---

## Phase 3 — Pagination

Add pagination logic appropriate to the API. Choose the pattern from `references/cel-pagination-patterns.md`.

For cursor/token pagination, the structure grows by adding:
- Query parameters with the page token
- `want_more` tied to the presence of a next-page indicator
- Cursor output with the token

For timestamp pagination:
- Time range parameters in the query
- Cursor tracking the latest timestamp from events
- `want_more` tied to whether results were returned

**Key rule:** keep the new code within the existing structure. Do not restructure what already works — only add the pagination layer.

**Validate:**

```bash
mito -data state.json -log_requests -max_executions 5 program.cel
```

**Expected:** multiple evaluation cycles shown, events from each page, pagination terminates naturally (final output has `"want_more": false`).

---

## Phase 4 — Initial vs. subsequent run

Add the guard that distinguishes first run (no cursor) from subsequent runs (cursor present). This uses `state.?cursor.field.orValue(default)` — after the first `?`, field access on an optional propagates `optional.none()` automatically.

For timestamp-cursor programs, the typical pattern:

```cel
state.?cursor.last_timestamp.orValue(
  string(now - duration(state.initial_interval))
).as(since,
  // ... existing request with `since` in query params ...
)
```

**Validate with first-run state:**

```bash
mito -data state.json -log_requests -max_executions 3 program.cel
```

**Validate with cursor state** (create `state_cursor.json` with a `"cursor"` key):

```bash
mito -data state_cursor.json -log_requests -max_executions 3 program.cel
```

**Expected:** first-run uses the lookback interval; cursor-run uses the stored timestamp. Both paginate correctly.

---

## Phase 5 — Complex branching (if needed)

Only add multi-phase state machines, time-window chunking, worklist patterns, or multi-endpoint flows after Phases 0–4 are working.

For multi-phase programs, add one phase at a time:
1. Add the phase guard (e.g., `state.?cursor.phase.orValue("list")`)
2. Implement the first branch body
3. Run mito, verify
4. Add the next branch body
5. Run mito, verify

**Never add all branches at once.** Each branch addition should be verified independently.

---

## Review — deduplicate before templating

After the program passes mito validation, review the branch structure for duplicated request/response handling. This is common when an initialization branch (cursor creation, subscription, token exchange) inlines the same fetch logic that the steady-state branch already contains.

**Check:** describe what each top-level branch does in one sentence. If two descriptions end with the same verb and object (e.g. "...then fetches events" / "...fetches events"), the fetch logic is duplicated.

**Fix:** apply Technique 6 from `cel-code-style.md`. Two equally valid approaches: Variant A splits the init into a separate evaluation via `want_more: true`; Variant B uses an intermediate result map to unify the branches within one evaluation. Either eliminates the duplication.

Re-run mito after any structural changes.

---

## Workflow summary

```
Phase 0: skeleton (state.with + request + empty events)     → mito
Phase 1: + error handling branch                             → mito
Phase 2: + decode_json + event mapping                       → mito
Phase 3: + pagination (want_more, cursor token/offset)       → mito -max_executions 5
Phase 4: + initial vs subsequent (cursor guard)              → mito with both state files
Phase 5: + complex branching (one branch at a time)          → mito per branch
Review:  deduplicate branches (Technique 6)                   → mito
```

Each `→ mito` is a hard gate. Fix all errors before proceeding.

---

## When things go wrong

If mito reports a compilation error:

1. Read the error message carefully. `no such overload for 'X' applied to 'Y.()'` means you called `X` as a method when it is a function (or vice versa), or you are missing required arguments.
2. Check the anti-patterns section at the top of this file.
3. Use `debug("tag", value).as(_, ...)` to inspect intermediate values and their types.
4. Use `-dump error` to get the full evaluation state on failure.
5. Do NOT rewrite the program from scratch. Revert to the last working phase and re-add changes incrementally.
6. Do NOT use Python, sed, or other external tools to modify `.cel` files. Use the editor's StrReplace/Write tools.

If `celfmt` hangs on a standalone `.cel` file:

`celfmt` can hang when run on standalone `.cel` files in some environments. **Use `celfmt -s -agent` on `cel.yml.hbs` as the reliable validation path for integration work:**

```bash
cd packages/<package_name>/data_stream/<stream>/agent/stream
celfmt -s -agent -i cel.yml.hbs -o cel.yml.hbs
```

Do not use `celfmt` on standalone `.cel` prototype files. If `celfmt` appears to hang, kill it and switch to the `-s -agent` form on the `.hbs` file instead.

If you are transferring a mito-validated `.cel` program into the `program: |` block in `cel.yml.hbs`:

- Every line of the program must be indented by **exactly 2 spaces** relative to the `program: |` key.
- Do NOT hand-paste and re-indent manually — transcription errors (extra parentheses, wrong indentation levels) are easy to introduce in deep `.as()` nesting.
- **Recommended approach**: write the complete program content to the `cel.yml.hbs` file programmatically using StrReplace/Write, then run `celfmt -s -agent` to normalize indentation, simplify, and verify the result.

If mito reports a runtime error (`failed eval`):

1. The error is a type mismatch at runtime (inside `.as()` bindings, types are `dyn`).
2. Add `int()` or `string()` casts at the boundary where the value enters your logic.
3. All JSON numbers are `double` — there is no `double > int` overload. Cast with `int()`.
