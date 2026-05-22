# Review Workflow

Read-only quality review of an existing Elastic integration package. No file edits. Use this when the goal is feedback and findings only; for actually fixing the issues, use `improve-workflow.md`.

## What to provide

| Input | How to provide | Examples |
|-------|----------------|----------|
| Target package | free text or `@`-mention | `acme_firewall`, `@packages/acme_firewall` |
| Scope | free text | "review pipeline only", "focus on ECS compliance", "full review" |
| Requirements / brief | `@`-mention file | `@notes/acme-research-brief.md` |
| Documentation links | paste URLs | `https://docs.acme.com/api/v2` |
| Specific concerns | free text | "worried about geoip field nesting", "CEL pagination might be wrong" |

Default scope: **full review** when no restriction is given.

## Phase 1: Parse scope and context

1. Identify the package directory and read its root `manifest.yml`.
2. Read any `@`-mentioned files; fetch any documentation URLs provided.
3. List all data streams and their input types.
4. Determine review scope: full package, specific streams, or specific aspects.

## Phase 2: Automated validation

Run validation and capture all output. This is fast and requires no domain context.

```bash
cd packages/<package_name>

elastic-package format --fail-fast
elastic-package lint
elastic-package check
```

If an Elasticsearch stack is available, run pipeline tests:

```bash
elastic-package test pipeline
```

If a full stack is available and system tests exist:

```bash
elastic-package test system
```

Record every failure with its full error message.

## Phase 3: Dispatch the integration reviewer

Delegate to the platform's **generic / general-purpose subagent** (Cursor: `generalPurpose` Task agent; Claude Code: `general-purpose` Task agent; or the equivalent on other platforms). Do **not** invoke a named specialised subagent.

The task prompt must include:

1. **An instruction to read `review-integration/references/reviewer-subagent-guidance.md` as the subagent's operating manual** before doing any other work — that file contains its scope, skill-load sequence (load `review-integration` skill and the domain skills/checklists it routes to), read-only operating rules, per-issue format checklist, verdict rules, and reporting contract. Pass only the path; **do NOT read the file yourself or paste/embed its contents into the task prompt** — the subagent will load it in its own fresh context.
2. **Package path** — absolute path to the package directory.
3. **Review scope** — full review or focused areas/streams.
4. **Requirements / brief** — paste key content or reference the file (the subagent cannot see your conversation).
5. **Specific concerns** — any areas the user highlighted.
6. **Automated validation results** — paste Phase 2 output so the reviewer does not re-run commands unnecessarily.
7. **Data stream list** — names and input types for each stream.

The subagent will: read `changelog.yml` to determine new-vs-existing severity calibration, classify every in-scope file by domain (using the `review-integration` skill's classification table), load the relevant domain skills and review checklists, run its full manual inspection, and produce findings in the format defined by `review-integration/references/review-output-template.md`.

The subagent already knows from the guidance file it reads to: avoid re-running validation the orchestrator already reported, read every in-scope file end to end (not just diffs), apply first-version leniency from `conflict-resolutions.md`, calibrate severity per `severity-rubric.md`'s new-vs-existing tables, consolidate duplicate findings, omit empty domains, include exactly one domain tag and a code-block recommendation on every finding, and never edit any files.

## Phase 4: Present results

The subagent returns its findings already formatted per `review-integration/references/review-output-template.md` and also writes the same content to `tmp/integration-review.md`. Present the reviewer's output in full — do not truncate, summarise, or re-format.

The template defines: per-domain sections (package root manifest/changelog/build, per-data-stream manifest/input/pipeline/field-mapping/tests, dashboards, transforms, documentation, anonymization, cross-domain consistency), per-issue format (title, severity, location, problem, recommendation with code block, domain tag), a summary count table, and the verdict line.

For severity definitions and the new-vs-existing calibration table, see `review-integration/references/severity-rubric.md` and `review-integration/SKILL.md` → "Reviewing new vs existing integrations". The reviewer subagent applies these automatically based on its reading of `changelog.yml`.

## Guardrails

- **Do not edit any files.** This workflow is read-only.
- Do not skip or summarize the reviewer's findings. Present them in full.
- When automated validation commands fail, include the full error output in the report.
- Do not load domain-specific skills yourself. The reviewer subagent loads everything it needs via the `review-integration` skill referenced from its guidance file.
