# Integration builder — data-collection setup subagent guidance

Operating manual for a subagent wiring up the data-collection plumbing for a
**non-CEL** data stream on behalf of the `create-integration` orchestrator
(invoked from `references/create-workflow.md` or
`references/add-datastream-workflow.md`).

The orchestrator embeds this entire file verbatim in your task prompt, so you do
not need to load any skill or reference file beyond what is listed in the "First
steps" section below.

The orchestrator's task prompt tells you **which package and data stream** to
work on, **which input type(s)** to configure, **what sample data** is
available, **package-level vars** that already exist, and **any
input-specific constraints**. This file tells you **how to operate** as the
data-collection setup subagent. Follow both.

## Scope

Your responsibility is strictly limited to wiring data collection so a system
test can later push sample data through the agent:

- `_dev/deploy/docker/docker-compose.yml` — service definition for the input
  type (TCP/UDP sender, HTTP webhook client, logfile copier, Kafka broker +
  producer, Pub/Sub emulator + publisher)
- `_dev/deploy/docker/sample_logs/` — anonymized sample log files
- `data_stream/<stream>/agent/stream/<input>.yml.hbs` — agent stream template
  trimmed to vars the integration actually needs
- `data_stream/<stream>/_dev/test/system/test-*-config.yml` — system test
  config(s) wiring the service to the agent
- `data_stream/<stream>/manifest.yml` — stream-level var cleanup, sensible
  defaults, accurate title/description
- Root `manifest.yml` — package-level var cleanup, format/conditions version
  enforcement

**You do NOT**:

- Build ingest pipelines (`elasticsearch/ingest_pipeline/`) — the pipeline
  builder handles this (see
  `ingest-pipelines/references/builder-subagent-guidance.md`)
- Define field mappings (`fields/fields.yml`, `fields/ecs.yml`, etc.) — the
  pipeline builder handles this
- Create pipeline test fixtures (`_dev/test/pipeline/`) — the pipeline builder
  handles this
- Handle CEL programs or `cel.yml.hbs` templates — the CEL program builder
  handles this (see `cel-programs/references/builder-subagent-guidance.md`)
- Run system tests (`elastic-package test system`) — the orchestrator
  dispatches a separate system-test-mode invocation after the pipeline builder
  completes. See
  `integration-testing/references/builder-system-test-subagent-guidance.md`
- Create or modify `sample_event.json` — it is generated only by
  `elastic-package test system --generate` in that later pass

If the orchestrator's prompt asks for system test execution rather than
setup, stop and report that the wrong guidance file was embedded — the
system-test workflow lives in
`integration-testing/references/builder-system-test-subagent-guidance.md`.

## Skill authority

The rules and patterns in the skills and their reference files are the
**authoritative source of truth**. You will examine 2–3 reference integrations
in the official `elastic/integrations` repository for service patterns, but
many of those integrations contain legacy patterns that predate current
standards. **Always follow the skills over patterns observed in other
integrations.** If a reference integration uses a deprecated docker-compose
shape, manifest var convention, or template structure, do not copy it.

## First steps — read the skills and their references

Before doing any work, read these skill files **and the specific reference
files listed** to load the patterns you must follow. Reading only the SKILL.md
files is not sufficient — the reference files contain the actual
docker-compose recipes, test config shapes, and template var conventions you
need.

1. **`integration-testing` skill** (SKILL.md) — then read
   `references/system-testing.md` (generic: required layout, system test
   config fields, `wait_for_data_timeout: 1m`, `service_notify_signal`,
   teardown failures, 0-hits debugging) **and** the input-specific reference
   matching the data stream's input type:
   - `tcp` or `udp`: `references/system-testing-tcp-udp.md`
   - `http_endpoint`: `references/system-testing-http-endpoint.md`
   - `logfile` or `filestream`: `references/system-testing-logfile.md`
   - `kafka` or `gcp-pubsub`: `references/system-testing-kafka-pubsub.md`

