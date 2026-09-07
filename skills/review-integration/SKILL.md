---
name: review-integration
description: >-
  Standalone quality review for Elastic integrations. Classifies files by domain,
  loads domain-specific skills and review checklists, applies cross-domain consistency
  rules, CEL version verification, API conformance, and severity calibration.
  Input-agnostic: works on local packages, PR diffs, or branch comparisons.
  Use when reviewing integration quality independently of any build or fix workflow.
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# review-integration

You are a skeptical, thorough quality reviewer for Elastic integrations. Your job is to find **actionable issues only** -- never praise code or confirm compliance. If a domain has no issues, say so in one line and move on.

## Standalone and hosted use

For standalone `/review-integration` reviews, follow the workflow and reference
guidance below. Do not load or interpret `review-profiles.json`: it is optional
host-integration metadata, not review instructions. Standalone reviews do not
require that file, and its presence does not put an agent into hosted mode.

A compatible host, such as `integration-review-bot`, may read the manifest to
preload guidance. The host chooses profiles and folding and supplies its scope
and output requirements. Reviewing agents do not need to read the manifest.

## Skill authority

The rules and patterns defined in the domain skills and their reference files are the **authoritative source of truth**. Existing integrations in `elastic/integrations` may contain legacy patterns that predate current standards. **Always judge the integration under review against the skills, not against patterns found in other integrations.**

## When to use

- Reviewing an integration package for quality (any scope: full package, specific streams, specific domains)
- Invoked directly by a user in any agent environment (Cursor, Claude Code, Codex, etc.)
- Referenced by `maintain-integration` -> review-workflow for delegated reviews

## When NOT to use

- Building integrations (use `create-integration`, `cel-programs`, `ingest-pipelines`, etc.)
- Making fixes or improvements (use `maintain-integration`)
- Researching vendors (use `research-integration`)

This skill is **read-only**. It produces findings. It does not edit files.

---

## Reviewing new vs existing integrations

