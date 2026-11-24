---
name: apply-mappings
description: >-
  Use when applying the findings of a genai-mappings or entity-mappings gap analysis report to an
  EXISTING data stream of an existing package: adding or fixing gen_ai.* or entity.* mappings,
  bumping the ECS pin, adding the request parameter, API call or config variable that makes the
  source send the missing data, extending fixtures, and updating README and changelog. Asks the
  user at each design decision. Invoke manually with /apply-mappings.
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# apply-mappings

Implements a gap analysis report on an existing package. The report comes from
`/genai-mappings` or `/entity-mappings`. This skill does not research or assess. It reads the
report, checks it against the package, asks the user about every design decision, dispatches
the builders, documents, validates, and checks the result against the report.

## When to use

- A `genai-mappings` or `entity-mappings` report exists for a package, and its mappings should
  be added to existing data streams
- The report lists source-side gaps (an API parameter, an extra call, a content-capture
  setting) that the integration itself can implement

## When not to use

- **No report yet**: run `/genai-mappings` or `/entity-mappings` first.
- **A new package or a new data stream**: use `create-integration`. A report item that needs a
  new data stream is handed over to it (see the action table).
- **General quality fixes** unrelated to a mapping report: use `maintain-integration`.
- **Packages on the `entity-analytics` input** (`entityanalytics_*`): they have their own
  pipelines and review checklist. Report that they are not covered and stop.

## Inputs

| Input | Example |
|---|---|
| Package | `@packages/claude_code` |
| Report(s) | `@genai-gap-analysis-claude_code.md`, `@entity-gap-analysis-authentik.md` (one per kind; both can be given) |
| Stream scope (optional) | "only `user`". Default: every stream in the report |
| Release scope (optional) | "the next minor", "the 3.0.0 scope". Default: asked when the report has Breaking rows (D3) |
| Constraints (optional) | "no cloud credentials for system tests", "don't touch the CEL program" |

## Rules

1. **Local only.** Never commit, push, open or update a pull request, or post anywhere. Leave
   every change uncommitted for the user.
2. **The report is a list of hypotheses.** Verify each item against the package files before
   changing anything. A stale or wrong item is reported, not applied. Where a report row and
   the mapping skill's references disagree on a name, value or shape, the references win.
3. **Ask at every design decision** (`references/decision-points.md`), before editing. When
   the report already records the answer, take it from there and say so. Never pick a breaking
   option silently.
4. **One run builds one release.** Removing, renaming, retyping or changing the meaning of a
   published field is a breaking change. The replacement ships in a minor, with the old field
   deprecated. The removal is a later run, for the next major. It can be built early, and it
   is released only after the rules, ML jobs and dashboards that read the field have moved
   (D3).
5. **Existing output only grows.** Outside a decision, a record the package handles today
   comes out with the same values plus the new fields. New processors do not overwrite a value
   the pipeline already sets, and a published vendor field that feeds an ECS field is copied,
   not renamed.
6. **Only released ECS fields.** Follow the mapping skills: nothing under `gen_ai.*`, `entity.*`
   or another ECS field set unless it is in the pinned ECS release. Everything else goes to
   `<integration>.<data_stream>.<field>`.
7. **The integration implements what it controls**: its own request, call or input
   configuration. What the user's environment or the vendor account controls (a logging
   setting, an environment variable in the user's application) is documented in the README,
   and the field is still mapped, so that it works once the setting is on. A variable that
   makes the integration collect prompts, responses, tool details or other content is **off by
   default**.
8. **Never hand-edit generated files**: `*-expected.json`, `sample_event.json`, the built
   `docs/README.md` (edit `_dev/build/docs/README.md`).
9. **Anonymize** every fixture and mock value.
10. **Delegate, one subagent at a time.** Do not load domain skills into the orchestrator
    thread: the builders load them in their own context. The exceptions are the direct edits of
    Phase 4 (ECS pin) and Phase 8 (README, changelog), for which the orchestrator loads
    `package-spec` and `elastic-package-cli`.

## How the report is read

Both reports use ✅ 🔄 🔍 ⛔, and the GenAI report adds ⚠️. The symbols are shared, the meanings
are not. This skill relies on the table below and on nothing either mapping skill says about the
other. Whatever the status, check the package before acting (Phase 1).

