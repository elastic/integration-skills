# GenAI steps

Steps that apply to a `genai-mappings` report. The pipeline builder reads this file together
with `genai-mappings/references/genai-field-catalog.md`,
`genai-mappings/references/genai-pipeline-patterns.md` and
`genai-mappings/references/genai-detection-conventions.md`. Those three are the authority on
fields, values, shapes, conventions and processors. This file only says how to apply a report
with them.

## Reading the GenAI report

- A ✅ means the package already populates the field correctly. Nothing to do.
- Per-stream field tables give status, recommendation, **Change** (New / Additive / Breaking /
  No change) and **Basis** for every field. Mixed streams have one column per record type:
  handle every record type of the stream.
- The *Incorrect mappings* section gives, per field, what the package does now, what it should
  do, and its Change. Decisions D2, D3 and D4 apply to those rows.
- The *Breaking changes and consumers* and *Release plan* sections split the work into the next
  minor (New, Additive, deprecations) and the next major (Breaking). D16 applies to them.
- The *Detection conventions* table says, per stream, which tool-call representation, identity
  derivation and message shape the stream needs.
- The *Content capture* table says what the user must enable at the source, who controls it,
  and whether the README already documents it. It drives S1, S2 and Phase 9.
- *Values with no ECS field* lists values that stay in the vendor namespace. Rows marked "wait
  for an ECS release" (RFC 0060) are vendor fields only. Never write the ECS name.
- A report that has no Change column predates these conventions: re-run the assessment (D14).

## Before any edit: the ECS check

List the `gen_ai` fields of the pinned ECS release
(`genai-detection-conventions.md`, section 1) and check every `gen_ai.*` name the work will
define or write against it. A name that is not in the list is not written, whatever the report,
an issue or a reference table says (`gen_ai.tool.call.count`, `gen_ai.tool.source.*`,
`gen_ai.usage.cache_*.input_tokens`, `gen_ai.conversation.id`). Its value goes to
`<integration>.<data_stream>.<field>`. Report the item as changed, not skipped.

## Order of work inside a stream

1. **Field definitions** (`fields/`): follow the catalog's field definition rules. The three
   `nested` fields (`finish_reasons`, `stop_sequences`, `encoding_formats`) are defined locally
   as `keyword`. The six `flattened` fields use `external: ecs` with `ignore_above: 8191`.
   Everything else is `external: ecs`. Nothing is defined under `gen_ai.*` that is not in the
   pinned ECS release. Fields deprecated by this release get the deprecation note in their
   `description` (catalog rule 6).
2. **Vendor-namespace definitions** for *Values with no ECS field* (cache and reasoning token
   counts, session or conversation ids, tool source, …): `<integration>.<data_stream>.<name>`,
   with the type the source uses.
3. **Pipeline**: put the work in a `genai` sub-pipeline, decode bodies into `_temp`, build the
   fields with the pattern snippets, copy the vendor-namespace values, then remove `_temp`.
   Order: decode, constants and lookups (provider, operation), identity, scalars, message
   normalization, tool definitions, tool calls, token totals, vendor copies, remove `_temp`.
   At the end of the main pipeline: truncation tags, empty-value cleanup (skipping tool
   definitions), depth cap. On OTel-native streams (`input: otelcol`), write under
   `attributes.gen_ai.*`.
4. **Fixtures**: extend the handwritten inputs so that every new mapping has a record that
   fills it. Include a content value longer than 32766 bytes in a pipeline test, to prove that
   `ignore_above` works, and a tool input or schema nested deeper than 20 levels. Follow the
   fixture checklist in the pipeline patterns. Anonymize account ids, ARNs and session names.
5. **Self-check** against the HIGH items of the catalog's review checklist before returning.

## Conventions to apply