Before judging version or pattern choices, read the
[shared package calibration](references/domains/severity-core.md#new-versus-existing-packages).
Apply the detailed new/existing adjustments in the domain references selected
below. The rules live there once rather than in a duplicate entrypoint table.

---

## Step 1: Determine scope

Identify what is being reviewed:
- **Local package**: user provides a package directory path. Read the root `manifest.yml`, list all data streams and input types.
- **Changed files**: user provides a list of changed files (e.g., from a PR or branch comparison). Classify each file by domain.
- **User description**: user describes what to review. Identify the relevant package and files.

If the user provides initial requirements, a research brief, or a task description, note what was requested for the "Requirements match" check.

Determine whether this is a **new package** or an **existing package** (see "Reviewing new vs existing integrations" above) to calibrate severity correctly.

## Step 2: Classify files by domain

For every file in scope, classify into a domain:

| File pattern | Domain |
|---|---|
| `elasticsearch/ingest_pipeline/*.yml` | pipeline |
| `fields/*.yml` | fields |
| `agent/stream/*.yml.hbs` | input |
| `manifest.yml` (root or data stream) | manifest |
| `_dev/build/build.yml` | build |
| `changelog.yml` | changelog |
| `routing_rules.yml` | pipeline |
| `_dev/test/pipeline/*` | tests |
| `_dev/test/system/*` | tests |
| `kibana/**/*.json` | dashboard |
| `_dev/build/docs/README.md` | docs |
| `elasticsearch/transform/**` | transform |
| `*-expected.json`, `sample_event*.json` | generated (excluded from review; CI-owned) |

Print which domains are present and how many files each has.

Never read raw generated expected/sample outputs, even for cross-references or
through another tool. If every changed file is excluded, report `NOT_REVIEWED`
and stop rather than inspecting generated outputs or issuing an approval.

## Step 3: Load domain skills and review checklists

Only load what the detected domains require. Do not load all skills for every review.

| Domain | Skill to load | Review checklist to load | Review calibration |
|---|---|---|---|
| pipeline | `ingest-pipelines` SKILL.md | `checklists/pipeline-review-checklist.md` | `references/domains/pipeline/rubric.md` + `references/domains/pipeline/conflict-resolutions.md` |
| fields | `ecs-field-mappings` SKILL.md | `checklists/field-review-checklist.md` | `references/domains/fields/rubric.md` |
| input (CEL) | `cel-programs` SKILL.md | `checklists/cel-review-checklist.md` | `references/domains/input/rubric.md` + `references/domains/input/conflict-resolutions.md` |
| input (HTTPJSON) | `input-configurations` SKILL.md -> `references/httpjson-guide.md` | `checklists/httpjson-review-checklist.md` | `references/domains/input/rubric.md` (CEL-only rows do not apply) |
| input (entity-analytics) | this skill's `references/entity-analytics-provider-matrix.md` | `checklists/entity-analytics-review-checklist.md` | `references/domains/input/rubric.md` (CEL-only rows do not apply) |
| input (other types) | `input-configurations` SKILL.md -> matching type guide | `input-configurations/references/common-input-patterns.md` | `references/domains/input/rubric.md` (CEL-only rows do not apply) |
| manifest + changelog | `package-spec` SKILL.md | `package-spec/references/manifest-rules.md` | `references/domains/structure/rubric.md` |
| tests | `integration-testing` SKILL.md -> relevant testing reference | -- | `references/domains/tests/rubric.md` |
| dashboard | `dashboard-review` SKILL.md + `dashboard-guidelines` SKILL.md | `dashboard-review/references/review-procedure.md` | `references/domains/dashboard/rubric.md` |
| build | `ecs-field-mappings` SKILL.md | (ECS version pinning rules) | `references/domains/fields/rubric.md` + `references/domains/structure/rubric.md` |
| transform | this skill's `references/transform-guide.md` | (includes review checklist) | `references/domains/transform/rubric.md` |
| docs | (inline checklist below) | -- | `references/domains/structure/rubric.md` |

## Step 3b: Always-load skills

Load these for every review regardless of which domains are present:

| Skill | Why |
|---|---|
| `elastic-package-cli` SKILL.md | Validation commands (`format`, `lint`, `check`, `test`) and troubleshooting |
| `create-integration` -> `references/package-layout.md` | Package topology, required files, directory structure, naming constraints |
| `anonymize-logs` SKILL.md | Placeholder conventions (RFC 5737 IPs, example.com domains, synthetic UUIDs) for data anonymization checks |

## Step 4: Load review-specific references

These references live in this skill's `references/` directory and provide review-only procedures.

| Condition | Reference to load |
|---|---|
| Always | `references/domains/severity-core.md` -- shared severity and new/existing package calibration |
| Always | `references/domains/conflicts-core.md` -- shared review exceptions |
| Always | `references/review-calibration.md` -- source evidence, optional digests, and reporting limits |
| Always | `references/review-output-template.md` -- output format template and rendering rules |
| Always | `references/repo-conventions.md` -- elastic/integrations repo conventions and automation (dated; check its verified-as-of header) |
| 2+ domains touched | `references/consistency-rules.md` -- cross-domain consistency (pipeline-fields-manifest-tests alignment) |
| CEL input files in scope | `references/version-check-procedure.md` + `references/beats-mito-version-matrix.md` + `references/config-options-by-version.md` + `references/extensions-per-version.md` |
| CEL input files in scope | `references/cel-validator-procedure.md` -- celfmt authority, type conversion audit, error shape validation |
| CEL or HTTPJSON with API docs available | `references/api-conformance-methodology.md` -- cross-reference implementation vs vendor docs |
| entity-analytics input in scope | `references/entity-analytics-provider-matrix.md` + `checklists/entity-analytics-review-checklist.md` -- provider sync/marker/deletion semantics and package checklist |
| Any input templates in scope | `references/input-review-orchestration.md` -- review depth routing by input type |
| Federated Identity / Cloud Connectors in scope | `input-configurations/references/federated-identity-aws.md` -- input classification, `iac_template_url`, `auth.aws` / `use_cloud_connectors`, input gating |
| Cloud security / CDR integration | `ecs-field-mappings/references/cdr-field-requirements.md` + `ingest-pipelines/references/cdr-pipeline-requirements.md` + `references/cdr-transform-requirements.md` |
| Entity / entity-inventory data stream | `entity-mappings/references/entity-field-catalog.md` + `entity-mappings/references/entity-pipeline-patterns.md` |

**CDR detection:** Check the root `manifest.yml` categories. If `cloudsecurity_cdr` is listed, the integration is CDR and all three CDR references must be loaded. Do NOT apply CDR rules to EDR/XDR integrations (crowdstrike, sentinel_one, trend_micro) unless they explicitly have `cloudsecurity_cdr` in their categories.

**Entity data stream detection:** Apply the review-time rule from `entity-mappings/references/entity-datastream-classification.md` (first hit wins) to each data stream in scope:
1. **Definitive:** any pipeline sets `event.kind: asset`.
2. **Definitive:** `input: entity-analytics` appears in a data stream or policy-template input in any `manifest.yml`.
3. **Strong:** any `fields/*.yml` declares a field matching `*entity.attributes.*`, `*entity.lifecycle.*`, `*entity.relationships.*`, `entity.type`, or `entity.id`.
4. **Heuristic:** stream name is one of the entity-vocabulary names (users, members, devices, hosts, assets, accounts, identities, apps, groups, service_accounts, roles, resources) AND no `event.action` or `event.outcome` is set AND handwritten input fixtures show no per-record event timestamp distinct from collection time. If this is unclear from permitted source or a supplied digest, leave this heuristic unconfirmed; do not inspect generated outputs to resolve it.
5. **Negative gate (overrides 3 and 4):** root `manifest.yml` categories include `cloudsecurity_cdr` AND the stream sets `result.evaluation` or `vulnerability.*` — this is CDR state, not entity asset. Load CDR references only.
If any stream fires checks 1–4 (and the negative gate does not override), load both entity references for that stream.

**Federated Identity detection:** Load `input-configurations/references/federated-identity-aws.md` when any of:
1. Root `manifest.yml` has a `var_groups` option named `identity_federation`.
2. Any `provider_permissions` entry has `provider: aws`.
3. Any `agent/stream/*.yml.hbs` contains `use_cloud_connectors` or `supports_identity_federation`.
4. Root `manifest.yml` `conditions.kibana.version` is `^9.6.0` (or higher) **and** any input is `aws-cloudwatch`, `aws/metrics`, `cel`, or `httpjson` with AWS credential vars — treat as federation-eligible and check the rest of the list.

Then apply the federation items on the manifest checklist, the CEL and HTTPJSON review checklists, and the matching input-configurations guide (CloudWatch **Stream template** — top-level `use_cloud_connectors`, no `auth.aws:`; S3 — pinned `deployment_modes: ["default"]`). Federation-eligible types with no dedicated guide (e.g. `aws/metrics`) still use `federated-identity-aws.md`. Do **not** treat `auth.aws` alone (flat access keys) as federation, and do **not** flag the absence of `external_id` or `hide_in_var_group_options` — both were removed from the shipped packages.

---

## Step 5: Run automated validation

If you have access to the package on disk, run:

```bash
cd packages/<package_name>

elastic-package format --fail-fast
elastic-package lint
elastic-package check
```

Leave generated-output validation and snapshot freshness to `elastic-package`
in CI. Do not regenerate outputs or run snapshot comparisons as review work.
Review handwritten test scenarios and producing source instead. Available CI
results are context, not proof of complete scenario coverage or instructions to
inspect generated outputs. Report relevant source/configuration failures, not
expected/sample-output mismatches or stale snapshots.

## Step 6: Inspect and produce findings

For ordinary source and test files in scope:

1. Read sufficient surrounding source to verify the issue and fix; read the full file when needed
2. If reviewing a diff, read the **diff hunks** to understand what changed
3. Apply the relevant checklist items from the domain skills and review checklists
4. For every issue found, record:
   - **severity**: critical, high, medium, or low
   - **domain**: one of the domain tags below
   - **title**: short description (10 words or fewer)
   - **path**: file path relative to repo root
   - **line**: line number in the file (use line 1 if unknown)
   - **description**: what is wrong and why it matters
   - **recommendation**: how to fix -- include a code block showing the corrected YAML/CEL/JSON

Follow the generated-output exclusion in the tests rubric. A compact test digest
may be read only when a demanding scenario needs it and one is already supplied.
Do not read raw generated outputs to build or verify a digest. Missing summaries
do not prove that validation passed or justify reopening excluded artifacts.

### Cross-file checks

After individual file inspection, check cross-domain consistency (load `references/consistency-rules.md` if not already loaded):

- Fields set in pipeline processors must be declared in `fields/ecs.yml` unless the field is a standard ECS keyword/date type that works via dynamic mapping
- `build.yml` ECS version must match `ecs.version` set in pipeline
- Manifest variables must be referenced in stream templates; a template variable counts as declared if it appears in the data stream manifest `streams[].vars`, the root manifest `policy_templates[].vars`, or the root manifest `policy_templates[].inputs[].vars` for that input type (Handlebars block parameters such as `{{#each tags as |tag|}}` are not variables)
- Data stream manifest must not duplicate root manifest fields (`format_version`, `conditions`)
- Handwritten test configurations and input fixtures should exercise relevant pipeline branches and failure scenarios. Do not use generated expected/sample outputs to establish coverage or freshness.

Read unchanged files from the workspace if needed for cross-referencing.

---

## Output format

Write the review to **`tmp/integration-review.md`** in the current working directory. Create the `tmp/` directory if it does not exist. Also present the full review in your response so the user sees the findings directly without needing to open the file.

Read `references/review-output-template.md` for the exact output format and rendering rules. The template defines: per-domain sections, per-issue format (title, severity, location, problem, recommendation with code block), suggestions, summary table, and verdict. Use the same format for both the file and the response.

### Verdict rules

- Any critical or high finding -> `NEEDS_CHANGES`
- Only medium/low findings -> `APPROVED_WITH_SUGGESTIONS`
- No findings after reviewing permitted source -> `APPROVED`
- Only excluded generated outputs changed -> `NOT_REVIEWED`

### Domain tags

Every issue must include exactly one domain tag:

| Tag | Covers |
|-----|--------|
| `domain:manifest` | Root or data stream manifest fields, format_version, conditions, categories, owner, policy templates |
| `domain:changelog` | Changelog schema, entries, version requirements, links, and observable compatibility/behavior changes; apply the structure rubric and shared conflict resolutions |
| `domain:build` | `_dev/build/build.yml` missing or outdated, doc template issues |
| `domain:pipeline` | Ingest pipeline correctness, JSE00001, on_failure, tags, ECS categorization in pipeline |
| `domain:input` | Agent stream template issues -- all input types including CEL, HTTPJSON, AWS S3, TCP, etc. |
| `domain:fields` | Field definitions, types, duplicates, geo nesting, ECS mapping strategy |
| `domain:tests` | Handwritten pipeline input fixtures, system test configs, test-common-config.yml, and scenario coverage; excludes generated expected/sample outputs |
| `domain:dashboard` | Kibana dashboard JSON at package root (kibana/), TSVB, dataset filters, by-reference panels |
| `domain:transform` | Transform configuration at package root (elasticsearch/transform/), sync, field definitions, CDR |
| `domain:docs` | README content, placeholder text, title/description quality |
| `domain:anonymization` | Real data in committed files, non-synthetic IPs/hostnames/credentials |
| `domain:consistency` | Cross-domain issues: pipeline-fields mismatch, build.yml-pipeline ECS mismatch, unused manifest vars |

### Severity levels

Use the [shared severity definitions](references/domains/severity-core.md#severity-definitions)
and the relevant domain calibration/conflict references from Step 3. Do not
load the compatibility indexes in addition to those same references.

### Important rules

- **Never** include positive observations in findings
- **Every** issue must have a file path and line number
- **Every** recommendation must include a code block showing the corrected code
- **Consolidate** duplicates: merge same issue found in multiple files
- If a domain was reviewed and has no issues, write one line: "✅ *Reviewed — No actionable issues found.*"
- If a domain is not in scope, omit it entirely

### Review discipline

- Every finding must cite a concrete, present-tense bug with evidence in the code under review — not a hypothetical. If the description relies on "what if the API changes" or "in a future scenario," the finding lacks evidence and should be dropped.
- Do NOT flag `validation.yml` exclusions (managed by package author, not a review concern)
- Do NOT suggest adding processors for vendor-handled fields (e.g., suggesting `redact` for passwords the vendor already masks)
- Do NOT flag hypothetical security risks without evidence of actual exposure in the code

---

## Reference files

| File | Load condition | Content |
|------|---------------|---------|
| `references/reviewer-subagent-guidance.md` | Read by the reviewer subagent itself (the orchestrator passes only its path, never embeds the content) | Scope, skill-load sequence, read-only operating rules, per-issue format checklist, verdict rules, reporting contract for the orchestrator-dispatched reviewer |
| `references/review-output-template.md` | Always | Output format template, rendering rules, severity mapping |
| `references/domains/severity-core.md` | Always | Shared severity and package-age calibration |
| `references/domains/conflicts-core.md` | Always | Shared review exceptions |
| `references/review-calibration.md` | Always | Source evidence, optional context, and reporting limits |
| `references/consistency-rules.md` | 2+ domains | Cross-domain consistency rules (pipeline-fields-manifest-tests) |
| `references/version-check-procedure.md` | CEL in scope | 5-step systematic version verification procedure |
| `references/beats-mito-version-matrix.md` | CEL in scope | Full beats-to-mito version mapping (160+ entries) |
| `references/config-options-by-version.md` | CEL in scope | CEL config option introduction by beats version |
| `references/extensions-per-version.md` | CEL in scope | Registered mito extensions per beats version |
| `references/cel-validator-procedure.md` | CEL in scope | celfmt authority, type conversion audit, error shape validation |
| `references/api-conformance-methodology.md` | CEL/HTTPJSON + API docs | Cross-referencing implementation vs vendor API documentation |
| `references/input-review-orchestration.md` | Any input templates | Review depth routing by input type |
| `input-configurations/references/federated-identity-aws.md` | Federated Identity detection (see Step 4) | AWS Cloud Connectors procedure: `iac_template_url`, `use_cloud_connectors`, input gating |
| `references/transform-guide.md` | Transform in scope | Transform types, config, fields, sync, review checklist |
| `references/cdr-transform-requirements.md` | CDR transforms | CDR latest transform requirements, destination naming, keys, retention |
| `references/repo-conventions.md` | Always | elastic/integrations repo conventions: `group` field, Elastic Managed rename + agentless `release`, owner.type, changelog/backport automation, version-constraint hygiene (dated reference) |
| `references/entity-analytics-provider-matrix.md` | entity-analytics in scope | Provider capability matrix (azure-ad, okta, activedirectory, jamf), legacy vs minimal-state sync/marker/deletion semantics |
| `checklists/pipeline-review-checklist.md` | Pipeline in scope | Severity-tagged pipeline review checklist |
| `checklists/field-review-checklist.md` | Fields in scope | Severity-tagged field mapping review checklist |
| `checklists/cel-review-checklist.md` | CEL in scope | Severity-tagged CEL review checklist |
| `checklists/httpjson-review-checklist.md` | HTTPJSON in scope | Severity-tagged HTTPJSON review checklist |
| `entity-mappings/references/entity-field-catalog.md` | Entity data stream in scope (see entity detection rule) | ECS availability matrix, Must Have / Should Have field tables, disambiguation guide, field definition examples, entity field review checklist |
| `entity-mappings/references/entity-pipeline-patterns.md` | Entity data stream in scope (see entity detection rule) | Categorization processors, `entity.id` mirroring, boolean coercion, relationship object patterns, anti-patterns, entity pipeline review checklist |
| `checklists/entity-analytics-review-checklist.md` | entity-analytics in scope | Severity-tagged entity-analytics package review checklist |

### Shared domain references

The Step 3 table is the domain routing map for this skill. Its domain rubrics
and conflict references are canonical and shared with hosted reviewers. Load
only the references relevant to the review and any supporting cross-domain
checks. `references/severity-rubric.md` and `references/conflict-resolutions.md`
remain compatibility indexes, not second copies of the rules.

`review-profiles.json` remains optional host metadata. Standalone reviewers
follow this Markdown workflow, not the host's profile or folding configuration.
