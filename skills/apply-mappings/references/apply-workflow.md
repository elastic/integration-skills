# Apply workflow

Apply a `genai-mappings` or `entity-mappings` gap analysis report to an existing package, one
phase at a time. Read `SKILL.md` first: its rules and the action table apply to every phase.

## Dispatch convention

All specialised work goes to the platform's **generic / general-purpose subagent** (Claude
Code: `general-purpose`; Cursor: `generalPurpose`), never a named one, and **one at a time**.
Every task prompt:

1. **Begins with an instruction to read the manual** for that role (table in `SKILL.md`), by
   path, end-to-end, before doing anything else. Do not read the manual yourself and do not
   paste it.
2. **Carries all the context the subagent needs.** It cannot see this conversation: package and
   stream paths, work items, decisions, constraints. A prompt sent again repeats that context
   and says which work items are already on disk.
3. **Tells a builder to return `DECISION NEEDED` instead of guessing**, because it cannot ask
   the user. You ask, then dispatch again with the answer. The work already on disk stays.

`work-item-template.md` has the skeletons and the `DECISION NEEDED` block.

## Phase 0: Intake

1. **Package.** Resolve the package directory. Names in reports can differ from directory
   names (`litellm` is `packages/lite_llm`). Run from the repository root that holds
   `packages/`.
2. **Report(s).** Identify the kind from the title: *ECS GenAI Field Mapping* or *ECS Entity
   Field Mapping*. Stop and ask for a new run of the mapping skill when the title is neither,
   or when a GenAI report's field tables have no Change column: it was written before the
   detection conventions and lacks the sections this workflow reads. A report saved inside
   the package directory (the entity skill's default) is not part of the work: leave it out
   of every diff and tell the user to move it before committing.
3. **Earlier runs.** If an `apply-mappings-<package>-*.md` exists, read its *Decisions*: they
   answer the same questions in this run.
4. **Release.** Find the last released version of the package: `manifest.yml` on the upstream
   default branch (ask when no remote tracks it). A higher version in the checkout is
   unreleased work, and this run adds to it. Take the release scope from the input. Without
   one it is decided in Phase 3 (D3) when the work has Breaking rows, and it is the next minor
   otherwise.
5. **Tools and stack.**
   - `elastic-package` is always required. When a stream in scope uses the `cel` input, run
     the Check block under *Preconditions* in
     `create-integration/references/scaffold-commands.md`.
   - Pipeline tests need Elasticsearch (`elastic-package stack up -d --services=elasticsearch`).
     System tests need the full stack and whatever the stream's test deployer needs (a Docker
     service, or Terraform and cloud credentials). The stack version must satisfy the package's
     `conditions.kibana.version`.
   - Check `elastic-package stack status`, and ask before starting or replacing a stack. A
     test that cannot run is reported as not run, never as passed.
   - **Baseline.** Before any edit, run `elastic-package check` and the pipeline tests of the
     streams in scope. A failure here is not caused by this work: D11.
6. **Git state.** Note the branch and any uncommitted changes under the package. Never
   discard, stage or commit them. If uncommitted changes sit in files this work will edit, ask
   first.
7. **Freshness.** Compare the report's stream list with the package. A GenAI report names a
   package version and a commit: `git log --oneline <commit>..HEAD -- <package>` should be
   empty. An entity report names neither: compare the report file's date with the last commit
   to the package. A difference is a reason for D1.

## Phase 1: Work items

Build the work item table from `work-item-template.md`, which says what a row is. Until D3 is
answered, a Breaking row keeps both of its halves. The major half also needs its replacement
to be in the package already: in a released version, or in the unreleased minor this branch is
built on.

Verify each row against the package:

- the source path exists in a handwritten fixture, mock response or generator code. A path
  that only the vendor documentation cited by the report shows is a D9 row: do not fetch the
  documentation
- the pipeline and field files do not already populate the field (this matters most for entity
  ✅ and 🔄 rows, and for 🔍 rows when the package changed since the report)
- for ⚠️ rows, the described current state is real

Mark each row `todo`, `done already` or `contradicted`. Contradicted rows are reported and not
applied. Ask D1 now, once, when Phase 0 or this phase gave a reason for it.

