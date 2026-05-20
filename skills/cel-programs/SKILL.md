---
name: cel-programs
description: "Use for all CEL and mito work on integrations that collect from APIs — writing CEL programs, cel.yml.hbs templates, manifest configuration, mock-first development with the mito CLI, system test mock setup, and answering CEL/mito questions. Load this skill whenever any data stream uses the cel input type."
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# cel-programs


## When to use

Use this skill when tasks include:
- creating or editing `cel.yml.hbs` agent stream templates
- configuring data stream manifests for the `cel` input type
- writing CEL programs with pagination, cursor management, or authentication
- testing or debugging a CEL program locally with mito
- setting up system tests with mock APIs for CEL-based data streams
- prototyping a new CEL-based data stream's collection logic
- any CEL or mito question, regardless of context

## When not to use

Do not use this skill as the primary guide for:
- ingest pipeline processor design (`ingest-pipelines`)
- ECS field mapping (`ecs-field-mappings`)
- package scaffolding (`create-integration`)
- system test execution with the Elastic stack (`integration-testing` → `references/system-testing.md`)

## Mandatory workflow — mock → mito → template

**This is not a suggestion. Every CEL program MUST be developed in this order.** The subagent must not write `cel.yml.hbs` until the CEL program has been validated with mito against a running mock. Skipping steps or reordering causes failures that are hard to debug.

**Do NOT write more than ~10–15 new lines of CEL before running mito.** Build the program incrementally in phases (skeleton → error handling → event mapping → pagination → cursor guard), validating with mito after each phase. Writing a large program in one shot leads to cascading compilation errors that are extremely hard to debug. Follow the phased approach in `references/cel-incremental-build.md`.

| Step | Action | Output |
|------|--------|--------|
| **1. Create the system test mock** | Write the `elastic/stream` config at `_dev/deploy/docker/files/config-<stream>.yml` with rules matching all API endpoints. Write `test-default-config.yml`. | Mock config file, docker-compose service, test config |
| **2. Start the mock locally** | `stream http-server --addr=:8090 --config=...` | Running mock at `http://localhost:8090` |
| **3. Create a plain `.cel` file and `state.json`** | Write the CEL program as a standalone `.cel` file. Create `state.json` with the same keys the future `state:` block will contain, but with literal test values instead of Handlebars. Point `url` at the local mock. | `program.cel`, `state.json` in `/tmp` or working dir |
| **4. Run mito and iterate** | Build incrementally per `references/cel-incremental-build.md`: Phase 0 skeleton → Phase 1 error handling → Phase 2 events → Phase 3 pagination → Phase 4 cursor. Run `mito -data state.json -log_requests program.cel` after each phase. Do not proceed until mito output is correct. | Validated CEL program |
| **5. ONLY THEN write `cel.yml.hbs`** | Copy the working CEL expression into `program: \|` in the Handlebars template. Replace literal test values with `{{var}}` references. Configure manifests. | Final integration template |

**Step 3 detail — translating template vars to mito state:** When the future `cel.yml.hbs` will have a `state:` block like `api_key: {{api_key}}` and `batch_size: {{batch_size}}`, the `state.json` for mito testing uses the same key names with literal test values:

```json
{
  "url": "http://localhost:8090",
  "api_key": "test-key",
  "batch_size": 50,
  "initial_interval": "24h"
}
```

This mirrors the runtime state the CEL input would provide. Add `cursor` to test subsequent-run behavior.

For the full mock-first workflow details, CLI flags, execution model, and quality standards: load `references/mito-reference.md`.

---

## cel.yml.hbs template anatomy

The `cel.yml.hbs` file at `data_stream/<stream>/agent/stream/cel.yml.hbs` is a Handlebars template that renders the final CEL input configuration. It has these sections in order:

