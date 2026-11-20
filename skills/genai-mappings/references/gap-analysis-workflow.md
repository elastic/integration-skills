# GenAI field gap analysis workflow

Analyse an existing integration and find, for every in-scope data stream, which `gen_ai.*`
fields are populated correctly, which are populated wrongly, which could be populated from data
the integration already receives, which need a source-side change, and which the source cannot
provide.

Triggered standalone with `/genai-mappings @packages/<package>`.

---

## Statuses

Five statuses. ✅ 🔄 🔍 ⛔ are shared with the `entity-mappings` gap analysis, so that
a report from either skill can be read the same way. ⚠️ is specific to this skill: it marks a
field that is already populated wrongly.

| Status | Meaning | Evidence required |
|---|---|---|
| ✅ Correct | Populated, and name, type, value and shape match the catalog | Pipeline processor + field definition, or (OTel-native streams) the source attribute that arrives under that name |
| ⚠️ Incorrect | Populated, but wrong field name, type, value, shape or definition (for example `gen_ai.system`, `nested` via `external: ecs`, vendor op name in `operation.name`) | What is wrong and what it should be |
| 🔄 Derived | Computable from other fields: a constant, a lookup, a sum, an inference | The rule in plain English, and why it is unambiguous |
| 🔍 Gap | The source can provide the value, the package does not populate it, and it can be collected. **Always carries one recommendation** (table below) | Layer 2: source path in a fixture, mock response, generator code, or vendor docs showing the attribute is sent in a record type the integration already collects. Layer 3: vendor doc URL, what must change, and who controls it |
| ⛔ No action possible | Either the field does not apply to this stream kind or record type (not applicable), or the source cannot provide it (not available). The report says which | Not applicable: the stream kind (`genai-datastream-classification.md`). Not available: what was checked in **each** of the three layers |

### Recommendations for 🔍

| Recommendation | Use when | Layer |
|---|---|---|
| Extract from existing data | The data already reaches the pipeline in this record type, with the current inputs and settings that are on by default or documented in the README, but the field isn't populated | 2 |
| Add API parameter or request setting | The integration issues the request or owns the input configuration, and a parameter, `include`/`expand` option or input setting makes the source return it | 3 |
| New API call | Another endpoint of the same API, called from the same data stream, returns it | 3 |
| Source-side setting (document only) | The user or a vendor administrator controls it (logging configuration, an SDK or CLI environment variable, a cloud account setting) and the integration cannot change it | 3 |
| New data stream | It arrives as a record type, transport or signal that no stream of the package collects (an endpoint with a different record shape, another log destination, another OTel signal) | 3 |

These are the recommendations of the `entity-mappings` gap analysis, reworded for logs and
telemetry: *Extract from existing call* and *Add API parameter* there are the first two rows
here. *Cannot be collected* there is ⛔ here.

**Who controls it decides between the last three rows.** If the integration's own request or
input configuration decides whether the value is sent, it is *Add API parameter or request
setting* or *New API call*. If the user's environment or the vendor account decides, it is
*Source-side setting*. The *Controlled by* column of the content capture table in the report
records this.

**A published object at an ECS path is ⚠️.** If the package publishes an object where ECS
defines a scalar (`gen_ai.request.model.id` under the keyword `gen_ai.request.model`), the
field is ⚠️ and Breaking, not 🔍, even though the ECS value itself is never set.

**Waiting on a decision.** A field whose mapping waits for an issue decision (the #22225
section 2 question) is ⛔ with the reason "pending #N", and goes in *Open questions*.

**Unpopulated is not ⚠️.** A field the package never sets is 🔍, 🔄 or ⛔, even if the
value exists in another field (for example only in `event.action`).

**🔄 or 🔍 Extract.** A value already in a parsed field of the document (a vendor field the
pipeline sets) is 🔄: a copy or lookup. A value that must be parsed out of a body, a string or
a message is 🔍 *Extract from existing data*.

**Fixtures against the docs.** When a handwritten fixture contradicts the vendor documentation
(a field the docs say is never logged), the docs win; the report names the fixture as
suspect.

**Collected by another package.** A value that only another integration's data carries (the
caller of an AgentCore record in CloudTrail, collected by `aws`) is ⛔ not available for this
package, with the other package named. Records are not joined at ingest time.

**Assess per record type.** In mixed streams, a field can be available on one record type and
not on another (request parameters only on a raw request body record, not on the summary
record). Give each record type its own status. On the record types that don't carry the value,
use ⛔ (not applicable) and name the record type that does. Records are not joined at ingest
time.

**Additional work is never a reason to drop a field.** Needing an opt-in, a new endpoint, a
new transport or a new data stream makes the field 🔍 with the matching recommendation, not
⛔. The report says what is needed.

### Change and Basis

The status says what the package does today. Two more columns say what the fix does to
published data and where the expected value comes from. Definitions are in
`genai-detection-conventions.md`, section 9:

