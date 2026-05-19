# CEL code style and nesting discipline

## The core structure rule

Every HTTP-based CEL program has the same fundamental shape. Keep all computation **outside** `state.with()` or **inline** at the call site. Inside `state.with()`, the depth target is 2 `.as()` levels: `resp` and `body`.

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

**Hard cap: `.as()` depth must never exceed 5 levels** on any execution path. If you count more than 5, stop and refactor using the techniques below. HTTP programs should target 2 levels inside `state.with()`.

---

## Automated simplification with `celfmt -s`

`celfmt -s` applies three rewrites that enforce several of the style rules below automatically:

1. **Inline single-use `.as()` bindings** — removes `.as(name, ...)` when `name` is used zero or one times in the body, replacing the binding with a direct substitution. This enforces the "do not bind single-use values" rule.
2. **Eliminate boolean comparisons** — rewrites `x == true` to `x` and `x == false` to `!x`. This enforces the "do not compare booleans" rule.
3. **Rewrite `has()` ternaries** — rewrites `has(x.f) ? x.f : d` (and the negated `!has(x.f) ? d : x.f`) to `x.?f.orValue(d)`.

**Always run `celfmt -s` on CEL programs.** Pass `-s` in every `celfmt` invocation — both during development (on standalone `.cel` files) and when formatting the final `cel.yml.hbs` template. The has-ternary rewrite skips cases where it would lose comments. The `x != true` and `x != false` forms are not handled because they would change a value-producing expression into a runtime error under `dyn`.

The `== true` and `== false` rewrites are not strictly semantics-preserving under `dyn` either — if `x` is not a bool, `x == true` evaluates to `false` via heterogeneous equality, while the simplified `x` evaluates to whatever `x` is. In practice, nobody writes `x == true` unless `x` is boolean, and code that wraps a bool in `dyn` to exploit the heterogeneous equality behaviour is already wrong. If the rewrite breaks something, the original code should be fixed rather than the simplification reverted.

```bash
celfmt -s -agent -i cel.yml.hbs -o /dev/null && celfmt -s -agent -i cel.yml.hbs -o cel.yml.hbs
```

The simplifier runs before formatting, so its output is always correctly formatted. During development, write code in whatever way is clearest — `celfmt -s` will clean up redundant bindings and boolean comparisons at the end.

---

## General style rules

**Do not compare booleans to `true` or `false`.** JSON deserialization always produces a CEL `bool`. Use the value directly or negate it. (`celfmt -s` fixes `== true` and `== false` automatically, but not `!= true` or `!= false` — rewrite those by hand.)

```cel
// WRONG
result.ok == false
body.?more_to_read.orValue(false) == true

// CORRECT
!result.ok
body.?more_to_read.orValue(false)
```

**Do not bind single-use values with `.as()`.** Every `.as()` adds a nesting level. If a value is used exactly once, inline it. See Technique 2 below for examples. This is not optional — unnecessary bindings are a common source of excessive nesting in generated programs. (`celfmt -s` removes these automatically.)

---

## Flattening techniques

### Technique 1 — Extract cursor and window defaults before `state.with()`

The most common cause of deep nesting is binding cursor fields *inside* the HTTP chain. Move them out.

**Before (deep — 5 levels inside `state.with`):**
```cel
state.with(
  state.?cursor.last_timestamp.orValue(
    string(now - duration(state.initial_interval))
  ).as(since,
    int(state.batch_size).as(limit,
      request("GET", state.url.trim_right("/") + "?" + {
        "since": [since],
        "limit": [string(limit)],
      }.format_query()).with({...}).do_request().as(resp,
        resp.StatusCode == 200 ?
          resp.Body.decode_json().as(body, {...})
        : {...}
      )
    )
  )
)
```

**After (flat — 2 levels inside `state.with`):**
```cel
state.?cursor.last_timestamp.orValue(
  string(now - duration(state.initial_interval))
).as(since,
  state.with(
    request("GET", state.url.trim_right("/") + "?" + {
      "since": [since],
      "limit": [string(int(state.batch_size))],
    }.format_query()).with({...}).do_request().as(resp,
      resp.StatusCode == 200 ?
        resp.Body.decode_json().as(body, {...})
      : {...}
    )
  )
)
```