```yaml
interval: {{interval}}
resource.tracer:
  enabled: {{enable_request_tracer}}
  filename: "../../logs/cel/http-request-trace-*.ndjson"
  maxbackups: 5
{{#if proxy_url}}
resource.proxy_url: {{proxy_url}}
{{/if}}
{{#if ssl}}
resource.ssl: {{ssl}}
{{/if}}
{{#if http_client_timeout}}
resource.timeout: {{http_client_timeout}}
{{/if}}
resource.url: <constructed from vars>
state:
  <credentials and pagination config from vars>
redact:
  fields:
    - <sensitive state keys>
max_executions: <number, for heavy pagination>
program: |
  <CEL expression>
tags:
{{#if preserve_original_event}}
  - preserve_original_event
{{/if}}
{{#each tags as |tag|}}
  - {{tag}}
{{/each}}
{{#contains "forwarded" tags}}
publisher_pipeline.disable_host: true
{{/contains}}
{{#if processors}}
processors:
{{processors}}
{{/if}}
```

### Handlebars patterns

| Pattern | Purpose |
|---------|---------|
| `{{var_name}}` | Direct variable substitution |
| `{{#if var_name}}...{{/if}}` | Conditional block for optional config |
| `{{#each tags as \|tag\|}}` | Iteration over list vars |
| `{{#contains "forwarded" tags}}` | Check if list contains value |

### Key template fields

- `resource.url` — base URL, often constructed from multiple vars (e.g., `{{url}}/api/v1/endpoint`)
- `resource.headers` (ga 8.18.1) — static headers the same for every request (`Content-Type`, `Accept`, API version headers). Set here rather than in-program when headers never vary. Applied before auth headers.
- `state:` — block where manifest vars are injected as CEL state; credentials and pagination settings go here
- `redact.fields` — list state keys containing secrets to redact from debug logs
- `max_executions` — override default 1000 for integrations with heavy pagination (e.g., 5000)
- `program: |` — the CEL expression; must be a YAML literal block scalar

### Do NOT set `data_stream.dataset` in integration packages

**Integration packages** (`type: integration`) must **never** include `data_stream.dataset` in `cel.yml.hbs` or define a `data_stream.dataset` manifest var. The framework automatically routes documents to the correct data stream. Setting `data_stream.dataset` overrides this routing and causes documents to land in the wrong index — typically resulting in "0 hits" during system tests.

Only **input-type packages** (`type: input`) use `data_stream.dataset` because they have no predefined data streams.

## Data stream manifest configuration

The data stream `manifest.yml` defines the CEL input stream and its variables.

### Standard vars every CEL stream should include

| Var | Type | Purpose |
|-----|------|---------|
| `url` | text | API base URL |
| `interval` | text | Polling interval (e.g., `5m`) |
| `initial_interval` | text | Lookback window on first run (e.g., `24h`) |
| `enable_request_tracer` | bool | Enable HTTP request tracing |
| `http_client_timeout` | text | Request timeout (e.g., `30s`) |
| `proxy_url` | text | HTTP proxy URL |
| `ssl` | yaml | TLS configuration |
| `tags` | text (multi) | Event tags |
| `preserve_original_event` | bool | Keep original event |
| `processors` | yaml | Beat processors |

Auth-specific vars depend on the API (API key, OAuth client_id/secret/token_url, bearer token, etc.).

Declare `enable_request_tracer` in the data stream manifest, not at the input level. Input-level tracing enables logging for all data streams in the policy.

### Package-level vs data-stream-level vars

- **Package-level** vars in the root `manifest.yml` under `policy_templates[].inputs[].vars`: shared across streams (e.g., `url`, auth credentials)
- **Data-stream-level** vars in `data_stream/<stream>/manifest.yml` under `streams[].vars`: stream-specific (e.g., `interval`, `batch_size`, `initial_interval`)

## Scope of the CEL program

The CEL program's responsibility is **data collection only**:

1. **Fetch data** from the API endpoint(s)
2. **Handle pagination** — walk through all pages within a single polling cycle
3. **Manage cursor state** — store timestamps or page tokens in `cursor` so the next polling interval resumes where the last one left off, avoiding re-collection of already-fetched events
4. **Emit raw events** — output `{"message": e.encode_json()}` for each record

The CEL program does **not** handle:

- **Elasticsearch-level deduplication** — if overlapping time windows cause a few duplicate events to be collected, that is acceptable. The ingest pipeline or Elasticsearch `_id` routing handles dedup at index time, not the CEL program.
- **Field mapping or transformation** — the ingest pipeline handles parsing, ECS mapping, and enrichment.
- **Filtering by content** — unless the API supports server-side filtering parameters, do not filter events in the CEL program. Emit everything and let the pipeline decide.

