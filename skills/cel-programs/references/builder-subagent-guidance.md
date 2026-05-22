# CEL program builder subagent guidance

Operating manual for a subagent building or modifying CEL programs on behalf
of the `create-integration` or `maintain-integration` orchestrator.

This subagent is an **orchestrator** for CEL integration development. Its
primary responsibilities are mock design, mock validation, template wrapping,
manifest configuration, and system test setup. For the CEL expression itself,
it delegates to the **cel-expression-builder** subagent (see
`references/expression-builder-subagent-guidance.md`), which translates
test-api.py into a validated `.cel` file.

The orchestrator dispatches you with a brief task prompt that points you at
this file by path. **Read this entire file end-to-end before doing any other
work**, then read the skills and reference files listed in the "First steps"
section below — they are mandatory. The orchestrator does not paste this
file's content into your task prompt (to avoid burning context twice); you
load it here in your own fresh context.

The orchestrator's task prompt tells you **what** to build or fix, **which
package and data stream** to work on, **the API details and sample data**, and
**any constraints**. This file tells you **how to operate** as a CEL program
builder subagent. Follow both.

## Scope

Your responsibility is strictly limited to:

- Building the `cel.yml.hbs` template (the CEL program and its Handlebars
  wrapper) at `data_stream/<stream>/agent/stream/cel.yml.hbs`
- Configuring the data stream manifest vars for CEL input (`data_stream/<stream>/manifest.yml`)
  and any package-level vars in the root `manifest.yml` that the template
  consumes
- Setting up system test mock API files (`_dev/deploy/docker/docker-compose.yml`,
  `_dev/deploy/docker/files/config-<stream>.yml`) and the test config
  (`data_stream/<stream>/_dev/test/system/test-default-config.yml`)
- Defining initial field mappings (`fields/fields.yml`) for the raw API
  response fields the CEL program emits

**You do NOT**:

- Create or modify pipeline test fixtures (`_dev/test/pipeline/`) — the
  pipeline builder owns these (see
  `ingest-pipelines/references/builder-subagent-guidance.md`)
- Create or modify the ingest pipeline (`elasticsearch/ingest_pipeline/`) or
  `fields/ecs.yml` — the pipeline builder handles this
- Create or modify `sample_event.json` — generated only by
  `elastic-package test system --generate`, run by the system-test subagent
  (see `integration-testing/references/builder-system-test-subagent-guidance.md`)
- Run system tests (`elastic-package test system`) — the system-test subagent
  runs them after the pipeline builder completes pipeline work for the data
  stream
- Implement document deduplication logic — overlapping windows producing a
  small number of duplicates is acceptable; dedup is not a CEL concern

If the orchestrator's prompt asks for pipeline work, sample event handling,
or system test execution rather than CEL program development, stop and report
that the wrong subagent or guidance file was invoked.

## Skill authority

The rules and patterns in the `cel-programs` skill and its reference files are
the **authoritative source of truth**. When examining reference integrations
in the official `elastic/integrations` repository for patterns
(authentication, pagination structures, mock configs), many existing
integrations contain legacy patterns that predate current standards —
**always follow the skills over patterns observed in other integrations.**

## First steps — read the skills and their references

Before doing any work, read these skill files **and the specific reference
files listed** to load the rules, patterns, and working code examples you must
follow. Reading only the SKILL.md files is not sufficient — the reference
files contain the working code examples and patterns you need.

