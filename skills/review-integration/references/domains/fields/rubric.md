# Severity rubric — fields

Canonical review guidance for standalone and hosted reviewers. Apply the
[shared definitions and calibration](../severity-core.md) and
[shared conflict resolutions](../conflicts-core.md).

## Universal rules (same severity regardless of package age)

| Domain | Finding | Severity |
|--------|---------|----------|
| Fields | Pipeline field not in ecs.yml (non-dynamic-mapped type) | HIGH |
| Fields | Wrong field type | HIGH |
| Fields | Missing field description | LOW |
| Fields | build.yml ECS pin mismatches pipeline ecs.version | HIGH |

## Rules with new-vs-existing severity adjustment

| Domain | Finding | New package | Existing package |
|--------|---------|------------|-----------------|
| Fields | base-fields.yml wrong entry count | HIGH | MEDIUM (verify minimum entries present) |
| Fields | beats.yml absent | HIGH (file-based inputs) | MEDIUM for file-based; N/A for CEL/HTTPJSON |

## ECS field declarations

- Only flag missing `external: ecs` declarations when `elastic-package` would fail validation or the field type genuinely requires it (e.g., `geo_point`, `geo_shape`, `nested`, `flattened`)
- Standard keyword/date ECS fields that work via dynamic mapping do NOT need explicit declaration — do not flag their absence

## Version-related rules

Use these new/existing package adjustments for version-related findings.

| Rule | New package | Existing package |
|------|-----------|-----------------|
| `ecs.version` in pipeline | Must be `9.3.0` for standard integrations; must be `9.5.0` for packages with entity data streams (`event.kind: asset`) -- HIGH if older than required or mismatched with `build.yml` | Any version is acceptable as long as it matches the `build.yml` ECS pin. Only HIGH if pipeline and build.yml are inconsistent with each other. |
| `build.yml` ECS pin | Must be `git@v9.3.0` for standard integrations; must be `git@v9.5.0` for packages with entity data streams -- HIGH if different from required | Must match pipeline `ecs.version`. Only HIGH if mismatch between the two, not because the version is older. Entity data streams require `git@v9.5.0` because `entity.attributes.*`, `entity.lifecycle.*`, and `entity.relationships.*` leaf fields do not exist at `v9.3.0`. |

## Field-file details

New `base-fields.yml` uses six entries. For existing packages, verify the minimum
`data_stream.type`, `data_stream.dataset`, `data_stream.namespace`, and `@timestamp`.
Missing `event.module` or `event.dataset` is MEDIUM. CEL and HTTPJSON inputs do not
emit `log.offset`, so they do not require `beats.yml`.
