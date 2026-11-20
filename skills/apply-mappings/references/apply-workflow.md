# Apply workflow

Apply a `genai-mappings` or `entity-mappings` gap analysis report to an existing package, one
phase at a time. Read `SKILL.md` first: its rules and the action table apply to every phase.

## Dispatch convention

All specialised work is delegated to the platform's **generic / general-purpose subagent**
(Claude Code: `general-purpose`; Cursor: `generalPurpose`). Do not invoke a named subagent.

Every task prompt must:

1. **Begin with an instruction to read the manual** for that role, by path, end-to-end, before
   doing anything else. Do not read the manual yourself and do not paste it.
2. **Carry all the context the subagent needs.** It cannot see this conversation: package and
   stream paths, work items, decisions, constraints, anonymization.

`work-item-template.md` has the skeletons.

**Only one subagent at a time.** Complete one group before starting the next.

**Subagents cannot ask the user.** A task prompt must tell the subagent to stop and return a
`DECISION NEEDED` block (decision id, what it found, the options) instead of guessing. You ask
the user, then dispatch again with the answer. The work already on disk stays.

## Phase 0: Intake

1. Resolve the package directory. Names in reports can differ from directory names (`litellm`
   is `packages/lite_llm`). Run from the repository root that holds `packages/`.
2. Read the report(s). Identify the kind from the title: *ECS GenAI Field Mapping* or *ECS
   Entity Field Mapping*. If neither, stop and ask for a report from the mapping skills. For a
   GenAI report, note which vocabulary it uses: the current one (✅ ⚠️ 🔄 🔍 ⛔, every 🔍 with a
   recommendation) or the older one (📥 🔌 —). Normalize older reports with the table in
   `SKILL.md`, and tell the user which rows you normalized.
3. Tools. `elastic-package` is always required. When a CEL change is planned, also `mito`,
   `celfmt` and `ceplx`: run the Preconditions blocks in `create-integration`'s
   `references/scaffold-commands.md` verbatim. Ask whether an Elastic stack is up for system
   tests. If not, system tests are skipped and listed as not run.
4. Git state. Note the branch and any uncommitted changes under the package. Never discard,
   stage or commit them. If uncommitted changes sit in files this work will edit, ask first.
5. Freshness. Compare the report's stream list and ECS pin with the package, and the report
   file's date with the last change to the package (`git log -1 --format=%cd -- <package>`). If
   the package changed after the report, or the streams differ, ask (D14): re-run the
   assessment, or continue with verified items only.

## Phase 1: Work items

Build the work item table from `work-item-template.md`: one row per field per stream (per
record type in mixed streams). Take status, recommendation and source path from the report.
Then verify each row against the package:

- the source path exists in a handwritten fixture, mock response or generator code, or in the
  vendor docs the report cites
- the pipeline and field files do not already populate the field (this matters most for entity
  ✅ and 🔄 rows, and for 🔍 rows when the package changed since the report)
- for ⚠️ rows, the described current state is real

Mark each row `todo`, `done already`, `contradicted` or `needs decision`. Show the user a
compact summary (counts per stream and the contradicted rows), not the whole table. Contradicted
rows are reported and not applied.

Scope: core fields and values with no ECS field. Adjacent ECS fields only after D13.

## Phase 2: Grouping

Handle **one stream at a time**, except that streams are grouped when **all** of these hold:

- same stream kind (entity: same `entity.type`)
- same input type and the same source record shape for the fields concerned (compare the
  fixture keys)
- the same work items: same fields, statuses and recommendations
- the same decisions apply

Otherwise they are separate. Entity user and host streams are separate. Two GenAI inference
streams reading the same body schema from the same API can be grouped. A mixed stream with
several record types is one stream, never split. Propose the groups and confirm them (D15). A
group is one builder task that handles its streams one after another. Groups run in sequence.

## Phase 3: Decisions

List every decision from `decision-points.md` that the work items trigger. Ask them **before
editing anything**, with `AskUserQuestion`, up to four questions per call, recommended option
first. Each question names the fields and streams concerned and the consequence. Record the
answers in the apply report. Do not ask the standing decisions again (they are listed in
`decision-points.md`).

## Phase 4: Package prerequisites

Once per package, before any stream work.

1. Required ECS pin: GenAI `git@v9.5.0`; entity at least `git@v9.4.0`, and use `git@v9.5.0`
   when bumping. If the package is below the floor, ask D1. The question lists every data
   stream whose pipeline `ecs.version` changes, in scope or not.
2. On a yes: set `dependencies.ecs.reference` in `_dev/build/build.yml` and `ecs.version` in
   the pipeline of **every** data stream, so that they match. These are direct edits.