The same technique applies to page tokens, offsets, window start/end times, and any other value derived purely from `state` without making an HTTP call.

---

### Technique 2 — Inline single-use bindings

Every `.as()` costs a nesting level. If a value is used exactly once, inline it. Do not bind it.

**Wrong — unnecessary `.as()` adds a nesting level for no benefit:**
```cel
int(state.batch_size).as(limit,
  request("GET", url + "?" + {
    "limit": [string(limit)],
  }.format_query())...
)

// Also wrong — binding body fields used once each:
string(body.?next_cursor.orValue("")).as(next_c,
  body.?more_to_read.orValue(false).as(more,
    {"cursor": {"next_cursor": next_c}, "want_more": more}
  )
)
```

**Correct — inline at call site:**
```cel
request("GET", url + "?" + {
  "limit": [string(int(state.batch_size))],
}.format_query())...

// Inline body fields directly:
{
  "cursor": {"next_cursor": string(body.?next_cursor.orValue(""))},
  "want_more": body.?more_to_read.orValue(false),
}
```

Bind with `.as()` only when a value is referenced **more than once**, or when the expression is complex enough that a name genuinely aids comprehension. "I might need it later" is not a reason to bind.

---

### Technique 3 — Sequential `.as(state, ...)` pipeline for multi-step flows

When a program must initialize state, normalize cursor fields, or perform multi-phase work (e.g., subscribe → list → fetch), chain top-level state transforms sequentially instead of nesting deeper.

**Wrong — deeply nested state init inside HTTP chain:**
```cel
state.with(
  state.?initial_start_time.orValue("").as(ist,
    (ist != "" ? state : state.with({"initial_start_time": string(int(timestamp(now - duration(state.initial_interval))))})).as(st,
      request(...).do_request().as(resp, ...)
    )
  )
)
```

**Correct — sequential `.as(state, ...)` pipeline:**
```cel
(
  !has(state.initial_start_time) ?
    state.with({"initial_start_time": string(int(timestamp(now - duration(state.initial_interval))))})
  :
    state
).as(state,
  (
    state.?want_more.orValue(false) ?
      state
    :
      state.with({"page": null})
  ).as(state,
    state.with(
      request(...).do_request().as(resp,
        resp.StatusCode == 200 ?
          resp.Body.decode_json().as(body, {...})
        : {...}
      )
    )
  )
)
```

Each `.as(state, ...)` block is at the top level — they do not nest inside each other. This pattern scales to arbitrarily complex multi-phase programs without increasing depth.

---

### Technique 4 — Compute URL outside the response chain

URL construction belongs before the HTTP call, not as a nested `.as()` inside the response chain.

**Wrong:**
```cel
state.with(
  (state.url.trim_right("/") + "/api/v1/events?" + params.format_query()).as(reqUrl,
    request("GET", reqUrl).do_request().as(resp, ...)
  )
)
```

**Correct — inline short URLs, or bind before `state.with()` for complex ones:**
```cel
// Short URL: inline directly
state.with(
  request("GET", state.url.trim_right("/") + "/api/v1/events?" + params.format_query())
  .do_request().as(resp, ...)
)

// Complex URL: bind before state.with
(state.url.trim_right("/") + "/admin/v1/orgs/" + state.org_id + "/events").as(endpoint,
  state.with(
    request("GET", endpoint + "?" + params.format_query()).do_request().as(resp, ...)
  )
)
```

---

### Technique 5 — Consolidate multiple cursor fields into a single map binding

When a program needs two or more cursor fields (e.g. a page token and a timestamp bookmark), nested `.as()` bindings add a level of indent per field. Constructing a map and binding it once removes those levels.

Optional values can be bound and carried through intermediate computation — they only need to be concretised (via `orValue`) when assigned to fields in an object that will be serialised to JSON, since JSON has no concept of optional values. Do not concretise at binding time; carry the optionals through and resolve them at the point of use.

**Before (nested — one level per field, early concretisation):**
```cel
state.?cursor.next_token.orValue("").as(next_token,
  state.?cursor.last_from.orValue(
    string(now - duration(state.initial_interval))
  ).as(since,
    state.with(
      request(...)...
    )
  )
)
```

