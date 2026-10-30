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

The usable `gen_ai` field set depends on the ECS version the package pins. **ECS v9.5.0 is the
minimum for GenAI work.**

| ECS pin | What you get |
|---|---|
| `< v9.1.0` | No `gen_ai` field set at all. |
| `v9.1.0` – `v9.4.0` | Old field set: `gen_ai.system` (no `gen_ai.provider.name`), token counts typed `integer`, **no** `input.messages`, `output.messages`, `system_instructions`, `tool.definitions`, `tool.call.arguments`, `tool.call.result`. |
| `v9.5.0` | Current field set: `gen_ai.system` removed and replaced by `gen_ai.provider.name`, counts typed `long`, the six `flattened` content fields added. |
| ECS `main` (unreleased) | Adds `gen_ai.conversation.id`. Not usable until an ECS release includes it. |

**Pin rule:** packages with GenAI data streams must set `dependencies.ecs.reference:
"git@v9.5.0"` (or newer) in `_dev/build/build.yml`, and set the matching `ecs.version` in
their pipelines. Most in-scope packages are pinned lower today (`v8.11.0`, `v8.17.0`,
`v9.3.0`); bumping the pin is part of the work.

Three field-definition traps are covered in detail in `references/genai-field-catalog.md`.
Each of them was reproduced on Elasticsearch 9.5:

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

To list the `gen_ai` fields at any tag:
```bash
curl -s https://raw.githubusercontent.com/elastic/ecs/<tag>/generated/csv/fields.csv \
  | awk -F, '$3=="gen_ai"' | cut -d, -f4,5 | sort
```

## Core rules

- **Only ECS fields under ECS field sets.** A `gen_ai.*` field (or a field under any other
  ECS field set) is valid only if it is defined in a released ECS version at or below the
  package's pin. OTel defines more GenAI attributes than ECS, and unreleased ECS `main` has
  `gen_ai.conversation.id`; neither is a reason to add them. ECS may adopt them under a
  different name or type, which would then conflict with the package's definition. Anything
  without an ECS field goes to `<integration>.<data_stream>.<field>`.
- **Values come from OTel.** ECS `gen_ai` is defined as a match of the OTel GenAI semantic
  conventions. Use OTel's well-known values for `gen_ai.provider.name`,
  `gen_ai.operation.name`, `gen_ai.output.type` and `gen_ai.tool.type`, and the OTel JSON
  schemas for the shape of the message fields. Vendor operation names (`InvokeModel`,
  `ChatCompletions_Create`, `acompletion`, `query_source`) do not belong in
  `gen_ai.operation.name`. Keep them in `event.action` or in the vendor namespace.
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
| **Standalone gap analysis** | User invokes `/genai-mappings @packages/<name>` | Read `references/gap-analysis-workflow.md`, then the classification, source-discovery, catalog and pipeline-patterns references as the workflow phases ask. Dispatch per-stream subagents with `references/analysis-subagent-guidance.md`. |
| **Build-time** | An orchestrator passes `references/genai-field-catalog.md` and `references/genai-pipeline-patterns.md` by path to the pipeline builder subagent | The builder reads both references. This SKILL.md does not need to be loaded in the orchestrator thread. |
| **Review-time** | A reviewer finds `gen_ai.*` fields, or a stream classified as GenAI | Reviewer reads `genai-field-catalog.md` (checklist at the end) and `genai-pipeline-patterns.md`. |
| **Research-time** | `research-integration` (orchestrator reads the classification; the Track G subagent reads both) | Load only `references/genai-datastream-classification.md` and `references/genai-source-discovery.md`. **Do not load the catalog or pipeline patterns during research**: they are implementation material. |

The development workflow loads these references automatically:

- `research-integration` classifies proposed streams with the classification reference,
  launches Track G with the classification and source-discovery references, and writes
  `genai-mapping-analysis.md` and section 5.6 of the research brief.
- `create-integration` (new packages and new data streams) classifies streams in Phase 1 and
  passes the catalog and pipeline patterns to the pipeline builder, with the `git@v9.5.0` pin.
- `review-integration` applies the review-time GenAI detection rule and loads the catalog and
  pipeline patterns; the `genai_ecs_pin_minimum` consistency rule covers the pin.

## Open questions / deferred scope

- **`gen_ai.conversation.id`** is only on ECS `main`. Keep the source's session or thread id
  in the vendor namespace until an ECS release includes it, then copy it with `external: ecs`.
- **OTel attributes that ECS has not adopted** (cache and reasoning token counts,
  `gen_ai.agent.version`, `gen_ai.tool.description`, …) are not used under `gen_ai.*`. The
  source values stay in the vendor namespace. Research still records them, so that they can be
  moved once ECS adds the fields.
- **`nested`-typed ECS fields**: once elastic/ecs#2560 is fixed, the local `keyword`
  overrides can become `external: ecs`.

## References

- `references/genai-field-catalog.md` — single source of truth: ECS availability matrix, every
  field with type, meaning, example and restrictions, well-known values, message shapes,
  values without an ECS field, field-definition rules, anti-patterns, review checklist
- `references/genai-source-discovery.md` — research method: where GenAI data hides in each
  source type, content-capture opt-ins, per-API source-to-field maps, field-by-field
  questions that must be answered before a field is marked unavailable
- `references/genai-pipeline-patterns.md` — tested processor patterns: constants, operation
  mapping, token totals, finish reasons, decoding serialized bodies, normalizing messages,
  tool calls, reasoning blocks
- `references/genai-datastream-classification.md` — which data streams are in scope and which
  field groups apply to each kind of stream
- `references/gap-analysis-workflow.md` — standalone audit of an existing package
- `references/gap-analysis-report-template.md` — report structure for the audit
- `references/analysis-subagent-guidance.md` — operating manual for per-stream analysis subagents
- [ECS gen_ai field reference](https://www.elastic.co/docs/reference/ecs/ecs-gen_ai)
- [OTel GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai)
