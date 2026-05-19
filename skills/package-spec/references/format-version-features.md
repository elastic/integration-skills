# Package spec format_version features

Curated table of features by `format_version`, sourced from the [elastic/package-spec](https://github.com/elastic/package-spec) repository's `spec/changelog.yml`. Use this to determine the minimum `format_version` a package needs based on the features it uses.

## Feature-to-version table

### Core features (pre-3.4.2)

| Feature | Minimum format_version | Notes |
|---------|----------------------|-------|
| Basic package structure | 1.0.0 | Manifest, data streams, ingest pipelines, fields |
| Input-level variables | 2.0.0 | `policy_templates[].inputs[].vars` |
| `elasticsearch.privileges` | 2.3.0 | Required privileges for Fleet |
| `routing_rules.yml` support | 2.9.0 | Dynamic dataset/namespace routing |
| `lifecycle` field | 3.0.0 | Data stream lifecycle configuration |
| Secret variables (`secret: true`) | 3.0.0 | Variables masked in Fleet UI |
| `elasticsearch.source_mode` | 3.0.3 | Synthetic source, TSDB mode |

### Current standard: 3.4.2

This is the standard `format_version` for new integrations. All features up to 3.4.2 are available.

### Recent additions (3.5.0+)

These features require bumping beyond the current standard. Only use them if the package specifically needs the feature.

| Feature | Minimum format_version | Package-spec reference |
|---------|----------------------|----------------------|
| Pipeline tag validations (enforced) | 3.6.0 | [#1010](https://github.com/elastic/package-spec/pull/1010) |
| Pipeline global on_failure validations (enforced) | 3.6.0 | [#1038](https://github.com/elastic/package-spec/pull/1038) |
| Deprecation support (packages, inputs, data streams, variables) | 3.6.0 | [#1053](https://github.com/elastic/package-spec/pull/1053) |
| ES\|QL query assets | 3.6.0 | [#1028](https://github.com/elastic/package-spec/pull/1028) |
| Time series index mode for input packages | 3.6.0 | [#1066](https://github.com/elastic/package-spec/pull/1066) |
| Multiple template paths | 3.6.0 | [#1089](https://github.com/elastic/package-spec/pull/1089) |
| Package dependencies (`requires` field) | 3.6.0 | [#1071](https://github.com/elastic/package-spec/pull/1071) |
| OTel input type | 3.6.0 | [#1091](https://github.com/elastic/package-spec/pull/1091) |
| Input type migration | 3.6.0 | [#1021](https://github.com/elastic/package-spec/pull/1021) |
| `var_groups` (policy template and input levels) | 3.6.1 | [#1120](https://github.com/elastic/package-spec/pull/1120) |
| Named inputs in policy templates | 3.6.1 | [#1135](https://github.com/elastic/package-spec/pull/1135) |
| Fleet-reserved variable validation | 3.6.1 | [#1134](https://github.com/elastic/package-spec/pull/1134) |
| `geo_shape` field type | 3.6.1 | [#1132](https://github.com/elastic/package-spec/pull/1132) |
| `sections` for Fleet UI layout | 3.6.1 | [#1133](https://github.com/elastic/package-spec/pull/1133) |
| `show_divider` on inputs | 3.6.1 | [#1133](https://github.com/elastic/package-spec/pull/1133) |
| Transform `num_failure_retries` | 3.6.1 | [#1124](https://github.com/elastic/package-spec/issues/1124) |
| ML modules in content packages | 3.6.2 | [#1149](https://github.com/elastic/package-spec/pull/1149) |
| `semantic_text` field type | 3.7.0 (unreleased) | [#807](https://github.com/elastic/package-spec/pull/807) |

## Breaking changes at 3.6.0

Spec version 3.6.0 introduced **stricter validations** that are breaking changes for packages that were previously valid:

1. **Pipeline tag validations**: every processor in an ingest pipeline must have a `tag` field. Packages at 3.6.0+ that lack tags will fail `elastic-package check`.
2. **Pipeline on_failure validations**: the pipeline-level `on_failure` block must follow the expected structure. Missing or malformed `on_failure` blocks fail validation.

Packages at the current standard `3.4.2` are NOT subject to these stricter validations. Bumping to 3.6.0+ adds these requirements. Only bump if the package needs a 3.6.0+ feature AND the pipeline already complies with tag and on_failure rules (which they should, per the `ingest-pipelines` skill).

## Upstream source

The authoritative source is `spec/changelog.yml` in the [elastic/package-spec](https://github.com/elastic/package-spec) repository. When new spec versions are released, update this table by reviewing that changelog for features relevant to integration developers.

The spec versioning model:
- A package at `format_version: x.y.z` must be valid against specs in `[x.y.z, X.0.0)` where `X = x + 1`
- Patch versions (x.y.Z) may add stricter validations
- Minor versions (x.Y.z) add new feature support
- Major versions (X.y.z) are reserved for significant format changes
