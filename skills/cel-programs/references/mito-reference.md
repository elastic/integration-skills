# Mito CLI reference

Companion to the `cel-programs` skill. Covers everything needed to use mito for local CEL development: installation, CLI flags, input state, execution model, mock-first workflow, and the extension library.

---

## Installation

```bash
go install github.com/elastic/mito/cmd/mito@latest
go install github.com/elastic/stream/cmd/stream@latest
# Both install to ~/go/bin/ — ensure that is in PATH
mito -version
stream -version
```

---

## Core usage

```bash
mito -data state.json program.cel
```

- `-data <path>` — JSON file with the initial state (exposed as `state` in CEL)
- `<path>` — file containing the CEL program (must be last argument)

Quick one-off with process substitution:

```bash
mito -data <(echo '{"url": "http://localhost:8090"}') <(echo 'get(state.url)')
```

---

## CLI flags

| Flag | Purpose |
|------|---------|
| `-data <path>` | JSON input exposed as `state` |
| `-log_requests` | Log HTTP request/response traces to stderr |
| `-insecure` | Disable TLS certificate verification |
| `-dump always\|error` | Dump full evaluation state (always or only on error) |
| `-max_executions <n>` | Max re-evaluations; `-1` for unbounded |
| `-max_log_body <n>` | Max body length in request traces |
| `-coverage <path>` | Write execution coverage report to file |
| `-cfg <path>` | YAML config for run control |
| `-fold` | Enable constant folding optimization |
| `-use <libs>` | Libraries to load (default `"all"`) |
| `-version` | Print version and exit |

---

## Input state structure

The JSON file mirrors what the CEL input provides at runtime. Include `cursor` to simulate a subsequent run:

```json
{
  "url": "http://localhost:8090",
  "api_key": "test-key",
  "batch_size": 50,
  "initial_interval": "24h",
  "cursor": {
    "last_timestamp": "2025-01-15T10:00:00Z"
  }
}
```

---

## Execution model

1. mito loads the JSON as `state`
2. The CEL program evaluates to a single map value
3. `"events"` are printed and removed from state
4. If `"want_more": true` and events were present, the remaining state feeds the next evaluation
5. `"cursor"` values in the output would be persisted across restarts in the real CEL input

Control re-evaluation depth with `-max_executions`. Use `-1` to verify natural pagination termination (watch for infinite loops; interrupt with Ctrl+C).

---

## Mock-first development workflow

**This workflow is mandatory, not a suggestion.** Every CEL program must follow these steps in order. Do NOT write `cel.yml.hbs` until the program has been validated with mito. See also the workflow table in the parent `cel-programs` SKILL.md.

**Step 1 — Set up the system test mock first (before writing any CEL)**

Build the `elastic/stream` http-server config at `_dev/deploy/docker/files/config-<stream>.yml` with rules matching all API endpoints, auth, and pagination. Include **variable-capture catchall rules** (`"startTime": "{startTime:.*}"`) for APIs with dynamic query parameters — without them, timestamp-cursor programs loop indefinitely during system tests. Write `test-default-config.yml`. See `references/cel-system-tests.md` for rule format.

**Step 2 — Start the mock locally**

```bash
# Option A — stream CLI (preferred):
stream http-server --addr=:8090 --config=_dev/deploy/docker/files/config-<stream>.yml &
MOCK_PID=$!
# Option B — docker-compose:
cd _dev/deploy/docker && docker-compose up -d <service-name>
```

**Step 3 — Create a standalone `.cel` file and `state.json` for mito**

Write the CEL program as a plain `.cel` file (not inside `cel.yml.hbs`). Create `state.json` with the same keys your future template's `state:` block will inject, but using literal test values instead of Handlebars expressions. Point `url` at the local mock.

**How to translate planned template vars → mito `state.json`:** Look at the vars your API needs (auth credentials, batch size, initial interval, etc.) — these are the keys that will eventually appear in the `state:` block of `cel.yml.hbs`. Use the same key names with concrete test values:

| Future `cel.yml.hbs` state block | Corresponding `state.json` for mito |
|---|---|
| `api_key: {{api_key}}` | `"api_key": "test-key"` |
| `batch_size: {{batch_size}}` | `"batch_size": 50` |
| `initial_interval: {{initial_interval}}` | `"initial_interval": "24h"` |
| `resource.url: {{url}}/api/v1/events` | `"url": "http://localhost:8090/api/v1/events"` |

For OAuth integrations where `auth.oauth2` handles tokens (no credentials in state), the `state.json` only needs non-auth vars. For header-auth APIs, include the credential keys in state.

Example `state.json`:

```json
{
  "url": "http://localhost:8090",
  "api_key": "test-key",
  "batch_size": 50,
  "initial_interval": "24h"
}
```

To test subsequent-run behavior, add a `cursor` key matching the cursor structure your program will produce:

```json
{
  "url": "http://localhost:8090",
  "api_key": "test-key",
  "batch_size": 50,
  "cursor": {
    "last_timestamp": "2025-01-15T10:00:00Z"
  }
}
```

**Step 4 — Iterate the CEL program with mito**

```bash
mito -data state.json -log_requests program.cel   # basic run with request traces
mito -data state.json program.cel -max_executions 5  # test pagination
mito -data state.json program.cel -dump always    # inspect full state per evaluation
mito -data state.json program.cel -insecure       # self-signed TLS
```

Validate syntax at any point: `celfmt -s program.cel -o /dev/null`

Test with and without a `cursor` in the input state (first run vs subsequent).

**Step 5 — ONLY NOW write `cel.yml.hbs`**

This is the first and only point where you write the Handlebars template. Stop the mock, then embed the mito-validated program:

```bash
kill $MOCK_PID   # or: cd _dev/deploy/docker && docker-compose down
```

Copy the working CEL expression into `program: |` in `cel.yml.hbs`. Replace literal test values in the program (if any — most values come from `state` which is populated by Handlebars at the template level, not inside the CEL program). Add the Handlebars boilerplate (resource config, state block, tags, processors). Run `celfmt -s` on the template to format and simplify. Configure manifests per the `cel-programs` skill. See `references/cel-template-examples.md` for the complete template structure.

---

## Mapping mito → integration

| Concern | mito CLI | Integration (`cel.yml.hbs`) |
|---------|----------|-----------------------------|
| URL | `state.url` from JSON | `resource.url: {{url}}` |
| Auth credentials | included in JSON | `state:` block via Handlebars |
| Cursor | included in JSON for testing | persisted by the CEL input |
| Interval | N/A (runs once or via want_more) | `interval: {{interval}}` |
| TLS | `-insecure` flag | `resource.ssl:` config |
| State dump | `-dump always\|error` | `failure_dump` config (ga 8.18.0) |

---

## Quality standards during mito development

- **`state.with()`** — wrap the entire program. This carries directly into the integration template.
- **Optional chaining** — `state.?cursor.last_timestamp.orValue(default)` over `has()` chains.
- **Error message format** — include HTTP method and URL path without query params.
- **2-space indentation**, meaningful `.as(name, ...)` bindings, broken long lines.

---

## Mito extension library quick reference

| Library | Key functions |
|---------|---------------|
| HTTP | `get()`, `post()`, `request()`, `get_request()`, `post_request()`, `.do_request()`, `.with()`, `format_query()`, `parse_query()`, `format_url()`, `parse_url()` |
| Collections | `.with()`, `.drop()`, `.drop_empty()`, `.flatten()`, `.collate()`, `.keys()`, `.values()`, `.zip()`, `.min()`, `.max()`, `.sum()`, `.front()`, `.tail()`, `.with_replace()`, `.with_update()` |
| JSON | `.encode_json()`, `.decode_json()`, `.decode_json_stream()` |
| XML | `.decode_xml()` |
| Strings | `.trim()`, `.trim_right()`, `.trim_left()`, `.replace()`, `.split()`, `.join()`, `.to_upper()`, `.to_lower()` |
| Crypto | `bytes(val)` (function, not method), `.base64()`, `.base64_decode()`, `.hex()`, `.hex_decode()`, `.md5()`, `.sha1()`, `.sha256()`, `.hmac()`, `.uuid()` |
| Time | `now`, `now()`, `duration()`, `timestamp()`, `.format()`, `str.parse_time(layout, loc)` — **requires two args** (Go layout + timezone) |
| Regexp | `.re_match()`, `.re_find()`, `.re_find_all()`, `.re_find_submatch()`, `.re_find_all_submatch()`, `.re_replace_all()` |
| Printf | `sprintf()` |
| Try | `try()`, `is_error()` |
| Debug | `debug()` |
| MIME | `.mime()` |
| Limit | `rate_limit()` — **do not use in new integrations**; use config-only `resource.rate_limit.*` instead |