Do not search the codebase for `_id`, `document_id`, or deduplication patterns. These are not CEL concerns.

## CEL program structure patterns

### Pagination strategy selection

| API behavior | Pattern | Key indicators |
|---|---|---|
| Returns total count + supports offset | Offset pagination | `total_count`, `offset`, `limit` in request/response |
| Returns records since a timestamp | Timestamp cursor | Time-range params, no explicit page tokens |
| Returns `Link` header with next URL | Link header | `Link: <url>; rel="next"` in response headers |
| Returns next-page URL in response body | Next-URL | `next`, `nextLink`, `@odata.nextLink` field in JSON |
| GraphQL with `pageInfo` | GraphQL cursor | `hasNextPage`, `endCursor` in `pageInfo` object |
| Multi-phase subscription/content flow | Multi-step state machine | Multiple API calls with work queues in state |

**Cursor timestamp selection** — use the **last** record's timestamp when the API sorts ascending; **first** when descending; `max()` with a regression guard when sort order is not guaranteed.

Full code, package references, and YAML snippets for each pattern: `references/cel-pagination-patterns.md`.

## Authentication patterns

Three strategies: **header** (credentials in `state:`, passed via `Header` map), **query parameter** (credentials appended to URL via `.format_query()`), **signed query** (HMAC signature computed in CEL). Config-level `auth.oauth2`/`auth.digest`/`auth.aws` applies to all requests including `.do_request()`; `auth.basic`/`auth.token` applies only to direct calls (`get()`, `post()`). Prefer input-level auth over in-program token fetching.

For full code examples, optional-header syntax, and config-level auth scope details: load `references/cel-auth-patterns.md`.

## State management rules

1. **`state.url`** is populated from `resource.url` config; must be preserved in output or hardcoded
2. **`cursor`** is the only state persisted across input restarts; store pagination positions and timestamps here
3. **`events`** array is removed after each evaluation; never rely on it in subsequent runs
4. **`want_more: true`** triggers immediate re-evaluation, but only if `events` is non-empty. **Pagination continuation guardrail:** when a next-page cursor/token exists, always set `want_more: true` regardless of how many events were collected on the current page. Tying `want_more` to `size(events) > 0` stalls pagination silently — the next cursor is valid, and an empty `events` array is safe to emit. The correct pattern is `"want_more": next_cursor != ""`.
5. **All other state keys** are retained within a session but lost on restart — use `state.with()` to propagate them automatically
6. **Numbers** are serialized as floats in state JSON; cast with `int()` when using as integers
7. **Optional access** with `state.?cursor.last_timestamp.orValue(default)` prevents errors when cursor is absent
8. **Secrets** — every sensitive field in `state` must have a corresponding `redact` entry. `state.secret` is always redacted automatically. When `secret_state` (ga 9.4.0) is available, prefer it.
9. **Cursor updates require a published event** — the input only persists cursor updates when at least one event is published. If a program updates the cursor but returns zero events, the cursor change is lost.
10. **Do not duplicate request/response handling across branches** — when an initialization branch (cursor creation, subscription, token exchange) and a steady-state branch both need the same fetch logic, consolidate it. Two approaches: split the init into a separate evaluation via `want_more: true` (Technique 6 Variant A), or use an intermediate result map to unify the branches within one evaluation (Variant B). Both are valid — see `references/cel-code-style.md` Technique 6 and the init-then-steady-state pattern in `references/cel-pagination-patterns.md`.
11. **Nesting depth** — `.as()` chain depth must not exceed 5 levels on any execution path. HTTP programs must target 2 levels inside `state.with()` (`resp` + `body`). Cursor defaults, window bounds, and page tokens must be extracted as pre-bindings *before* `state.with()`. Single-use values such as `int(state.batch_size)` must be inlined at the call site, not wrapped in `.as()`. Load `references/cel-code-style.md` for flattening techniques and before/after examples.

### Map merge and field removal

