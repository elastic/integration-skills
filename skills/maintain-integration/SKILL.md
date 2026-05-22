---
name: maintain-integration
description: "Use when reviewing, fixing, or improving an EXISTING Elastic integration package. Covers quality reviews, targeted fixes (pipelines, field mappings, CEL programs, manifests, changelogs), full improvement passes, and minor adjustments. Use create-integration instead when creating a new package or adding a new data stream from scratch."
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# maintain-integration

## When to use vs create-integration

Use this skill when the **package already exists**:
- reviewing quality, ECS compliance, or correctness of an existing package
- fixing specific issues: pipeline errors, field mappings, ECS categorization, CEL programs, manifests
- running a full quality improvement pass (review → fix → re-validate loop)
- making minor adjustments to existing data streams

Use `create-integration` instead when:
- creating a new integration package from scratch
- adding a new data stream to an existing package (`create-integration` → `references/add-datastream-workflow.md`)

## Modes

### Review only (read-only, no edits)

→ **Read `references/review-workflow.md` fully before starting.**

Run automated validation, delegate inspection to a subagent (see Dispatch convention in `references/review-workflow.md`) pointing it at `review-integration/references/reviewer-subagent-guidance.md` as its operating manual, present findings with no file changes.

### Full improvement pass (analyze → fix → re-validate)

→ **Read `references/improve-workflow.md` fully before starting.**

Analyze issues (from prior review or fresh reviewer run), prioritize by severity, fix directly or delegate to subagents, re-validate, and report.

### Minor direct fix (no subagents needed)

For small targeted changes you can handle inline without loading a full workflow:
- manifest field corrections (title, description, format_version, conditions, owner)
- changelog entries and version bumps — see `package-spec` skill
- documentation placeholder text in `_dev/build/docs/README.md`
- `_dev/build/build.yml` creation or ECS reference bump
- simple field file fixes (typos, missing entry, duplicate removal)
- CEL formatting only — run `celfmt -s -agent -i cel.yml.hbs -o cel.yml.hbs` in the stream's `agent/stream/` directory

Run `elastic-package lint` and `elastic-package check` after any direct edits to confirm no regressions.

## Skills to load for direct work

- `elastic-package-cli` — validation and test commands
- `package-spec` — manifest rules, version bumps, and changelog schema

Do **not** load domain-specific skills (pipelines, CEL, ECS, field mappings) into your own context. Delegate to subagents that already have that knowledge.

## Subagents

All specialised work is delegated to the platform's **generic / general-purpose subagent** (Cursor: `generalPurpose` Task agent; Claude Code: `general-purpose` Task agent; or the equivalent on other platforms). Each task prompt must **point the subagent at the relevant `*-subagent-guidance.md` file by path** and instruct it to read that file (plus the skill SKILL.md it lists in "First steps") end-to-end before doing any other work. **Do NOT read the guidance file yourself or paste its contents into the task prompt** — that doubles its context cost. Pass only the path plus the task-specific context. The subagent will load the manual itself in its own fresh context. Full dispatch rules and per-workflow detail live in `references/review-workflow.md` and `references/improve-workflow.md`.

| Subagent guidance file | Use for |
|----------|---------|
| `review-integration/references/reviewer-subagent-guidance.md` | Thorough read-only quality inspection: classifies files by domain, loads all relevant domain skills and checklists via the `review-integration` skill, returns severity-ranked, domain-tagged findings |
| `ingest-pipelines/references/builder-subagent-guidance.md` | Pipeline fixes: JSE00001, error handling, processor tags, ECS categorization, field definitions, test fixtures |
| `cel-programs/references/builder-subagent-guidance.md` | CEL fixes: program logic, cursor management, error handling, mito validation, mock API, `cel.yml.hbs` template, manifest var cleanup |

When delegating, provide the subagent with: package path, data stream path, specific issues to fix (paste findings), sample data if relevant, and any constraints.

## Data anonymization

All data committed must be fully anonymized — no real IPs, hostnames, emails, tokens, or org identifiers in any committed file. When fixing or adding test fixtures, mock responses, sample events, or documentation examples, verify all values are synthetic. Anonymize any real data found as part of the improvement pass.

## References

- `references/review-workflow.md` — read-only review workflow (phases 1–4, mandatory checklists, output format)
- `references/improve-workflow.md` — full improvement workflow (analyze → prioritize → fix → re-validate → report)
