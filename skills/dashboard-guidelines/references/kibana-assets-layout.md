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

Package dashboards are Kibana saved objects. A dashboard exported from a
Kibana 9.4+ stack looks like:

```json
{
  "attributes": { "...": "..." },
  "id": "package-identifier",
  "type": "dashboard",
  "coreMigrationVersion": "8.8.0",
  "typeMigrationVersion": "10.3.0",
  "references": [ { "...": "..." } ]
}
```

Older exports carry `migrationVersion: { "dashboard": "8.x.x" }` instead of
`typeMigrationVersion`; both forms install.

Key `attributes` members:
- `title`, `description`
- `panelsJSON`: panel definitions. A list in source files exported with
  `elastic-package` (it decodes the string on export); a JSON string in older
  or hand-edited source files and in built packages. Each panel has `gridData`
  (`x`, `y`, `w`, `h`, and `sectionId` when it sits in a section) and an
  inline `embeddableConfig` for by-value panels.
- `sections`: collapsible sections (`gridData.sectionId` on a panel refers to
  one).
- `pinned_panels` (recent exports) or `controlGroupInput` (older exports):
  dashboard controls.
- `kibanaSavedObjectMeta.searchSourceJSON`: dashboard-level query and filters.
- `optionsJSON`, `timeRestore`/`timeFrom`/`timeTo`, `refreshInterval`.

Lens panels keep their data source in
`embeddableConfig.attributes.state.datasourceStates`. ES|QL panels use the
`textBased` datasource, and their query is in
`embeddableConfig.attributes.state.query.esql`.

This is a different shape from a Kibana Dashboards API request body
(top-level `panels`, `pinned_panels`, `config.data_source`). API bodies are not
package assets: export the saved object or compile YAML instead.

`references` usually include index-pattern/search dependencies. Many dashboards point to broad index patterns (`logs-*`, `metrics-*`) and then scope with filters like:
- `data_stream.dataset: <package>.<dataset>`

The package-spec validator requires every dashboard to have a filter, either
on every panel or at dashboard level (`SVR00002`). It does not read filters
inside ES|QL queries, and it only checks by-value panels of type `lens`, `map`
or `visualization`. An all-ES|QL dashboard of `lens` panels therefore fails
without a dashboard-level filter; one of `vis` panels (recent Kibana UI
exports) passes, but is still unscoped. Add the dashboard-level filter in both
cases (see `../SKILL.md`).

## YAML dashboard sources

Packages may keep dashboards as YAML in `_dev/shared/kibana/*.yaml`, compiled
with `kb-dashboard` into `kibana/dashboard/*.json`:

```text
packages/<package>/
  _dev/shared/kibana/        # YAML sources (not shipped)
    overview.yaml
  kibana/dashboard/          # compiled JSON (shipped)
    <package>-overview.json
```

Commit both. The integrations repo CI (`validate-yaml-dashboards.yml`) fails
when the compiled JSON does not match the YAML. Never edit the compiled JSON by
hand when a YAML source exists. Compiler usage and pinned versions are in the
integrations repo's `docs/yaml_dashboards.md`.

## Naming and alignment rules

Use these together:

- Dashboard title convention:
  - `[<Metrics | Logs> <PACKAGE NAME>] <Name>`
  - OTel content packages: `[<Product> OTel] <Name>`
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
- **anthropic_metrics** — 9.4+ UI exports with collapsible `sections` and
  `pinned_panels` controls. Copy the structure only: its titles
  (`[Anthropic] …`) do not follow the convention, its dashboards have no
  dashboard-level `data_stream.dataset` filter (they pass `SVR00002` only
  because their panels are of type `vis`), and one dashboard has no sections.
- **activemq_otel** — YAML dashboard sources in `_dev/shared/kibana/` compiled
  to all-ES|QL `lens` dashboards with descriptions and a dashboard-level
  filter. It does not use sections.

Note:
- Some folders seen in upstream packages (for example `alerting_rule_template/`, `security_ai_prompt/`) may be package-specific patterns outside the baseline described in `kibana-spec.md`. Keep dashboard work aligned to the package's existing conventions and run validation commands.

## Export and edit commands

Use `elastic-package` commands from the target package directory:

```bash
# export dashboards (and their dependencies) from Kibana into the package
elastic-package export dashboards

# make installed managed dashboards editable before exporting
elastic-package edit dashboards
```

`elastic-package export` has subcommands only (`dashboards`,
`ingest-pipelines`, `workflows`); on its own it exports nothing.

Recommended review loop after export:
1. inspect changed files under `kibana/`
2. verify naming/patterns and dataset filters
3. run `elastic-package check`