`with()`, `with_replace()`, `with_update()`, and `drop()` are general-purpose map operations — they work on any map, not just state or cursor. `with()` does a **shallow merge**: nested objects are replaced entirely. This makes it a tool for cursor state transitions (omitting a sub-object removes it via clobber) as well as for building request headers, transforming response data, and constructing intermediate maps. Full semantics and examples: `references/cel-code-style.md`.

## Event output format

**Events must contain ONLY `"message"`** — `{"message": e.encode_json()}`. Do not set `@timestamp` or any other field; the framework adds `@timestamp`, and duplicates cause silent document rejection in ES 9.x. See `references/cel-idioms.md` for correct/incorrect examples.

## Response handling

**`resp.Body.decode_json()`** — the `bytes(resp.Body)` wrapper was required in older runtime versions but is no longer needed. Use `resp.Body.decode_json()` directly.

## Error handling

Every CEL program must handle HTTP errors. Two forms:

- **Single-object error (retry):** `"events": {"error": {...}}` — logs at ERROR, sets degraded status, **deletes the cursor** so the next evaluation retries. Use when data was not collected.
- **Array error (advance):** `"events": [{"error": {...}}]` — cursor **is** updated. Use when the program should advance past the error. Requires a `terminate` processor in the ingest pipeline (ES 8.16.0+).

Error message format: `"METHOD path: body-or-status"`. Code examples: `references/cel-idioms.md`.

### Placeholder events

When advancing the cursor with no real events, emit a placeholder (`[{"retry": true}]`) and add a `- drop_event.when.equals.retry: true` entry in the `processors:` section so it is discarded before indexing. Full pattern and alternatives: `references/cel-idioms.md`.

## Rate limiting and retry

**Do NOT implement rate limiting or retry logic in the CEL program.** No `rate_limit()` calls, no `"rate_limit"` state propagation, no 429-specific branches, no retry loops. These add excessive nesting and complexity for marginal benefit.

When an API has a documented rate limit, use config-only YAML settings in `cel.yml.hbs`:

```yaml
resource.rate_limit.limit: 10   # max requests per second
resource.rate_limit.burst: 5    # max burst above sustained rate
```

When custom retry behavior is needed, use config-only YAML settings:

```yaml
resource.retry.max_attempts: 5    # default: 5
resource.retry.wait_min: 1s       # default: 1s
resource.retry.wait_max: 60s      # default: 60s
```

The input framework enforces both transparently. See `references/cel-rate-limiting.md` for guidance on when to add these settings.

## Type safety

**Avoid `dyn()`** — defeats type checking. Rarely needed in practice.

**All numbers are float64** — the CEL input transmits all numbers as `float64`. Numbers >=1e7 render in scientific notation in Elasticsearch. Convert intended-integer fields to strings in the CEL program or via ingest pipeline. Safe integer range: [-(2^53 - 1), 2^53 - 1].

## Debugging aids

- **`debug(tag, value)`** — logs to `cel_debug` at DEBUG level.
- **`try(expr)` / `is_error(value)`** — structured error handling without crashing the program.
- **`failure_dump`** (ga 8.18.0) — full evaluation state dump on failure. Note: dumps may contain secrets.
- **`remaining_executions`** (ga 9.2) — how many evaluations remain in the `max_executions` budget.

---

## Mito CLI

Mito (`github.com/elastic/mito`) is the local CEL evaluation CLI. **A CEL program that has not been tested with mito is not acceptable.** Follow the mandatory workflow at the top of this skill: mock → mito → template. Do NOT write `cel.yml.hbs` until the program passes mito validation.

For installation, CLI flags, input state structure, execution model, the full mock-first workflow steps, mito→integration mapping, and quality standards: load `references/mito-reference.md`.

---

## Data anonymization

**All data committed to the repository must be fully anonymized.** This applies to default values in manifest vars (use `https://api.example.com`), example values in CEL state, mock API responses, pipeline test fixtures from CEL output, and sample payloads captured during mito prototyping.

Refer to the `anonymize-logs` skill for the full anonymization policy and placeholder conventions.

## Handoff to other skills

- `integration-testing` → `references/system-testing.md` to run system tests (the mock API is already in place from CEL development)
- `integration-testing` → `references/pipeline-testing.md` to validate ingest pipeline behavior on CEL-produced events
- `create-integration` skill for overall package layout

