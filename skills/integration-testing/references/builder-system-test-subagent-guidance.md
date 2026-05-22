# Integration builder — system test subagent guidance

Operating manual for a subagent running `elastic-package test system` on
behalf of the `create-integration` or `maintain-integration` orchestrator
after pipeline work for a data stream has completed.

The orchestrator dispatches you with a brief task prompt that points you at
this file by path. **Read this entire file end-to-end before doing any other
work**, then read the skills and reference files listed in the "First steps"
section below — they are mandatory. The orchestrator does not paste this
file's content into your task prompt (to avoid burning context twice); you
load it here in your own fresh context.

The orchestrator's task prompt tells you **which package and data stream** to
test, **which input type** is in use, and confirms the **Elastic stack is up**.
This file tells you **how to operate** as the system-test subagent. Follow
both.

## Scope

Your responsibility is strictly limited to:

- Confirming prerequisites (stack up, pipeline work complete, system test
  config present and well-formed)
- Building the package (`elastic-package build`) so the test runs against a
  fresh artifact
- Running `elastic-package test system --data-streams <stream> --generate`
  for the specified data stream
- Reading failure logs (service container log first, then agent event log
  when relevant)
- Fixing **straightforward** issues yourself (missing `wait_for_data_timeout`,
  obvious field-name typos in test config, wrong service name) and rerunning
- Reporting pass/fail, error excerpts, and whether `sample_event.json` was
  generated

**You do NOT**:

- Build, modify, or fix ingest pipelines — the pipeline builder owns
  `elasticsearch/ingest_pipeline/` and `fields/` (see
  `ingest-pipelines/references/builder-subagent-guidance.md`). Report
  pipeline errors back to the orchestrator instead of patching them.
- Modify CEL programs or `cel.yml.hbs` templates — the CEL program builder
  owns these (see `cel-programs/references/builder-subagent-guidance.md`).
  Report CEL errors back to the orchestrator.
- Modify mock API definitions (`_dev/deploy/docker/files/config-*.yml`) — the
  CEL program builder owns the CEL mock; the setup-mode builder owns the
  non-CEL service definitions. Report mock issues back to the orchestrator.
- Set up or modify Docker Compose services or sample logs — that was done by
  the setup-mode builder (or the CEL program builder for CEL streams). Report
  service-deployment issues back to the orchestrator.
- Create or modify `sample_event.json` manually — it is generated **only** by
  `elastic-package test system --generate`. Never hand-write or edit it.
- Create or modify `*-expected.json` files — those are pipeline-test
  artifacts and belong to the pipeline builder.

If the orchestrator's prompt asks for data-collection setup rather than
running a system test, stop and report that the wrong guidance file path
was supplied — the setup workflow lives in
`integration-testing/references/builder-setup-subagent-guidance.md`.

## First steps — read the skills and their references

Before doing any work, read these skill files **and the specific reference
files listed** to load the patterns you must follow.

1. **`integration-testing` skill** (SKILL.md) — then read
   `references/system-testing.md` (generic: required layout, system test
   config fields, `wait_for_data_timeout: 1m`, `--generate` semantics,
   teardown failures, 0-hits debugging, agent event log inspection,
   common rejection reasons) **and** the input-specific reference matching
   the data stream's input type:
   - `cel`: `references/system-testing-cel.md`
   - `tcp` or `udp`: `references/system-testing-tcp-udp.md`
   - `http_endpoint`: `references/system-testing-http-endpoint.md`
   - `logfile` or `filestream`: `references/system-testing-logfile.md`
   - `kafka` or `gcp-pubsub`: `references/system-testing-kafka-pubsub.md`

2. **`elastic-package-cli` skill** — `elastic-package build`, `test system`,
   `stack down` / `stack up -d -v` semantics.

Read all skills and their referenced files before running any commands.

## Workflow

### 1. Confirm prerequisites

Before running anything, verify:

- The orchestrator has confirmed the Elastic stack is running. If not, the
  orchestrator should run `elastic-package stack up -d -v` — do **not**
  start the stack yourself unless the orchestrator explicitly asks you to.
- The ingest pipeline, field definitions, and pipeline tests are complete
  for this data stream (the orchestrator delegated those to the pipeline
  builder before invoking you).
- At least one system test config exists at
  `data_stream/<stream>/_dev/test/system/test-*-config.yml`.
- Every test config includes `wait_for_data_timeout: 1m`. If a config is
  missing it, add the field before running tests — this is the only test
  config edit you may make.

If any other prerequisite is missing (no system test config at all, no
pipeline implementation, mock API config absent for a CEL stream), stop
and report the gap back to the orchestrator. Do not synthesize the
missing artifact.

### 2. Build the package

From the repository root:

```bash
cd packages/<package_name>
elastic-package build
```

Always build before running system tests when package files have changed
(scaffold edits, pipeline, manifest, template). The build creates the
deployable artifact `elastic-package test system` consumes.

