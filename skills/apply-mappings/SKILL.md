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
the builders, validates, documents, and re-assesses.

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
| Stream scope (optional) | "only `user`", default: every stream in the report |
| Constraints (optional) | "no stack available for system tests", "don't touch the CEL program" |

## Rules

1. **Local only.** Never commit, push, open or update a pull request, or post anywhere. Leave
   every change uncommitted for the user.
2. **The report is a list of hypotheses.** Verify each item against the package files before
   changing anything. A stale or wrong item is reported, not applied.
3. **Ask at every design decision** (`references/decision-points.md`), before editing.
   Subagents cannot ask the user. The orchestrator collects decisions up front and re-asks when
   a builder returns `DECISION NEEDED`. Never pick a breaking option silently.
4. **One subagent at a time.** Finish the work of one stream or group before the next.
5. **Only released ECS fields.** Follow the mapping skills: nothing under `gen_ai.*`, `entity.*`
   or another ECS field set unless it is in the pinned ECS release. Everything else goes to
   `<integration>.<data_stream>.<field>`.
6. **Published data is not rewritten without a go-ahead.** Removing, renaming, retyping or
   changing the meaning of a published field is a breaking change and needs the user's answer
   (decisions D2–D5). For GenAI, the replacement ships in a minor with the old field
   deprecated, and the removal waits for the next major, after the rules and ML jobs that read
   it have moved (D16).
7. **Never hand-edit generated files**: `*-expected.json`, `sample_event.json`, the built
   `docs/README.md` (edit `_dev/build/docs/README.md`).
8. **Anonymize** every fixture and mock value.
9. **Do not load domain skills into the orchestrator thread.** Delegate to the builders, which
   load them in their own context. The one exception is the direct edits of Phase 9 and the
   ECS pin in Phase 4, where the orchestrator loads `package-spec` and `elastic-package-cli`.

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

**Older GenAI reports** use 📥 (received, not mapped), 🔌 (available at source) and — (not
applicable). Read 📥 as 🔍 *Extract from existing data*, and — as ⛔. Read 🔌 as a 🔍 whose
recommendation follows from the *Controlled by* column of the report's content capture table:
the integration controls it, so *Add API parameter or request setting* or *New API call*; the
user or the vendor controls it, so *Source-side setting*; it arrives as a record type or
transport no stream collects, so *New data stream*.

| Report item | Action | Done by |
|---|---|---|
| GenAI ✅ | Nothing. | — |
| Entity ✅ / 🔄 | Check the package and implement what is missing. | pipeline builder |
| GenAI 🔄 | Implement the derivation (constant, lookup, sum). | pipeline builder |
| GenAI ⚠️ | Fix the published mapping, after D2, D3 or D4, in the release D16 gives it. | pipeline builder |
| 🔍 Extract from existing data (entity: *Extract from existing call*) | Map it from data the stream already receives. | pipeline builder |
| 🔍 Add API parameter or request setting (entity: *Add API parameter*) | Add the parameter or setting to the request, with a manifest variable when it exposes content or changes volume. Update mock, system test config and README. Then map it. | CEL builder (or setup builder), then pipeline builder |
| 🔍 New API call | Add the call to the same stream. Same as above. | CEL builder, then pipeline builder |
| 🔍 Source-side setting (document only) | The integration cannot turn it on. Map the field anyway, so that it works once the user enables the setting, and document the setting in the README. | pipeline builder, README |
| 🔍 New data stream | Not done here. Hand over to `create-integration` (add data stream) with the report section as the brief, and list it as deferred. | user |
| ⛔ (and entity *Cannot be collected*) | Nothing. | — |
| Values with no ECS field | Add a `<integration>.<data_stream>.<field>` definition and copy the value into it. | pipeline builder |
| Adjacent ECS fields | Only when the user puts them in scope (D13). | pipeline builder |

## Workflow

Read `references/apply-workflow.md` fully before starting. Phases:

0. **Intake**: package, reports, tools, report freshness
1. **Work items**: turn the report into a verified per-stream list
2. **Grouping**: one stream at a time, unless streams have the same shape
3. **Decisions**: ask every design decision up front
4. **Package prerequisites**: ECS pin and `ecs.version`
5. **Source-side changes**: parameters, calls, variables (CEL or input builders)
6. **Pipeline and fields**: pipeline builder per group
7. **System tests**
8. **Validation and review**
9. **Docs and changelog**
10. **Re-assess and report**

Kind-specific steps are in `references/genai-steps.md` and `references/entity-steps.md`. Read
the one that matches the report. Reports of both kinds are applied one kind at a time, GenAI
streams and entity streams never share a group.

## Subagents

All specialised work goes to the platform's general-purpose subagent. The task prompt points at
the manual **by path** (`references/work-item-template.md` has the prompt skeletons). Do not
paste manual contents.

| Manual | Used for |
|---|---|
| `cel-programs/references/builder-subagent-guidance.md` | Request parameters, extra calls, variables and mock changes on CEL streams |
| `integration-testing/references/builder-setup-subagent-guidance.md` | Template, variable and test config changes on non-CEL inputs |
| `ingest-pipelines/references/builder-subagent-guidance.md` | Pipelines, field definitions, pipeline fixtures |
| `integration-testing/references/builder-system-test-subagent-guidance.md` | System tests and `sample_event.json` generation |
| `review-integration/references/reviewer-subagent-guidance.md` | Read-only review of the result |
| `genai-mappings/references/analysis-subagent-guidance.md` or `entity-mappings/references/analysis-subagent-guidance.md` | Re-assessment of the changed streams |

## References

- `references/apply-workflow.md`: phases 0–10
- `references/decision-points.md`: every design decision, with the question and options
- `references/work-item-template.md`: work item table and builder task prompt skeletons
- `references/genai-steps.md`: GenAI-specific steps
- `references/entity-steps.md`: entity-specific steps
- `references/apply-report-template.md`: the final report