Full documentation: [pkg.go.dev/github.com/elastic/mito/lib](https://pkg.go.dev/github.com/elastic/mito/lib)

---

## Syntax pitfalls — common compilation failures

These cause `failed compilation` in mito. See `references/cel-incremental-build.md` for the full anti-patterns list with examples.

| Mistake | Error | Fix |
|---------|-------|-----|
| `(str + ":").bytes()` | `no such overload for 'bytes' applied to 'string.()'` | `bytes(str + ":")` — `bytes` is a function, not a method |
| `str.parse_time()` | `no such overload for 'parse_time'` | `str.parse_time("2006-01-02T15:04:05Z07:00", "UTC")` — requires layout + timezone |
| `(a, b, c)` tuple | `mismatched input ','` | CEL has no tuples; use a map `{"a": a, "b": b}` |
| Unbalanced `)` in deep `.as()` chains | `mismatched input ')' expecting <EOF>` | Keep nesting <=5 levels; verify every `.as(` has one `)` |

---

## Testscript harness

The mito repo (`$GOPATH/src/github.com/elastic/mito`, typically `~/src/github.com/elastic/mito`) includes a `testscript` harness (rogpeppe/go-internal). Test files live in `testdata/*.txt` and run via `go test`. Useful for repeatable regression tests — especially when HTTP responses need to be mocked at test time.

### Basic test format

```
mito -data state.json src.cel
cmp stdout want.json
! stderr .

-- state.json --
{"limit": 1, "api_key": "test"}
-- src.cel --
int(state.limit).as(n, {"result": n + 1})
-- want.json --
{
	"result": 2
}
```

### HTTP mocking with `serve`

`serve` starts a local HTTP server from a response file and sets `$URL`. Use `expand` to substitute `$URL` into the CEL source before running:

```
serve response.json
expand src_var.cel src.cel

mito -data state.json src.cel
cmp stdout want.json

-- response.json --
{"items": [1, 2, 3]}
-- state.json --
{"api_key": "test"}
-- src_var.cel --
request("GET", "${URL}/api/items").with({
  "Header": {"Authorization": ["Bearer " + state.api_key]},
}).do_request().as(resp,
  resp.Body.decode_json()
)
-- want.json --
{
	"items": [1, 2, 3]
}
```

`serve` returns the same body for all requests regardless of method or path. For multi-endpoint programs test each phase independently or use a response body containing fields for all phases.

### `want_more` pagination tests

Mito re-evaluates automatically when the result contains `"want_more": true`. Each evaluation's output is printed. Assert multiple JSON objects in `want.json` (one per evaluation) to test full pagination.

### Running a single test

```bash
cd ~/src/github.com/elastic/mito
go test -run TestScripts/your_test_name -v
```

### Incremental debugging workflow

When a CEL program fails in the harness:

1. Reproduce the error in a minimal testscript or standalone `.cel` + `.json` pair.
2. Strip the program to the smallest expression that still fails.
3. Add `debug()` calls around the failing area to inspect types and intermediate values.
4. Fix the type mismatch or logic error.
5. Build back up to the full program, testing at each step.

For multi-phase programs (subscribe-then-fetch), test each phase separately before combining.

---

## Debugging code patterns

### Inspecting intermediate values with `debug()`

`debug(tag, value)` logs `tag: value` to stderr and returns `value` unchanged. Chain it with `.as(_,` to insert probes anywhere without changing the expression's value:

```cel
debug("offset", offset).as(_,
  debug("limit", state.limit).as(_,
    int(body.num_found_items) > offset + int(state.limit)
  )
)
```

Full program example with multiple probes:

```cel
state.with(
  state.?cursor.last_timestamp.orValue("none").as(ts,
    debug("since_value", ts).as(_,
      request("GET", state.url.trim_right("/") + "?" + {
        "since": [ts],
      }.format_query()).do_request().as(resp,
        debug("status", resp.StatusCode).as(_,
          resp.StatusCode == 200 ?
            resp.Body.decode_json().as(body, {
              "events": body.map(e, {"message": e.encode_json()}),
            })
          :
            {"events": {"error": {"message": string(resp.Body)}}, "want_more": false}
        )
      )
    )
  )
)
```

Run with: `mito -data state.json program.cel -log_requests`

Combine with `-dump always` for full state visibility: `mito -data state.json program.cel -dump always -log_requests`

### Using `-dump error` for post-mortem

`-dump error` prints the full evaluation state only when the program fails. Useful during iterative development to avoid noise from successful runs:

```bash
mito -data state.json -dump error program.cel
```

### Probing fragile expressions with `try()` / `is_error()`

```cel
try(resp.Body.decode_json()).as(result,
  is_error(result) ?
    {"events": {"error": {"message": "JSON decode failed"}}, "want_more": false}
  :
    result.as(body, {
      "events": body.items.map(e, {"message": e.encode_json()}),
    })
)
```

---

## Compile-time vs runtime errors

Mito reports both compile-time and runtime errors. The distinction matters when debugging type mismatches.

Literal expressions with concrete types fail at **compile time** (`failed compilation`):

```cel
// Fails at compile time: double vs int
2.0 > 1
```

Inside `.as()`, bound variables are `dyn`, so the same mismatch **compiles but fails at runtime** (`failed eval`):

```cel
some_double_value.as(n, n > 1)  // compiles; fails at runtime with "no such overload"
```

This means type errors on real data are always runtime errors. Focus on the error message (e.g. `no such overload for '_>_' applied to '(double, int)'`) rather than the source position — positions inside `.as()` macros are often wrong due to a known CEL runtime issue.

---

## Rate limiting — config-only approach

**Do not use `rate_limit()` in new integrations.** Use config-only YAML settings (`resource.rate_limit.limit`, `resource.rate_limit.burst`) in `cel.yml.hbs` instead. The input framework enforces the limit transparently — no CEL program changes needed.

> **Full reference:** `references/cel-rate-limiting.md` — when to add config-only rate limit and retry settings.
