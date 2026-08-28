---
name: entity-mappings
description: >-
  Use when adding or auditing ECS entity.* fields (entity inventory / entity store) on
  Elastic integrations — classifying a data stream as entity vs event, mapping vendor fields
  to entity.attributes.*, entity.lifecycle.*, and entity.relationships.*, or running an
  entity-coverage gap analysis on an existing package. Invoke manually with /entity-mappings.
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# entity-mappings

## Skill authority

The guidance in this skill takes precedence over patterns observed in any integration in the
`elastic/integrations` repository. Legacy integrations may predate these requirements or use
inconsistent patterns. Always follow this skill's rules over what you observe in the repo.

## When to use

- Adding entity/inventory data streams to a new or existing integration
- Deciding whether a proposed or existing data stream is an entity stream or an event stream
- Selecting the correct `entity.type` value for a new stream
- Mapping vendor fields to `user.entity.*`, `host.entity.*`, or other nested entity prefixes
- Auditing an existing package's entity field coverage (standalone gap analysis)
- Troubleshooting `event.kind: asset` usage or `entity.*` field errors

## When not to use

- **CDR cloud security findings** (misconfiguration / vulnerability findings) — these are
  `event.kind: state`, not `asset`. Use `ecs-field-mappings/references/cdr-field-requirements.md`
  and `ingest-pipelines/references/cdr-pipeline-requirements.md` instead.
- **Generic field file authoring** (non-entity fields) — use the `ecs-field-mappings` skill.
- **Processor mechanics** (grok, date, JSON, Painless) — use the `ingest-pipelines` skill.
- **CEL program logic** — use the `cel-programs` skill.

## Applicability gate

Entity fields apply **only** to entity data streams — those whose purpose is to represent a
stable inventory of subjects (users, hosts, devices, applications, services) rather than a
timeline of events. **Never apply entity field requirements to event logs, metric streams,
APM data, or CDR findings streams.**

See `references/entity-datastream-classification.md` to classify a data stream before using
this skill. If you are not sure, check the classification reference first.

## ECS availability — read this first

The `entity.attributes.*`, `entity.lifecycle.last_activity`, and all
`entity.relationships.*` leaf fields do **not exist at ECS v9.3.0** (the repo default pin).
They first appear at ECS v9.4.0.

- At `git@v9.3.0`: `entity.attributes` is a bare `object` with no subfields; `schemas/entity_reference.yml` does not exist. Using `external: ecs` on these leaves at that pin causes `field is undefined` build failures.
- At `git@v9.4.0+` / `git@v9.5.0` (recommended): all leaf fields exist and `external: ecs` resolves correctly.

**Conditional pin rule:** packages with entity data streams must set:
- `_dev/build/build.yml`: `dependencies.ecs.reference: "git@v9.5.0"`
- Pipeline `ecs.version`: `9.5.0`

The two must match. Standard (non-entity) packages keep `git@v9.3.0`.

To verify at any tag:
```bash
curl -s https://raw.githubusercontent.com/elastic/ecs/<tag>/generated/csv/fields.csv \
  | awk -F, '$3=="entity"' | cut -d, -f4,5 | sort -u
```

## Modes

| Mode | How it's triggered | What to load |
|---|---|---|
| **Standalone gap analysis** | User invokes `/entity-mappings @packages/<name>` | Read `references/gap-analysis-workflow.md` and `references/entity-field-catalog.md`. Dispatch per-stream subagents via `references/analysis-subagent-guidance.md`. |
| **Build-time** | Orchestrator (`create-integration` or `add-datastream`) passes `references/entity-field-catalog.md` and `references/entity-pipeline-patterns.md` by path to the pipeline builder subagent | Pipeline builder reads both references; this skill's SKILL.md is not loaded into the orchestrator thread. |
| **Review-time** | `review-integration` Step 4 loads the two references when the entity detection rule fires | Reviewer reads `entity-field-catalog.md` + `entity-pipeline-patterns.md`; this SKILL.md is not required in the reviewer thread. |
| **Research-time** | `research-integration` loads only `references/entity-datastream-classification.md` | **Do not load the rest of this skill during research** — the catalog and pipeline patterns are implementation material and violate the research guardrail against prescribing pipeline/field details. |

## Open questions / deferred scope

The following topics are out of scope for this skill's v1:

- **Entity-store latest transforms.** The CDR precedent has a third leg (`review-integration/references/cdr-transform-requirements.md`) covering latest transforms per integration. Whether new entity data streams should ship an accompanying latest transform is not yet resolved. Note it as an open question in research briefs and gap analysis reports until that decision is made.
- **Repo-wide ECS pin bump to v9.5.0.** Recommended as a follow-up once entity streams are common; the conditional exception in this skill carries packages until then.

## References

- `references/entity-field-catalog.md` — single source of truth: ECS availability matrix, reusable nesting, `entity.type` allowed values, categorization, Must Have / Should Have field tables, disambiguation guide, field definition YAML examples, review checklist
- `references/entity-pipeline-patterns.md` — pipeline-side patterns: categorization processors, building `entity.id`, boolean coercion, array attributes, relationship objects, anti-patterns, pipeline review checklist
- `references/entity-datastream-classification.md` — research-time and review-time rules for classifying a data stream as entity vs event; worked examples
- `references/gap-analysis-workflow.md` — 4-phase standalone analysis: classify streams → read package → fetch docs → map fields → investigate gaps → write report
- `references/gap-analysis-report-template.md` — structured report template for gap analysis output
- `references/analysis-subagent-guidance.md` — operating manual for per-stream analysis subagents dispatched during gap analysis
- [ECS entity fieldset reference](https://www.elastic.co/docs/reference/ecs/ecs-entity)
