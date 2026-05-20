# CEL expression reference

This reference covers the CEL expression itself — the program that runs
inside `program: |` in a cel.yml.hbs template. It does not cover
Handlebars, YAML template anatomy, manifest configuration, or system
test setup.

The expression builder's job: given `state.json` (literal test values)
and a running mock URL, produce a validated `.cel` file via incremental
mito development.

---

## Interface contract

**Inputs:**
- `test-api.py` — the Python implementation of the API interaction
  (the specification; the ground truth)
- `state.json` — keys matching the future `state:` block, with literal
  test values (url pointing at the mock, credentials, batch_size, etc.)
- Mock URL — a running `elastic/stream` mock derived from test-api.py
- Research brief — supplementary context (field meanings, edge cases
  not exercised by the script)

**Outputs:**
- A validated `.cel` file that passes mito against the mock
- A taxonomy classification (pagination pattern + state management
  pattern at the least complex class that satisfies requirements)

The expression builder never touches `cel.yml.hbs`, manifests, or
system test files. It returns the working CEL expression and the
classification. The orchestrator wraps it.

---

## Translation framing

The task is **translation from Python to CEL**, not generation from
prose. The test-api.py collection function (`run_collection()` or
`collect()`) is the specification. Every construct has a direct CEL
equivalent:

| Python construct | CEL equivalent |
|-----------------|---------------|
| `requests.get(url, headers=...)` | `request("GET", url).with({"Header": ...}).do_request()` |
| `if resp.status_code != 200:` | `resp.StatusCode == 200 ? ... : {error event}` |
| `resp.json()` | `resp.Body.decode_json()` |
| `data["items"]` | `body.items` or `body.?items.orValue([])` |
| `while has_next_page:` | `"want_more": has_next_cursor` |
| `cursor = resp["next"]` | `"cursor": {"next": body.next}` |
| `for item in items:` | `body.items.map(e, {"message": e.encode_json()})` |
| `if "errors" in resp:` | `has(body.errors) ? ... : ...` |

The builder translates the collection function, not the CLI scaffolding
(argument parsing, logging, archiving).

---

## Incremental build phases

Every expression must be built in phases, validating with mito after
each. Do NOT write the full program before running mito.

| Phase | What to add | Corresponds to in Python |
|-------|------------|------------------------|
| 0 — skeleton | `state.with(request(...).do_request().as(resp, {...}))` | `do_request()` call structure |
| 1 — error handling | `resp.StatusCode == 200 ?` branch with error event | Status code checks, exception handling |
| 2 — event mapping | `body.items.map(e, {"message": e.encode_json()})` | Response navigation + event extraction |
| 3 — pagination | `want_more` + cursor/offset/token tracking | `while` loop + cursor propagation |
| 4 — cursor guard | `state.?cursor.field.orValue(...)` for first-vs-subsequent | Initial-vs-subsequent run handling |

Run mito after each phase (always use `-fb` for filebeat-compatible
validation):
```bash
mito -fb -data state.json -log_requests program.cel
```

For pagination testing:
```bash
mito -fb -data state.json -log_requests -max_executions 5 program.cel
```

For cursor persistence testing:
```bash
mito -fb -data state_cursor.json -log_requests -max_executions 3 program.cel
```

---

## Core structure

Every HTTP-based expression has this shape:

```
[pre-bindings: cursor defaults, window math, URL construction]
state.with(
  request(...).do_request().as(resp,        ← level 1
    resp.StatusCode == 200 ?
      resp.Body.decode_json().as(body, {    ← level 2
        ...result map...
      })
    : { ...error... }
  )
)
```

**Hard cap: `.as()` depth must never exceed 5 levels** on any
execution path. HTTP programs target 2 levels inside `state.with()`.

### Pre-bindings

Extract these *before* `state.with()`:
- Cursor defaults: `state.?cursor.last_ts.orValue(...)`
- Window bounds: `now - duration(state.initial_interval)`
- URL construction for complex paths
- Page tokens from previous state

Do NOT bind single-use values with `.as()` — inline them.

### Result map

The map inside `body.as(body, {...})` contains:
- `"events"`: the event array
- `"cursor"`: state to persist across restarts
- `"want_more"`: pagination continuation signal
- `"url"`: preserved from state (required)

