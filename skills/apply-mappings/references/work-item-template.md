# Work items and task prompt skeletons

## Work item table

One row per piece of work, not per report cell. A row covers one field, or several fields that
share status, recommendation, source object and decision, on one or several record types. Rows
with nothing to do (GenAI ✅, ⛔) are left out: count them only. Keep the table in your notes
and include it in the builder task prompts and the apply report.

| # | Stream | Record types | Fields | Report status | Recommendation | Source path | Check | Action | Decision |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `<stream>` | `<types or all>` | `gen_ai.request.temperature`, `.top_p`, `.max_tokens` | 🔍 | Extract from existing data | `input.inputBodyJson.*` | todo | map | — |
| 2 | `<stream>` | all | `gen_ai.system` | ⚠️ | — | `gen_ai.system` (published) | todo | fix (minor): add `gen_ai.provider.name` next to it, deprecate it in its description | D3 |

- **Check**: `todo`, `done already` or `contradicted` after the Phase 1 verification, and
  `deferred` for what Phase 3 leaves to another run.
- **Action** comes from the action table in `SKILL.md`: `map`, `derive`, `fix`, `add request
  parameter`, `add call`, `map + document`, `add vendor field`, `defer`. For a D3 row it
  states the half this run builds, in words a builder can follow without the decision file.
- **Decision** is the decision id that governs the row, or `—`.

## `DECISION NEEDED` block

Append this to every builder task prompt:

```
If you meet a decision that this prompt does not cover, stop and return, instead of guessing:

DECISION NEEDED: <short name of the decision>
Found: <what was found, and where>
Options: 1) <option and its cost> 2) <option and its cost>
Recommendation: <one option, with the reason>
```

## Pipeline builder

```
Read ingest-pipelines/references/builder-subagent-guidance.md end-to-end before doing anything
else, then follow its "First steps". This is an EXISTING data stream: you change its pipeline,
field files and pipeline fixtures, you do not build them from scratch.

Then read apply-mappings/references/<genai|entity>-steps.md and the mapping references it
names.

Package: <absolute path of packages/<package>>
Data stream(s): <streams>  (handle them one after another)
Kind: <GenAI (inference | agent | tool execution | message | usage metrics | product
  telemetry) | entity (<entity.type>)>
ECS pin: build.yml and the ecs.version of these streams are <version>. Do not change them.
Release: <the next minor | the major>

Report: <path>, sections: <names>
Work items: <table, only the rows with Check = todo>
Decisions: <id: answer, ...>
Sample of the new data: <path, from the source-side change or the existing fixtures | vendor
  documentation URL, when there is no real sample>

Constraints:
- Existing output only grows. A record the pipeline handles today keeps every value it has,
  and a new processor does not overwrite a value that is already set. The work items and
  decisions above are the only exceptions.
- Where an ECS field is filled from a published vendor field, copy it and keep the vendor
  field. Do not add a published field to a removal list, such as the one behind
  preserve_duplicate_custom_fields.
- Extend the handwritten fixtures. Do not replace or reorder their records.
- After regenerating expected output, compare every expected file that existed before with
  HEAD, and list the fields whose value changed or disappeared.
- Do not modify CEL programs, agent templates, manifests, system test config or
  sample_event.json.

Return: changed files; for each work item what was done, or why not; the list of changed or
removed values; test results; any DECISION NEEDED blocks; anything in the report that the
package or the mapping references contradict; problems you found that are not part of the
work items.
```

## CEL builder (request parameter, extra call, variable, test data)