- **Change**: New / Additive / Breaking / No change. ✅ is *No change* when the released
  version already has it, and *New* or *Additive* when only unreleased work does. ⚠️ is
  *Breaking* when the fix changes a value, type or shape that is published, or removes a field.
  🔄 and 🔍 are *New* or *Additive*. ⛔ has no Change.
- **Basis**: `main` (package source at a named commit), `issue #N`, `PR #N` (open PR, at a
  named head), `RFC` (an accepted ECS RFC), or `proposal` (this skill's own convention, or a
  recommendation not confirmed anywhere).

Every *Breaking* row goes through Phase 5b.

---

## Phase 0 — Locate and frame

1. Resolve the package directory. Names in issues may differ from directory names (`litellm`
   is `packages/lite_llm`).
2. If a tracking issue exists (for example a sub-issue of elastic/integrations#20737), read it
   with all its comments. Treat its tables as **hypotheses to verify**. They contain known
   errors in provider values, field availability and the system-instruction rule. Do the same
   for any reference table the user gives (a team's list of expected values per event): later
   decisions on the issues override it, and every difference goes in the report.
3. Read elastic/integrations#22224 and #22225 for comments newer than
   `genai-detection-conventions.md`. A maintainer answer there overrides the conventions file.
4. Note the ECS pin (`_dev/build/build.yml`) and the pipeline `ecs.version`. List the `gen_ai`
   fields of that release (`genai-detection-conventions.md`, section 1). Use this list, not the
   catalog or OTel, to decide whether a `gen_ai.*` name may exist. If the pin is below
   `v9.5.0`, list the v9.5.0 fields too: the report recommends the bump.
5. Note the package version and the latest commit that touched it. Basis `main` cites it. If
   the checkout is not the released state (an open PR branch, an unreleased changelog entry),
   also locate the last released version (`git show origin/main:packages/<pkg>/...`, or the
   changelog's last released entry): Change is measured against it
   (`genai-detection-conventions.md`, section 9).

## Phase 1 — Classify

Read `genai-datastream-classification.md`. Classify every data stream, and every record type
within mixed streams. Out-of-scope streams get one line in the report and no field table.

If no stream is in scope, report that and stop, but first check the audit-log trap (record
types that carry request bodies) and whether the vendor offers GenAI data that a **new** data
stream could collect.

## Phase 2 — Read the package (layers 1 and 2)

For each in-scope stream, read:

1. `fields/*.yml`: every `gen_ai.*` field and its definition; vendor fields of type
   `keyword`/`text`/`flattened` that may hold JSON
2. `elasticsearch/ingest_pipeline/*.yml`: what sets `gen_ai.*`, what is parsed, renamed,
   removed or dropped
3. Handwritten fixtures: `_dev/test/pipeline/test-*.log` / `*.json`, mock responses under
   `_dev/deploy/`, system test samples, and **generator code** that produces system test data
   (for example `_dev/deploy/docker/**/main.go`). **Decode** every embedded body and list its
   keys.
4. `agent/stream/*.yml.hbs` and `manifest.yml`: endpoints, transports, variables that enable
   more content
5. `docs/README.md` / `_dev/build/docs/README.md`: setup steps, content-capture opt-ins

Use generated `*-expected.json` and `sample_event.json` only to confirm layer 1. Layer 2
comes from inputs.

## Phase 3 — Read the source (layer 3)

Read `genai-source-discovery.md`. Then fetch the **current** vendor documentation for:

- the API or log schema of every record type, including fields that are not in the fixtures
- content-capture settings and their limits
- other transports and endpoints for the same data
- request parameters the API accepts (any accepted parameter can appear in a logged request)

Use the per-API source maps as a starting point and confirm them against the docs.

## Phase 4 — Map every field

Read `genai-field-catalog.md` and `genai-detection-conventions.md`. For each in-scope stream
(and record type), assign a status to **every** field below. Skip none silently.

- Identity: `provider.name`, `operation.name`, `request.model`, `response.model`,
  `response.id`, `output.type`
- Request: `max_tokens`, `temperature`, `top_p`, `top_k`, `frequency_penalty`,
  `presence_penalty`, `seed`, `choice.count`, `stop_sequences`, `encoding_formats`
- Response and usage: `response.finish_reasons`, `usage.input_tokens`, `usage.output_tokens`,
  `token.type`
- Content: `input.messages`, `output.messages` (including reasoning parts),
  `system_instructions`, `tool.definitions`
- Agent and tool: `agent.id`, `agent.name`, `agent.description`, `tool.name`, `tool.type`,
  `tool.call.id`, `tool.call.arguments`, `tool.call.result`
- No ECS field yet (vendor namespace): conversation or session id, cache read and cache write
  token counts, reasoning token count, and any other value in the catalog's *Source values
  with no ECS field* table that the source provides. Record where the value is and the vendor
  field that holds it (or should). Never propose a `gen_ai.*` name for them.
- Wait for ECS (RFC 0060): tool source (`gen_ai.tool.source.*`) and cache token counts. Status
  as above for the vendor field; the report lists them as "wait for an ECS release".
- Fields outside the pinned ECS: every `gen_ai.*` name the package defines or writes that is
  not in the Phase 0 list (`gen_ai.system`, `gen_ai.prompt`, `gen_ai.request.model.*`, …) gets
  a row: ⚠️, Change *Breaking* (removed in the next major after deprecation), and where its
  value should live instead.
- Adjacent ECS: `user.*` (and whether `user.name` is the stable principal), `related.user`,
  `source.ip`, `file.path`, `url.*`, `destination.address`, `process.command_line`, `error.*`,
  `event.outcome`, `event.duration`
- Detection conventions (`genai-detection-conventions.md`): `event.action` (the native verb),
  `event.category` / `event.type` on tool records, `tags` truncation markers, and the
  tool-call representation (option A or B).

For each status, give the evidence listed in the status table, and for each 🔍 the one
recommendation. Quote real field names from fixtures or docs. Give every row its Change and
Basis.

## Phase 5 — Check definitions and conventions

Read `genai-pipeline-patterns.md`, which defines the expected token totals, message shape and
tool-name handling. Run the catalog's review checklist against the existing `gen_ai.*` fields: ECS pin, `nested`
fields, `flattened` + `ignore_above`, scalars into `flattened`, invented names, provider and
operation values, token totals, message shape, README opt-in documentation.

Then check each in-scope stream against `genai-detection-conventions.md`:

- provider and operation values against the per-source tables (sections 2 and 3), with the
  native verb in `event.action`;
- the tool-call representation: option A for records of one tool run, option B arrays (aligned,
  generation order, only the response's calls, no count field) for provider logs;
- `execute_tool` and `event.category` only on execution-side records;
- call results: section 5, including the open question for provider logs;
- `user.name` is the stable principal, and the README says how it is derived;
- tool definitions carry `type` (OTel value), `name` and `description`;
- messages: tool results under `role: tool`, a normalized `finish_reason` per output message,
  `gen_ai.response.finish_reasons` verbatim, built from the structured body;
- `flattened` safety: `ignore_above: 8191`, the depth cap of 20 on every `flattened` value
  (raw copies included), an empty-value cleanup that skips tool schemas, serialization with
  `Json.dump`;
- removed or cut content is marked in `tags`;
- TSDB streams: a new field that splits series is a dimension.

## Phase 5b — Breaking rows: consumers and release plan

For every row with Change *Breaking*:

1. Find its consumers (detection rules, ML jobs, the package's dashboards and transforms) as in
   `genai-detection-conventions.md`, section 9. Record the count and the public files.
2. Plan it in the release sequence: what the next minor adds and deprecates, what the next
   major removes, and what has to be released by the consumers in between.
3. If a rule matches over a whole body that the change removes or splits, plan a full-body
   `text` field in the vendor namespace.

Group the plan into releases: one minor with every New and Additive row plus the
deprecations, and one major with the Breaking rows, gated on the consumer releases.

## Phase 6 — Report

Write the report with `gap-analysis-report-template.md`. Save it as
`genai-gap-analysis-<package>.md` in the current working directory, or at the path the user
gives. **Never save it inside the package directory**, even when the given path points there:
files there are built into the package. Pick a location outside it and say where.
Include a section that lists where the findings differ from the tracking issue and from any
reference table the user gave, with the reason for each difference (a later decision on an
issue, a field outside the pinned ECS, an error in the reference).

Status counts in the summary cover the core `gen_ai.*` fields of the Phase 4 list
(identity, request, response and usage, content, agent and tool). Values with no ECS field and adjacent ECS
fields have their own sections and are not counted. Change counts cover every row with a
Change.

---

## Dispatching per-stream subagents

When two or more streams are in scope, dispatch one subagent **per stream**. A subagent
handles all record types of its stream. Do not split a stream by record type:

1. Point each subagent at `genai-mappings/references/analysis-subagent-guidance.md` **by
   path**. Do not paste its content.
2. Tell each subagent: package path, data stream, record types, stream kind, vendor doc URLs
   you already found, the tracking issue URL if any, the pinned ECS tag and its `gen_ai` field
   list, and the package commit for Basis `main`.
3. Each subagent writes `genai-gap-analysis-<package>-<stream>.md` outside the package
   directory, containing the template's per-stream sections. You copy those sections into the
   final report, recompute the summary counts,
   resolve contradictions, and check provider values, operation values, identity derivation,
   tool-call representation and conversation id sources for consistency across streams.
4. Run Phase 5b yourself, once for the package, over the Breaking rows the subagents report.
5. When subagents disagree, decide by `genai-detection-conventions.md` first, then the
   catalog, then the tracking issue, and record each decision and its reason in the report.
