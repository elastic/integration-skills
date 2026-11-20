---
name: genai-mappings
description: >-
  Use when adding or auditing ECS gen_ai.* fields on Elastic integrations that collect
  telemetry from LLM providers, AI gateways, agent runtimes, or AI coding assistants —
  deciding which data streams carry GenAI data, finding every source field that can feed a
  gen_ai.* field (including content that is logged but not yet parsed), normalizing prompts,
  responses, tool calls and reasoning into the OTel message shape, or running a GenAI-coverage
  gap analysis on an existing package. Invoke manually with /genai-mappings.
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# genai-mappings

## Skill authority

The guidance in this skill takes precedence over patterns observed in any integration in the
`elastic/integrations` repository. Several GenAI integrations predate the ECS v9.5.0 `gen_ai`
field set and use fields that are not ECS (`gen_ai.system`, `gen_ai.prompt`,
`gen_ai.completion`, `gen_ai.usage.prompt_tokens`, `gen_ai.request.model.id`). Do not copy
them. Follow this skill's rules over what you see in the repo.

## When to use

- Adding `gen_ai.*` fields to a new or existing integration
- Deciding whether a data stream carries GenAI data, and which `gen_ai.*` fields apply to it
- Researching a GenAI data source so that no field that could become a `gen_ai.*` field is missed
- Mapping prompts, responses, system prompts, tool definitions, tool calls and reasoning
  ("thinking") content into `gen_ai.input.messages`, `gen_ai.output.messages`,
  `gen_ai.system_instructions`, `gen_ai.tool.*`
- Choosing `gen_ai.provider.name` and `gen_ai.operation.name` values
- Auditing an existing package's GenAI field coverage (standalone gap analysis)
- Fixing ingest failures on `gen_ai.*` fields (`flattened` / `nested` mapping errors)

## When not to use

- **Generic ECS field work** (non-`gen_ai` fields, categorization) — use `ecs-field-mappings`.
- **Processor mechanics** (grok, date, JSON, error handling) — use `ingest-pipelines`.
- **CEL program logic** for a new API-based data stream — use `cel-programs`.
- **Entity / inventory streams** — use `entity-mappings`.

## Applicability gate

`gen_ai.*` fields describe **GenAI operations**: a model inference, an agent invocation, a tool
call made by an agent or model, or token usage attributed to a model. They apply to a data
stream when its records describe one of those operations, or aggregate one of them (usage and
cost metrics per model). They do **not** apply to records that only mention an AI product, such
as a generic admin audit log ("user X changed workspace setting Y").

Classify every data stream with `references/genai-datastream-classification.md` before
mapping fields. If you are not sure, read that file first.

## ECS availability — read this first

**ECS v9.5.0 is the minimum for GenAI work.** Earlier releases have no `gen_ai` field set
(below v9.1.0) or the old one (v9.1.0 – v9.4.0: `gen_ai.system`, `integer` counts, no content
fields). Later additions (`gen_ai.conversation.id` on ECS `main`, the RFC 0060 fields) are not
usable until an ECS release includes them. The matrix is in
`references/genai-field-catalog.md`.

**Pin rule:** packages with GenAI data streams must set `dependencies.ecs.reference:
"git@v9.5.0"` (or newer) in `_dev/build/build.yml`, and set the matching `ecs.version` in
their pipelines. Most in-scope packages are pinned lower today (`v8.11.0`, `v8.17.0`,
`v9.3.0`); bumping the pin is part of the work.

Three field-definition traps, each reproduced on Elasticsearch 9.5 (catalog, *Field definition
rules*):