1. **`cel-programs` skill** (SKILL.md) — start with the **Mandatory workflow**
   table at the top, then template anatomy, manifest configuration, state
   management rules, error handling, and event output format. Then read these
   references **in this order** (mock/mito references before template
   examples — order matters):
   - **`references/cel-system-tests.md`** — MUST READ FIRST: mock API setup
     with `elastic/stream`, docker-compose config, rule format, variable-
     capture patterns, hit_count calculation, debugging 0-hits failures
   - **`references/cel-incremental-build.md`** — MUST READ SECOND: the
     **phased build ladder you MUST follow** (skeleton → error handling →
     events → pagination → cursor), syntax anti-patterns that cause
     compilation failures (`bytes()`, `parse_time()`, tuples, unbalanced
     parens), and debugging guidance. **You will build the CEL program in
     these phases — do NOT write the full program before validating a
     skeleton.**
   - **`references/mito-reference.md`** — MUST READ THIRD: mito CLI flags,
     input state structure, mock-first workflow steps, translating template
     vars to `state.json`, extension library quick-reference, syntax pitfalls
   - **`references/cel-template-examples.md`** — MUST READ FOURTH (these are
     FINAL output — do not write templates until mito validation passes):
     complete working `cel.yml.hbs` examples with manifest configs
   - **`references/cel-code-style.md`** — MUST READ FIFTH: nesting discipline
     rules, the 2-level HTTP core structure, flattening techniques with
     before/after examples — **read this before writing any multi-line CEL so
     structure is correct from the start**
   - **`references/cel-pagination-patterns.md`** — read when writing
     pagination logic: all 6 pattern types with code
   - **`references/cel-auth-patterns.md`** — read when implementing
     authentication
   - **`references/cel-rate-limiting.md`** — config-only rate limiting and
     retry policy (do **not** use `rate_limit()` in CEL programs)
   - **`references/cel-idioms.md`** — quick-reference for common idioms, HTTP
     patterns, structure conventions (anti-patterns table at the top)
   - **`references/cel-polymorphic-patterns.md`** — read when choosing between
     config auth, lib functions, and manual CEL: version-tagged tables

2. **`integration-testing` skill** (SKILL.md) — then read
   **`references/system-testing.md`** fully, focusing on the CEL system test
   section, mock API setup, and required test config fields
   (`wait_for_data_timeout: 1m`, `service`, vars, `assert.hit_count`).

3. **`elastic-package-cli` skill** — `elastic-package format / lint / check`
   and the build commands you will run.

4. **`anonymize-logs` skill** — placeholder conventions for any data
   committed (mock responses, default manifest values, sample state values).

Read all skills and their MUST READ references before writing any CEL code.
Do not rely on the SKILL.md summaries — the reference files contain the
working code examples and patterns you must follow.

## Mandatory workflow — do NOT skip or reorder steps

The core principle: **build the system test mock first, then develop the CEL
program against it with mito, then — and only then — write the template.**
This eliminates custom Python mock servers and keeps the mock, the CEL
program, and the system test infrastructure consistent from the start.

**CRITICAL — do NOT write `cel.yml.hbs` first.** Even if you have template
examples, API documentation, and a clear picture of the final template, you
MUST follow this order:

1. Investigate the API via test-api.py (the ground truth)
2. Derive the system test mock from test-api.py's request/response flow
   (with the full two-round flow described in step 3c)
3. Start the mock locally
4. Validate the mock with test-api.py (hard gate — do not proceed until
   it passes)
5. Verify mock completeness gate (2+ pages, terminal page, second-round
   cursor resume, optional regression guard)
6. Build the CEL expression (preferred: delegate to cel-expression-builder
   with test-api.py as the translation source)
7. ONLY THEN write `cel.yml.hbs` by wrapping the validated program in
   Handlebars
8. Run `celfmt -s -agent`, configure manifest vars, define field mappings,
   validate

Writing the template first and trying to extract a `.cel` file from
Handlebars for mito does not work — Handlebars syntax is not valid CEL.
Always develop the raw CEL program first, validate it with mito, then wrap it
in the template.

If the orchestrator provides real API credentials, you may **additionally**
test against the live API for highest-confidence validation, but mock-first
development is always the primary path — it is faster, reproducible, and
does not depend on API availability or rate limits.

### Step 1 — investigate the API via test-api.py

**Start with the research `test-api.py` script.** This is always present
for CEL integrations and is the ground truth — it has been tested against
the real API. Read its collection function (`run_collection()` or
equivalent) to identify:

- Base URL and endpoint paths
- Authentication method (header auth, query parameter auth, signed query
  params, OAuth2 client credentials, OAuth2 token refresh)
- Pagination pattern — which loop structure and termination condition does
  the Python script use? Map it to the patterns in the `cel-programs`
  skill / `references/cel-pagination-patterns.md`
- Response JSON structure (where the event array lives, total count fields,
  next-page indicators) — visible in the script's response navigation
- Time-range filtering parameters
- Batch size constraints
- Error handling branches (status codes, missing fields, malformed responses)

The research brief provides supplementary context (field meanings, edge
cases not exercised by the script). If the API documentation is incomplete
and credentials are available, use `curl` or `python` to make exploratory
requests against the real API, but the Python script remains the primary
specification.

### Step 2 — derive the system test mock from test-api.py

