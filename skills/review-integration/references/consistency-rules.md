# Cross-domain consistency rules

Rules that span multiple skills. Each rule specifies which files to compare.

This file is the authoritative inventory of cross-domain rules. Each rule
group carries a rule key and the domain that owns it, so a review split
across domains knows who judges what. **In a single-pass review you own
every rule below** -- the owner annotations tell you which domain tag the
finding takes, not which rules to skip.

> **Sync duty:** the rule keys below mirror the integration-review-bot's
> ownership matrix. Adding, removing, or renaming a key here requires a
> matching change in that repository, and vice versa. The bot repository
> carries the mirror-image note.

## Pipeline to fields consistency

- Every field SET by a pipeline processor (rename target, set target, append target, convert target) must have a declaration in `fields/ecs.yml` (if ECS) or `fields/fields.yml` (if custom) -- EXCEPT standard keyword/date and standard-prefix geo ECS fields on packages whose `conditions.kibana.version` floor is >= 8.13.0, which the `ecs@mappings` component template (applied by the stack at install time from 8.13; package-spec version is not the gate) maps dynamically. For those packages, declarations are required only for types dynamic mapping cannot infer (geo_point on non-standard prefixes, geo_shape, nested, flattened) or where `elastic-package` fails validation (see `conflict-resolutions.md`).
- Every field DECLARED in field files should be written by the pipeline. Declared-but-never-written fields indicate stale declarations or missing pipeline logic.
- Field types must match: a field extracted as a number must not be declared as `keyword` unless specifically needed for range queries.

Rule key: `pipeline_set_fields_declared` -- owned by the pipeline reviewer.

## Build config to pipeline consistency

- `_dev/build/build.yml` must exist when field files are present.
- ECS reference pin in build.yml must match the `ecs.version` value set in the pipeline. For new packages the current standard is `git@v9.3.0` / `ecs.version: 9.3.0`. For existing packages, any ECS version is acceptable as long as the pipeline and build.yml are consistent with each other. Only flag HIGH if there is a mismatch between the two, not because the version is older than the current standard.

Rule key: `ecs_pin_judgment_residue` -- owned by the pipeline reviewer.

- A package containing an entity data stream must pin `git@v9.4.0` or higher in `_dev/build/build.yml` (`git@v9.5.0` is the recommendation for new packages). Compare the pin against each data stream's entity classification: `entity.attributes.*`, `entity.lifecycle.*`, and `entity.relationships.*` leaf fields are undefined at `git@v9.3.0` and fail the build. This is a presence check on the pin, not a judgment call.

Rule key: `entity_ecs_pin_minimum` -- enforced deterministically by review tooling.

## Manifest to template consistency

- Every variable declared in data stream `manifest.yml` must be referenced in at least one stream template (`agent/stream/*.yml.hbs`).
- No unused variables (declared but never `{{variable_name}}` in any template).
- Variable names in manifest must match exactly what the template references.

Rule key: `template_vars_judgment_residue` -- owned by the input reviewer.

## Root manifest to data stream manifest

- Data stream `manifest.yml` must NOT set its own `format_version` or `conditions` -- these belong only in the root manifest.
- Root manifest `format_version` should be `"3.4.2"` for new packages. For existing packages, the minimum version that supports all features used is acceptable. Flag as HIGH if the version is too low for features used or if a new package uses anything other than the current standard.
- Root manifest `conditions.kibana.version` -- for new packages should be `"^8.19.0 || ^9.1.0"`. For existing packages, verify the constraint supports all agent features the package uses (CEL functions, config options, input types). Only flag HIGH if features require a higher version than declared, not merely because the constraint is older than the current standard.

Rule key: `stream_manifest_root_duplication` -- owned by the structure reviewer.

## Test coverage

- Pipeline test fixtures must cover every branch: if a router pipeline sends to sub-pipelines, each sub-pipeline needs test input.
- Input fixtures follow naming: `test-<package>-<datastream>-<type>-sample.log` (or `.json`).
- `test-common-config.yml` must include `fields.tags: [preserve_original_event]`.
- `source.geo.*` fields should NOT be in `dynamic_fields`. For new packages, fix by ensuring `format_version` and `conditions.kibana.version` are current. For existing packages where updating those versions is not in scope, `source.geo` in `dynamic_fields` may be an acceptable workaround -- note as technical debt.
- Expected output files should be generated, not hand-written.

Rule key: `fixtures_cover_pipeline_branches` -- owned by the tests reviewer.

## Sample event

- `sample_event.json` must be system-test-generated, not hand-crafted.
- If absent, `{{ event "stream" }}` must be commented out in `_dev/build/docs/README.md`.

## Routing rules to manifest datasets

- Every target dataset named by a package-local routing rule (`data_stream/*/routing_rules.yml`) must be a dataset the package actually defines -- compare each rule's `target_dataset` against the data stream directory names and any `elasticsearch.index_template.data_stream.dataset` override in the data stream manifests. A rule pointing at a dataset the package does not ship routes documents into an index nobody owns.
- Routing to a dataset owned by a different package is valid only when that package is a declared dependency of the deployment; say so in the finding rather than assuming it is a typo.

Rule key: `routing_rule_targets` -- owned by the pipeline reviewer.

## Dashboards to fields and manifest

- Every field a dashboard panel references (in its query, filter, axis, or column configuration) must be declared in some `fields/*.yml` of the package, or be an ECS field the pipeline sets. A dashboard referencing an undeclared field renders empty and gives no error.
- Every dataset a dashboard filters on (`data_stream.dataset: <value>`) must be a dataset the package ships.
- Compare `kibana/dashboard/*.json` against `data_stream/*/fields/*.yml` and the data stream manifests.

Rule key: `dashboard_references_exist` -- owned by the dashboard reviewer.

## Kibana asset reference resolution

- Every by-reference panel, saved search, index pattern, or map a Kibana asset points at must resolve to an asset the package ships under `kibana/`. An unresolvable reference breaks the asset at install time.
- This is a presence check across `kibana/**/*.json` -- the referenced id either exists in the package or it does not.

Rule key: `kibana_reference_resolution` -- enforced deterministically by review tooling.

## ILM and lifecycle consistency across data streams

- ILM policies and lifecycle settings must be consistent across the package's data streams. Compare `data_stream/*/lifecycle.yml` and any `elasticsearch.ilm_policy` set in the data stream manifests: streams carrying the same kind of data should not have divergent retention without a reason visible in the change.
- A lifecycle policy on some streams and not others is a finding only when the streams are comparable; a metrics stream and a logs stream legitimately differ.

Rule key: `ilm_lifecycle_consistency` -- owned by the structure reviewer.

## README to package reality

- The README (`_dev/build/docs/README.md`, and the generated `docs/README.md`) must describe what the package actually ships: every data stream it lists must exist, every data stream the package defines should be documented, and the described inputs, requirements, and setup steps must match the manifests.
- Compare the README against the root manifest, the data stream directories, the data stream manifests, and the pipelines. A README describing a data stream that was renamed or removed in the same change is a finding, as is one describing fields the pipelines no longer produce.

Rule key: `readme_matches_package_reality` -- owned by the structure reviewer.