| Topic | Apply |
|---|---|
| Provider and operation | The per-source tables (conventions, sections 2 and 3). The native verb goes to `event.action`. A record that is not an operation gets none. |
| Tool calls, execution-side record | Option A: scalar `gen_ai.tool.*`, `execute_tool` only when the tool ran, `event.outcome` of the call, categorization by what the tool did. |
| Tool calls, provider log | Option B: `gen_ai.tool.name`, `.type`, `.call.id` aligned, generation order, only the response's calls. No count field. `event.category` unset. README note on order, `_source` pairing and `MV_COUNT`. |
| Tool results | Execution-side: `gen_ai.tool.call.result` with its call id. Provider logs: in `gen_ai.input.messages` under `role: tool` until #22225 section 2 is answered (D17). |
| Identity | `user.name` from the stable principal, session names to `related.user`. README section on the derivation. |
| Agents | `gen_ai.agent.*` only where a hosted agent exists, never from the caller. |
| Tool definitions | `{type, name, description, parameters}` with OTel types. README note that `description` is kept on purpose. |
| Messages | OTel shape, tool results under `role: tool`, normalized `finish_reason` per output message, `gen_ai.response.finish_reasons` verbatim, built from the structured body. |
| Removed or cut content | A tag per field, listed in the README. |
| TSDB streams | A new field that splits series gets `dimension: true`; a copy of an existing dimension does not. |

## Rules specific to applying on an existing package

- **A published `gen_ai.system`**, `gen_ai.prompt`, `gen_ai.completion`, `gen_ai.usage.*_tokens`
  with old names, or any OpenTelemetry attribute under `gen_ai.*`: D2.
- **A `nested` trio field or a `flattened` field without `ignore_above`**, already published:
  D3. Do not change the definition without the answer.
- **Token totals** that become cache-inclusive, **operation names** mapped to the OTel values,
  a changed provider string, **message fields** moved to the OTel shape, or an `event.action`
  that changes meaning: D4.
- **Any Breaking row**: D16 decides the release it goes in. Without consumers found, the
  answer is still asked; never remove a published field in the release that adds its
  replacement.
- **Provider** on a multi-backend product: D8. A `constant_keyword` is only correct when every
  record of the stream comes from one provider.
- **Raw bodies** stay (D5, copy). The normalized message fields are added next to them. When
  detection rules match over the whole body, a full-body `text` field in the vendor namespace
  survives the major.
- **TSDB metric streams**: a `gen_ai.request.model` that copies an existing dimension gets no
  `dimension: true` of its own.
- **A 🔍 source-side setting without a sample**: D12. The fixture is built from the vendor
  documentation and the report says it was not verified against real data.
- **`flattened` safety is not optional.** If the package already has a `flattened` field that
  can exceed the depth limit, or a cleanup that reaches tool definitions, fix it in the same
  change, even when the report only names it in passing: these reject or alter documents.

## By stream kind

| Kind | Notes |
|---|---|
| Inference | All field groups. Tool calls inside the output are `tool_call` parts and the option B arrays. |
| Agent | `operation.name` `invoke_agent` or `create_agent`, agent fields, content when logged. |
| Tool execution | `operation.name: execute_tool` where the tool ran, one call per record. `tool.call.arguments` is the tool's input, never product metadata about the call. The native verb stays in `event.action`. |
| Message | One message in `input.messages` or `output.messages`. A string system prompt is wrapped as `[{type: text, content}]` in the flattened fields. |
| Usage metrics | `provider.name`, `request.model`, bucket totals, `token.type` on rows split by token kind. No message fields, no operation. |
| Product telemetry | Map per record type. A record type of another kind follows that kind's notes. |

## README and changelog

For every opt-in in the content capture table, Phase 9 documents the setting, who controls it,
the effect, the limits, and the sensitive-data warning. A setting the integration cannot change
(S1) is documented as a prerequisite for the content fields.

Also document, where they apply: how `user.name` is derived; the option B tool arrays (order,
`_source` pairing, `MV_COUNT(gen_ai.tool.call.id)`); the truncation tags; that tool
`description` is kept; which fields are deprecated, what replaces them and the release that
removes them. In the major, add a migration table (old field → new field).

The changelog of the minor names each deprecated field and its replacement (for example
`gen_ai.system` → `gen_ai.provider.name`). The major uses a `breaking-change` entry.
