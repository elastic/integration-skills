# Cross-domain consistency rules

Rules that span multiple skills. Each rule specifies which files to compare.

## Pipeline to fields consistency

- Every field SET by a pipeline processor (rename target, set target, append target, convert target) must have a declaration in `fields/ecs.yml` (if ECS) or `fields/fields.yml` (if custom).
- Every field DECLARED in field files should be written by the pipeline. Declared-but-never-written fields indicate stale declarations or missing pipeline logic.
- Field types must match: a field extracted as a number must not be declared as `keyword` unless specifically needed for range queries.

## Build config to pipeline consistency

- `_dev/build/build.yml` must exist when field files are present.
- ECS reference pin in build.yml must match the `ecs.version` value set in the pipeline. For new packages the current standard is `git@v9.3.0` / `ecs.version: 9.3.0`. For existing packages, any ECS version is acceptable as long as the pipeline and build.yml are consistent with each other. Only flag HIGH if there is a mismatch between the two, not because the version is older than the current standard.

## Manifest to template consistency

- Every variable declared in data stream `manifest.yml` must be referenced in at least one stream template (`agent/stream/*.yml.hbs`).
- No unused variables (declared but never `{{variable_name}}` in any template).
- Variable names in manifest must match exactly what the template references.

## Root manifest to data stream manifest

- Data stream `manifest.yml` must NOT set its own `format_version` or `conditions` -- these belong only in the root manifest.
- Root manifest `format_version` should be `"3.4.2"` for new packages. For existing packages, the minimum version that supports all features used is acceptable. Flag as HIGH if the version is too low for features used or if a new package uses anything other than the current standard.
- Root manifest `conditions.kibana.version` -- for new packages should be `"^8.19.0 || ^9.1.0"`. For existing packages, verify the constraint supports all agent features the package uses (CEL functions, config options, input types). Only flag HIGH if features require a higher version than declared, not merely because the constraint is older than the current standard.

## Test coverage

- Pipeline test fixtures must cover every branch: if a router pipeline sends to sub-pipelines, each sub-pipeline needs test input.
- Input fixtures follow naming: `test-<package>-<datastream>-<type>-sample.log` (or `.json`).
- `test-common-config.yml` must include `fields.tags: [preserve_original_event]`.
- `source.geo.*` fields should NOT be in `dynamic_fields`. For new packages, fix by ensuring `format_version` and `conditions.kibana.version` are current. For existing packages where updating those versions is not in scope, `source.geo` in `dynamic_fields` may be an acceptable workaround -- note as technical debt.
- Expected output files should be generated, not hand-written.

## Sample event

- `sample_event.json` must be system-test-generated, not hand-crafted.
- If absent, `{{ event "stream" }}` must be commented out in `_dev/build/docs/README.md`.