**After (single map binding, optionals carried through):**
```cel
{
  "next_token": state.?cursor.next_token,
  "since": state.?cursor.last_from,
}.as(cursor,
  state.with(
    request("GET", state.url.trim_right("/") + "/v1/events?" + (
      cursor.next_token.orValue("") != "" ?
        {"limit": [...], "cursor": [cursor.next_token.orValue("")]}
      :
        {"limit": [...], "since": [cursor.since.orValue(
          string(now - duration(state.initial_interval))
        )]}
    ).format_query())...
  )
)
```

The map values are optional-typed — `cursor.next_token` and `cursor.since` remain optional until `orValue` is called at the point where a concrete value is needed (query parameter construction, cursor output). This preserves the semantic distinction between "field absent" and "field present but empty".

Optional keys (`?"next_token": state.?cursor.next_token`) are also valid — absent optionals omit the key entirely, and access uses `cursor.?next_token`. Either form works; the choice depends on whether downstream code benefits from the key always being present (with an optional value) or conditionally absent.

### Technique 6 — Eliminate duplicated request/response handling

When an initialization branch (cursor creation, subscription, token exchange) and a steady-state branch both contain the same fetch logic, the duplication must be removed. Two approaches work equally well — choose based on the situation.

#### Variant A — Split initialization into a separate evaluation

When the init request's output is a cursor or token that the steady-state path already uses, split the work across two evaluations.

**Problem — duplicated fetch block:**
```cel
state.?cursor.realtime.as(persisted,
  persisted.hasValue() ?
    // Phase A: fetch events with persisted cursor (30 lines)
    state.with(
      request("GET", fetch_url + "?cursor=" + persisted.orValue(""))
        .do_request().as(resp, ...)
    )
  :
    // Phase B: create cursor, then immediately fetch events
    state.with(
      request("GET", create_url).do_request().as(r1,
        r1.StatusCode == 200 ?
          // fetch events — identical 30 lines copy-pasted from Phase A
          request("GET", fetch_url + "?cursor=" + r1.Body.decode_json().next_cursor)
            .do_request().as(r2, ...)
        : // create error
      )
    )
)
```

Phase B inlines the same fetch-and-process logic as Phase A. Two copies diverge over time.

**Solution — Phase B stores the cursor and defers fetching:**
```cel
state.?cursor.realtime.as(persisted,
  persisted.hasValue() ?
    // Phase A: fetch events with persisted cursor (30 lines — single copy)
    state.with(
      request("GET", fetch_url + "?cursor=" + persisted.orValue(""))
        .do_request().as(resp, ...)
    )
  :
    // Phase B: create cursor, persist it, let Phase A handle fetching
    state.with(
      request("GET", create_url).do_request().as(r1,
        r1.StatusCode == 200 ?
          {
            "events": [{"retry": true}],
            "cursor": {
              ?"realtime": r1.Body.decode_json().?next_cursor.optMap(v, string(v)),
            },
            "want_more": true,
          }
        : // create error
      )
    )
)
```

Phase B now makes one request, stores the cursor via a placeholder event, and sets `want_more: true`. The immediate re-evaluation enters Phase A with the cursor present — the fetch logic exists in one place. Each evaluation has a single HTTP concern.

**Trade-offs:** each step's success is durable independently — if the init succeeds and the subsequent fetch fails, the cursor is already persisted and the retry is a normal steady-state attempt. The init work is not repeated. However, it introduces a transient state (cursor stored, no events fetched yet) and requires a placeholder event with a matching drop processor.

---

#### Variant B — Intermediate result map within a single evaluation

CEL has no functions. When multiple branches need the same downstream processing, unify the branches into an intermediate result map, then bind it once before the shared code.

**Trade-offs:** the init and first fetch are atomic — both happen in one evaluation. But if the fetch fails after a successful init, the init's result (e.g. the created cursor) is lost because no event was published to persist it. Handling this requires careful use of error event forms (array to preserve cursor vs single-object to reset), adding complexity to the error paths.

