# Work items and task prompt skeletons

## Work item table

One row per field per stream (per record type in mixed streams). Keep it in your notes and
include it in the builder task prompts and the apply report.

| # | Stream | Record type | Field | Report status | Recommendation | Source path | Check | Action | Decision |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `<stream>` | `<type or all>` | `gen_ai.request.model` | 🔍 | Extract from existing data | `modelId` | todo | map | — |
| 2 | `<stream>` | all | `gen_ai.system` | ⚠️ | — | `gen_ai.system` (published) | todo | fix | D2 |

- **Check** is the result of the Phase 1 verification: `todo`, `done already`, `contradicted`
  or `needs decision`.
- **Action** comes from the action table in `SKILL.md`: `map`, `derive`, `fix`, `add request
  parameter`, `add call`, `map + document`, `add vendor field`, `defer`, `none`.
- **Decision** is the decision id that governs the row, or `—`.

## `DECISION NEEDED` block

Every task prompt tells the subagent to return this instead of guessing:

```
DECISION NEEDED: <decision id from decision-points.md, or "new">
Found: <what was found, and where>
Options: 1) <option and its cost> 2) <option and its cost>
Recommendation: <one option, with the reason>
```

## Pipeline builder

```
Read ingest-pipelines/references/builder-subagent-guidance.md end-to-end before doing anything
else, then follow its "First steps". This is an EXISTING package: you are changing a pipeline
and field files, not building them from scratch.

Package: packages/<package>
Data stream(s): <streams>  (handle them one after another)
Kind: <GenAI (inference | agent | tool execution | message | usage metrics | product
  telemetry) | entity (<entity.type>)>
ECS pin: the pin and ecs.version are already set to <version>. Do not change them.

Also read, by path:
- <genai-mappings|entity-mappings>/references/<kind>-field-catalog.md
- <genai-mappings|entity-mappings>/references/<kind>-pipeline-patterns.md
- apply-mappings/references/<genai|entity>-steps.md

Report: <path>, sections: <names>
Work items: <table, only the rows with Check = todo>
Decisions made by the user: <id: answer, ...>
Sample of the new data: <path, from the source-side change or the existing fixtures>

Constraints:
- Only fields defined in the pinned ECS release. Anything else goes to
  <integration>.<data_stream>.<field>.
- Do not remove, rename or retype a published field unless a decision above allows it. Where an
  ECS field is filled from a published vendor field, copy (set with copy_from) and keep the
  vendor field.
- Extend the handwritten test fixtures with the source fields the new mappings need.
  Anonymize everything. For a source-side setting with no real sample, build the fixture from
  the vendor documentation (<url>) and say so in your return.
- Generate expected output only with `elastic-package test pipeline --generate`, review it, and
  never edit *-expected.json by hand.
- Do not modify CEL programs, agent templates, manifests, system test config or
  sample_event.json.
- If you meet a decision that is not covered above, stop and return DECISION NEEDED.

Return: changed files; for each work item what was done, or why not; test results; any
DECISION NEEDED blocks; anything in the report that contradicted the package.
```

## CEL builder (request parameter, extra call, variable)

```
Read cel-programs/references/builder-subagent-guidance.md end-to-end before doing anything
else. This is an EXISTING CEL program: take its "Direct path" (the one for fixing an existing
program) and change it incrementally, validating with mito at every step.

Package: packages/<package>
Data stream: <stream>
Change: <add request parameter X | add call to endpoint Y | add variable Z>, so that the source
returns <fields>. Source: <report section and vendor documentation URL>.
Variable (if any): name <name>, title <title>, scope <data stream | package>, default <off | ...>
(decision D6, standing decision S2).
Backwards compatibility: with the variable off, the request and the emitted events must be
identical to today.
Also update: the mock server and system test config so that they return the new data
(anonymized), and the raw field definitions for the new response fields.

Do not modify pipelines, pipeline fixtures or sample_event.json. If you meet a decision that is
not covered above, stop and return DECISION NEEDED.

Return: changed files; a sample of the new response shape; mito results; any DECISION NEEDED.
```

## Setup builder (non-CEL input: template, variable, test config)

```
Read integration-testing/references/builder-setup-subagent-guidance.md end-to-end before doing
anything else. This is an EXISTING data stream: change only the agent template option, the
manifest variable and the system test configuration described below.

Package: packages/<package>   Data stream: <stream>   Input: <type>
Change: <option or variable>, so that the source sends <fields>. Source: <report section, doc URL>.
Variable: name <name>, title <title>, default <off | ...>.
Backwards compatibility: with the variable off, the collected data is identical to today.

If the change needs a new service, a new stream or a new input, stop and return DECISION
NEEDED. Do not modify pipelines or sample_event.json.

Return: changed files; what the new data looks like; any DECISION NEEDED.
```

## System test

```
Read integration-testing/references/builder-system-test-subagent-guidance.md end-to-end before
doing anything else.

Package: packages/<package>   Data stream: <stream>   Input: <type>
The Elastic stack is up. Pipeline and source-side changes for this stream are complete.
Run the system test and regenerate sample_event.json. Report pass or fail with the error
excerpts.
GenAI streams with flattened fields: the test data must include a document with message
content longer than 32766 bytes and one with a tool schema deeper than 20 levels. After the
test, query <data stream>::failures and report any document there as a failure.
```

## Reviewer

```
Read review-integration/references/reviewer-subagent-guidance.md end-to-end before doing
anything else.

Package: packages/<package>
Scope: the uncommitted changes under the package (git diff against HEAD). Read-only: change
nothing.
Context: these changes apply a <GenAI | entity> mapping report. The standard GenAI or entity
detection in the review skill applies. Automated validation already passed: <results>.
```

## Re-assessment

```
Read <genai-mappings|entity-mappings>/references/analysis-subagent-guidance.md end-to-end
before doing anything else.

Package: packages/<package>   Data stream: <stream>   Kind: <kind>
Assess the stream as it is now, with the original report as the tracking document: <path>.
Write the report to <path outside the package>. Do not modify any package file.
```
