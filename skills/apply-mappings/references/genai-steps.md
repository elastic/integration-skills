# GenAI steps

How to apply a `genai-mappings` report. The pipeline builder reads this file and then, under
`genai-mappings/references/`, `genai-field-catalog.md`, `genai-pipeline-patterns.md` and
`genai-detection-conventions.md`. Those three are the authority on fields, values, shapes,
conventions and processors, and they win when a report row disagrees with them: apply the
row with their value and report it as changed from the report. This file only adds what
applying a report to a published stream needs.

## Reading the GenAI report

| Report section | What it gives |
|---|---|
| Per-stream field tables | Status, recommendation, **Change** (New / Additive / Breaking / No change) and **Basis** for every field. A ✅ means the package already populates the field correctly. Mixed streams have one column per record type: handle every record type of the stream. |
| *Incorrect mappings* | Per field: what the package does now, what it should do, and its Change. |
| *Detection conventions* | Per stream: the tool-call representation, where call results go, the identity derivation, the message shape, and the README notes that are missing. |
| *Fields outside the pinned ECS*, *Values with no ECS field* | The names that must leave `gen_ai.*`, and the values that stay in the vendor namespace. A row that says "wait for an ECS release" (RFC 0060) is a vendor field only. Never write the ECS name. |
| *Breaking changes and consumers*, *Release plan* | What ships in the next minor (New, Additive, deprecations) and what waits for the next major. |
| *Content capture and source configuration* | What the user must enable at the source, who controls it, and whether the README already documents it. |

## Order of work inside a stream

1. **ECS check**, before any edit: check every `gen_ai.*` name the work will define or write
   against the pinned release (conventions, section 1). A name that is not in it goes to
   `<integration>.<data_stream>.<field>`, whatever the report says. Report the item as
   changed, not skipped.
2. **Field definitions** (`fields/`): the catalog's *Field definition rules*. A field that
   this release deprecates gets the deprecation note in its `description` (catalog rule 6).
3. **Vendor-namespace definitions** for *Values with no ECS field* (cache and reasoning token
   counts, session or conversation ids, tool source, …): `<integration>.<data_stream>.<name>`,
   with the type the source uses.
4. **Pipeline**: the patterns' *Layout*. Processors that already work stay where they are.
   Order of the new ones: decode, provider and operation, identity, scalars, messages, tool
   definitions, tool calls, token totals, vendor copies, remove `_temp`. Then, at the end of
   the main pipeline: truncation tags, the package's empty-value cleanup if it has one
   (changed to skip tool definitions), depth cap.
5. **Conventions**: sections 2 to 8 and 10 of the conventions, with the options the report's
   *Detection conventions* row gives the stream. Two points differ on a published stream:
   - Section 10's capture default is for a new stream. Here a new content variable is off by
     default: turning collection on at upgrade changes the default behaviour.
   - The conventions ask to read #22224 and #22225 again. If a later comment changes a row,
     do not apply it yourself: return `DECISION NEEDED`.
6. **Fixtures**: every new mapping has a record that fills it, plus the cases of the patterns'
   *Test fixtures* that the changed fields can reach. Anonymize account ids, ARNs and session
   names.
7. **Index-time check**: pipeline tests do not index, and LogsDB hides the length limit even
   in a system test. So do the check of *Test fixtures* yourself: index the pipeline output
   for a document with content longer than 32766 bytes, and for one with a tool input or
   schema deeper than 20 levels, into an index in standard mode that maps the fields as the
   package does. Report what was accepted and what was rejected, and delete the index.
8. **Self-check** against the HIGH items of the catalog's review checklist before returning.

## Rules specific to a published stream

- **A D3 work item** (a legacy or non-ECS name, a retype, a value that changes meaning,
  message fields moved to the OTel shape): do what its Action says for this release, and
  nothing more. Never remove a published field in the release that adds its replacement.
- **`flattened` safety is not a decision.** A published `flattened` field without
  `ignore_above` or a depth cap, or a cleanup that reaches tool definitions, rejects or alters
  documents. Fix it in this change, even when the report only names it in passing. It only
  stops rejections (Additive, conventions section 9).
- **Raw bodies** stay. The normalized message fields are added next to them: they have a
  different shape.
- **TSDB metric streams**: a new field that splits series gets `dimension: true`. A
  `gen_ai.request.model` that copies an existing dimension does not.
- **A fixture without a real sample** is built from the vendor documentation, and your return
  says it was not verified against real data.

## What the orchestrator needs back for the README

Besides the return the task prompt asks for: how `user.name` is derived, the tags set when
content is removed or cut, the option the stream uses for tool calls, and every field
deprecated by this release with its replacement.