```
Read cel-programs/references/builder-subagent-guidance.md end-to-end before doing anything
else. Its workflow builds a new program. This is an EXISTING one, with no test-api.py: take
the "Direct path" of its step 4 and change the program incrementally, validating with mito at
every step. Keep the existing mock and add only what the change needs. Add the new variable
only: do not remove, move or rename any other variable.

Package: <absolute path of packages/<package>>
Data stream: <stream>
Change: <add request parameter X | add call to endpoint Y | add variable Z>, so that the source
returns <fields>. Source: <report section and vendor documentation URL>.
  (or: extend the mock response with <fields or documents> and nothing else)
Variable (if any): name <name>, title <title>, scope <data stream | package>, default <off | ...>
(decision D4).
Backwards compatibility: with the variable off, the request and the emitted events must be
identical to today.
Also update: the mock server and system test config so that they return the new data
(anonymized), and the raw field definitions for the new response fields.

Do not modify pipelines, pipeline fixtures or sample_event.json.

Return: changed files; a sample of the new response shape; mito results; any DECISION NEEDED.
```

## Setup builder (non-CEL input: template, variable, test config, test data)

```
Read integration-testing/references/builder-setup-subagent-guidance.md end-to-end before doing
anything else. Its workflow sets up a new stream. This is an EXISTING one: change only the
agent template option, the manifest variable and the system test data or configuration
described below. Do not trim the template, do not remove or move variables, and leave
format_version and conditions.kibana.version as they are. Where the manual has no guide for
this input type, follow the existing template.

Package: <absolute path of packages/<package>>   Data stream: <stream>   Input: <type>
Change: <option or variable>, so that the source sends <fields>. Source: <report section, doc URL>.
  (or: extend the sample data with <fields or documents> and nothing else)
Variable (if any): name <name>, title <title>, default <off | ...> (decision D4).
Backwards compatibility: with the variable off, the collected data is identical to today.

If the change needs a new service, a new stream or a new input, return DECISION NEEDED. Do not
modify pipelines or sample_event.json.

Return: changed files; what the new data looks like; any DECISION NEEDED.
```

## System test

```
Read integration-testing/references/builder-system-test-subagent-guidance.md end-to-end before
doing anything else.

Package: <absolute path of packages/<package>>   Data stream: <stream>   Input: <type>
The Elastic stack is up. Pipeline and source-side changes for this stream are complete.
Run the system test and regenerate sample_event.json. Report pass or fail with the error
excerpts.
GenAI streams: after the test, query <data stream>::failures and report any document there as
a failure.
```

## Reviewer

```
Read review-integration/references/reviewer-subagent-guidance.md end-to-end before doing
anything else.

Package: <absolute path of packages/<package>>
Scope: these changed files: <git status --porcelain for the package, tracked and untracked,
without *-expected.json, sample_event.json and docs/README.md>. Compare tracked files with
HEAD and review new files whole. Change nothing in the package, and write
tmp/integration-review.md at the repository root.
Context: these changes apply a <GenAI | entity> mapping report to existing data streams, for
<the next minor | the major>. The standard GenAI or entity detection in the review skill
applies. Decisions: <id: answer, ...>. Deferred to the major, so still present: <fields>.
Automated validation already passed: <results>.
```

## Check of the applied rows

```
Read <genai-mappings|entity-mappings>/references/analysis-subagent-guidance.md end-to-end
before doing anything else, and the references it lists. Your task is narrower than its
workflow: you check work that was just applied, you do not write a new analysis.

Package: <absolute path of packages/<package>>   Data stream: <stream>   Kind: <kind>
Original report: <path>
Applied rows: <the work item table rows that were applied, with the decisions>

For each applied row, say whether the package now populates the field as the mapping
references require. Read the pipeline, the field definition, the handwritten fixture and the
regenerated expected output. Answer "populated correctly", or "not", with the evidence. In
this reply, do not use the report's status symbols for an entity stream: there they do not say
what the package does.

Do not fetch vendor documentation: take the source facts from the original report, unless a
row's source changed in this work (<rows, or "none">).
Also list anything wrong you see in the changed streams that is outside the applied rows.

Write the result to <path outside the package>. Do not modify any package file.

Return: per row, the verdict and the evidence; counts; the findings outside the applied rows.
```