### Flat decode pattern (structural constraint)

After `try(resp.Body.decode_json()).as(body, ...)` or
`resp.Body.decode_json().as(body, ...)`, the success path must follow
this shape:

```cel
body.as(body,
  error_check_1 ? error_result_1 :
  error_check_2 ? error_result_2 :
    {
      "items": body.?data.orValue([]),
      "next":  body.?pagination.next.orValue(""),
    }.as(page, {
      "events": page.items.map(e, {"message": e.encode_json()}),
      "want_more": size(page.items) > 0 && page.next != "",
      "cursor": { "next": page.next },
      "url": state.url,
    })
)
```

The key technique: **extract response navigation into a flat
intermediate map**, then build the result from that map. Do NOT chain
nested `.as()` calls to extract individual fields. Each `.as()` level
multiplies cognitive complexity of everything inside it.

**Wrong — nested extraction (high complexity):**
```cel
body.?events.optMap(events, type(events)==type([]) ? dyn(events) : dyn([]))
  .orValue([]).as(events_list,
    body.?pagination.optMap(pg, pg.?next.optMap(n, n).orValue(""))
      .orValue("").as(next_str,
        { ... result using events_list and next_str ... }
      )
  )
```

**Right — intermediate map (low complexity):**
```cel
{
  "items": body.?events.orValue([]),
  "next":  body.?pagination.next.orValue(""),
}.as(page, {
  "events": page.items.map(e, {"message": e.encode_json()}),
  "want_more": size(page.items) > 0 && page.next != "",
  "cursor": { "next": page.next },
  "url": state.url,
})
```

Both extract the same two values from the response body. The
intermediate map does it in one `.as()` level; the nested version uses
two (or more). The complexity difference compounds with every additional
field extracted.

### Worked example: Airtable (cursor_token + time_window)

Python (`run_collection`):
```python
events = body.get("events", [])
next_token = body.get("pagination", {}).get("next", "")
# stop if no events or no next token
if not events or not next_token:
    break
```

CEL (flat):
```cel
state.?cursor.next.orValue("").as(page_token,
  state.with(
    request("GET", url + "?" + query_params).with({...}).do_request().as(resp,
      resp.StatusCode == 200 ?
        try(resp.Body.decode_json()).as(parsed,
          is_error(parsed) ? { error result } :
          parsed.as(body,
            (has(body.error) && body.error != null) ? { error result } :
              {
                "items": body.?events.orValue([]),
                "next":  body.?pagination.next.orValue(""),
              }.as(page, {
                "events": page.items.map(e, {"message": e.encode_json()}),
                "want_more": size(page.items) > 0 && page.next != "",
                "cursor": { "next": page.next },
                "url": state.url,
              })
          )
        )
      : { error result }
    )
  )
)
```

`.as()` depth inside `state.with()`: resp (1) → parsed (2) → body (3)
→ page (4). The page level is the intermediate map — it doesn't add
nesting depth to the result map contents because the result map is a
flat literal.

### Worked example: Buildkite (graphql_relay + time_window)

Python (`run_collection`):
```python
edges = parsed["data"]["organization"]["auditEvents"]["edges"]
page_info = parsed["data"]["organization"]["auditEvents"]["pageInfo"]
has_next = page_info.get("hasNextPage", False)
end_cursor = page_info.get("endCursor", "")
```

CEL (flat, with relay condition pre-bound):
```cel
poll_from.as(poll_from,
  pages_before.as(pages_before,
    state.with(
      post_request(...).do_request().as(resp,
        resp.StatusCode == 200 ?
          try(resp.Body.decode_json()).as(parsed,
            is_error(parsed) ? { error } :
            size(parsed.?errors.orValue([])) > 0 ? { graphql error } :
            (!has(parsed.?data.organization) || ...) ? { org error } :
              parsed.data.organization.?auditEvents.orValue({"edges":[],"pageInfo":{}}).as(audit, {
                "has_next": audit.?pageInfo.?hasNextPage.orValue(false),
                "end_cursor": string(audit.?pageInfo.?endCursor.orValue("")),
                "edges": audit.?edges.orValue([]),
              }.as(page, {
                "events": page.edges.map(e, {"message": e.node.encode_json()}),
                "want_more": page.has_next && page.end_cursor != "" && (pages_before+1) < int(state.max_pages),
                "cursor": page.has_next && page.end_cursor != "" && (pages_before+1) < int(state.max_pages) ?
                  {"poll_occurred_at_from": poll_from, "after": page.end_cursor, "pages_in_cycle": pages_before+1}
                : {},
                "url": state.url,
              }))
          )
        : { error }
      )
    )
  )
)
```