Before writing any CEL code, build the mock HTTP API the system test will
use. The mock is **derived from** test-api.py's request/response flow, not
independently designed from the research brief. The Python script defines
which endpoints are called, what request shapes are sent, and what
response structures are expected — the mock replays this interaction with
anonymised data. If a `trace.json` exists from a real API run, use it as
a reference for response structure and field presence.

Use the `elastic/stream` http-server — do NOT write a custom Python mock.

1. Define the mock service in `_dev/deploy/docker/docker-compose.yml` using
   `docker.elastic.co/observability/stream:v0.20.0`.
2. Create a rule-based config file at
   `_dev/deploy/docker/files/config-<stream>.yml` that models the **complete
   API request flow** the CEL program will make. Follow the patterns and
   rule examples in `references/cel-system-tests.md` — mock API flow design,
   variable capture (`{varName:.*}`), OAuth token endpoints, GraphQL
   request-body matching. A poorly designed mock is the single largest cause
   of system test failures.
3. Write the test config at
   `data_stream/<stream>/_dev/test/system/test-default-config.yml` with:
   - `wait_for_data_timeout: 1m` (required — caps how long
     `elastic-package test system` waits for data)
   - `input: cel`
   - `service: <mock-service-name>`
   - Vars pointing to `http://{{Hostname}}:{{Port}}` — never a real URL
   - **`interval: 2s`** — short enough that the agent completes pagination,
     persists the cursor, and fires a second evaluation cycle that verifies
     cursor persistence within the test window
   - `assert.hit_count` summing events from **both** evaluation rounds (the
     first pagination round + the second cursor-based round) — see step 3c

### Step 3 — start the mock server locally

Start the `elastic/stream` mock so mito can make requests against it.

**Option A — `stream` CLI (preferred, lightweight):**

```bash
stream http-server --addr=:8090 --config=_dev/deploy/docker/files/config-<stream>.yml &
MOCK_PID=$!
```

The mock listens on `http://localhost:8090`. Use this URL in your mito input
state.

**Option B — docker-compose:** start only the mock service from the system
test docker-compose:

```bash
cd _dev/deploy/docker
docker-compose up -d <service-name>
```

Find the mapped port with `docker-compose port <service-name> 8090` and use
`http://localhost:<mapped-port>` in your mito input state.

Either approach gives mito the exact same mock the system test will use —
no divergence between what mito tests and what `elastic-package test system`
tests.

### Step 3b — validate the mock with test-api.py (hard gate)

**This is a hard gate, not optional.** The research `test-api.py` script
is always present for CEL integrations. Run it against the running mock
before writing any CEL:

```bash
python3 test-api.py --base-url http://localhost:8090 --mock
```

If the script fails against the mock, assume the mock is wrong unless
there is an obvious flaw in the script (wrong endpoint path, missing
optional header). Fix the mock rules to match what the script expects
(missing query params, wrong response shape, missing auth endpoint, wrong
status codes).

Do NOT proceed to step 3c until test-api.py passes against the mock. This
gate ensures the mock faithfully models the API interaction that the CEL
program will be translated from.

If a `trace.json` exists from a real API run, compare the mock's responses
against it as an additional fidelity check — field presence, response
shape, and pagination state transitions should match.

### Step 3c — verify mock completeness gate (hard gate)

Before writing any CEL, verify the mock implements the **full two-round
pagination flow**. This is a hard gate, not a suggestion:

- **Round 1 — initial fetch with full pagination:**
  - **Page 1**: returns events + a non-terminal pagination signal
    (`hasNextPage: true`, non-empty next cursor, `offset < total`)
  - **Page 2**: returns events + a non-terminal signal (at minimum 2 pages
    of results)
  - **Terminal page**: returns events (or empty) + the terminal pagination
    signal (`hasNextPage: false`, empty next cursor, `offset >= total`)
    that stops `want_more`.

- **Round 2 — cursor-persisted resume (interval-driven):**
  After the short `interval: 2s`, the agent fires a new cycle using the
  persisted cursor bookmark (e.g. `last_from`). The mock must have a rule
  matching this second-round request pattern; this round returns at least
  one additional event so cursor persistence is observable in `hit_count`.

- **Optional auth route:** include an auth endpoint rule when authentication
  is not a static API key (OAuth, token refresh).

- **Regression guard (recommended):** add a catch-all rule that fires if the
  cursor was incorrectly cleared (e.g. the program re-requests from
  `now - initial_interval` instead of using the persisted bookmark). The
  rule returns extra synthetic events that cause `hit_count` to exceed the
  expected value, failing the test if the cursor regresses.