**Problem — duplicated fetch block (anti-pattern):**
```cel
(stored != "") ?
  // fetch events with stored cursor + error handling (50 lines)
:
  create_cursor_request(...).as(rc,
    rc.StatusCode == 200 ?
      // identical fetch events + error handling (50 lines, copy-pasted)
    :
      // create error
  )
```

**Solution — intermediate result, shared downstream:**
```cel
(
  (stored != "") ?
    {"ok": true, "cursor": stored}
  :
    request("GET", create_url).do_request().as(rc,
      rc.StatusCode == 200 ?
        {"ok": true, "cursor": string(rc.Body.decode_json().?next_cursor.orValue(""))}
      :
        {
          "ok": false,
          "code": string(rc.StatusCode),
          "status": string(rc.Status),
          "body": string(rc.Body),
        }
    )
).as(result,
  !result.ok ?
    {
      "events": {
        "error": {
          "code": result.code,
          "id": result.status,
          "message": "GET /create: " + (size(result.body) != 0 ? result.body : result.status),
        },
      },
      "want_more": false,
    }
  :
    // Single copy of fetch + error handling using result.cursor
    request("GET", fetch_url + "?cursor=" + result.cursor)
      .do_request().as(resp, ...)
)
```

The intermediate map acts as a result type: `ok` distinguishes success from failure, and the remaining fields carry the payload for each case. This pattern keeps the fetch logic in one place and avoids the nesting that comes from inlining both paths.

---

## Map merge, update, and field removal

These are general-purpose map operations. They apply to any map — request headers, query parameter maps, response objects, cursor state, or intermediate values. All examples in this section can be verified with `mito`. See `tests/map_merge.txt` for testscript cases.

### Merge strategies

| Method | Existing keys | New keys |
|---|---|---|
| `with()` | Override | Add |
| `with_replace()` | Override | Ignore |
| `with_update()` | Keep | Add |

```cel
{"a": 1, "b": 2}.with({"a": 10, "c": 3})         // {"a": 10, "b": 2, "c": 3}
{"a": 1, "b": 2}.with_replace({"a": 10, "c": 3})  // {"a": 10, "b": 2}
{"a": 1, "b": 2}.with_update({"a": 10, "c": 3})   // {"a": 1, "b": 2, "c": 3}
```

`with()` is the most common — it's what `state.with()` uses. All three do a **shallow merge**: top-level keys are merged according to the strategy, but nested objects are replaced entirely, not merged recursively.

### Field removal with `drop()`

`drop()` removes fields by name, supporting dot-path navigation into nested structures:

```cel
m.drop("key")                              // remove a single key
m.drop(["a", "b"])                         // remove multiple keys
{"a": [{"b": 1, "c": 2}]}.drop("a.b")    // {"a": [{"c": 2}]} — dot-path into arrays
```

### Cursor key naming — avoid stuttering the parent

Keys inside `cursor` should not repeat the word "cursor". The parent path already provides context:

```cel
// WRONG — stutters the parent key
"cursor": {"realtime_cursor": ...}   // cursor.realtime_cursor
"cursor": {"next_cursor": ...}       // cursor.next_cursor

// CORRECT — concise, no redundancy
"cursor": {"realtime": ...}          // cursor.realtime
"cursor": {"next": ...}              // cursor.next
```

The same principle applies to sub-objects: `cursor.page.token` not `cursor.page.page_token`.

### Application: cursor state transitions via clobber

Since `with()` replaces nested objects entirely, omitting a field from the cursor output removes it. This is useful for managing state transitions — namespace transient pagination state in a sub-object so the phase end cleans it up:

```cel
// During backfill — transient pagination state in cursor.next
"cursor": {
  "bookmark": string(body.?first_id.orValue("")),
  "next": {"after_id": string(body.?last_id.orValue(""))},
}

// Backfill complete — omitting "next" removes it via clobber
"cursor": {
  "bookmark": cursor.bookmark,
}

// Selective update — keep all cursor fields, update one
"cursor": cursor.with({"bookmark": new_bookmark}),
```

Namespacing transient state (e.g. `cursor.next`) separately from persistent state (e.g. `cursor.bookmark`) means the entire sub-object is cleaned up by clobber when the phase ends. No need to remove individual fields or rely on sentinel values.