2. **`input-configurations` skill** (SKILL.md) — then read
   `references/common-input-patterns.md` (tags, processors passthrough,
   `forwarded`/`publisher_pipeline.disable_host` coupling, variable
   conventions) **and** the type-specific guide for the input type
   (`references/tcp-guide.md`, `references/udp-guide.md`,
   `references/http-endpoint-guide.md`, `references/filestream-guide.md`,
   `references/logfile-guide.md`, `references/gcp-pubsub-guide.md`, etc.).
   Load only the guide(s) for the input type(s) the data stream uses.

3. **`create-integration` skill** — read `references/scaffold-commands.md`
   for post-scaffold edits (manifest version enforcement, `tz_offset` rule
   for syslog, `aws-s3` filename/SSL caveats, doc template handling,
   `_dev/build/build.yml` requirement, `fields/beats.yml` requirement).

4. **`elastic-package-cli` skill** — validation commands you will run
   (`elastic-package format`, `lint`, `check`).

5. **`anonymize-logs` skill** — placeholder conventions for sample log files
   and any data committed to the repository.

Read all skills and their relevant references before producing any files.

## Workflow

### 1. Parse the orchestrator's prompt

From the task prompt, extract:

- Package path (absolute) and data stream name
- Input type(s) for the data stream (e.g. `tcp,udp`, `http_endpoint`,
  `logfile`, `kafka`, `gcp-pubsub`)
- Sample log data (inline or file references) and log format (JSON, syslog,
  CEF, key-value, multiline)
- Package-level vars already defined in the root `manifest.yml` (shared auth,
  base URL) so you can reuse them
- Stream-specific constraints (ports, auth, TLS, multi-input combinations)
- Acceptance criteria

### 2. Examine 2–3 reference integrations

Search the official `elastic/integrations` github repository for 2–3 packages that already use the same
input type if available. Examine each one's:

- `_dev/deploy/docker/docker-compose.yml` — service definitions, command
  patterns, environment vars
- `data_stream/<stream>/_dev/test/system/test-*-config.yml` — config
  structure and var wiring
- `data_stream/<stream>/agent/stream/*.yml.hbs` — template var usage
- `data_stream/<stream>/manifest.yml` — stream-level var definitions
- Root `manifest.yml` — package-level var placement (shared auth, URLs)

Use these as **reference patterns only**. Do not copy blindly — adapt to the
integration's specific requirements, and follow the skills when they conflict
with what a reference integration does.

If the path above does not exist in the current environment, ask the
orchestrator where the reference integrations checkout lives (or proceed
without it and rely solely on the skill references).

### 3. Create sample log files

Place representative sample log data in `_dev/deploy/docker/sample_logs/`:

- Use the data provided by the orchestrator. If the data is not yet
  anonymized, apply the `anonymize-logs` skill's placeholder conventions
  before committing.
- Include enough lines to cover the expected event types and edge cases (at
  minimum one happy-path event per format variant).
- Name files descriptively: `<package>-<stream>.log`,
  `<package>-<stream>.ndjson`, etc.
- Note the exact line count — it drives `assert.hit_count` in the test
  config.

### 4. Set up the Docker Compose service

Create or update `_dev/deploy/docker/docker-compose.yml` using the service
pattern from the input-specific `integration-testing` reference for the
data stream's input type. Apply only the parts of the pattern that the
integration needs (e.g. add a TLS variant alongside TCP only when the
integration must test TLS).

Key cross-cutting rules from the references:

- Use the **exact `elastic/stream` image and command shape** documented in
  the input-specific reference — do not invent new flag combinations.
- Coordinate startup with `service_notify_signal: SIGHUP` for inputs that
  require the agent to be listening before the sender starts (TCP, UDP,
  HTTP endpoint).
- For Kafka, include the `healthcheck` and `depends_on: service_healthy`
  block so the producer waits for the broker.
- Use unique ports per service to avoid collisions when multiple input
  variants share one data stream.

If a single data stream supports multiple inputs (e.g. tcp + udp + logfile),
define one service per input variant in the same docker-compose.yml.

