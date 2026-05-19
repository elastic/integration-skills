# Add Data Stream — Workflow

This reference covers the end-to-end workflow for adding one or more data streams to an **existing** Elastic integration package. Read this fully before starting.

## Dispatch convention (read once, applies to every subagent step below)

All specialised work in this workflow is delegated to the platform's **generic / general-purpose subagent** (Cursor: `generalPurpose` Task agent; Claude Code: `general-purpose` Task agent; or the equivalent on other platforms). Do **not** invoke a named specialised subagent.

Every subagent task prompt must:

1. **Embed the full content of the relevant `*-subagent-guidance.md` file verbatim at the top.** That file is the subagent's operating manual — it contains the skill-load sequence, workflow, scope boundaries, and reporting contract. The subagent will **not** load its skill automatically; it relies entirely on the embedded manual.
2. **Provide all context** the subagent needs (it cannot see your conversation): package path, data stream path, sample data, API docs / payloads, research brief, authoritative requirement files, requirements, existing package state (especially package-level vars in the root `manifest.yml`), API credentials when supplied.

**CRITICAL: Only run ONE subagent at a time.** Process data streams sequentially — never launch multiple builder subagents (CEL, data-collection setup, pipeline, system test) in parallel. Complete all work for one data stream before starting the next.

### Builder / reviewer manuals

| Embedded guidance file | When to use | What the subagent handles |
|----------|-------------|-----------------|
| `cel-programs/references/builder-subagent-guidance.md` | CEL data streams | Mock API (docker-compose + `elastic/stream` config + system test config), incremental mito-validated CEL program, `cel.yml.hbs` template, data stream manifest vars, initial `fields/fields.yml`. Includes the mock-first workflow, mock completeness gate, and phased build ladder. |
| `integration-testing/references/builder-setup-subagent-guidance.md` | Non-CEL data streams (tcp, udp, http_endpoint, logfile, filestream, kafka, gcp-pubsub) | Docker Compose service, sample logs, agent stream template, system test config, manifest var cleanup. |
| `ingest-pipelines/references/builder-subagent-guidance.md` | Each data stream's pipeline | Ingest pipeline, field definitions, pipeline test fixtures, ECS categorization. |
| `integration-testing/references/builder-system-test-subagent-guidance.md` | After pipeline work, for each testable data stream (CEL, tcp, udp, http_endpoint, logfile, filestream, kafka, gcp-pubsub) | Runs `elastic-package build` + `elastic-package test system --data-streams <stream> --generate`, reports pass/fail and whether `sample_event.json` was produced. |
| `review-integration/references/reviewer-subagent-guidance.md` | After all streams are built (optional) | Read-only quality review: classifies files by domain via the `review-integration` skill, runs check/lint/format validation, inspects manifest/fields/pipeline/CEL/docs/changelog, returns severity-ranked domain-tagged findings. |

## Phase 1: Parse context and verify package

1. Extract from the user message: target package, stream name(s), stream type, input type(s), and any constraints.
2. Read any `@`-mentioned files. Fetch any documentation or API URLs provided inline.
3. Verify the target package exists at `packages/<package_name>/` and read its root `manifest.yml` to understand existing structure (existing data streams, policy template inputs, shared vars).
4. If package name is ambiguous or missing, ask before proceeding.
5. Default stream type to `logs` unless explicitly specified as `metrics`.

## Phase 2: Scaffold the data stream

For each requested stream:

1. Verify you are inside the package directory:

```bash
cd packages/<package_name>
```

2. Verify `_dev/build/build.yml` exists with a current ECS reference. If missing, create it as described in `references/scaffold-commands.md` (post-scaffold step 1) or the `ecs-field-mappings` skill.

3. Run the data-stream scaffold:

```bash
elastic-package create data-stream --name <stream_name> --type <logs|metrics> --inputs <input_types>
```

**Important:** every file produced by `elastic-package create data-stream` is placeholder scaffolding only. For `cel` inputs this is mandatory: generated CEL/template/manifest content is never production-ready and must be replaced with real implementation logic. For non-CEL inputs, generated manifests/templates may include useful defaults but still must be treated as placeholders and implemented against the actual source requirements.

4. Update `data_stream/<stream>/manifest.yml`: set correct title and description, review vars.
5. For CEL inputs: strip the verbose generic scaffold vars (the subagent will configure the template properly), and ensure only vars referenced by `cel.yml.hbs` remain.
6. Wire package-level config if needed: add new package-level vars (shared auth, URL) to root `manifest.yml` under `policy_templates[].inputs[]`.

7. Validate the scaffold:

```bash
elastic-package check
```

Treat both package-level and data stream `manifest.yml` files as placeholders after scaffold generation.

## Phase 3: Delegate specialized work per data stream

**CRITICAL: Process one data stream at a time. Complete all steps for one stream before starting the next.**

### Step 1: Data collection setup (input-type dependent)