---

## Before/after: complete example

A typical deeply-nested generated program with cursor fields, pagination metadata, and URL construction stacked in one chain:

**Before (12 levels — anti-pattern):**
```cel
state.with(
  int(state.batch_size).as(limit,
    state.?cursor.next_token.orValue("").as(nt,
      state.?cursor.last_from.orValue(
        string(now - duration(state.initial_interval))
      ).as(since,
        (nt != "" ?
          {"limit": [string(limit)], "cursor": [nt]}
        :
          {"limit": [string(limit)], "since": [since]}
        ).format_query().as(qs,
          (state.url.trim_right("/") + "/v1/events?" + qs).as(reqUrl,
            request("GET", reqUrl).with({
              "Header": {"Authorization": ["Bearer " + state.api_key]},
            }).do_request().as(resp,
              resp.StatusCode == 200 ?
                resp.Body.decode_json().as(body,
                  (has(body.data) ? body.data : []).as(items,
                    body.?meta.next_cursor.orValue("").as(next,
                      {
                        "events": items.map(e, {"message": e.encode_json()}),
                        "cursor": {
                          "next_token": next,
                          "last_from": since,
                        },
                        "want_more": next != "",
                      }
                    )
                  )
                )
              : { "events": {"error": {...}}, "want_more": false }
            )
          )
        )
      )
    )
  )
)
```

**After (4 levels — correct):**
```cel
state.?cursor.next_token.orValue("").as(next_token,
  state.?cursor.last_from.orValue(
    string(now - duration(state.initial_interval))
  ).as(since,
    state.with(
      request("GET", state.url.trim_right("/") + "/v1/events?" + (
        next_token != "" ?
          {"limit": [string(int(state.batch_size))], "cursor": [next_token]}
        :
          {"limit": [string(int(state.batch_size))], "since": [since]}
      ).format_query()).with({
        "Header": {"Authorization": ["Bearer " + state.api_key]},
      }).do_request().as(resp,
        resp.StatusCode == 200 ?
          resp.Body.decode_json().as(body, {
            "events": body.?data.orValue([]).map(e, {"message": e.encode_json()}),
            "cursor": {
              "next_token": body.?meta.next_cursor.orValue(""),
              "last_from": since,
            },
            "want_more": body.?meta.next_cursor.orValue("") != "",
          })
        :
          {
            "events": {
              "error": {
                "code": string(resp.StatusCode),
                "id": string(resp.Status),
                "message": "GET /v1/events: " + (
                  size(resp.Body) != 0 ? string(resp.Body) : string(resp.Status)
                ),
              },
            },
            "want_more": false,
          }
      )
    )
  )
)
```

Changes made:
- `int(state.batch_size)` inlined (used once)
- `nt`, `since` extracted before `state.with()`
- `qs` and `reqUrl` eliminated — query and URL built inline
- `items` and `next` inlined into the result map
- Net result: 4 levels instead of 12, same logic, same correctness

---

## Well-structured reference integrations

These programs from the public `elastic/integrations` repository demonstrate clean structure. Read them for real-world examples of the techniques above:

- [vectra_rux audit](https://github.com/elastic/integrations/blob/main/packages/vectra_rux/data_stream/audit/agent/stream/cel.yml.hbs) — cursor bound before `state.with()`, 3 levels total
- [openai completions](https://github.com/elastic/integrations/blob/main/packages/openai/data_stream/completions/agent/stream/cel.yml.hbs) — sequential `.as(state, ...)` pipeline for state normalization, then shallow HTTP
- [o365 audit](https://github.com/elastic/integrations/blob/main/packages/o365/data_stream/audit/agent/stream/cel.yml.hbs) — long complex program kept readable with sequential state phases and comments
- [authentik event](https://github.com/elastic/integrations/blob/main/packages/authentik/data_stream/event/agent/stream/cel.yml.hbs) — minimal 2-level HTTP pattern, clean pagination
- [airlock_digital execution_histories](https://github.com/elastic/integrations/blob/main/packages/airlock_digital/data_stream/execution_histories/agent/stream/cel.yml.hbs) — checkpoint cursor, 2 levels inside `state.with()`