1. `gen_ai.response.finish_reasons`, `gen_ai.request.stop_sequences` and
   `gen_ai.request.encoding_formats` are typed `nested` in ECS with no sub-fields
   ([elastic/ecs#2560](https://github.com/elastic/ecs/issues/2560)). With `external: ecs`, a
   string array such as `["stop"]` **rejects the whole document**. Declare them locally as
   `keyword`.
2. The six `flattened` fields reject the whole document when any leaf string is longer than
   32766 bytes (prompts often are), and Fleet adds no default `ignore_above`. Declare them with
   `external: ecs` **plus `ignore_above: 8191`**.
3. `flattened` fields reject scalars. A plain-string system prompt must be wrapped as
   `[{type: text, content: ...}]`, not copied as a string.

## Core rules

- **Only ECS fields under ECS field sets.** A `gen_ai.*` field (or a field under any other
  ECS field set) is valid only if it is defined in a released ECS version at or below the
  package's pin. Attributes that only OTel defines and names that are only on ECS `main` are
  not: ECS may adopt them under a different name or type, which would then conflict with the
  package's definition. Their values go to `<integration>.<data_stream>.<field>`. Check names
  against the pinned release (`references/genai-detection-conventions.md`, section 1), in gap
  analyses and in builds alike.
- **Values come from OTel.** ECS `gen_ai` is defined as a match of the OTel GenAI semantic
  conventions. Use OTel's well-known values for `gen_ai.provider.name`,
  `gen_ai.operation.name`, `gen_ai.output.type` and `gen_ai.tool.type`, and the OTel JSON
  schemas for the shape of the message fields. Vendor operation names (`InvokeModel`,
  `ChatCompletions_Create`, `acompletion`, `query_source`) do not belong in
  `gen_ai.operation.name`. Keep them in `event.action` or in the vendor namespace.
- **Detection conventions.** elastic/integrations#22224 and #22225 fix how integrations fill
  `gen_ai.*` for detection rules and ML jobs: provider and operation values per source, one
  record per tool call or order-aligned arrays, call results, the stable principal in
  `user.name`, tool definition types, tool results under `role: tool`. They are in
  `references/genai-detection-conventions.md`.
- **Published fields change in two releases.** Find the rules, ML jobs and dashboards that read
  a field before renaming or removing it. Add the new field and deprecate the old one in a
  minor, and remove it in the next major, after the consumers have moved.
- **Research the source, not the current pipeline.** The most common gap is data that the
  source already sends but the integration stores as an unparsed string (request and response
  bodies, `tool_parameters`, raw API bodies), or data that the source sends only when a
  setting is enabled. `references/genai-source-discovery.md` lists where to look.
- **OTel-native streams are different.** In `otelcol` streams, source attributes already named
  `gen_ai.*` arrive through the platform's OTel mappings without any processor. Judge them as
  sent, and write fixes under `attributes.gen_ai.*` (see `references/genai-source-discovery.md`).
- **Document how to turn on content capture.** If prompts, responses or reasoning content are
  only logged after a vendor-side setting is enabled, the package README must say how to
  enable it.

## Modes

| Mode | How it's triggered | What to load |
|---|---|---|
| **Standalone gap analysis** | User invokes `/genai-mappings @packages/<name>` | Read `references/gap-analysis-workflow.md`, then the classification, source-discovery, catalog, detection-conventions and pipeline-patterns references as the workflow phases ask. Dispatch per-stream subagents with `references/analysis-subagent-guidance.md`. |
| **Build-time** | An orchestrator (`create-integration`, for new packages and new data streams) classifies streams in Phase 1 and passes `references/genai-field-catalog.md` and `references/genai-pipeline-patterns.md` by path to the pipeline builder subagent, with the `git@v9.5.0` pin | The builder reads both references, and `references/genai-detection-conventions.md` when the stream has tool calls, a caller identity, or changes a published field. This SKILL.md does not need to be loaded in the orchestrator thread. |
| **Review-time** | `review-integration` finds `gen_ai.*` fields, or a stream classified as GenAI | Reviewer reads `genai-field-catalog.md` (checklist at the end) and `genai-pipeline-patterns.md`. The `genai_ecs_pin_minimum` consistency rule covers the pin. |
| **Research-time** | `research-integration` (the orchestrator reads the classification; the Track G subagent reads both, and writes `genai-mapping-analysis.md` and section 5.6 of the research brief) | Load only `references/genai-datastream-classification.md` and `references/genai-source-discovery.md`. **Do not load the catalog or pipeline patterns during research**: they are implementation material. |
| **Apply-time** | User invokes `/apply-mappings @packages/<name> @<report>.md` with a report from this skill | The `apply-mappings` skill reads the report, asks the user about design decisions, and dispatches the pipeline builder with `genai-field-catalog.md`, `genai-pipeline-patterns.md` and `genai-detection-conventions.md` by path. In a GenAI report ✅ means the package already populates the field. |

## Open questions / deferred scope

- **Fields ECS has not released** (`gen_ai.conversation.id`, the RFC 0060 fields
  `gen_ai.tool.source.*` and `gen_ai.usage.cache_read.input_tokens` /
  `cache_write.input_tokens`, and other OTel attributes such as reasoning token counts,
  `gen_ai.agent.version` or `gen_ai.tool.description`): the source values stay in the vendor
  namespace, and research still records them so that they can be moved once ECS adds the
  fields (catalog, *Source values with no ECS field*).
- **Tool results on provider logs** (#22225 section 2) were an open question on 2026-11-20.
  Until it is answered, results stay in the input messages (detection conventions, section 5).
- **`nested`-typed ECS fields**: once elastic/ecs#2560 is fixed, the local `keyword`
  overrides can become `external: ecs`.

## References

- `references/genai-field-catalog.md` — single source of truth for the fields: ECS availability
  matrix, types, well-known values, message shapes, values without an ECS field,
  field-definition rules, review checklist
- `references/genai-detection-conventions.md` — the #22224 / #22225 conventions: which records
  get which fields (provider and operation per source, tool calls and results, categorization,
  identity, tool definitions) and how to change a published field
- `references/genai-pipeline-patterns.md` — tested processors: lookups, token totals, message
  normalization, tool records, identity, flattened safety, test fixtures
- `references/genai-source-discovery.md` — research method: where GenAI data hides,
  content-capture opt-ins, per-API source maps, field-by-field questions
- `references/genai-datastream-classification.md` — which data streams are in scope and which
  field groups apply to each kind of stream
- `references/gap-analysis-workflow.md`, `references/gap-analysis-report-template.md`,
  `references/analysis-subagent-guidance.md` — the standalone audit of an existing package, its
  report structure, and the manual for its per-stream subagents
- [ECS gen_ai field reference](https://www.elastic.co/docs/reference/ecs/ecs-gen_ai)
- [OTel GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai)
