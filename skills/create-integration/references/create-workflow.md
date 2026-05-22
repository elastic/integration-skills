# Create Integration — Full Workflow

This reference covers the complete end-to-end workflow for creating a new Elastic integration package. Read this fully before starting creation work.

## Dispatch convention (read once, applies to every subagent step below)

All specialised work in this workflow is delegated to the platform's **generic / general-purpose subagent** (Cursor: `generalPurpose` Task agent; Claude Code: `general-purpose` Task agent; or the equivalent on other platforms). Do **not** invoke a named specialised subagent.

Every subagent task prompt must:

1. **Begin with an instruction to read the subagent's operating manual.** Point the subagent at the relevant `*-subagent-guidance.md` file **by path** and tell it to read that file (plus the skill SKILL.md it points at in its "First steps" section) end-to-end **before doing any other work**. **Do NOT read the guidance file yourself or paste/embed its content into the task prompt** — that doubles the context cost. The subagent must load the manual itself in its own fresh context. The guidance file contains the skill-load sequence, workflow, scope boundaries, and reporting contract.
2. **Provide all context** the subagent needs (it cannot see your conversation): package path, data stream path, sample data, API docs / payloads, research brief, authoritative requirement files, requirements, existing package state, API credentials when supplied.

**CRITICAL: Only run ONE subagent at a time.** Process data streams sequentially — never launch multiple builder subagents (CEL, data-collection setup, pipeline, system test) in parallel. Complete all work for one data stream before starting the next.

### Builder / reviewer manuals (pass these by path, do not embed)

| Subagent guidance file | When to use | What the subagent handles |
|----------|-------------|-----------------|
| `/research-integration` skill (orchestrates its own research subagents) | Before building, when API/product docs need investigation and no research brief was provided | Vendor research, API docs, sample payloads, architecture recommendations. Do not launch a `deep-research` subagent directly. |
| `cel-programs/references/builder-subagent-guidance.md` | Each CEL data stream | Mock API (docker-compose + `elastic/stream` config + system test config), incremental mito-validated CEL program, `cel.yml.hbs` template, data stream manifest vars, initial `fields/fields.yml`. Includes the mock-first workflow, mock completeness gate, and phased build ladder. |
| `integration-testing/references/builder-setup-subagent-guidance.md` | Each non-CEL data stream (tcp, udp, http_endpoint, logfile, filestream, kafka, gcp-pubsub) | Docker Compose service, sample logs, agent stream template, system test config, manifest var cleanup. |
| `ingest-pipelines/references/builder-subagent-guidance.md` | Each data stream's pipeline | Ingest pipeline, field definitions, pipeline test fixtures, ECS categorization. |
| `integration-testing/references/builder-system-test-subagent-guidance.md` | After pipeline work, for each testable data stream (CEL, tcp, udp, http_endpoint, logfile, filestream, kafka, gcp-pubsub) | Runs `elastic-package build` + `elastic-package test system --data-streams <stream> --generate`, reads failure logs, reports pass/fail and whether `sample_event.json` was produced. |
| `review-integration/references/reviewer-subagent-guidance.md` | After all streams are built | Read-only quality review: classifies files by domain via the `review-integration` skill, runs check/lint/format validation, inspects manifest/fields/pipeline/CEL/docs/changelog, returns severity-ranked domain-tagged findings. |

## Phase 1: Parse context

1. Extract from the user message: package name, product description, input type(s), data stream name(s), auth method, pagination pattern, and any constraints.
2. Read any `@`-mentioned files (research briefs, sample data). Fetch any documentation or API URLs provided inline.
3. If critical information is missing (package name or input type), ask before proceeding.
4. Default to package type `integration` unless explicitly told otherwise.
5. If the product/vendor needs research and no brief is provided, hand off to the `/research-integration` skill (or instruct the user to invoke it) to investigate documentation, API details, and sample payloads before proceeding. That skill orchestrates its own research subagents — do not launch a named `deep-research` subagent yourself.

## Phase 2: Scaffold the package

1. Verify you are in the repository root (check for `packages/` directory).
2. Run the package scaffold and apply all post-scaffold steps per `references/scaffold-commands.md` (scaffold command, `_dev/build/build.yml` creation, manifest edits, initial validation).

