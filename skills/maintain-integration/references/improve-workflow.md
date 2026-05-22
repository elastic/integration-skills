# Improve Workflow

Full improvement pass for an existing Elastic integration package: analyze issues, prioritize by severity, fix directly or delegate to subagents, re-validate, and report.

## What to provide

| Input | How to provide | Examples |
|-------|----------------|----------|
| Target package | free text or `@`-mention | `acme_firewall`, `@packages/acme_firewall` |
| Focus area | free text | "fix pipeline error handling", "full quality pass" |
| Prior review | `@`-mention file or paste | `@review-output.md`, or paste review findings inline |
| Requirements / brief | `@`-mention file | `@notes/acme-research-brief.md` |
| Sample data | `@`-mention files | `@samples/acme_event.json` |
| Documentation links | paste URLs | `https://docs.acme.com/api/v2` |
| Constraints | free text | "don't touch CEL program", "no stack available for system tests" |
| Acceptance criteria | free text | "all CRITICAL and HIGH issues resolved" |

Default: **quality-first** — analyze all aspects and fix highest-impact issues.

## Dispatch convention (read once, applies to every subagent step below)

All specialised work in this workflow is delegated to the platform's **generic / general-purpose subagent** (Cursor: `generalPurpose` Task agent; Claude Code: `general-purpose` Task agent; or the equivalent on other platforms). Do **not** invoke a named specialised subagent.

Every subagent task prompt must:

1. **Begin with an instruction to read the subagent's operating manual.** Point the subagent at the relevant `*-subagent-guidance.md` file **by path** and tell it to read that file (plus the skill SKILL.md it points at in its "First steps" section) end-to-end **before doing any other work**. **Do NOT read the guidance file yourself or paste/embed its content into the task prompt** — that doubles the context cost. The subagent must load the manual itself in its own fresh context. The guidance file contains the skill-load sequence, workflow, scope boundaries, and reporting contract.
2. **Provide all context** the subagent needs (it cannot see your conversation): package path, data stream path, specific issues to fix (paste findings), sample data if relevant, and any constraints.

Available manuals in this workflow (pass these by path, do not embed):

| Subagent guidance file | Use for |
|----------|---------|
| `review-integration/references/reviewer-subagent-guidance.md` | Read-only quality review (Phase 1 reviewer dispatch, Phase 5 final review) |
| `ingest-pipelines/references/builder-subagent-guidance.md` | Pipeline / field / pipeline-test fixes |
| `cel-programs/references/builder-subagent-guidance.md` | CEL program / mock API fixes |

## Phase 1: Analyze

**If the user provided prior review findings**, use those as the issue list. Read any `@`-mentioned files and fetch any documentation or API URLs provided inline.

**If no prior review is available**, run a quick pre-check yourself, then dispatch the reviewer:

```bash
cd packages/<package_name>

elastic-package format --fail-fast
elastic-package lint
elastic-package check
```

Then dispatch a subagent per the **Dispatch convention** above, instructing it to read `review-integration/references/reviewer-subagent-guidance.md` as its operating manual, to perform the review.

The task prompt must include (in addition to the read-the-manual directive):

1. Package path
2. Any user-provided requirements, research brief, or focus areas
3. Automated validation results from the pre-check above (so the subagent does not re-run them)
4. Any constraints

The reviewer returns a severity-ranked issue list with domain tags.

## Phase 2: Prioritize

Categorize all issues by severity:

1. **CRITICAL** — broken functionality, build/lint failures, missing required files
2. **HIGH** — quality standard violations (missing error handling, wrong ECS values, no test coverage)
3. **MEDIUM** — suboptimal patterns, missing edge case coverage, documentation gaps
4. **LOW** — style issues, minor improvements

Default strategy: address **all** issues in priority order — CRITICAL → HIGH → MEDIUM → LOW. Every finding must result in either a fix or an explicit decision not to fix (with a stated reason). If the user specified a focus area, prioritize that regardless of severity ranking.

## Phase 3: Route and fix

Route each issue to the appropriate handler based on the domain tag from the review:

### Fix directly (no subagent needed)

| Domain tag | What to fix |
|------------|-------------|
| `manifest` | Manifest field corrections (title, description, format_version, conditions, owner) |
| `changelog` | Version bumps, changelog entry additions — follow `package-spec` skill |
| `docs` | Documentation placeholder content, README updates |
| `fields` (simple) | Field file typos, missing `base-fields.yml` entries, duplicate removal |
| `build` | `_dev/build/build.yml` creation or ECS reference version bump |

**CEL formatting you can fix directly** (not logic errors):

