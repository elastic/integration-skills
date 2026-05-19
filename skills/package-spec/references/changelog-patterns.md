# changelog-patterns

This reference captures practical `changelog.yml` patterns used in this repository and the package spec constraints enforced by `elastic-package lint`.

## Schema baseline

Source: `docs/extend/changelog-spec.md` (from the `elastic/integrations` upstream repo)

```yaml
spec:
  type: array
  items:
    type: object
    additionalProperties: false
    properties:
      version:
        $ref: "./manifest.spec.yml#/definitions/version"
      changes:
        type: array
        items:
          type: object
          additionalProperties: false
          properties:
            description:
              type: string
            type:
              type: string
              enum:
                - "breaking-change"
                - "bugfix"
                - "enhancement"
            link:
              type: string
          required:
            - description
            - type
            - link
    required:
      - version
      - changes
```

Operational rules:
- `changelog.yml` is required in each package
- top-level is a list of version sections
- each version section contains one or more `changes`
- only `enhancement`, `bugfix`, and `breaking-change` are valid `type` values

## Entry ordering and grouping

Repository convention:

```yaml
# newer versions go on top
```

Patterns:
- one section per package version
- all changes for the same package version are grouped under that section
- prepend new versions at the top to preserve descending order

## Representative entry patterns

### Enhancement

From `packages/nginx/changelog.yml` (elastic/integrations):

```yaml
- version: "2.3.0"
  changes:
    - description: Use links panel in Dashboards.
      type: enhancement
      link: https://github.com/elastic/integrations/pull/14380
```

### Bugfix

From `packages/nginx/changelog.yml` (elastic/integrations):

```yaml
- version: "2.3.2"
  changes:
    - description: Remove unused agent files.
      type: bugfix
      link: https://github.com/elastic/integrations/pull/14995
```

### Breaking change

From `packages/apache/changelog.yml` (elastic/integrations):

```yaml
- version: "3.0.0"
  changes:
    - description: Remove third-party pipeline for previously removed 'third-party REST API' input.
      type: breaking-change
      link: https://github.com/elastic/integrations/pull/16133
```

### Multi-change release section

Use this pattern when several changes ship in the same version:

```yaml
- version: "1.18.0"
  changes:
    - description: Prepare package for serverless.
      type: enhancement
      link: https://github.com/elastic/integrations/pull/9818
    - description: Remove duplicated and ambiguous field definitions.
      type: bugfix
      link: https://github.com/elastic/integrations/pull/9818
```

### Multi-line description

From `packages/wiz/changelog.yml` (elastic/integrations):

```yaml
- version: "4.0.0"
  changes:
    - description: |
        As `sourceRule` is deprecated by the Wiz Get Issue API, this version removes the deprecated `source_rule` field from the issue data stream.
        Previous versions added the new `source_rules` field to the issue data stream.
        Users should update their custom-user artifacts if they are using the deprecated `source_rule` field to use the new `source_rules` field.
      type: breaking-change
      link: https://github.com/elastic/integrations/pull/16892
```

## Link conventions

Preferred links:
- PR URL: `https://github.com/elastic/integrations/pull/<number>`
- issue URL: `https://github.com/elastic/integrations/issues/<number>`

Guidelines:
- always provide a resolvable URL
- prefer the PR that introduces the change when available
- use issue links only when a PR link is not the right source of detail

## Versioning guidance

Apply semver aligned with user impact:
- patch (`x.y.Z`): backward-compatible bug fixes
- minor (`x.Y.z`): backward-compatible enhancements
- major (`X.y.z`): breaking changes

When selecting `breaking-change`, check for:
- field type changes (mapping conflicts for existing data)
- field removals or renames
- ECS field mapping collisions or incompatible remapping
- required config/auth changes that break existing policies
- data stream split/merge/restructure changes
- default behavior changes that alter collected/normalized output

## CLI workflows

`elastic-package changelog add` can create entries in the expected format.

Add entry for next patch/minor/major:

```bash
# run inside packages/<package_name>/
elastic-package changelog add \
  --type bugfix \
  --description "Fix parser for empty status field" \
  --link "https://github.com/elastic/integrations/pull/12345" \
  --next patch
```

Add entry for explicit version:

```bash
elastic-package changelog add \
  --type enhancement \
  --description "Add support for additional API region" \
  --link "https://github.com/elastic/integrations/pull/12345" \
  --version 1.14.0
```

Validate after changelog updates:

```bash
elastic-package lint
# or full sequence:
elastic-package check
```

## CI and automation pattern

Automation in `.github/workflows/docs-edit-automation.yml` (elastic/integrations) uses:

```bash
elastic-package changelog add \
  --type "$CHANGE_TYPE" \
  --description "$CHANGELOG_DESC" \
  --link "https://github.com/${GITHUB_REPOSITORY}/pull/$PR_NUMBER" \
  --next "$VERSION_BUMP"
```

This pattern is useful for scripted, repeatable changelog updates where the change type and version bump can be inferred from workflow context.