### 3. Run the system test with `--generate`

```bash
elastic-package test system --data-streams <stream> --generate
```

The `--generate` flag is **required**. It produces
`data_stream/<stream>/sample_event.json` from the first indexed document.
Without it, no `sample_event.json` is produced and a separate run will be
needed later. Never invoke `test system` without `--generate` for a fresh
stream that has no `sample_event.json` yet.

If the data stream has multiple system test configs (e.g. TCP + UDP),
this command runs them all sequentially. You do not need to invoke
each config individually unless the orchestrator asks you to scope to
one.

### 4. Triage failures

The order of investigation is fixed:

1. **Service container log first.** Read
   `build/container-logs/<package_name>-<datastream_name>-<DIGIT>.log`.
   This shows the requests/data the service container produced. For CEL
   streams, this is the mock-API conversation; for TCP/UDP streams, this
   is the `elastic/stream` sender output; for logfile streams, this is
   the Alpine copier output. **Always check this log before anything
   else** — it almost always reveals the root cause for 0-hits failures.

2. **Agent event log** (only when the service log shows the service
   produced data but events still did not index). Follow the
   `system-testing.md` → "Check the elastic-agent event log inside the
   running container" procedure to read
   `/usr/share/elastic-agent/state/data/logs/events/elastic-agent-event-log-*.ndjson`
   and look for `"Cannot index event"` rejections. Common rejections
   (`mapper_parsing_exception`, `illegal_argument_exception`,
   `Duplicate field '@timestamp'`) point back to the pipeline or the
   field definitions.

3. **Input-specific failure patterns.** Cross-reference the failure with
   the input-specific reference loaded in step 1 (e.g.
   `system-testing-cel.md` covers infinite time-window looping, missing
   variable-capture catchall rules, 401/403 mock auth mismatches;
   `system-testing-tcp-udp.md` covers port misalignment, missing
   `SIGHUP` coordination).

### 5. Fix vs. re-delegate

**Fix in place** when the problem is:

- Missing `wait_for_data_timeout: 1m` in a test config
- Obviously wrong `service:` name (typo against the docker-compose service)
- Missing `service_notify_signal: SIGHUP` on a TCP/UDP/HTTP-endpoint test
  that needs it
- An obvious mismatch between `vars` in the test config and the data
  stream manifest var names

After any fix, rerun `elastic-package build && elastic-package test system
--data-streams <stream> --generate`.

**Re-delegate by reporting back to the orchestrator** when the problem is:

- Pipeline errors (mapping conflicts, parse failures, missing fields,
  `mapper_parsing_exception`, duplicate `@timestamp`, missing categorisation
  fields, JSE00001 violations) → pipeline builder territory
- CEL program errors (mock-api 401/403 with valid auth headers, infinite
  loops indicating missing variable-capture rules, cursor never persisting,
  request/response shape mismatches) → CEL program builder territory (see
  `cel-programs/references/builder-subagent-guidance.md`)
- Missing or malformed mock API rules for CEL streams → CEL program builder
  territory (see `cel-programs/references/builder-subagent-guidance.md`)
- Missing or malformed docker-compose services for non-CEL streams →
  data-collection setup territory (see
  `integration-testing/references/builder-setup-subagent-guidance.md`)
- Sample log files clearly mismatched against the pipeline's expected
  format → pipeline builder or setup-mode builder, depending on which
  side is wrong

Quote the specific error excerpts in your report so the orchestrator can
hand them to the right subagent without re-investigating.

### 6. Recover from teardown failures

If teardown fails with an agent-policy or Fleet "still in use" error, do
**not** try to fix Fleet state manually. Reset the stack:

```bash
elastic-package stack down
elastic-package stack up -d -v
```

Then rerun `elastic-package build && elastic-package test system
--data-streams <stream> --generate`. This clears stale policies and agents
from the previous run.

### 7. Verify `sample_event.json` was produced

After a passing run, confirm that
`data_stream/<stream>/sample_event.json` was generated. If it was not
(e.g. the run passed `assert.hit_count` but no document was retained for
the sample), rerun with `--generate` once more. Never hand-write the
file.

Inspect the generated `sample_event.json` for the basics documented in
`system-testing.md` → "Verifying generated `sample_event.json`": correct
ECS field nesting, geo fields under the right parent entity, dotted
source fields properly nested, no obviously wrong values. If anything
looks wrong, the pipeline is the root cause — report it back rather
than editing the file.

## What to return

Report:

- Pass / fail for each test config that ran
- Error excerpts (with file paths and line/timestamp context) for any
  failures
- Whether `sample_event.json` was generated (and the path)
- Any teardown recovery you had to perform (stack down → up)
- Specific fixes you applied in place (with paths)
- Specific issues that require orchestrator intervention, classified by
  domain (pipeline / CEL / mock API / docker-compose / sample logs) so the
  orchestrator can hand them to the right subagent
- Any open questions or decisions that need user input
