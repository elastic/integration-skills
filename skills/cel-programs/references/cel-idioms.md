# Common CEL idioms and conventions

Quick reference for idioms, HTTP usage, pagination strategy bullets, events, structure, and YAML configuration notes used with CEL programs.

## Syntax anti-patterns — NEVER use these

These are the most common mistakes that cause compilation failures. See `references/cel-incremental-build.md` for detailed explanations and correct alternatives.

| Wrong | Correct | Error produced |
|-------|---------|----------------|
| `(a, b, false)` as a return value | `{"a": a, "b": b, "done": false}` (use a map) | `Syntax error: mismatched input ','` |
| `(str + ":").bytes()` | `bytes(str + ":")` (`bytes` is a function) | `no such overload for 'bytes' applied to 'string.()'` |
| `str.parse_time()` | `str.parse_time("2006-01-02T15:04:05Z07:00", "UTC")` (requires layout + tz) | `no such overload for 'parse_time'` |
| Deeply nested `.as()` with unbalanced `)` | Keep nesting <=5 levels; count each `.as(` vs `)` | `mismatched input ')' expecting <EOF>` |

## Common CEL idioms

| Idiom | Example |
|-------|---------|
| State propagation | `state.with({...})` |
| Sub-expression naming | `expr.as(name, body)` |
| Query string building | `{"key": ["val"]}.format_query()` |
| JSON encode/decode | `.encode_json()`, `.decode_json()` |
| Optional header | `?"Key": has(state.x) ? optional.of([state.x]) : optional.none()` |
| Optional access | `state.?cursor.field.orValue(default)` |
| Duration from string | `duration(state.initial_interval)` |
| Int cast from float | `int(state.batch_size)` |
| Time arithmetic | `now - duration("24h")` |
| Explicit request | `request("GET", url).with({"Header": {...}}).do_request()` |
| Simple GET | `get(state.url)` or `get_request(url).do_request()` |
| Simple POST | `post(url, content_type, body)` or `post_request(url, ct, body).do_request()` |
| Wrap events | `items.map(e, {"message": e.encode_json()})` |
| Flatten nested lists | `nested.flatten()` |
| Remove empties | `list_or_map.drop_empty()` |
| Selective merge | `map.with()`, `map.with_replace()`, `map.with_update()` |
| Remove fields | `map.drop("key")`, `map.drop(["a", "b.c"])` |
| Type mismatch in ternary | Wrap branches in `dyn()` — see `cel-incremental-build.md` |

## HTTP requests

**Simple requests** — use `get(url)` or `post(url, ct, body)`. These direct calls automatically pick up `auth.basic` and `auth.token` config. Use `request("METHOD", url).with({...}).do_request()` when additional headers beyond auth are needed, or for methods other than GET/POST/HEAD.

**`resource.headers`** (ga 8.18.1) — static headers that are the same for every request (e.g. `Content-Type`, `Accept`, API version headers) can be set in the YAML config rather than in the CEL program. These are added before auth headers.

**URL normalization** — use `trim_right("/")` to handle trailing slashes.

**Query strings** — build with `format_query()` on a map with optional keys. Avoid constructing query strings via string concatenation.

```cel
(state.url.trim_right("/") + "/api/v1/alerts?" +
  {
    "limit": [string(state.batch_size)],
    "sort": ["updated_timestamp|asc"],
    ?"after": state.?cursor.token.optMap(v, [v]),
    ?"filter": state.?query.optMap(v, [v]),
  }.format_query()
)
```

`optMap` is safe here because the body always evaluates to a concrete value (`[v]`). Do **not** use `optMap` when the body evaluates to `optional.of(...)` or `optional.none()`. `optMap` is `map`, not `flatMap` — it wraps the result, so `optional.none()` from the body becomes `optional.of(optional.none())`, which serialises as `null` instead of omitting the key:

```cel
// WRONG — empty string produces "event_types": null, breaking format_query()
?"event_types": state.?event_types.optMap(et,
  (et != "") ? optional.of([et]) : optional.none()
),

// CORRECT — ternary at the top level; optional.none() omits the key
?"event_types": (state.?event_types.orValue("") != "") ?
  optional.of([state.event_types])
:
  optional.none(),
```

## Pagination

**Match the strategy to the API:**

- **Cursor/token** — API returns a next-page token; pass it in the next request. Set `"want_more": has(body.?meta.pagination.next)`.
- **Offset** — increment offset by page size each iteration.
- **Next-link** — API returns a full URL for the next page.
- **Time-window** — advance a timestamp cursor based on response data.
- **Worklist** — fetch a list of IDs, then iterate over each.

**Cursor timestamp tracking** — use the last record's timestamp when results are known to be sorted by the API (first record if reverse-sorted). Use `max()` with a regression guard when sort order is not guaranteed.

## Event output

**Standard structure** — `body.<path>.map(e, {"message": e.encode_json()})` where `<path>` matches the API's response (e.g. `body.data`, `body.items`, `body.resources`).

**Events must contain ONLY `"message"`.** Do not set `@timestamp`, `event.original`, or any other field. The Elastic Agent framework adds `@timestamp`; duplicates cause silent document rejection in ES 9.x (`Duplicate field '@timestamp'`).

```cel
// CORRECT
items.map(e, {"message": e.encode_json()})

// WRONG — causes duplicate @timestamp, ES drops all events
items.map(e, {"message": e.encode_json(), "@timestamp": e.timestamp})
```

### Placeholder events for cursor persistence

The input only persists cursor updates when at least one event is published. When a page returns no data but the cursor should advance, emit a placeholder and drop it before indexing:

```cel
"events": body.?data.orValue([]).map(e, {"message": e.encode_json()}).as(events,
  (size(events) > 0) ? dyn(events) : dyn([{"retry": true}])
),
```

