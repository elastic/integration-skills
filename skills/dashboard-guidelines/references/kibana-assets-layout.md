# kibana-assets-layout

This reference captures Kibana asset layout rules, naming constraints, and practical package patterns for dashboard-related work in this repository.

## Spec baseline (`kibana/`)

Canonical source: `docs/extend/kibana-spec.md`.

Supported folders under `kibana/`:

| Asset type | Folder | File pattern |
|---|---|---|
| Dashboard | `dashboard/` | `^{PACKAGE_NAME}-.+\.json$` |
| Visualization | `visualization/` | `^{PACKAGE_NAME}-.+\.json$` |
| Saved search | `search/` | `^{PACKAGE_NAME}-.+\.json$` |
| Map | `map/` | `^{PACKAGE_NAME}-.+\.json$` |
| Lens | `lens/` | `^{PACKAGE_NAME}-.+\.json$` |
| Index pattern | `index_pattern/` | `^.+\.json$` |
| Security rule | `security_rule/` | `^.+\.json$` |
| CSP rule template | `csp_rule_template/` | `^.+\.json$` |
| ML module | `ml_module/` | `^{PACKAGE_NAME}-.+\.json$` |
| Tag | `tag/` | `^{PACKAGE_NAME}-.+\.json$` |
| Osquery pack asset | `osquery_pack_asset/` | `^{PACKAGE_NAME}-.+\.json$` |
| Osquery saved query | `osquery_saved_query/` | `^{PACKAGE_NAME}-.+\.json$` |
| SLO | `slo/` | `^{PACKAGE_NAME}-.+\.json$` |
| Tags definition file | `tags.yml` | YAML file, optional |

Forbidden for dashboard/visualization/search/map/lens/slo:
- filenames ending in `-(ecs|ECS).json`

Version notes from spec:
- `slo/` support is removed for older package-spec versions (`before 3.5.0`)
- `tags.yml` support is removed for older package-spec versions (`before 2.10.0`)

## Canonical directory tree

```text
kibana/
  dashboard/
  visualization/
  search/
  map/
  lens/
  index_pattern/
  security_rule/
  csp_rule_template/
  ml_module/
  tag/
  osquery_pack_asset/
  osquery_saved_query/
  slo/
  tags.yml
```

Not every package uses every folder. Most observability integrations primarily use `dashboard/` + `search/`, with optional `ml_module/`, `map/`, and `tag/`.

## Dashboard JSON anatomy

A typical dashboard asset file contains:

```json
{
  "attributes": { "...": "..." },
  "id": "package-identifier",
  "type": "dashboard",
  "migrationVersion": { "dashboard": "8.x.x" },
  "references": [ { "...": "..." } ]
}
```

Key `attributes` members commonly used:
- `panelsJSON`: embedded panel definitions (often by-value Lens panels)
- `kibanaSavedObjectMeta.searchSourceJSON`: default query/filter scope
- `optionsJSON`: dashboard-level display/options settings
- `controlGroupInput`: dashboard-native controls (dropdowns, etc.)

`references` usually include index-pattern/search dependencies. Many dashboards point to broad index patterns (`logs-*`, `metrics-*`) and then scope with filters like:
- `data_stream.dataset: <package>.<dataset>`

## Naming and alignment rules

Use these together:

- Dashboard title convention:
  - `[<Metrics | Logs> <PACKAGE NAME>] <Name>`
- Visualization title convention:
  - `<Name>` only
- File naming convention:
  - `{PACKAGE_NAME}-{identifier}.json`

Common file-name styles in this repo:
- UUID-based: `nginx-046212a0-a2a1-11e7-928f-5dbe6f6f5519.json`
- Descriptive: `apache-Logs-Apache-Dashboard.json`

## `tags.yml` patterns

`kibana/tags.yml` can assign tags by asset type or by explicit asset IDs.

By asset type:

```yaml
- text: Security Solution
  asset_types:
    - dashboard
    - search
```

By asset ID:

```yaml
- text: Security Solution
  asset_ids:
    - aws-4746e000-bacd-11e9-9f70-1f7bda85a5eb
    - aws-562bdea0-4ba7-11ec-8282-5342b8988acc
```

## Concrete package examples

Representative patterns from the upstream `elastic/integrations` repository:

- **nginx** — mostly UUID-named dashboards, includes `ml_module/` usage
- **apache** — descriptive dashboard filenames, includes `ml_module/`
- **system** — many dashboards with both logs and metrics focus, includes `search/` and `alerting_rule_template/` usage
- **auditd** — dashboard + search + `tags.yml`
- **cisco_duo** — includes `map/` assets
- **aws** — significant `alerting_rule_template/` usage

Note:
- Some folders seen in upstream packages (for example `alerting_rule_template/`, `security_ai_prompt/`) may be package-specific patterns outside the baseline described in `kibana-spec.md`. Keep dashboard work aligned to the package's existing conventions and run validation commands.

## Export and edit commands

Use `elastic-package` commands from the target package directory:

```bash
elastic-package service
elastic-package export
```

Dashboard-specific helpers:

```bash
elastic-package export dashboards
elastic-package edit dashboards
```

Recommended review loop after export:
1. inspect changed files under `kibana/`
2. verify naming/patterns and dataset filters
3. run `elastic-package check`