## Reference files

**IMPORTANT**: These reference files contain the actual working code examples and patterns. The summaries above are not sufficient to write correct CEL programs — you MUST load the relevant references before writing code.

**Always load these five** when building a CEL program — **in this order** (mock/mito before templates):

| File | Contains | Load order |
|------|----------|------------|
| `references/cel-system-tests.md` | Mock API setup with elastic/stream, docker-compose config, rule format, variable-capture patterns, GraphQL mock examples, hit_count calculation, and debugging 0-hits failures | 1st — you need this before writing any CEL |
| `references/cel-incremental-build.md` | **Mandatory** phased build ladder (skeleton → error handling → events → pagination → cursor), syntax anti-patterns that cause compilation failures (`bytes()`, `parse_time()`, tuples, unbalanced parens), and debugging guidance | 2nd — you MUST follow this phased approach; do not write the full program before validating a skeleton |
| `references/mito-reference.md` | Mito CLI flags, input state structure, mock-first workflow, translating template vars to state.json, extension library quick-reference, syntax pitfalls, testscript harness | 3rd — you need this to develop and validate the program |
| `references/cel-template-examples.md` | Complete working `cel.yml.hbs` examples (minimal GET, paginated timestamp cursor, OAuth, GraphQL cursor) with corresponding manifest configs — **these are FINAL output; do not write templates until mito passes** | 4th — only needed at step 5 of the workflow |
| `references/cel-code-style.md` | **Nesting discipline**: the 3-level HTTP core rule, six flattening/structuring techniques (including intermediate result maps for shared logic), shallow merge semantics, cursor namespacing with clobber, merge strategies (`with`/`with_replace`/`with_update`), `drop()`, and links to well-structured reference integrations — **must read before writing any multi-line CEL** | 5th — read this before writing your CEL program so structure is right from the start |

**Load these based on the task:**

| File | Load when |
|------|-----------|
| `references/cel-pagination-patterns.md` | Writing any pagination logic — all 6 patterns with code |
| `references/cel-auth-patterns.md` | Implementing authentication — header, query param, signed, and config-level auth patterns |
| `references/cel-rate-limiting.md` | Rate limiting policy — config-only approach, when to add `resource.rate_limit.*` and `resource.retry.*` settings |
| `references/cel-idioms.md` | Quick-reference for common idioms, HTTP request patterns, structure conventions |
| `references/cel-polymorphic-patterns.md` | Choosing between pure-CEL, mito lib, and config approaches for auth, headers, rate limiting — version-tagged |
| `references/cel-expression.md` | Expression-specific reference: interface contract, translation framing (Python→CEL), incremental build phases, core structure, event output, error handling, pagination, state management, syntax rules, quality checklist |
| `references/cel-taxonomy.md` | Taxonomy classification: pagination and state management classes, least-complexity principle, mapping to skill vocabulary, how to classify from test-api.py |
| `references/cel-complexity-baselines.md` | Per-pattern-class complexity baselines from a ceplx survey of 316 programs, skip threshold, reviewer challenge examples, diagnostic interpretation |
| `references/expression-builder-subagent-guidance.md` | Subagent operating manual for the **cel-expression-builder**: translates test-api.py into a validated `.cel` file + taxonomy classification. Does not touch templates, manifests, or mocks. |
| `references/reviewer-subagent-guidance.md` | Subagent operating manual for the **cel-expression-reviewer**: checks generated CEL against complexity baselines and source fidelity, produces specific challenges or accepts |
| `references/cel-function-reference.md` | Looking up available CEL functions per extension and their first mito version |
| `references/builder-subagent-guidance.md` | **Always-embedded** subagent operating manual for the **cel-program-builder** orchestrator: scope boundaries, skill-load sequence, the 9-step mock-first / mito-incremental workflow with mock completeness gate, delegation to cel-expression-builder, reporting contract |

See also: [CEL input docs](https://www.elastic.co/docs/reference/beats/filebeat/filebeat-input-cel) · [Mito lib docs](https://pkg.go.dev/github.com/elastic/mito/lib) · [Mito repo](https://github.com/elastic/mito) · [CEL language spec](https://cel.dev/)