| Symbol | GenAI report | Entity report |
|---|---|---|
| ✅ | The package already populates the field correctly. | A direct mapping **instruction**: this source field feeds that ECS field. It does not say the package already does it. |
| 🔄 | Not populated yet, but computable (constant, lookup, sum). To implement. | A derived mapping **instruction**, with the derivation in plain English. |
| 🔍 | A gap with one recommendation: *Extract from existing data*, *Add API parameter or request setting*, *New API call*, *Source-side setting (document only)*, *New data stream*. | A gap with one recommendation: *Extract from existing call*, *Add API parameter*, *New API call*, *New data stream*, *Cannot be collected*. |
| ⛔ | Not applicable, or not available at the source. Nothing to do. | Not applicable. Nothing to do. |
| ⚠️ | Populated, but wrongly. To fix. | Not used. |

| Report item | Action | Done by |
|---|---|---|
| GenAI ✅, any ⛔, entity *Cannot be collected* | Nothing. | — |
| Entity ✅ / 🔄 | Check the package and implement what is missing. | pipeline builder |
| GenAI 🔄 | Implement the derivation (constant, lookup, sum). | pipeline builder |
| GenAI ⚠️ | Fix the published mapping. An Additive fix goes in this release, a Breaking one in the release D3 gives it. | pipeline builder |
| 🔍 Extract from existing data (entity: *Extract from existing call*) | Map it from data the stream already receives. | pipeline builder |
| 🔍 Add API parameter or request setting (entity: *Add API parameter*), 🔍 New API call | Add it to the request of the same stream (D4), and update mock, system test config and README. Then map it. | CEL builder (or setup builder), then pipeline builder |
| 🔍 Source-side setting (document only) | Map the field and document the setting (rule 7). | pipeline builder, README |
| 🔍 New data stream | Not done here. List it as deferred, to build with `create-integration` (add data stream) using the report section as the brief. | user |
| Values with no ECS field (🔍 rows) | Add a `<integration>.<data_stream>.<field>` definition and copy the value into it. | pipeline builder |
| Adjacent ECS fields | The ones the report's *Detection conventions* table asks for (identity, the native verb in `event.action`, categorization) are in scope. The others only after D10. | pipeline builder |

## Workflow

Read `references/apply-workflow.md` fully before starting. Its phases: 0 intake, 1 work items,
2 grouping, 3 decisions, 4 package prerequisites (ECS pin), 5 source-side changes, 6 pipeline
and fields, 7 system tests, 8 docs and changelog, 9 validation and review, 10 check against
the report.

Kind-specific steps are in `references/genai-steps.md` and `references/entity-steps.md`. Read
the one that matches the report. Reports of both kinds make one run and one release: phases 0
to 4 and 8 to 10 run once, and phases 5 to 7 run for the GenAI groups, then for the entity
groups. GenAI streams and entity streams never share a group.

## Subagents

The dispatch convention is in `references/apply-workflow.md`, and the task prompt skeletons in
`references/work-item-template.md`. The manuals, passed **by path**:

| Manual | Used for |
|---|---|
| `cel-programs/references/builder-subagent-guidance.md` | Request parameters, extra calls, variables and mock changes on CEL streams |
| `integration-testing/references/builder-setup-subagent-guidance.md` | Template, variable and test config changes on non-CEL inputs |
| `ingest-pipelines/references/builder-subagent-guidance.md` | Pipelines, field definitions, pipeline fixtures |
| `integration-testing/references/builder-system-test-subagent-guidance.md` | System tests and `sample_event.json` generation |
| `review-integration/references/reviewer-subagent-guidance.md` | Read-only review of the result |
| `genai-mappings/references/analysis-subagent-guidance.md` or `entity-mappings/references/analysis-subagent-guidance.md` | Check of the applied rows against the report |

## References

- `references/apply-workflow.md`: dispatch convention, phases 0–10, stop conditions
- `references/decision-points.md`: every design decision, with the question and options
- `references/work-item-template.md`: work item table and task prompt skeletons
- `references/genai-steps.md`: GenAI-specific steps
- `references/entity-steps.md`: entity-specific steps
- `references/apply-report-template.md`: the final report
