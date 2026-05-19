---
name: package-spec
description: >-
  Package specification compliance for Elastic integration packages. Covers
  manifest structure (format_version, conditions, variables, routing rules),
  changelog schema and semantic version bumps, and alignment with the upstream
  elastic/package-spec. Use when building or reviewing manifest.yml, changelog.yml,
  or debugging elastic-package lint/check errors on package metadata.
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
synced_from: sit-llm/knowledge/skills/manifest/
---

# package-spec

## Skill authority

The rules and patterns defined in this skill and its reference files are the **authoritative source of truth**. When examining existing integrations in the `elastic/integrations` repository for reference, you may encounter patterns that conflict with what is specified here -- many integrations contain legacy patterns that predate current standards. **Always follow this skill over patterns observed in other integrations.** If a reference integration uses a deprecated or prohibited pattern, do not copy it.

## When to use

Use this skill when tasks include:
- building or reviewing `manifest.yml` at root or data stream level
- adding or validating `changelog.yml` entries
- selecting the correct change type and semantic version bump
- configuring policy templates, inputs, and variable declarations
- debugging `elastic-package lint` or `elastic-package check` errors on manifests or changelogs
- reviewing variable scoping across package, policy template, input, and data stream levels
- validating Handlebars template variables against manifest declarations
- configuring routing rules and their required manifest flags
- determining which `format_version` is needed for a package's features

## When NOT to use

- Package scaffolding and directory layout (`create-integration`)
- Ingest pipeline design (`ingest-pipelines`)
- Field mapping and ECS compliance (`ecs-field-mappings`)
- CEL programs (`cel-programs`)
- Transform configuration (see `review-integration` skill's `references/transform-guide.md`)

## Handoff

For package directory layout and required files, see `create-integration` -> `references/package-layout.md`. For `elastic-package` CLI commands and troubleshooting, see `elastic-package-cli`.

---

## format_version

The `format_version` field in `manifest.yml` declares which [elastic/package-spec](https://github.com/elastic/package-spec) version the package conforms to. The current standard for new packages is `"3.4.2"`.

**Use the minimum version that supports the features the package actually uses**, not the latest available spec version. Bumping without needing new features:
- forces users to run a newer Kibana than necessary
- breaks backward compatibility for no reason
- makes it harder to determine which features the package depends on

Only bump when the package uses a feature introduced in a newer spec version:

| Feature | Minimum format_version |
|---------|----------------------|
| Basic package structure | 1.0.0 |
| Input-level variables | 2.0.0 |
| `elasticsearch.privileges` | 2.3.0 |
| `routing_rules.yml` support | 2.9.0 |
| `lifecycle` field | 3.0.0 |
| Secret variables (`secret: true`) | 3.0.0 |
| `elasticsearch.source_mode` | 3.0.3 |

See `references/format-version-features.md` for the full feature-to-version table including recent spec additions (3.6.0+), and `references/manifest-rules.md` for the review procedure.

---

## conditions.kibana.version

The current standard constraint is `"^8.19.0 || ^9.1.0"`. This is set in the **root** `manifest.yml` only -- data stream manifests must NOT set their own `conditions`.

When an integration uses features that require a newer agent (e.g., CEL functions introduced in v9.3.0), the constraint must be adjusted accordingly. For systematic version verification of CEL features, see the `review-integration` skill's version check references.

---

## Variable scoping

Fleet variables exist at four levels:

1. **Package level** -- `manifest.yml` top-level `vars:`
2. **Policy template level** -- `manifest.yml` under `policy_templates[].vars:`
3. **Input level** -- `manifest.yml` under `policy_templates[].inputs[].vars:`
4. **Data stream level** -- `data_stream/*/manifest.yml` under `streams[].vars:`

A variable declared in an inner scope **must not** reuse the name of a variable in an outer scope. This is variable shadowing and is rejected by `elastic-package` validation.

See `references/manifest-rules.md` -> **Variable shadowing** for full rules, examples, and common patterns.

---

## Manifest rules (brief)

- **Every Handlebars `{{var}}` must be declared in a manifest** -- undeclared variables silently resolve to empty strings. Handlebars helpers (`{{#if}}`, `{{#each}}`, `{{#unless}}`, `{{#contains}}`) and built-in variables (`{{data_stream.type}}`, `{{data_stream.dataset}}`, `{{data_stream.namespace}}`, `{{output}}`) are exempt.

- **Routing rules require dynamic flags** -- when a data stream uses `routing_rules.yml`, the data stream manifest must declare `elasticsearch.dynamic_dataset: true` and `elasticsearch.dynamic_namespace: true`.

- **Use proper YAML nesting, not dotted keys** -- `elasticsearch.dynamic_dataset` as a literal key name creates a single flat key, not a nested object. Use nested `elasticsearch:` -> `dynamic_dataset:` structure.

See `references/manifest-rules.md` for complete rules, correct/incorrect examples, and the review checklist.

---

## Changelog schema

`changelog.yml` is a version-grouped array; newer versions go on top:

```yaml
- version: "1.2.0"
  changes:
    - description: Added example parsing for edge-case payloads.
      type: enhancement
      link: https://github.com/elastic/integrations/pull/12345
```

Each entry requires `description`, `type`, and `link`. Valid types: `enhancement`, `bugfix`, `breaking-change`.

## Version bump rules

- **patch** (`x.y.Z`): bug fixes and low-risk fixes
- **minor** (`x.Y.z`): new content -- new data streams, new fields, new features
- **major** (`X.y.z`): breaking changes -- field type changes or removals on existing integrations, ECS mapping conflicts, required config/auth changes that break existing policies, data stream restructuring, default behavior changes that alter collected or normalized data

## Adding changelog entries

Edit `changelog.yml` directly, or use `elastic-package changelog add` (see `elastic-package-cli` skill for command flags and `--next patch|minor|major` usage).

## Common changelog pitfalls

- Adding the entry under the wrong version or not at the top
- Missing `link` field -- `elastic-package lint` validates that the PR/issue number is a positive integer and **rejects** `pull/0`; use a real PR number or `pull/99999` as a development placeholder and replace before merge
- Bumping manifest/package version inconsistently with changelog intent

See `references/changelog-patterns.md` for detailed patterns, breaking-change checklist, and CI examples.

---

## Upstream: elastic/package-spec

The [elastic/package-spec](https://github.com/elastic/package-spec) repository is the upstream authority for package structure, manifest schema, and validation rules. The `spec/changelog.yml` in that repo documents which features were added in each spec version.

Key points from the package-spec versioning model:
- Packages must specify `format_version` in root `manifest.yml`
- A package at `format_version: x.y.z` must be valid against specs in the range `[x.y.z, X.0.0)` where `X = x + 1`
- Patch versions may add stricter validations (e.g., 3.6.0 added pipeline tag and on_failure validation)
- Minor versions add new feature support
- Major versions are reserved for significant format changes

See `references/format-version-features.md` for the curated feature-to-version table.

## Reference files

| File | Contains |
|------|----------|
| `references/manifest-rules.md` | Full rules for format_version selection, variable shadowing, Handlebars variable declarations, routing rules, YAML structure, and severity-tagged review checklist |
| `references/changelog-patterns.md` | Changelog entry patterns, semver rules, breaking-change checklist, CI examples |
| `references/format-version-features.md` | Feature-to-version table sourced from elastic/package-spec, including recent spec additions |