The relay condition (`has_next && end_cursor != "" && pages < max`) is
expressed once in `page.has_next && page.end_cursor != ""` rather than
repeated with full optional-access chains. The intermediate map absorbs
the navigation complexity; the result map stays flat.

---

## Event output

Events contain ONLY `"message"`:
```cel
body.items.map(e, {"message": e.encode_json()})
```

Do NOT set `@timestamp` or any other field. The framework handles
metadata. Duplicating `@timestamp` causes silent document rejection
in ES 9.x.

---

## Error handling

Every HTTP request needs a status check. Two error forms:

**Single-object error (retry — deletes cursor):**
```cel
resp.StatusCode == 200 ?
  ...success...
: {
    "events": {
      "error": {"message": "GET /path: " + string(resp.StatusCode)}
    },
    "want_more": false,
  }
```

**Array error (advance — preserves cursor):**
```cel
"events": [{"error": {"message": "..."}}],
"cursor": state.cursor,
"want_more": false,
```

Use single-object (retry) when data was not collected. Use array
(advance) when the program should skip past the error.

---

## Pagination

The `want_more` field drives pagination. Set it based on the API's
pagination signal, NOT based on whether events were returned:

```cel
"want_more": body.?meta.next.orValue("") != "",
"cursor": {
  "next": body.?meta.next.orValue(""),
  "last_ts": /* high-water mark */,
},
```

**Cursor field separation:** Store page tokens (transient, drive
`want_more`) and time bookmarks (persistent, drive the starting point)
as separate cursor fields. Never use one field for both.

---

## State management rules

1. `state.url` — from `resource.url` config; preserve in output
2. `cursor` — only state persisted across restarts
3. `events` — removed after each evaluation; never rely on it
4. `want_more: true` — triggers immediate re-evaluation (only if
   `events` is non-empty)
5. Numbers are float64; cast with `int()` for integer operations
6. Optional access: `state.?cursor.field.orValue(default)`
7. After first `?` in a chain, subsequent `?` are automatic

---

## Syntax rules

| Wrong | Correct |
|-------|---------|
| `(str + ":").bytes()` | `bytes(str + ":")` |
| `str.parse_time()` | `str.parse_time("2006-01-02...", "UTC")` |
| `(a, b, false)` | `{"a": a, "b": b, "done": false}` |
| `body.?more.orValue(false) == true` | `body.?more.orValue(false)` |
| Deep `.as()` nesting (>5) | Extract pre-bindings, keep <=5 |
| Single-use `.as(x, ...x...)` | Inline the value directly |
| Repeated sub-expression (3+ times) | Extract into a pre-binding `.as(name, ...)` |
| Flat map with 1 field `.as(p, ...p.f...)` | Inline the field — flat decode is for 2+ fields |
| `int(size(x))` | `size(x)` — `size` already returns `int` |
| `x ? [] : y ? [] : z ? [] : val` | `(x \|\| y \|\| z) ? [] : val` — collapse ternaries sharing a default |
| `x.?f.hasValue() ? optional.of(x.f) : optional.none()` | `x.?f` — optional access already returns an optional |
| `state.?cursor.?field` | `state.?cursor.field` — only the first `?` is needed; the rest propagate |

---

## Quality checklist

Before returning the `.cel` file, verify:

- [ ] Passes mito against the mock at each phase
- [ ] All error paths from test-api.py are represented
- [ ] Pagination logic matches the Python loop's termination conditions
- [ ] Response fields navigated the same way as the Python script
- [ ] Cursor state captures the same info Python propagates between iterations
- [ ] No invented logic (branches that don't exist in the Python source)
- [ ] `.as()` depth <= 5 on every path
- [ ] No rate limiting or retry logic in the expression
- [ ] Events contain only `"message"`
- [ ] `want_more` driven by pagination signal, not event count
- [ ] `celfmt -s -i program.cel -o program.cel` run to simplify/format the final file