**Consumers.** For every row that changes or removes a published field, know what reads it
before asking anything. A GenAI report lists them in *Breaking changes and consumers*. For a
field it does not list, and for an entity report, run the *Consumers first* search in section 9
of `genai-mappings/references/genai-detection-conventions.md`: it is not specific to GenAI.

## Phase 2: Grouping

Handle **one stream at a time**, except that streams are grouped when **all** of these hold:

- same stream kind (entity: same `entity.type`)
- same input type and the same source record shape for the fields concerned (compare the
  fixture keys)
- the same work items: same fields, statuses and recommendations
- the same decisions apply

Entity user and host streams are separate. Two GenAI inference streams reading the same body
schema from the same API can be grouped. A mixed stream with several record types is one
stream, never split. A group is one builder task that handles its streams one after another.
Groups run in sequence.

## Phase 3: Decisions

Show the user a compact summary, not the whole table: counts per stream, the contradicted
rows, the groups, and the consumers per field. Then list every decision from
`decision-points.md` that the `todo` rows trigger, plus D2 when the pin is below the floor,
and settle all of them **before editing anything**:

- **Already answered.** Where the report records the answer (a row whose Basis is an issue or
  a pull request, an answered open question) or an earlier run does, do not ask again. Show
  it in the summary with its origin, so that the user can object. The report's *Release plan*
  says what each release holds, not which one this run builds: that is D3.
- **Open questions.** Every item of the report's *Open questions* that a `todo` row depends on
  is asked, as the decision it matches or as `new`.
- **The rest** is asked with the platform's question tool (Claude Code: `AskUserQuestion`, up
  to four questions per call), recommended option first. Each question names the fields and
  streams concerned and what the choice costs.

After D3, the half of each Breaking row that this run does not build becomes `deferred`.
Record every answer and its origin in the apply report.

## Phase 4: Package prerequisites

Once per package, before any stream work. These are direct edits: load `package-spec` and
`elastic-package-cli`.

1. **Pin.** The floor is `git@v9.5.0` for GenAI and `git@v9.4.0` for entity (use `git@v9.5.0`
   when bumping). On a yes to D2, set `dependencies.ecs.reference` in `_dev/build/build.yml`
   and change `ecs.version` in every pipeline that sets one. On a no, stop for the affected
   kind: the mappings cannot be implemented without the pin.
2. **`ecs.version` of the streams in scope.** Whatever the pin, each one sets `ecs.version` to
   the pin's version. Add or correct the `set` processor: a metrics stream may have none.
3. Run, in the package directory, `elastic-package format`, `lint`, `check` and `build`, then
   `elastic-package test pipeline --generate` for every stream. Review the generated diff: only
   `ecs.version` and field type differences are expected. When `check` reports a field
   undefined at the new pin and a work item keeps that field in this release (a deprecated
   `gen_ai.system`), give it a local definition with its previous type and continue. For any
   other undefined field or difference, stop and report it to the user.

## Phase 5: Source-side changes

For work items whose recommendation is *Add API parameter or request setting* or *New API
call*, and for any variable or manifest change a decision adds (D5, D6, D11), group by stream.
Skip this phase when there are none. The answers to D4 and D5 apply.

1. CEL streams: dispatch the CEL builder. Non-CEL inputs: dispatch the setup builder, for
   template, variable and test config changes only. The skeletons say what each one changes,
   and that with a new variable off the request and the output stay what they are today.
2. Keep the sample of the new response shape that the subagent returns. The pipeline builder
   uses it as fixture input.
3. Run `elastic-package format`, `lint` and `build`.

A change to a `cel` or `httpjson` input makes the reviewer check that its policy template
enables agentless (`package-spec` → `references/manifest-rules.md` → *Agentless (Elastic
Managed) deployment for API inputs*). If it does not, that is D11: it is not part of the
report.

## Phase 6: Pipeline and fields

For each group, dispatch the pipeline builder with the skeleton in `work-item-template.md`,
which states its constraints and what it returns. It reads `genai-steps.md` or
`entity-steps.md`, which names the mapping references. A stream with many work items can go
out as several tasks in sequence, by record type or by field group.

