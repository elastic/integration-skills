# Entity analysis subagent guidance

Operating manual for a subagent dispatched by the `entity-mappings` orchestrator to perform
a per-stream entity field gap analysis on behalf of the `/entity-mappings` skill.

The orchestrator dispatches you with a brief task prompt that points you at this file by
path. **Read this entire file end-to-end before doing any other work.** The orchestrator
does not paste this file's content into your task prompt (to avoid burning context twice);
you load it here in your own fresh context.

The orchestrator's task prompt tells you **what** to analyse — which package, which data
stream, which entity type, and any documentation URLs. This file tells you **how to
operate** — methodology, reference loading, output contract, and guardrails. Follow both.

---

## Scope

Your responsibility is strictly limited to:

- Classifying the assigned data stream as entity or event
- Reading the integration package files to understand current field coverage
- Fetching vendor documentation to identify available source fields
- Producing a per-stream mapping status (✅ / 🔄 / 🔍 / ⛔) for each catalog field
- Investigating gaps through API documentation and package internals
- Writing your findings to a file and returning a concise summary

You do **not**:
- Write pipeline YAML, processor configurations, or field definition files
- Design new data streams beyond describing what data the API provides
- Recommend specific ECS pin versions to use (state whether `v9.5.0` is required, nothing more)
- Modify any integration package files
- Invent `entity.*` field names — only use fields that exist in ECS at the pinned version; for source fields with no ECS match, propose `<integration_name>.<datastream_name>.<field_name>` as a custom field
- Defer or deprioritize any entity field because it requires additional work (extra API call, different endpoint, additional scope) — every entity field must be investigated and included in scope for the first implementation cycle; implementation complexity is for the builder to handle, not a reason to exclude from the gap report

---

## First steps — read these references

Before doing any analytical work, read these files end-to-end:

1. **`entity-mappings/references/entity-field-catalog.md`** — MUST READ: the complete field
   catalog with ECS availability matrix, allowed values, field definitions, and review
   checklist. This is the authoritative source for which fields to assess and what they mean.
2. **`entity-mappings/references/entity-datastream-classification.md`** — MUST READ: the
   classification rule. Apply it to the assigned stream before any field mapping.

Do not proceed with field mapping until you have read both files.

---

## Workflow

### Step 1 — Classify the data stream

Apply the review-time classification rule from `entity-datastream-classification.md` to the
assigned data stream. State the classification and the deciding signal.

If the stream is classified as an **event stream**, write that conclusion to your output
file and return. Do not attempt entity field mapping on event streams.

### Step 2 — Read the integration files

Navigate to the data stream directory and read:
- `fields/*.yml` — existing field declarations
- `elasticsearch/ingest_pipeline/*.yml` — current pipeline
- `_dev/test/pipeline/test-*.json` or `sample_event.json` — real data samples
- `agent/stream/*.yml.hbs` — collection method and API calls

Note which source fields are available in the sample data.

### Step 3 — Fetch vendor documentation

Identify the upstream API or endpoint (usually visible in the agent stream template or
the integration README). Fetch the relevant API documentation to understand the full field
schema available from the vendor, beyond what the current pipeline extracts.

### Step 4 — Map each catalog field

For each field in the catalog's "Core identity fields" and "Attributes / Lifecycle /
Relationships" sections, assign ✅ / 🔄 / 🔍 / ⛔ with your reasoning. Be specific:

- **✅ Direct:** name the exact source field and note any type conversion needed.
- **🔄 Derived:** explain the logic in plain English. Do not write processor YAML.
- **🔍 Investigate:** only if the source *might* have the data; moves to Step 5.
- **⛔ N/A:** only if the entity type genuinely lacks this concept. Always justify.

### Step 5 — Investigate gaps

For each 🔍 field:
- Check the package for commented-out fields, TODOs, alternative config vars
- Check vendor API docs for the data (existing call / different endpoint / new call)
- Produce a recommendation: Extract from existing call / Add API parameter / New API call / Cannot be collected
- **Implementation complexity is not a reason to exclude a field.** If an entity field requires an additional API call, a different endpoint, or an extra OAuth scope to collect, document that clearly (endpoint path, response shape, required scopes) and mark the field in scope. That information is planning material for the build phase. Only mark ⛔ when the data provably cannot be collected at all from the vendor API.
- **Do not design the pipeline** — describe the data and the API; describe what is available and how, not how to process it

### Step 5b — Custom fields for source fields with no ECS equivalent

For each source field that carries entity-relevant state but has no matching ECS field:
- Do **not** propose an invented `entity.*` path — only fields that exist in ECS at the pinned version are valid
- Propose the custom namespace instead: `<integration_name>.<datastream_name>.<field_name>`
- Note in the gap report that it is a custom field, not ECS, so the reader understands the scoping decision
- Example: source field `isEmployee` → `github.members.is_employee` (custom field, no ECS equivalent)

### Step 6 — Write findings and return

Write the full analysis to a file following the structure in
`entity-mappings/references/gap-analysis-report-template.md`. Use a descriptive filename
such as `entity-gap-analysis-<stream>.md` in the package root or a location the
orchestrator specified.

Return a **concise summary** (not the full file inline) containing:
- Data stream classification and deciding signal
- Count of fields by status (✅ N / 🔄 N / 🔍 N / ⛔ N)
- Key findings (most important direct mappings, most impactful gaps)
- Whether `git@v9.5.0` ECS pin is required
- Any new scopes/permissions required
- Path to the file you wrote

---

## Quality standards

- **Do not guess at mappings.** If you are uncertain, mark 🔍 and investigate.
- **Fetch external docs when needed.** Do not rely solely on training data for API schemas —
  APIs change, and the current pipeline may not expose all available fields.
- **Show your reasoning** for derived mappings — a future engineer needs to understand why
  the mapping is valid.
- **Be conservative with ⛔ "not applicable"** — only use it when the entity type genuinely
  lacks the concept. Always provide evidence from the integration's own sample data or
  vendor documentation.
- **Be conservative with ⛔.** Any entity field that can be collected — regardless of how many API calls, endpoints, or scopes it requires — is in scope for the first implementation cycle. Only mark ⛔ when the data provably cannot be collected at all. "Requires additional work" is a note for the builder, not grounds for exclusion.
- **Never invent `entity.*` field names.** Only fields that exist in ECS at the pinned version
  are real ECS fields. Source fields with no ECS match go to `<integration>.<datastream>.*`.
- **Be descriptive with examples.** Quote actual field names from sample events or vendor
  documentation to support each decision.
- **Describe data, not pipeline.** The output should tell the pipeline builder what fields
  are available in the source data, not how to configure the pipeline.

---

## What to return

When you finish, report back with:
1. One-sentence classification result
2. A 4-line status summary (count per status symbol)
3. Top 3–5 key findings (most useful mappings or most important gaps)
4. Whether a `git@v9.5.0` pin is required
5. New scopes/permissions required (or "none")
6. The path to the written analysis file
