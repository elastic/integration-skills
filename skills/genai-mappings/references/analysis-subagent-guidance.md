# GenAI analysis subagent guidance

Operating manual for a subagent dispatched by the `genai-mappings` orchestrator to analyse one
data stream (or one group of record types) of an integration.

The orchestrator's task prompt points you at this file by path. **Read this whole file before
doing anything else.** The task prompt says **what** to analyse (package, stream, record types,
stream kind, doc URLs, tracking issue). This file says **how**.

---

## Scope

You do:

- Confirm the classification of the assigned stream and its record types
- Read the package files and decode every embedded body in the fixtures
- Fetch the current vendor documentation for the source
- Assign a status, with evidence, to every field in the workflow's Phase 4 list
- Check the existing `gen_ai.*` definitions against the catalog's rules and checklist
- Write your findings to a file and return a short summary

You do **not**:

- Write pipeline YAML, Painless or field definitions
- Modify any package file
- Propose any `gen_ai.*` name that is not in the pinned ECS release (v9.5.0). OTel registry
  attributes and `gen_ai.conversation.id` (ECS `main` only) are not valid. Their values go to
  `<integration>.<data_stream>.<field>`.
- Mark a field ⛔ because collecting it needs an opt-in, an extra endpoint, a different
  transport or a new data stream. That is 🔍, with the matching recommendation and what is
  needed.
- Accept the tracking issue's claims without evidence

---

## First steps — read these references

1. `genai-mappings/references/genai-field-catalog.md`: fields, values, shapes, definition
   rules, checklist
2. `genai-mappings/references/genai-source-discovery.md`: the three layers, where data hides,
   per-API maps, field-by-field questions
3. `genai-mappings/references/genai-datastream-classification.md`: stream kinds
4. `genai-mappings/references/gap-analysis-workflow.md`: the status table and Phase 4 field list
5. `genai-mappings/references/genai-pipeline-patterns.md`: expected token totals, message shape
   and tool-name handling, needed for the definition check (you still don't write processors)

Do not start mapping until you have read all five.

---

## Workflow

1. **Classify** the stream and each record type. If out of scope, check the audit-log trap,
   write the conclusion, and return.
2. **Layer 1**: list every `gen_ai.*` field the package defines and sets, with its definition.
3. **Layer 2**: list everything the stream already receives. Decode JSON strings in fixtures and
   mock responses. Note fields that are parsed and then dropped or left as strings.
4. **Layer 3**: fetch vendor docs. List record types, payload schemas, content opt-ins, other
   transports and endpoints, and accepted request parameters.
5. **Map** every Phase 4 field with a status and evidence, and give every 🔍 exactly one
   recommendation from the workflow's table. Decide it by who controls the setting. Answer the
   field-by-field questions in `genai-source-discovery.md` for every field you do not mark ✅.
6. **Check** existing definitions and values against the catalog checklist.
7. **Compare** with the tracking issue, if one was given, and list the differences.
8. **Write** the findings using `gap-analysis-report-template.md` (the per-stream sections) to
   the path the orchestrator gave, or `genai-gap-analysis-<package>-<stream>.md` in the current
   working directory. Never write inside the package directory, even if the given path
   points there.

---

## Quality standards

- **Evidence for every status.** Quote the payload path, fixture line or doc URL.
- **⛔ not available needs all three layers.** Say what you checked in each. ⛔ not
  applicable needs the stream kind.
- **Fetch documentation.** Do not rely on training data for API schemas or logging settings.
- **Values from the catalog.** Provider and operation values must be OTel well-known values.
  Say so when a vendor value has no mapping.
- **Content needs its opt-in.** For every content field, name the setting that enables it
  and whether the README documents it.
- **Describe data, not processors.** Say where the value is and in what form (string, object,
  array, JSON-in-string). The builder writes the pipeline.

---

## What to return

1. One sentence: stream kind and the deciding evidence
2. Counts per status (✅ ⚠️ 🔄 🔍 ⛔), and the 🔍 count per recommendation
3. The 3–5 most important findings (incorrect mappings first, then the most useful 🔍 gaps)
4. Source-side changes needed (opt-ins, transports, endpoints, new streams), or "none"
5. Differences from the tracking issue, or "none"
6. Path of the file you wrote