Then add a `drop_event` processor in `cel.yml.hbs` to discard it before indexing:

```yaml
processors:
- drop_event.when.equals.retry: true
```

The `dyn()` wrapping is required because the two branches have different compile-time types (`list(map(string,string))` vs `list(map(string,bool))`). See `cel-incremental-build.md` for the full workflow: write without `dyn()` first, add it only when `celfmt -s` reports a type mismatch, then verify both paths with mito.

The alternative form uses `[{"message": "retry"}]` with `- drop_event.when.equals.message: retry` in `processors:`. The boolean form is preferred — `retry` is a dedicated control flag that no real event would have. The `{"message": "retry"}` form avoids the type mismatch (both branches are `map(string,string)`) so `dyn()` is not needed.

## Error handling

Two error event forms with distinct semantics:

**Single-object error (retry):** `"events": {"error": {...}}` — the input logs at ERROR, sets degraded status, and **deletes the cursor** so the next evaluation retries. Use when data was not collected.

```cel
{
  "events": {
    "error": {
      "code": string(resp.StatusCode),
      "id": string(resp.Status),
      "message": "GET " + state.url.trim_right("/") + "/api/v1/items: " + (
        size(resp.Body) != 0 ? string(resp.Body) : string(resp.Status)
      ),
    },
  },
  "want_more": false,
}
```

**Array error (advance):** `"events": [{"error": {...}}]` — processed as a normal event array. The cursor **is** updated. Use when the program should advance past the error. Ensure the ingest pipeline has a `terminate` processor (ES 8.16.0+).

**Error message format:** include HTTP method and URL path without query params: `"METHOD path: body-or-status"`.

### Nested mapping with `flatten()` and `drop_empty()`

When an API response contains nested arrays or when mapping conditionally produces items, the result is a list of lists or a list with empty elements. Use `flatten()` to collapse nesting and `drop_empty()` to remove empties.

**Expanding sub-arrays** — each item contains a nested array that should become separate events:

```cel
// API returns: {"records": [{"id": "a", "events": [e1, e2]}, {"id": "b", "events": [e3]}]}
// Want: [e1, e2, e3] as separate events
body.records.map(r, r.events).flatten().map(e, {"message": e.encode_json()})
```

Without `flatten()`, the inner `map` produces `[[e1, e2], [e3]]` — a list of lists. `flatten()` collapses it to `[e1, e2, e3]`.

**Conditional mapping** — some items produce events, others don't:

```cel
// Filter and transform: only include items with status "complete"
body.items.map(item,
  item.status == "complete" ?
    [{"message": item.encode_json()}]
  :
    []
).flatten()
```

Each item maps to either a single-element list or an empty list. `flatten()` merges them into a flat event list.

**Cleaning up after `drop()`** — removing fields from nested objects can leave empty maps:

```cel
body.items.drop("internal_id").drop_empty().map(e, {"message": e.encode_json()})
```

`drop_empty()` recursively removes all empty maps and lists, so items that contained only the dropped field disappear entirely rather than becoming `{}`.

## Structure and readability

- **2-space indentation** throughout, reflecting scope.
- **Break long lines** — only very simple ternary expressions should be one-liners.
- **`.as(name, ...)`** with meaningful names. For values extracted from a dotted path, use the final field name: `state.?cursor.next.orValue("").as(next, ...)`, not `.as(stored, ...)` or `.as(nc, ...)`.
- **Comment non-obvious intent**, not obvious code. Multi-phase state machines (subscribe-list-fetch, create-poll-download) must include a comment block explaining the phases and state variables.
- **Describe each major branch** — CEL has no functions, so a multi-branch ternary tree is the only way to express control flow. When a program has top-level branches (init vs steady-state, paginating vs backfilling, different API call types), add a short comment at each branch entry describing its purpose (e.g. `// Steady state: fetch events with persisted cursor`). These act as section headings in an expression that would otherwise require tracing every condition to navigate.
- **Avoid stringly typed expressions** when CEL extensions exist — e.g. use `format_query()` instead of string-concatenated query strings.

### Nesting discipline

**`.as()` depth must not exceed 5 levels** on any execution path. HTTP programs must target 2 levels inside `state.with()`: `resp` and `body`.

| Rule | How to achieve it |
|------|-------------------|
| Keep cursor/window defaults outside `state.with()` | Bind `since`, `page_token`, `windowStart` with `.as()` *before* `state.with(` |
| Inline single-use values | `int(state.batch_size)` used once → inline it; no `.as(limit, ...)` needed |
| Sequential pipeline for multi-step flows | Chain `.as(state, ...)` at the top level instead of nesting deeper |
| URL construction | Short URLs inline; complex ones bound before `state.with()` |
| Consolidate multiple cursor fields | `{"token": ..., "since": ...}.as(cursor, ...)` instead of nested `.as()` per field |
| Shared downstream logic | Unify branches into `{"ok": true, ...}` / `{"ok": false, ...}` intermediate result, bind with `.as(result, ...)`, then write shared code once |

See `references/cel-code-style.md` for before/after examples of all six techniques.

## Configuration

**Request tracer** — use the always-present style (from v8.15):

```yaml
resource.tracer:
  enabled: {{enable_request_tracer}}
  filename: "../../logs/cel/http-request-trace-*.ndjson"
  maxbackups: 5
```

rather than the conditional `{{#if}}` block. The newer form supports trace deletion when tracing is disabled. If the integration uses the old form, consider upgrading if the stack version allows.

**Tracer at data stream level** — declare `enable_request_tracer` in the data stream manifest, not at the input level. Input-level tracing enables logging for all data streams in the policy, increasing load and risk of secret leakage.