```bash
cd packages/<package_name>/data_stream/<stream>/agent/stream
celfmt -s -agent -i cel.yml.hbs -ocel.yml.hbs
```

If `celfmt` reports syntax errors, fix the source before re-running. Do not proceed until `celfmt` exits cleanly (no stdout output).

### Dispatch the pipeline builder

Per the **Dispatch convention** above, point the subagent at `ingest-pipelines/references/builder-subagent-guidance.md` as its operating manual.

Use for:

- `pipeline` — JSE00001 compliance, `on_failure` handlers, processor tags, date parsing, type conversions, grok patterns, ECS categorization, processor ordering
- `fields` (complex) — field type mismatches or new ECS fields intertwined with pipeline changes
- `tests` (pipeline) — missing pipeline test fixtures, broken expected output

### Dispatch the CEL program builder

Per the **Dispatch convention** above, point the subagent at `cel-programs/references/builder-subagent-guidance.md` as its operating manual.

Use for:

- `cel` — error handling, cursor management, `want_more` logic, `state.with()` structure, `redact.fields`, auth scope, template configuration, system test mock API

If the user provided API credentials, pass them to the subagent so it can re-validate the fix with mito against the real API in addition to the mock.

When delegating, batch all related issues for the same data stream into a single subagent launch.

## Phase 4: Re-validate

After all fixes (direct and subagent) are applied:

```bash
elastic-package format
elastic-package lint
elastic-package check
```

If pipeline test fixtures exist:

```bash
elastic-package test pipeline
```

If the pipeline changed and expected output needs regeneration:

```bash
elastic-package test pipeline --generate
```

Review the generated `*-expected.json` to confirm correctness, then re-run `elastic-package test pipeline`.

## Phase 5: Final review and fix loop

Dispatch a subagent per the **Dispatch convention** above, instructing it to read `review-integration/references/reviewer-subagent-guidance.md` as its operating manual, for a final verification pass.

The task prompt must include (in addition to the read-the-manual directive):

1. Package path
2. Summary of what was fixed
3. Automated validation results from Phase 4 (so the subagent does not re-run them)
4. Original requirements (if available)

**If the reviewer returns remaining issues, do not attempt to fix them all yourself.** Re-delegate (per the **Dispatch convention**):
- Pipeline/field/test issues: point the subagent at `ingest-pipelines/references/builder-subagent-guidance.md` with the specific issues to fix
- CEL issues: point the subagent at `cel-programs/references/builder-subagent-guidance.md` with the specific issues to fix
- Only fix minor issues (manifest, changelog, docs, simple field typos) yourself

After subagent fixes complete, re-run `elastic-package check` and re-launch the reviewer the same way. Repeat until the reviewer returns `APPROVED` or only `APPROVED_WITH_SUGGESTIONS` (LOW/MEDIUM) findings remain.

## Phase 6: Report

```
# Improvement Report: <Package Name>

## Issues Found
(total count by severity: X CRITICAL, Y HIGH, Z MEDIUM, W LOW)

## Fixes Applied
1. [CRITICAL] <description> — <file(s) changed> — fixed by: self/pipeline-builder/cel-builder
2. [HIGH] <description> — <file(s) changed> — fixed by: ...
...

## Validation After Fixes
- format: PASS/FAIL
- lint: PASS/FAIL
- check: PASS/FAIL
- test pipeline: PASS/FAIL/SKIPPED

## Final Review
- Verdict: APPROVED / NEEDS CHANGES
- Remaining issues (if any)

## Remaining Issues (not fixed)
1. [MEDIUM] <description> — <suggested fix>
2. [LOW] <description> — <suggested fix>
...

## Files Changed
- <path> (created/modified/deleted)
...

## Next Steps
- Items requiring user input
- Tests that need stack availability
- Suggested follow-up improvements
```

## Guardrails

- Always analyze before fixing. Never apply fixes without understanding the full issue landscape.
- Fix the minimal set of changes needed. Do not refactor working code that has no quality issue.
- Re-validate after every batch of fixes. Do not accumulate many changes without checking.
- Never hand-write `sample_event.json` or `*-expected.json`. Always generate with `--generate`.
- Never remove or weaken existing test coverage.
- When fixing pipelines, preserve existing processor logic that works correctly.
- When adding field mappings, follow the ECS mapping strategy already in use by the package.
- Update `changelog.yml` when the changes are user-visible (follow `package-spec` skill).
- If a fix requires decisions the user hasn't made (auth method, field naming, categorization), mark it as a TODO rather than guessing.
- Do not load domain-specific skills (CEL, pipelines, ECS, field mappings) into your own context. Delegate to subagents.