**Mandatory manifest version settings** — after scaffolding, verify the root `manifest.yml` has these exact values (the scaffold may generate different defaults):
- `format_version: "3.4.2"`
- `conditions.kibana.version: "^8.19.0 || ^9.1.0"`

3. **Start the Elastic stack** (needed for system tests later):

```bash
elastic-package stack up -d -v
```

This runs in detached mode. Do not wait for it to finish — continue while the stack boots. If the stack is already running, this is a no-op.

## Phase 3: Scaffold data streams

For each requested data stream, scaffold and apply post-scaffold edits per `references/scaffold-commands.md`.

## Phase 4: Delegate specialized work per data stream

**CRITICAL: Process one data stream at a time. Complete all steps for one stream before starting the next.**

For each data stream, follow this sequence. The steps vary by input type.

### Step 1: Data collection setup (input-type dependent)

#### CEL inputs

Dispatch a subagent per the **Dispatch convention** above, pointing it at `cel-programs/references/builder-subagent-guidance.md` as its operating manual.

The task prompt must include (in addition to the read-the-manual directive):

1. Package and data stream paths.
2. API endpoint details (URL, auth method, pagination pattern, response structure).
3. Sample data or research brief findings.
4. At least one representative API request and response payload (sanitized).
5. Links to authoritative requirement files.
6. **API credentials** (if the user provided them): pass these so the subagent can additionally test against the real API alongside mock-first development.
7. Any stream-specific constraints.
8. Path to the research results folder (if any) — the subagent will look for a `test-api.py` script there to validate the mock against documented API behaviour.

The subagent will: set up the system test mock first (docker-compose + `elastic/stream` config + `test-default-config.yml`), start the mock locally, run any research `test-api.py` against it, verify the mock completeness gate (2+ pages + terminal page + round-2 cursor resume + regression guard), then develop and validate the CEL program with mito incrementally (skeleton → error handling → events → pagination → cursor). Only after mito passes does it write `cel.yml.hbs`, run `celfmt -s -agent`, configure manifest vars, and define initial field mappings.

**The CEL program builder does NOT**: create pipeline test fixtures, touch the ingest pipeline or `fields/ecs.yml`, modify `sample_event.json`, run system tests, or implement document deduplication logic.

Wait for the subagent to complete before proceeding to Step 2.

#### TCP, UDP, HTTP endpoint, logfile, Kafka, Pub/Sub inputs

Dispatch a subagent per the **Dispatch convention** above, pointing it at `integration-testing/references/builder-setup-subagent-guidance.md` as its operating manual.

The task prompt must include (in addition to the read-the-manual directive):

1. Package and data stream paths.
2. Input type(s) for the data stream.
3. Sample log data or event payloads (paste inline or reference file paths).
4. Log format details (JSON, syslog, CEF, key-value, etc.).
5. Package-level vars already defined in the root `manifest.yml` (shared auth, base URL) so the subagent can reuse them.
6. Any stream-specific constraints (ports, auth, TLS requirements).

The subagent will: set up `_dev/deploy/docker/docker-compose.yml` with the appropriate service pattern, create sample log files in `_dev/deploy/docker/sample_logs/`, configure the agent stream template, write system test config files, and clean up scaffold manifest vars. It examines 2-3 existing integrations of the same input type in the official `elastic/integrations` repo for manifest var conventions and template structure.

