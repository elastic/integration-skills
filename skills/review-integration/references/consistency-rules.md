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

Rule key: `entity_ecs_pin_minimum` -- reviewed against source by the reviewer; optional tooling provides evidence only.

## Manifest to template consistency

A stream template (`agent/stream/*.yml.hbs`) may reference a variable declared at any of three sites, and all three count as declared:

- the data stream `manifest.yml`, under `streams[].vars`;
- the root `manifest.yml`, under `policy_templates[].vars`;
- the root `manifest.yml`, under `policy_templates[].inputs[].vars` for the stream's input type -- the usual home of settings shared across streams (`proxy_url`, `ssl`, OAuth credentials).

Handlebars block parameters (`{{#each tags as |tag|}}` ... `{{tag}}`) and helper names (`#if`, `#contains`, `escape_string`) are not variables and need no declaration.

- Every variable declared in data stream `manifest.yml` must be referenced in at least one stream template (`agent/stream/*.yml.hbs`).
- No unused variables (declared but never `{{variable_name}}` in any template).
- Variable names in manifest must match exactly what the template references.
- A variable a template references but no site declares renders empty when the policy is compiled. Before reporting one as undeclared, read the root `manifest.yml` and check the `inputs[].vars` block for the stream's input type; a tool report or digest that lists only stream-level declarations is not sufficient evidence.

Rule key: `template_vars_judgment_residue` -- owned by the input reviewer.

## Root manifest to data stream manifest

- Data stream `manifest.yml` must NOT set its own `format_version` or `conditions` -- these belong only in the root manifest.
- Root manifest `format_version` should be `"3.4.2"` for new packages, or `"3.6.4"` when the package declares `provider_permissions` / `var_groups` (Federated Identity). For existing packages, the minimum version that supports all features used is acceptable. Flag as HIGH if the version is too low for features used or if a new package uses anything other than the applicable standard.
- Root manifest `conditions.kibana.version` -- for new packages should be `"^8.19.0 || ^9.1.0"`, or `"^9.6.0"` with `conditions.agent.version: "^9.4.0"` when Federated Identity is in scope. For existing packages, verify the constraint supports all agent features the package uses (CEL functions, config options, input types). Only flag HIGH if features require a higher version than declared, not merely because the constraint is older than the current standard.

Rule key: `stream_manifest_root_duplication` -- owned by the structure reviewer.

## Test coverage

- Review handwritten pipeline inputs and test configurations for scenario coverage: if a router sends to sub-pipelines, check that relevant branches have test input.
- Input fixtures follow naming: `test-<package>-<datastream>-<type>-sample.log` (or `.json`).
- `test-common-config.yml` must include `fields.tags: [preserve_original_event]`.
- `source.geo.*` fields should NOT be in `dynamic_fields`. For new packages, fix by ensuring `format_version` and `conditions.kibana.version` are current. For existing packages where updating those versions is not in scope, `source.geo` in `dynamic_fields` may be an acceptable workaround -- note as technical debt.
- Do not read or compare generated expected outputs. Snapshot freshness, generation, and pipeline-output mismatches belong to `elastic-package` in CI, not review findings.

Rule key: `fixtures_cover_pipeline_branches` -- owned by the tests reviewer.

## Generated sample events

Do not read `sample_event*.json` or audit its freshness/provenance. Leave generated
artifact validation to CI. A supplied compact test digest is optional evidence
for demanding scenarios only; it does not justify reading raw snapshots.

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

Rule key: `kibana_reference_resolution` -- reviewed against source by the reviewer; optional tooling provides evidence only.

## ILM and lifecycle consistency across data streams

- ILM policies and lifecycle settings must be consistent across the package's data streams. Compare `data_stream/*/lifecycle.yml` and any `elasticsearch.ilm_policy` set in the data stream manifests: streams carrying the same kind of data should not have divergent retention without a reason visible in the change.
- A lifecycle policy on some streams and not others is a finding only when the streams are comparable; a metrics stream and a logs stream legitimately differ.
- A data stream whose input re-collects the whole collection every interval (see `cel_cursor_and_relist_bound` below) and has neither an attached ILM policy nor a `lifecycle.yml` is a finding regardless of what sibling streams do.

Rule key: `ilm_lifecycle_consistency` -- owned by the structure reviewer.

## Retention assets and README

Fleet applies retention differently per deployment type. On stateful stacks (self-managed, Elastic Cloud Hosted) the data stream manifest's `ilm_policy` names a policy shipped at `elasticsearch/ilm/<name>.json`; `lifecycle.yml` is ignored there. On Serverless, ILM does not exist and Fleet applies `lifecycle.yml` (`data_retention`) instead. A package that bounds growth must therefore ship **both**, and they must agree.

- A data stream with `elasticsearch/ilm/*.json` but no `ilm_policy:` in its `manifest.yml` is a finding: the policy is installed but never attached, so stateful backing indices fall back to the default `logs` policy, which never deletes (elastic/integrations#21661 fixed this in ti_misp).
- A data stream with `ilm_policy` but no `lifecycle.yml` (or package-level `lifecycle.yml`) is a finding: Serverless deployments have no retention at all.
- A data stream with `lifecycle.yml` but no ILM policy is a finding unless the package is Serverless-only: stateful deployments get the default `logs` policy.
- The ILM delete age and the lifecycle `data_retention` should express the same intent. ILM `delete.min_age` counts from rollover, so the effective stateful retention is between `min_age` and `rollover.max_age + min_age`; a 2d/3d ILM policy next to a 30d lifecycle (or the reverse) is a finding.
- Every data stream that ships retention must be covered in `_dev/build/docs/README.md`: the period, the reason (usually repeated collection per interval), which mechanism applies on stateful versus Serverless, and how to override each (edit the ILM policy; `PUT _data_stream/<name>/_lifecycle` on Serverless). Compare `data_stream/*/lifecycle.yml`, `data_stream/*/manifest.yml` `ilm_policy`, and `elasticsearch/ilm/` against the README.
- README text that describes only ILM, or only a lifecycle, or states "deleted after N days" without saying which deployment type that applies to, is incomplete.

Rule key: `retention_assets_and_readme` -- owned by the structure reviewer.

## CEL cursor placement and re-list bound

- In every CEL stream template, pagination position (page token, offset, next URL, worklist, "more pending" flag) must be read from and written to `state.cursor.*`. Top-level `state.<position>` is lost on restart and the walk restarts from the beginning. Compare the keys the program reads before its request against the keys it writes under `cursor`.
- A CEL stream that sends no change-timestamp lower bound to the API (fetches the full collection every interval) must have a `fingerprint → _id` processor in `elasticsearch/ingest_pipeline/default.yml` and bounded retention on both deployment types: `ilm_policy` + `elasticsearch/ilm/*.json` for stateful and `lifecycle.yml` for Serverless (see `retention_assets_and_readme`). Compare the stream template, the pipeline, and the data stream directory.

Rule key: `cel_cursor_and_relist_bound` -- owned by the input reviewer.

## README to package reality

- The README (`_dev/build/docs/README.md`, and the generated `docs/README.md`) must describe what the package actually ships: every data stream it lists must exist, every data stream the package defines should be documented, and the described inputs, requirements, and setup steps must match the manifests.
- Compare the README against the root manifest, the data stream directories, the data stream manifests, and the pipelines. A README describing a data stream that was renamed or removed in the same change is a finding, as is one describing fields the pipelines no longer produce.

Rule key: `readme_matches_package_reality` -- owned by the structure reviewer.
