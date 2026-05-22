# CEL expression builder subagent guidance

Operating manual for a subagent that translates a Python API interaction
(test-api.py) into a validated CEL expression. Returns a working `.cel`
file and a taxonomy classification. Does not touch cel.yml.hbs,
manifests, or system tests.

The orchestrator dispatches you with a brief task prompt that points you at
this file by path. **Read this entire file end-to-end before doing any other
work**, then read the skills and reference files listed in the "First steps"
section below — they are mandatory. The orchestrator does not paste this
file's content into your task prompt (to avoid burning context twice); you
load it here in your own fresh context.

## Scope

Your sole job is to translate a working Python API interaction into an
equivalent CEL program, validate it with mito against a running mock,
and return the validated `.cel` file alongside a taxonomy classification.

**You do NOT:**
- Write or modify `cel.yml.hbs` templates
- Configure manifests or data stream vars
- Set up system tests or mock APIs
- Run `elastic-package` commands
- Create field mappings

The orchestrator handles all of that. You produce a validated CEL
expression and nothing else.

## Your inputs

The orchestrator provides:

1. **`test-api.py`** — the Python implementation of the API interaction.
   This is your specification. The collection function
   (`run_collection()` or `collect()`) defines the contract: which
   endpoints to call, how to paginate, what errors to handle, what
   response fields to navigate.

2. **`state.json`** — keys matching the future template's `state:`
   block, with literal test values. The `url` key points at the running
   mock.

3. **Mock URL** — a running `elastic/stream` mock (already started by
   the orchestrator). The mock was derived from test-api.py and has been
   validated against it.

4. **Research brief** (optional supplementary context) — field meanings,
   data types, edge cases not exercised by the script. The Python source
   is the primary specification; the brief provides additional
   requirements (cursor regression guards, rate limit config, etc.).

## Your outputs

1. **A validated `.cel` file** — the CEL expression that mito has
   validated against the mock at each incremental phase.

2. **A taxonomy classification** — the least complex pattern class that
   satisfies the API's requirements:
   - **Pagination:** none | cursor_token | offset | page_number |
     next_url_in_body | link_header | graphql_relay |
     worklist_expansion | async_job_polling | export_blob |
     multi_entity_orchestration
   - **State management:** stateless | timestamp_cursor | time_window |
     state_machine | job_cursor

   Classify at the *least complex class*. If cursor_token suffices, do
   not classify as state_machine. The classification is derived from the
   Python collection function's loop structure, cursor propagation, and
   termination conditions.

## First steps — read the skills and references

Before writing any CEL code, read these:

1. **`cel-programs` skill** (SKILL.md) — state management rules, error
   handling, event output format, pagination strategy selection
2. **`references/cel-expression.md`** — the expression-specific
   reference (translation framing, interface contract, core structure,
   quality checklist)
3. **`references/cel-taxonomy.md`** — classification dimensions,
   how to classify from test-api.py, least-complexity principle
4. **`references/cel-incremental-build.md`** — the phased build ladder
   you MUST follow and syntax anti-patterns
5. **`references/cel-code-style.md`** — nesting discipline, flattening
   techniques
6. **`references/cel-pagination-patterns.md`** — pagination pattern code
   (load when writing phase 3)
7. **`references/mito-reference.md`** — mito CLI flags, execution model

## Workflow

### 1. Analyse test-api.py

Read the collection function. Identify:
- HTTP method and endpoint construction
- Authentication header/parameter setup
- Pagination loop structure and termination condition
- Response navigation path to the event array
- Error handling branches (status codes, missing fields, malformed
  responses)
- Cursor/state propagation between iterations
- Initial-vs-subsequent run logic

### 2. Classify the pattern

From the Python code's structure, classify:
- **Pagination pattern** — what drives the loop? A cursor token? An
  offset? A next-URL in the body? GraphQL relay?
- **State management** — how does the script resume? Timestamp cursor?
  Stateless? State machine?

Choose the *least complex class* that matches the code's behaviour.

### 3. Translate incrementally

Follow the phased build from `references/cel-expression.md`:

**Phase 0 — skeleton:** Translate the basic request structure. The
Python `do_request()` or `requests.get()` call becomes
`request("METHOD", url).with({...}).do_request()`. Run mito.

**Phase 1 — error handling:** Translate the Python status code checks.
Every `if resp.status_code != 200:` becomes a ternary branch. Run mito.

**Phase 2 — event mapping:** Translate the Python response navigation.
The path `resp["data"]["items"]` becomes `body.data.items`. The
`for item in items:` loop becomes
`.map(e, {"message": e.encode_json()})`. Run mito.

**Phase 3 — pagination:** Translate the Python `while` loop. The loop
condition becomes `want_more`. The cursor update
(`next_token = resp["meta"]["next"]`) becomes a cursor field. Run mito
with `-max_executions 5`.

**Phase 4 — cursor guard:** Translate the Python initial-vs-subsequent
logic. The `if first_run:` branch becomes
`state.?cursor.field.orValue(default)`. Test with both initial and
cursor state. Run mito.

**Structural constraint for phase 2 onwards:** After decoding the
response body, extract all needed fields into a flat intermediate map
in a single `.as()`, then build the result from that map. Do NOT nest
multiple `.as()` calls to extract individual fields. See the "Flat
decode pattern" section in `references/cel-expression.md` for the
correct shape and worked examples.

At each phase: if mito reports a compilation error, revert to the last
working version and re-add changes incrementally. Do NOT rewrite from
scratch.

### 4. Validate fidelity

After phase 4, check the CEL program against test-api.py:
- Are all error paths in the Python script represented?
- Does the pagination logic match the Python loop's termination
  conditions?
- Are all response fields navigated the same way?
- Does the cursor state capture the same information Python propagates?
- Are there Python branches the CEL dropped, or CEL branches Python
  doesn't have?

If the research brief describes additional requirements not covered by
the script (e.g., cursor regression guards, empty-page handling), add
them after the core translation is complete.

### 5. Format and return

Run `celfmt -s -i program.cel -o program.cel` to simplify and format
the `.cel` file. (`-i` is input, `-o` is output; without `-o` the
result goes to stdout and the file is unchanged.) Fix any issues it
reports.

Return:
- The final `.cel` file content (after formatting)
- The taxonomy classification
- The mito command that validated it
- Which phases were completed and confirmed

## Quality standards

- `.as()` depth <= 5 on every execution path
- No rate limiting or retry logic
- Events contain only `{"message": e.encode_json()}`
- `want_more` driven by pagination signal, not event count
- No boolean comparisons (`== true`, `== false`)
- No `bytes()` wrapper on `resp.Body`
- Cursor defaults use `state.?cursor.field.orValue(...)`
- Single-use values inlined, not bound with `.as()`
- All state keys from `state.json` used correctly

## What NOT to do

- Do NOT write `cel.yml.hbs`
- Do NOT configure manifests
- Do NOT set up mocks (the orchestrator did this)
- Do NOT run system tests
- Do NOT invent API behaviour not present in test-api.py
- Do NOT add rate limiting, retry, or 429 handling in the CEL program
- Do NOT set `@timestamp` or any field besides `"message"` in events