Sum events from all pages across both rounds — that sum is the
`assert.hit_count` value in `test-default-config.yml`.

Do NOT proceed to step 4 until the mock implements all of the above.

### Step 4 — build the CEL expression

**Every CEL program must be developed and validated through mito.** This is
not optional. The mock from step 3 is already running.

#### Preferred path — delegate to cel-expression-builder

When the orchestrator provided a `test-api.py` script (which is always the
case for new CEL integrations), launch a **cel-expression-builder** subagent
with:

- The `test-api.py` file content
- A `state.json` with literal test values (url pointing at the running mock,
  credentials, batch_size, initial_interval)
- The mock URL
- The research brief (if available)

Point the subagent at `references/expression-builder-subagent-guidance.md`
(relative to the `cel-programs` skill) as its operating manual and instruct
it to read that file (plus the skill SKILL.md it lists) end-to-end before
doing any other work. **Do NOT read the guidance file yourself or paste its
contents into the task prompt** — pass only the path plus the task-specific
context. The expression builder returns a validated `.cel` file and a
taxonomy classification.

#### Step 4b — structured review (when complexity warrants it)

After receiving the `.cel` file and classification from the expression
builder, run `ceplx -diag -json program.cel` to get complexity metrics.

**Skip the review** if cognitive complexity is below the class p50 (from
`references/cel-complexity-baselines.md`) **and** below 40.

Otherwise, launch a **cel-expression-reviewer** subagent with:

- The generated `.cel` file
- The taxonomy classification
- The `ceplx -diag -json` output
- The `test-api.py` file content
- The research brief

Point the subagent at `references/reviewer-subagent-guidance.md` (relative
to the `cel-programs` skill) as its operating manual and instruct it to
read that file end-to-end before doing any other work. **Do NOT paste the
guidance file's contents into the task prompt** — pass only the path plus
the task-specific context.

If the reviewer returns **revise**, pass the challenges back to the
expression builder (resume the same subagent) and ask it to address
each challenge — either justify the current approach or produce a
revised `.cel` file.

If a revision is produced, re-run `ceplx` and compare. Select the
version with lower complexity unless the revision drops fidelity.

Proceed to step 5 with the final `.cel` file.

#### Direct path — build expression yourself

If the orchestrator did not provide `test-api.py`, or if you are fixing an
existing CEL program rather than building one from scratch, build the
expression directly following the incremental approach below.

**Build incrementally — never write the full program at once.** Even if you
"know" what the final program looks like, follow the phased ladder in
`references/cel-incremental-build.md`. Each phase is a hard gate; do not add
the next phase until the current one runs cleanly under mito.

| Phase | Adds | Validation command |
|-------|------|--------------------|
| 0 — skeleton | `state.with()` + single request + `"events": []` | `mito -data state.json -log_requests program.cel` |
| 1 — error handling | `resp.StatusCode == 200 ?` branch with error event | `mito -data state.json -log_requests program.cel` (test both success and forced-error inputs) |
| 2 — event mapping | `resp.Body.decode_json()` + `body.items.map(e, {"message": e.encode_json()})` | `mito -data state.json -log_requests program.cel` |
| 3 — pagination | `want_more` + cursor/offset/token tracking | `mito -data state.json -log_requests -max_executions 5 program.cel` (must terminate naturally) |
| 4 — cursor guard | `state.?cursor.field.orValue(...)` first-run vs subsequent-run | `mito` with both `state.json` (no cursor) and `state_cursor.json` (with cursor) |
| 5 — complex branching | multi-phase, time-window chunking, worklist patterns | `mito` after each branch addition; never add all branches at once |

If mito reports a compilation error, do NOT rewrite the program from
scratch. Revert to the last working phase and re-add changes incrementally.
Do NOT use Python, sed, or bash scripts to modify `.cel` files — use the
editor's StrReplace/Write tools only.

**Nesting discipline applies at every phase.** Before writing any multi-line
CEL, read `references/cel-code-style.md`. Target the 2-level HTTP core
inside `state.with()` (`resp` + `body`); extract cursor defaults, window
math, page tokens, and URL construction as pre-bindings *before*
`state.with()`; inline single-use values such as `int(state.batch_size)`. The
hard cap is 5 `.as()` levels on any execution path. If at any phase nesting
exceeds this, STOP and refactor using the flattening techniques before
continuing — do NOT defer.

You can also validate and simplify the standalone `.cel` syntax with
`celfmt` during this step — it works on plain `.cel` files too:

```bash
celfmt -s -i program.cel -o /dev/null
```

If `celfmt` hangs on a standalone `.cel` file (a known issue in some
environments), skip it during prototyping and rely on `celfmt -s -agent`
against `cel.yml.hbs` once the template exists in step 6.

For complex multi-phase programs (e.g. subscribe-then-fetch), test each
phase separately by adjusting `state.json` or the mock rules so mito
exercises one branch at a time before integrating them.

If the orchestrator provided real API credentials, you may additionally
point a copy of the program at the live API for highest-confidence
validation. Mock-first development remains the primary path.

### Step 5 — write `cel.yml.hbs` (only after mito validation passes)

**Do not reach this step until step 4 is complete and the program works in
mito.** Embed the **mito-validated** CEL program into
`data_stream/<stream>/agent/stream/cel.yml.hbs` following the template
anatomy in the `cel-programs` skill (and the worked examples in
`references/cel-template-examples.md`):

- `interval: {{interval}}`, resource block (`tracer`, `proxy`, `ssl`,
  `timeout`) using standard Handlebars conditionals
- `resource.url` constructed from template vars
- `resource.headers` (ga 8.18.1) for any static headers identical across
  every request (`Accept`, `Content-Type`, API version headers) — prefer
  this over per-request header construction in CEL
- `state:` block injecting credentials and pagination config from manifest
  vars
- `redact.fields` listing all secret state keys
- `max_executions` if heavy pagination is expected (override the default
  1000)
- `program: |` containing the validated CEL expression as a YAML literal
  block scalar — every line indented exactly 2 spaces relative to
  `program:`
- Tags, `publisher_pipeline`, and `processors` blocks using the standard
  patterns

Write the full program with StrReplace/Write rather than hand-pasting and
re-indenting — transcription errors (extra parentheses, wrong indentation
levels) are easy to introduce in deep `.as()` nesting. Then use
`celfmt -s -agent` (step 6) to normalize indentation and verify the result.

### Step 6 — format and simplify with `celfmt -s -agent`

After writing the template, run `celfmt -s -agent` to validate, simplify,
and format the embedded CEL. The `-s` flag inlines single-use `.as()`
bindings, eliminates boolean comparisons (`x == true` → `x`,
`x == false` → `!x`), and rewrites `has(x.f) ? x.f : d` to
`x.?f.orValue(d)`. The `-agent` flag tells `celfmt` the input is an agent
template (YAML with embedded CEL in the `program:` block).

**WARNING: `-o` overwrites the output file unconditionally — even on syntax
errors.** Always validate first before writing back:

```bash
cd data_stream/<stream>/agent/stream

# Step 1: validate only — /dev/null protects the source if there are errors.
celfmt -s -agent -i cel.yml.hbs -o /dev/null

# Step 2: only if step 1 succeeds (exit code 0), apply formatting in place.
celfmt -s -agent -i cel.yml.hbs -o cel.yml.hbs
```

Or as a single safe one-liner:

```bash
celfmt -s -agent -i cel.yml.hbs -o /dev/null && celfmt -s -agent -i cel.yml.hbs -o cel.yml.hbs
```

If validation fails (non-zero exit, diagnostics on stderr), fix the source
and re-run validation. Do not proceed until validation passes cleanly.

### Step 7 — configure the data stream manifest

Edit `data_stream/<stream>/manifest.yml`:

- Set `input: cel` and `template_path: cel.yml.hbs`
- Define stream-level vars (`interval`, `initial_interval`, `batch_size`,
  and any stream-specific settings)
- Ensure package-level vars in the root `manifest.yml` cover shared settings
  (`url`, auth credentials)
- Include the standard CEL stream vars from the `cel-programs` skill
  (`enable_request_tracer`, `http_client_timeout`, `proxy_url`, `ssl`,
  `tags`, `preserve_original_event`, `processors`)
- **Strip every var the scaffold added that is not consumed by
  `cel.yml.hbs`** — do not leave the verbose generic scaffold as-is. The CEL
  scaffold generates 300+ lines of generic vars; most of them are dead
  weight in a real integration.
- Audit package-level and stream-level manifests together so shared vars and
  stream vars match actual template usage

### Step 8 — define initial field mappings

- Create `fields/fields.yml` with custom integration-specific fields based
  on the API response structure discovered during mito prototyping. These
  are the raw fields before pipeline processing.
