# Apply report template

Write the report as `apply-mappings-<package>.md` in the current working directory, **never
inside the package directory** (files there are built into the package). Fill every section.
Where a section does not apply, write `N/A` and one sentence saying why.

```markdown
# Apply mappings: {{PACKAGE}}

## Summary

[3–5 sentences: which report(s) were applied, which streams changed, what was deferred, whether
anything is breaking, and what was not run.]

| Stream | Group | Kind | Items applied | Done already | Contradicted | Deferred |
|---|---|---|---|---|---|---|
| `<stream>` | `<group id>` | GenAI / entity | n | n | n | n |

## Reports applied

| Report | Kind | Stale? | Notes |
|---|---|---|---|
| `<path>` | GenAI / entity | no / yes (D14 answer) | |

## Decisions

| Id | Question | Answer | Affects |
|---|---|---|---|
| S1–S7 | Standing decisions | as in `decision-points.md` | |
| D1 | ECS pin bump | Bump | all streams |

## Changes per stream

For each stream: the work item table with the final result.

| Field | Report status | Recommendation | Action taken | Result |
|---|---|---|---|---|
| `gen_ai.request.model` | 🔍 | Extract from existing data | mapped from `modelId` | ✅ after |

### Files changed

[Grouped by stream. Include `build.yml`, manifests, templates, fixtures, README, changelog.]

## Source-side changes

| Change | Stream | Variable | Default | Backwards compatible? |
|---|---|---|---|---|
| `include=usage` request parameter | `<stream>` | `<name>` | off | yes |

## Breaking changes

[Each: field or behaviour, decision id, changelog type, version bump, dashboards or rules that
reference it (from the Phase 8 search).]

## Deferred

| Item | Reason | Next step |
|---|---|---|
| `gen_ai.x` | New data stream | `/create-integration`, add data stream, using `<report section>` as the brief |

## Documentation

[README sections added or changed. Placeholder changelog link to replace after the pull request
is opened.]

## Validation

| Check | Result |
|---|---|
| `elastic-package format` / `lint` / `check` / `build` | |
| Pipeline tests | |
| System tests | pass / fail / not run: no stack |
| Reviewer | n findings, n fixed, n left |

## Re-assessment

| Stream | Items applied | Now ✅ | Still open | Why |
|---|---|---|---|---|

Fixtures built from vendor documentation instead of real samples (D12): [list, or "none"].

## Follow-ups for the user

[Uncommitted changes to review, changelog link, new streams to build, decisions left open.]
```