After each group:

1. Run `elastic-package test pipeline` (no `--generate`) for its streams.
2. **Existing-output check.** The builder returns the fields whose value changed or
   disappeared in the expected output of the fixtures that existed before. That list must
   hold only what the decisions allow, plus the `flattened` safety changes of
   `genai-steps.md`. Anything else is a bug or a decision nobody asked: send it back to the
   builder, or ask. The reviewer does not read expected output, so nothing later catches
   this.

## Phase 7: System tests

Only for streams that a work item changed, and only when the stream's system test can run.
One stream at a time:

1. **Test data.** When the mock response or sample data of the system test lacks the source
   fields of the new mappings, dispatch the CEL builder (CEL streams) or the setup builder
   (other inputs) to extend that data and nothing else. For GenAI `flattened` fields it
   includes the long-content and deep-schema documents of the patterns' *Test fixtures*. The
   sample files of a Terraform deployer have no builder: D11.
2. Dispatch the system-test subagent. It regenerates `sample_event.json` and, for GenAI
   streams, checks `<data stream>::failures`.

When the system test cannot run (no stack, no cloud credentials), list the stream as not run
and leave `sample_event.json` as it is. Do the same for streams that only the pin bump
touched.

## Phase 8: Docs and changelog

These are direct edits. Load `package-spec` and `elastic-package-cli`.

1. **README** (`_dev/build/docs/README.md`, not the built `docs/README.md`). Document what
   this release makes true, not what is deferred:
   - every new variable, and every new scope or permission with how to grant it
   - every content-capture setting: what it enables, who controls it, the limits, and a
     warning that prompts, responses and tool details can contain sensitive data
   - GenAI: the items of the report's *Documentation changes* section
   - deprecated fields with their replacement and the release that removes them; in a major,
     a migration table (old field → new field)
2. **Changelog and version**: follow `package-spec`. One entry per logical change. Use
   `breaking-change` for any field type change, removal, rename, changed meaning of a published
   field, or new required scope or auth change. Otherwise `enhancement`, or `bugfix` for a
   defect fixed under D11. Enabling agentless is its own `enhancement`. An entry that
   deprecates a field names the field and its replacement. Add the entries under the top
   version when it is unreleased (Phase 0), and raise it only when this run needs a higher
   bump. Use the `pull/99999` placeholder link and tell the user to replace it once the pull
   request exists. This skill does not open it.

## Phase 9: Validation and review

1. Run `elastic-package format`, `lint`, `check` and `build`, the pipeline tests of every
   changed stream, `elastic-package test static`, and `elastic-package test policy` when the
   package has policy tests and Phase 5 changed a template or a variable. `format` can rewrite
   files this work did not touch: restore them, unless they held uncommitted changes at intake
   (then leave them and say so).
2. Dispatch the reviewer on the changed files. Send back to the right builder every CRITICAL
   and HIGH finding, and the MEDIUM ones on what this run added or changed. Fix README and
   changelog findings yourself. A finding on something this run did not introduce is D11.
   Then repeat step 1. At most two rounds. Remaining findings go in the report.

## Phase 10: Check against the report, and report

1. Dispatch one subagent per changed stream or group with the *Check of the applied rows*
   skeleton. It says, per applied row, whether the package now populates the field correctly.
   It is not a new analysis. A row that fails goes back to the builder once, and then into the
   report with the reason. What it finds outside the applied rows goes into the report as a
   new finding, and to the user as D11 when it needs an answer.
2. Write the apply report with `apply-report-template.md`, as
   `apply-mappings-<package>-<version>.md` in the current directory, **never inside the
   package**. Show the user its summary, what was not run, and the follow-ups.

## Stop conditions

Stop and report, instead of continuing, when: the report is not one this workflow can read
(Phase 0, step 2); the package cannot be found; Elasticsearch cannot be started for pipeline
tests; the user answers D1 with a re-run; D2 is declined; `check` fails after the pin bump for
a reason outside this work; a builder returns the same `DECISION NEEDED` twice; or required
tools are missing for a step that cannot be skipped.