### 5. Write system test configs

Create `data_stream/<stream>/_dev/test/system/test-<input>-config.yml` for
each input variant the data stream supports. Use the test config pattern
from the input-specific reference and the required fields from
`integration-testing/references/system-testing.md`:

- **`wait_for_data_timeout: 1m`** — required in every system test config
- `input: <input_type>`
- `service: <docker-compose-service-name>`
- `service_notify_signal: SIGHUP` — when the input-specific reference says
  so (TCP, UDP, HTTP endpoint)
- `data_stream.vars` and `vars` matching the stream and package manifests
- `assert.hit_count` equal to the number of non-empty lines in the sample
  log file

Use one config file per input variant rather than parameterising a single
config.

### 6. Configure the agent stream template

Review and update `data_stream/<stream>/agent/stream/<input>.yml.hbs`. The
scaffold produces a verbose, generic template — trim it to include only the
vars the integration actually consumes, and apply the patterns from
`input-configurations/references/common-input-patterns.md`:

- `preserve_original_event` is a **conditional** tag, not hardcoded.
- User-defined `tags` are iterated with `{{#each tags as |tag|}}`.
- If default tags include `forwarded`, the template **must** include the
  matching `publisher_pipeline.disable_host: true` block (these two are
  always coupled).
- Top-level `{{#if processors}}` passthrough must be present.
- All user-configurable values are template vars, not hardcoded literals.

Follow the type-specific guide loaded in step 2 for input-specific template
shape (TCP/UDP listener vars, HTTP endpoint URL + auth vars, logfile paths,
Kafka topics/brokers, Pub/Sub credentials).

### 7. Clean up manifest vars

Audit both `data_stream/<stream>/manifest.yml` and the package root
`manifest.yml`:

- Remove scaffold vars not referenced by any template (`*.yml.hbs`).
- Move shared vars (auth credentials, base URLs) to the package root when
  they apply to multiple data streams; keep stream-specific vars at the
  stream level.
- Every var must have `title`, `description`, `type`, `required`, and a
  sensible non-empty default for optional vars.
- Apply the `tz_offset` rule from `scaffold-commands.md`: include
  `tz_offset` **only** for syslog (`tcp`/`udp`) streams where the source
  lacks a timezone. Never on `cel`, `http_endpoint`, or other non-syslog
  inputs.
- For syslog (`tcp`/`udp`) streams, always retain the `ssl` and
  `processors` vars regardless of other simplification.
- For `aws-s3` inputs, remove the scaffolded `ssl` var block (S3 uses the
  AWS SDK, not direct TLS sockets) — see the scaffold-commands reference.

**Root `manifest.yml` version enforcement** (do this even if the scaffold
generated other values):

- `format_version: "3.4.2"`
- `conditions.kibana.version: "^8.19.0 || ^9.1.0"`

These belong only in the root manifest — never duplicate them at the data
stream level.

### 8. Validate

Run format, lint, and check from the package directory:

```bash
elastic-package format
elastic-package lint
elastic-package check
```

Fix any issues before reporting back. **Do not run `elastic-package test
system`** — the orchestrator dispatches the system-test pass (which loads
`builder-system-test-subagent-guidance.md`) after the pipeline builder
completes pipeline work for this data stream.

## What to return

When you finish, report:

- Files created or modified (with paths)
- Input type(s) configured
- Docker Compose service(s) defined and their patterns (TCP sender, webhook
  client, Alpine copier, Kafka broker + producer, etc.)
- Sample log file details: name, format, line count
- System test config(s): service mapping, `assert.hit_count`, vars
- Template changes: vars kept, vars removed, `forwarded` /
  `publisher_pipeline.disable_host` coupling status
- Manifest changes: vars cleaned up at data stream and package level,
  `format_version` / `conditions.kibana.version` verification
- Validation results from `elastic-package format/lint/check`
- Any open issues or decisions that need user input (e.g. unresolved auth
  details, port collisions, missing sample data variants)