3. Run, in the package directory, `elastic-package format`, `lint`, `check` and `build`, then
   `elastic-package test pipeline --generate` for every stream. Review the generated diff: only
   `ecs.version` and field type differences are expected. If `check` reports fields undefined at
   the new pin, or the diff shows something else, stop and report it to the user.

On a no for D1, stop for the affected kind: the mappings cannot be implemented without the pin.

## Phase 5: Source-side changes

For work items whose recommendation is *Add API parameter or request setting* or *New API
call*, group by stream. Skip this phase when there are none. The answers to D6 and D7 apply.

1. CEL streams: dispatch the CEL builder. Non-CEL inputs: dispatch a subagent with the setup
   builder manual, for template, variable and test config changes only. If it needs a new
   service or a new stream, it stops and reports.
2. The change must be backwards compatible. With a new variable off, the request and the output
   stay what they are today.
3. The subagent updates the template, the manifest variable (name, title, description per D6),
   the mock server and system test config (anonymized responses that carry the new data), and
   field definitions for the raw response fields. It does not touch pipelines.
4. It returns a sample of the new response shape. The pipeline builder uses it as fixture
   input.
5. Run `elastic-package format`, `lint` and `build`.

Items with *Source-side setting (document only)* need no code here. Their pipeline mapping is
Phase 6 and their README text is Phase 9. *New data stream* items are listed as deferred.

## Phase 6: Pipeline and fields

For each group, dispatch the pipeline builder with the skeleton in `work-item-template.md`.
Pass, by path: the report, the kind's field catalog and pipeline patterns, and `genai-steps.md`
or `entity-steps.md`. The builder:

- implements the group's work items, field definitions included
- extends the handwritten test fixtures with the source fields the new mappings need,
  anonymized, then regenerates expected output with `elastic-package test pipeline --generate`
  and reviews it
- for 🔍 *Source-side setting* items without a real sample, builds the fixture from the vendor
  documentation and says so (D12)
- never removes, renames or retypes a published field except as the decisions allow
- returns the list of changed files, per field what was done, and any `DECISION NEEDED`

After each group, run `elastic-package test pipeline` (no `--generate`) for its streams.

## Phase 7: System tests

For every stream whose request or output changed, when a stack is up: dispatch the system-test
subagent, one stream at a time. It regenerates `sample_event.json`. Without a stack, list the
streams as not run.

## Phase 8: Validation and review

1. Run `elastic-package format`, `lint`, `check` and `build`, and the pipeline tests of every
   changed stream.
2. For each field that was removed, renamed, retyped or given a new meaning, search `kibana/`
   (dashboards, saved searches, alerting rules), transforms and ML configs for references. List
   the hits in the report. They are part of the consequence the user was told about in the
   decision.
3. Dispatch the reviewer on the uncommitted diff of the package. Send HIGH and CRITICAL findings
   back to the right builder. At most two rounds. Remaining findings go in the report.

## Phase 9: Docs and changelog

These are direct edits. Load `package-spec` and `elastic-package-cli`.

1. **README** (`_dev/build/docs/README.md`, not the built `docs/README.md`): for every setting
   from the report's content-capture table, say what it enables, who controls it, the limits,
   and a warning that prompts, responses and tool details can contain sensitive data. Document
   every new variable and, for entity reports, every new scope or permission and how to grant
   it.
2. **Changelog and version**: follow `package-spec`. One entry per logical change. Use
   `breaking-change` for any field type change, removal, rename, changed meaning of a published
   field, or new required scope or auth change. Otherwise `enhancement`. The version bump is the
   highest one needed. Use the `pull/99999` placeholder link and tell the user to replace it
   once the pull request exists. This skill does not open it.
3. Run `elastic-package lint` and `check`.

## Phase 10: Re-assess and report

1. Dispatch an analysis subagent per changed stream (or group) with the mapping skill's
   `analysis-subagent-guidance.md`, writing outside the package. Compare with the original
   report: every item that was applied should now be ✅. Anything else goes in the report with
   the reason.
2. Write the apply report with `apply-report-template.md`, as `apply-mappings-<package>.md` in
   the current directory, **never inside the package**. Show the user the summary, what was not
   run, the deferred items and the follow-ups: placeholder changelog link, new streams to build
   with `create-integration`, uncommitted changes to review.

## Stop conditions

Stop and report, instead of continuing, when: the report is not from a mapping skill; the
package cannot be found; D1 is declined; `check` fails after the pin bump for a reason outside
this work; a builder returns the same `DECISION NEEDED` twice; or required tools are missing for
a step that cannot be skipped.