#### CEL inputs

Dispatch a subagent per the **Dispatch convention** above, embedding `cel-programs/references/builder-subagent-guidance.md`.

The task prompt must include (in addition to the embedded manual):

1. Package and data stream paths.
2. API endpoint details (URL, auth method, pagination pattern, response structure).
3. Sample data or research brief findings.
4. Existing package-level vars in the root `manifest.yml` (so the subagent reuses shared auth/URL vars rather than redefining them at the stream level).
5. At least one representative API request and response payload (sanitized).
6. Links to authoritative requirement files.
7. **API credentials** (if the user provided tokens, API keys, OAuth client ID/secret): pass these so the subagent can also test against the real API. Mock-first development remains the primary path.
8. Path to the research results folder (if any) — the subagent will look for a `test-api.py` script there to validate the mock against documented API behaviour.
9. Any stream-specific constraints.

The subagent will: set up the system test mock first (docker-compose + `elastic/stream` config + `test-default-config.yml`), start the mock locally, run any research `test-api.py` against it, verify the mock completeness gate (2+ pages + terminal page + round-2 cursor resume + regression guard), then develop and validate the CEL program with mito incrementally (skeleton → error handling → events → pagination → cursor). Only after mito passes does it write `cel.yml.hbs`, run `celfmt -s -agent`, configure manifest vars, and define initial field mappings.

**The CEL program builder does NOT**: create pipeline test fixtures, touch the ingest pipeline or `fields/ecs.yml`, modify `sample_event.json`, run system tests, or implement document deduplication logic.

Wait for the subagent to complete before proceeding to Step 2.

#### TCP, UDP, HTTP endpoint, logfile, Kafka, Pub/Sub inputs

Dispatch a subagent per the **Dispatch convention** above, embedding `integration-testing/references/builder-setup-subagent-guidance.md`.

The task prompt must include (in addition to the embedded manual):

1. Package and data stream paths.
2. Input type(s) for the data stream.
3. Sample log data or event payloads.
4. Existing package-level vars in the root `manifest.yml` (so the subagent reuses shared config rather than re-defining shared auth/URL vars at the stream level).
5. Log format details (JSON, syslog, CEF, key-value, etc.).
6. Any stream-specific constraints (ports, auth, TLS requirements).

The subagent will: set up `_dev/deploy/docker/docker-compose.yml`, create sample log files, configure the agent stream template, write system test configs, and clean up scaffold manifest vars. It examines 2-3 existing integrations of the same input type in the official repo for patterns.