**The setup subagent does NOT**: build ingest pipelines, run system tests (that's a separate system-test invocation in Step 3), or handle CEL programs.

Wait for the subagent to complete before proceeding to Step 2.

#### Cloud storage inputs (aws-s3, gcs, azure-blob-storage, azure-eventhub)

These inputs **do not have a standard docker-based system test pattern**. Skip the data collection setup step:

1. The scaffold provides a usable agent stream template — review and trim vars to match the integration's needs. Consider moving shared credentials (access keys, connection strings) to the policy template level. **For `aws-s3` inputs**: remove the `ssl` configuration section from the data stream `manifest.yml` — the scaffold adds SSL vars to all input types, but `aws-s3` does not use them (S3 connectivity is handled through the AWS SDK, not direct TLS socket configuration).
2. Note that system tests will be skipped for this data stream (see Step 3).
3. Proceed directly to Step 2 (ingest pipeline).

### Step 2: Ingest pipeline

Dispatch a subagent per the **Dispatch convention** above, pointing it at `ingest-pipelines/references/builder-subagent-guidance.md` as its operating manual.

The task prompt must include (in addition to the read-the-manual directive):

1. Package and data stream paths.
2. **For CEL streams**: tell it the data structure is already known from the CEL builder output and system test mock data. Point it to the mock API response files. Require the pipeline to follow CEL-only opening processors, `ecs.version: 9.3.0`, full `on_failure` baseline, JSE00001 rename/remove, parsing from `event.original`, and `rename` over `set` when mapping into ECS.
3. **For non-CEL streams**: provide sample log data and log format details (JSON, syslog, CEF, key-value, etc.). Tell it whether the input is CEL or not, so it knows whether to include CEL-only opening processors.
4. Representative request/response payloads or raw-event fixtures.
5. Links to authoritative requirement files.
6. Expected ECS categorization if known.

The subagent will: design and implement the ingest pipeline, define field mappings, create pipeline test fixtures, run `elastic-package test pipeline --generate`, and verify the generated expected output.

**The pipeline builder does NOT**: run system tests or modify `sample_event.json`.

Wait for the pipeline builder to complete before proceeding to Step 3.

### Step 3: System test (input-type dependent)

Running full system tests in the orchestrator thread burns context. **Do not execute `elastic-package test system` yourself.**

#### CEL, TCP, UDP, HTTP endpoint, logfile, Kafka, Pub/Sub inputs

System test configs must set **`wait_for_data_timeout: 1m`**. The CEL builder or the data-collection setup subagent should add this when creating the file; if missing, the system-test subagent will add it before running.

Dispatch a subagent per the **Dispatch convention** above, pointing it at `integration-testing/references/builder-system-test-subagent-guidance.md` as its operating manual, to run the system test.

The task prompt must include (in addition to the read-the-manual directive):

1. Clarify this is a **system test run** (not a data-collection setup invocation).
2. Absolute package path, data stream name, input type.
3. Confirmation that the Elastic stack is up (`elastic-package stack up -d -v` already issued).
4. Instruction to `cd packages/<package_name>/`, run `elastic-package build`, then **`elastic-package test system --data-streams <stream> --generate`**. The `--generate` flag is required — it produces `sample_event.json` from the first indexed document. Without it, `sample_event.json` will not be created and a separate run will be needed later.
5. Ask for a concise report: pass/fail per test config, error excerpts, whether `sample_event.json` was generated, and any issues classified by domain (pipeline / CEL / mock API / docker-compose / sample logs) that need orchestrator intervention.

If the system test fails, fix straightforward issues yourself or re-dispatch a subagent (per the **Dispatch convention**) based on the domain-classified report:

- **Pipeline / fields / pipeline-test issues** → point the subagent at `ingest-pipelines/references/builder-subagent-guidance.md`
- **CEL program or mock API issues** → point the subagent at `cel-programs/references/builder-subagent-guidance.md`
- **Docker-compose / sample log / template / non-CEL test config issues** → point the subagent at `integration-testing/references/builder-setup-subagent-guidance.md`

**Never create `sample_event.json` manually.**

Wait for this subagent to finish before moving to the next data stream or phase.

#### Cloud storage inputs (aws-s3, gcs, azure-blob-storage, azure-eventhub)

**Skip system tests.** These inputs require cloud infrastructure that cannot be reliably emulated in Docker. See `integration-testing` skill → `references/system-testing-cloud-skip.md`.

- Focus on pipeline tests for coverage.
- `sample_event.json` must be created through alternative means (construct from pipeline test expected output, or run a temporary local stack session with real cloud credentials).
- Note in the final report: "System tests skipped for `<stream>` — no docker-based mock available for `<input>` inputs."

### Repeat for each data stream

Move to the next data stream and repeat Steps 1–3.

## Phase 5: Validate

After all data streams are complete, run the full check sequence yourself:

```bash
elastic-package format
elastic-package lint
elastic-package check
```

Fix any minor issues (manifest typos, formatting, changelog). For significant pipeline or CEL errors, re-delegate to the appropriate subagent.

## Phase 6: Review

Dispatch a subagent per the **Dispatch convention** above, pointing it at `review-integration/references/reviewer-subagent-guidance.md` as its operating manual, to run the review.

The task prompt must include (in addition to the read-the-manual directive):

1. Package path.
2. The original requirements / research brief.
3. What was built (data streams, input types, architecture decisions).
4. **Which tests have already passed**: list pipeline tests and system tests that succeeded so the reviewer does not re-run them.
5. Explicit request to verify manifest/template parity: no unused vars in package-level or data stream `manifest.yml` not consumed by corresponding `*.yml.hbs` templates.

The reviewer returns a severity-ranked list of issues with domain tags, formatted per `review-integration/references/review-output-template.md`.

## Phase 7: Fix from review

- **Minor issues** (manifest fields, changelog, documentation, field file typos): fix directly.
- **Pipeline issues**: re-dispatch a subagent (per the **Dispatch convention**) pointing it at `ingest-pipelines/references/builder-subagent-guidance.md` with the specific issues to fix.
- **CEL issues**:
  - **Formatting-only** (indentation, style): run `celfmt -s` yourself:
    ```bash
    cd packages/<package_name>/data_stream/<stream>/agent/stream
    celfmt -s -agent -i cel.yml.hbs -ocel.yml.hbs
    ```
  - **Logic issues** (error handling gaps, cursor problems, pagination bugs): re-dispatch a subagent (per the **Dispatch convention**) pointing it at `cel-programs/references/builder-subagent-guidance.md` with the specific issues to fix.

After fixes, run `elastic-package check` again.

## Phase 8: Report

Report back with:
- Files created (with paths)
- Input type and pipeline/CEL architecture chosen
- Decisions made and rationale
- Review results (pass/fail, any remaining items)
- TODO items that need user input
- Next steps

## Data anonymization

**All data committed to the repository must be fully anonymized.** No real production data, customer data, or identifiable information may appear in any committed file — including sample events, test fixtures, mock API responses, documentation examples, and manifest placeholder values.

Replace every identifying value with a synthetic example value of the same format before committing:
- Pipeline test fixtures and expected output
- System test mock API responses and sample logs
- `sample_event.json` (regenerate from anonymized test data)
- Documentation examples in README templates
- Default values in manifest vars (use `https://api.example.com`, not real URLs)

Ensure subagents receive this instruction: all fixture data, mock API responses, and sample events must use anonymized values. Refer to the `anonymize-logs` skill for the full anonymization policy and placeholder conventions.

## Guardrails

- Always use `elastic-package create` for scaffolding. Never fabricate scaffold files manually.
- Treat all scaffold output as placeholders. A passing scaffold validation does not mean the integration logic is implemented.
- Treat `manifest.yml` as a placeholder until aligned with implemented templates and requirements.
- **Root `manifest.yml` must set `format_version: "3.4.2"` and `conditions.kibana.version: "^8.19.0 || ^9.1.0"`.** The scaffold may generate different values — always override. These settings belong only in the root manifest, not in data stream manifests.
- For CEL streams, remove all unused manifest vars. If a var is not used in `cel.yml.hbs`, remove it.
- Run from the correct directory: `packages/` for package creation, `packages/<name>/` for data-stream creation.
- Run `elastic-package build` before any system test whenever package files changed.
- **Always create `_dev/build/build.yml` immediately after scaffolding the package, before creating data streams.** Required for ECS field resolution.
- Do not leave default placeholder values in `manifest.yml` (title, description, owner).
- Do not create or modify `sample_event.json` manually. Only generated by `elastic-package test system`.
- **Do not run `elastic-package test system` in the orchestrator thread** — delegate per the **Dispatch convention** pointing the subagent at `integration-testing/references/builder-system-test-subagent-guidance.md`.
- **Do not develop CEL programs or mock APIs in the orchestrator thread** — delegate per the **Dispatch convention** pointing the subagent at `cel-programs/references/builder-subagent-guidance.md`.
- Do not create `*-expected.json` manually. Only generated by `elastic-package test pipeline --generate`.
- Do not uncomment `{{ event "stream" }}` in the doc template until `sample_event.json` exists.
- For CEL inputs, strip unused scaffold vars rather than leaving the verbose generic scaffold.
- **Never include `data_stream.dataset` in `cel.yml.hbs` or as a manifest var for integration packages** (`type: integration`). The framework routes documents automatically. Only input-type packages (`type: input`) use this field. Setting it in an integration package overrides routing and causes "0 hits" in system tests.
- Set version to `0.1.0` for new integrations.
- Do not load domain-specific skills (CEL, pipelines, ECS, field mappings) into your own context. Delegate to subagents.
