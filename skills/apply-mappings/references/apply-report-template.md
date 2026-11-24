# Apply report template

Write the report as `apply-mappings-<package>-<version>.md` in the current working directory,
**never inside the package directory** (files there are built into the package). Fill every
section. Where a section does not apply, write `N/A` and one sentence saying why.

```markdown
# Apply mappings: {{PACKAGE}} {{VERSION}}

## Summary

[3–5 sentences: which report(s) were applied, for which release (last released version →
this version), which streams changed, what was deferred, whether anything is breaking, and
what was not run.]

| Stream | Group | Kind | Work items applied | Done already | Contradicted | Deferred |
|---|---|---|---|---|---|---|
| `<stream>` | `<group id>` | GenAI / entity | n | n | n | n |

## Reports applied

| Report | Kind | Stale? | Scope applied |
|---|---|---|---|
| `<path>` | GenAI / entity | no / yes (D1 answer) | the next minor / the major / streams |

## Decisions

| Id | Question | Answer | From | Affects |
|---|---|---|---|---|
| D2 | ECS pin bump | Bump | user | all streams |
| D3 | Release | The next minor | user / input | `<stream>` |
| D7 | `<question>` | | report, open question n / earlier run | |
| new | `<question>` | | user | |

## Changes per stream

For each stream: the work item table with the final result.

| Fields | Report status | Recommendation | Action taken | Result |
|---|---|---|---|---|
| `gen_ai.request.model` | 🔍 | Extract from existing data | mapped from `modelId` | populated correctly |

Rows applied with the mapping references' value instead of the report's: [list, or "none"].

### Files changed

[Grouped by stream. Include `build.yml`, manifests, templates, fixtures, README, changelog.]

## Source-side changes

| Change | Stream | Variable | Default | Backwards compatible? |
|---|---|---|---|---|
| `include=usage` request parameter | `<stream>` | `<name>` | off | yes |

## Breaking changes

[Each: field or behaviour, what this release does and what waits for the major, changelog
type, version bump, and the rules, ML jobs and dashboards that read it. Name the package's
own assets that the major must update.]

## Deferred

| Item | Reason | Next step |
|---|---|---|
| `gen_ai.x` | New data stream | `/create-integration`, add data stream, using `<report section>` as the brief |
| `gen_ai.system` removal | Breaking | a run of this skill for the major, released after the consumers move |

## Documentation

[README sections added or changed. Placeholder changelog link to replace after the pull request
is opened.]

## Validation

| Check | Result |
|---|---|
| Baseline before any edit | pass / failed: `<what>` (D11) |
| `elastic-package format` / `lint` / `check` / `build` | |
| Pipeline, static and policy tests | n/n pass, on Elasticsearch `<version>` |
| Existing output | only added fields / changed: `<fields>` (decision `<id>`) |
| Index-time check (GenAI `flattened` fields) | long content: accepted / rejected; deep schema: accepted / rejected |
| System tests | pass / fail / not run: `<reason>` |
| Reviewer | n findings, n fixed, n left |

Fixtures built from vendor documentation instead of real samples (D9): [list, or "none"].

## Check against the report

| Stream | Rows applied | Populated correctly | Not | Why |
|---|---|---|---|---|

New findings outside the applied rows: [list with severity and what was decided (D11), or
"none"].

## Follow-ups for the user

[Uncommitted changes to review, changelog link, tests to run elsewhere, stale
`sample_event.json` files, new streams to build, the run for the major, findings left open.]
```