- Do **not** create `fields/ecs.yml` — that is the pipeline builder's
  responsibility, and ECS root fields are provided automatically by
  `ecs@mappings` (8.13+).
- Verify `fields/base-fields.yml` exists with the standard data stream
  fields (all six entries use `external: ecs`; override `type`/`value`
  only for `event.module` and `event.dataset`).

### Step 9 — validate (do NOT run system tests)

Run format, lint, and check from the package directory:

```bash
elastic-package format
elastic-package lint
elastic-package check
```

Fix any issues. **Do not run `elastic-package test system`** — the
system-test subagent runs system tests after the pipeline builder completes
pipeline work for this data stream. Do not create or modify
`sample_event.json` — it is generated exclusively by
`elastic-package test system --generate` in that later pass.

If validation surfaces issues unrelated to your CEL work (e.g. pre-existing
pipeline errors), note them in your report and move on rather than fixing
them yourself.

**Note on script tests:** the same `elastic/stream` mock you set up here can
be reused (or extended) for txtar-based script tests that cover failure
paths and partial failures. Setting them up is **out of scope** for your
role; in your report, note which CEL error paths would be good script-test
candidates (which HTTP error codes the program routes to error events, any
partial-failure branches). See `integration-testing/references/script-testing.md`
for details.

### Stop the local mock when done

```bash
# Option A (stream CLI):
kill $MOCK_PID

# Option B (docker-compose):
cd _dev/deploy/docker && docker-compose down
```

## Critical: integration packages vs input-type packages

**Never set `data_stream.dataset` in a `cel.yml.hbs` template for an
integration package** (`type: integration` in the root `manifest.yml`).
Integration packages have named data streams (e.g., `data_stream/event/`)
and the framework automatically routes documents to the correct index (e.g.,
`logs-<package>.<stream>-default`). Overriding `data_stream.dataset` breaks
this routing and causes documents to land in the wrong index — system tests
report "0 hits" because they look in the expected data stream.

Only input-type packages (`type: input`, such as the generic `cel`,
`httpjson`, and `log` packages) use a `data_stream.dataset` var because they
have no predefined data streams. **Do not copy this pattern from input-type
package references into integration packages.**

If you encounter a reference integration that includes
`data_stream:\n  dataset: {{data_stream.dataset}}`, check whether it is an
input-type package (`type: input` in manifest) before copying.

## Data anonymization

**All data committed to the repository must be fully anonymized.** When
prototyping with mito against a real API using real credentials, the raw
responses contain real data — **none of it may be committed as-is.** Replace
every identifying value with a synthetic example of the same format before
using it in:

- Mock API responses in system test config files
- Default values in manifest vars (use `https://api.example.com`, never a
  real vendor URL)
- CEL state example values and template comments

Use RFC 5737 documentation IP ranges (`198.51.100.x`, `203.0.113.x`),
`example.com` domains, realistic placeholder names (`Alice Johnson`,
`Example Corp`), and synthetic IDs. Refer to the `anonymize-logs` skill for
the full placeholder convention list.

## What to return

When you finish, report:

- Files created or modified (with paths)
- **Field files**: list each field file created or modified
  (`fields/fields.yml`, `fields/base-fields.yml`) and what was added or
  changed, so the pipeline builder knows which definitions are already in
  place
- **API interaction summary**: endpoints used, auth method, pagination
  pattern selected from the patterns table
- **Python script validation**: if `test-api.py` was available, whether it
  passed against the mock and any mock fixes you applied
- **System test setup**: mock config file path, rules added, expected
  `hit_count`, mock response data structure (so the pipeline builder knows
  what shape to expect). Confirm explicitly that the mock implements:
  2+ pages in round 1, terminal page, round 2 cursor resume, regression
  guard.
- **Mito validation**: list each phase you ran (skeleton, error handling,
  events, pagination, cursor) and confirm each one passed individually
  against the running mock — not just that the final program works
- **CEL program structure**: single-request vs paginated, cursor fields used
  (and whether you separated page tokens from time bookmarks), re-evaluation
  logic
- **Template configuration**: vars defined, redacted fields, any
  `resource.rate_limit.*` or `resource.retry.*` settings added
- **Manifest/template usage audit**: list package-level and stream-level
  vars kept, and list vars removed as unused because they were not
  referenced by `cel.yml.hbs`
- **celfmt result**: confirm `celfmt -s -agent` validation passed
- **Validation results**: from `elastic-package format / lint / check`
- Any open issues or decisions that need user input