**The setup subagent does NOT**: build ingest pipelines, run system tests (that's a separate system-test invocation in Step 3), or handle CEL programs.

Wait for the subagent to complete before proceeding to Step 2.

#### Cloud storage inputs (aws-s3, gcs, azure-blob-storage, azure-eventhub)

Skip the data collection setup step. The scaffold provides a usable agent stream template — review and trim vars to match the integration's needs. System tests will be skipped for this data stream (see Step 3). Proceed directly to Step 2.

### Step 2: Ingest pipeline

Dispatch a subagent per the **Dispatch convention** above, embedding `ingest-pipelines/references/builder-subagent-guidance.md`.

The task prompt must include (in addition to the embedded manual):

1. Package and data stream paths.
2. **For CEL streams**: tell it the data structure is already known from the CEL builder output and the system test mock data it produced. Point it to the mock API response files so it understands the data format.
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

Ensure `data_stream/<stream>/_dev/test/system/test-*-config.yml` includes **`wait_for_data_timeout: 1m`** before running. The system-test subagent will add it if missing.

Dispatch a subagent per the **Dispatch convention** above, embedding `integration-testing/references/builder-system-test-subagent-guidance.md`, to run the system test.

The task prompt must include (in addition to the embedded manual):

1. Clarify this is a **system test run** (not a data-collection setup invocation).
2. Absolute package path, data stream name, input type.
3. Confirmation that the Elastic stack is up.
4. Instruction to `cd packages/<package_name>/`, run `elastic-package build`, then **`elastic-package test system --data-streams <stream> --generate`**. The `--generate` flag is required — it produces `sample_event.json` from the first indexed document.
5. Ask for a concise report: pass/fail per test config, error excerpts, whether `sample_event.json` was generated, and any issues classified by domain (pipeline / CEL / mock API / docker-compose / sample logs) that need orchestrator intervention.

If the system test fails, fix straightforward issues yourself or re-dispatch a subagent (per the **Dispatch convention**) based on the domain-classified report:

- **Pipeline / fields / pipeline-test issues** → embed `ingest-pipelines/references/builder-subagent-guidance.md`
- **CEL program or mock API issues** → embed `cel-programs/references/builder-subagent-guidance.md`
- **Docker-compose / sample log / template / non-CEL test config issues** → embed `integration-testing/references/builder-setup-subagent-guidance.md`

**Never create `sample_event.json` manually.**

Wait for this subagent to finish before moving to the next data stream.

#### Cloud storage inputs (aws-s3, gcs, azure-blob-storage, azure-eventhub)

**Skip system tests.** These inputs require cloud infrastructure that cannot be reliably emulated in Docker. See `integration-testing` skill → `references/system-testing-cloud-skip.md`.

- Focus on pipeline tests for coverage.
- `sample_event.json` must be created through alternative means (construct from pipeline test expected output, or run a temporary local stack session with real cloud credentials).
- Note in the final report: "System tests skipped for `<stream>` — no docker-based mock available for `<input>` inputs."

### Repeat for each data stream

Move to the next data stream and repeat Steps 1–3. Do not start a new data stream until the current one is complete.

## Phase 4: Validate and report

After all data streams are complete (including system tests):

1. Run the full check sequence from the package directory:

```bash
elastic-package format
elastic-package lint
elastic-package check
```

2. Fix any minor issues (manifest wiring, formatting). For significant pipeline errors, re-dispatch a subagent (per the **Dispatch convention**) embedding `ingest-pipelines/references/builder-subagent-guidance.md` with the specific issues to fix. For CEL errors, re-dispatch embedding `cel-programs/references/builder-subagent-guidance.md`.

3. Optionally dispatch a subagent (per the **Dispatch convention**) embedding `review-integration/references/reviewer-subagent-guidance.md` for a quality check of the new stream(s). The task prompt must additionally pass: (a) which tests have already passed (so the reviewer does not re-run them); (b) explicit request to verify manifest/template parity (no unused vars in package-level or data stream `manifest.yml` not consumed by `*.yml.hbs`); (c) any focus areas specific to the newly added stream(s).

4. If the reviewer reports CEL-related issues:
   - **Formatting-only issues** (indentation, style): run `celfmt -s` yourself:
     ```bash
     cd packages/<package_name>/data_stream/<stream>/agent/stream
     celfmt -s -agent -i cel.yml.hbs -ocel.yml.hbs
     ```
   - **Logic issues** (error handling, cursor management, pagination): re-dispatch a subagent (per the **Dispatch convention**) embedding `cel-programs/references/builder-subagent-guidance.md` with the specific issues to fix.

5. Report back with:
   - Files created and modified (with paths)
   - Input type and pipeline/CEL architecture chosen
   - How the stream fits into the existing package structure
   - Decisions made and rationale
   - System test results per data stream
   - TODO items requiring user input
   - Next steps

## Data anonymization

**All data committed to the repository must be fully anonymized.** No real production data, customer data, or identifiable information may appear in any committed file — including sample events, test fixtures, mock API responses, documentation examples, configuration defaults, and manifest placeholder values.

Replace every identifying value with a synthetic example value of the same format before committing. This applies to all fixtures, mock responses, sample events, documentation, and default manifest values (use `https://api.example.com`, not real URLs).

Ensure subagents receive this instruction: all fixture data, mock API responses, and sample events they produce must use anonymized values. Refer to the `anonymize-logs` skill for the full anonymization policy and placeholder conventions.

## Guardrails

- Always use `elastic-package create data-stream` for scaffolding. Never fabricate stream directories manually.
- Treat all scaffold output as placeholders only. A passing scaffold validation does not mean the data stream implementation is complete.
- Treat package-level and data stream `manifest.yml` as placeholders until aligned with implemented templates and requirements.
- **Verify root `manifest.yml` sets `format_version: "3.4.2"` and `conditions.kibana.version: "^8.19.0 || ^9.1.0"`.** If the existing package has different values, update them. These settings belong only in the root manifest, not in data stream manifests.
- For CEL streams, remove all unused manifest vars (package-level and data stream-level). If a var is not used in `cel.yml.hbs`, remove it.
- Run from inside the target package directory (`packages/<name>/`).
- Run `elastic-package build` before any system test whenever package files changed.
- Verify the package exists before attempting scaffold.
- Do not duplicate package-level vars that already exist in root `manifest.yml`.
- Do not create or modify `sample_event.json` manually. It is only generated by `elastic-package test system`.
- Do not create `*-expected.json` manually. It is only generated by `elastic-package test pipeline --generate`.
- For CEL inputs, strip unused scaffold vars.
- Choose `--inputs` based on the product's data delivery method. Allowed values: `aws-cloudwatch`, `aws-s3`, `azure-blob-storage`, `azure-eventhub`, `cel`, `entity-analytics`, `etw`, `filestream`, `gcp-pubsub`, `gcs`, `http_endpoint`, `journald`, `netflow`, `redis`, `tcp`, `udp`, `winlog`.
- Do not load domain-specific skills (CEL, pipelines, ECS, field mappings) into your own context. Delegate to the subagents that already have that knowledge.
- **Never include `data_stream.dataset` in `cel.yml.hbs` or as a manifest var for integration packages** (`type: integration`). The framework routes documents automatically.
