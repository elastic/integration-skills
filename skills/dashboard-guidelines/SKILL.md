---
name: dashboard-guidelines
description: "Use when creating or reviewing Kibana assets in packages, including dashboard design for Kibana 9.4+, YAML or exported dashboard sources, naming, and data stream alignment."
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# dashboard-guidelines


## When to use

Use this skill when tasks include:
- creating new Kibana dashboards for an integration package
- reviewing dashboard JSON changes in `kibana/` folders
- writing or compiling YAML dashboard sources in `_dev/shared/kibana/`
- exporting dashboard updates from Kibana into package source
- verifying dashboard naming and file layout against package spec
- checking dashboard/data stream alignment through `data_stream.dataset` filtering

## When not to use

Do not use this skill as the primary guide for:
- package and data stream directory scaffolding (`create-integration`, `package-structure`)
- ingest pipeline parsing and normalization logic (`ingest-pipelines`)
- package-wide command orchestration and stack lifecycle decisions (`elastic-package-cli`)
- test suite selection outside dashboard-focused checks (`integration-testing`  → `references/system-testing.md`)

## Preconditions

Before creating or updating dashboard assets, verify:
1. you are in the correct package directory (`packages/<package_name>/`)
2. for the export path, Kibana/Elastic services are available for editing and
   exporting assets (compiling YAML sources does not need a running Kibana)
3. sample data exists and dashboards can be validated against realistic events/metrics
4. the package's Kibana floor is known: the lowest version admitted by
   `conditions.kibana.version` in `manifest.yml`. New packages use `^9.4.0`
   (see `package-spec`). The floor decides which dashboard settings you may use
   (see "Settings that need a newer Kibana" below).

## Authoring paths

Both paths produce saved-object JSON in `kibana/dashboard/`, which is what
Fleet installs. Dashboards API request bodies (top-level `panels`,
`pinned_panels`, `config.data_source`) are **not** package assets; never commit
them to `kibana/dashboard/`.

### Preferred for new dashboards: YAML sources

Write the dashboard as YAML in `_dev/shared/kibana/*.yaml` and compile it with
`kb-dashboard` to `kibana/dashboard/*.json`. Commit both; CI
(`validate-yaml-dashboards.yml`) fails when they are out of sync. YAML is
diffable and suits LLM-assisted work. It supports ES|QL and Lens panels,
collapsible sections and controls.

Use the compiler and linter versions pinned in the integrations repo
(`docs/yaml_dashboards.md` and
`.github/workflows/validate-yaml-dashboards.requirements.txt`); do not use a
newer unpinned version.

```bash
REQS=.github/workflows/validate-yaml-dashboards.requirements.txt
uvx --with-requirements "$REQS" --from kb-dashboard-cli==<pinned> kb-dashboard compile --help
uvx --with-requirements "$REQS" --from kb-dashboard-lint==<pinned> kb-dashboard-lint check --help
```

### Supported: build in Kibana, then export

1. Start a stack at the package's Kibana floor version or later (stable
   release, not SNAPSHOT) and build the dashboard in the UI or through the
   Kibana Dashboards API (for example with the `kibana-dashboards` skill from
   `elastic/agent-skills`).
2. Export into the package:

```bash
# from package root
elastic-package export dashboards
```

3. To change installed managed dashboards before exporting:

```bash
elastic-package edit dashboards
elastic-package export dashboards
```

If the stack is newer than the package floor, check the exported JSON for
settings the floor does not support (see below) before committing.

### Validate

1. Review files under `kibana/`: names match the package spec, no stale field
   names after mapping changes, queries scoped to the package's datasets.
2. Run `elastic-package check`.

## Design for Kibana 9.4+ (new dashboards)

Dashboards for packages whose floor is 9.4 or later should use the current
Kibana dashboard layout. `references/dashboard-design.md` has panel sizes, chart
rules and ES|QL patterns. The rules that matter most:

- **Description:** set a dashboard description that says what the dashboard
  covers.
- **Order:** summary metrics → trends over time → breakdowns → detail tables.
- **Sections:** with roughly 6 or more visualization panels, group them into
  collapsible sections (for example "Key metrics", "Trends over time",
  "Breakdowns", and a domain section such as "MITRE ATT&CK coverage").
- **Controls:** 3–5 options-list controls on the fields users filter by most
  (severity, status, category, account). Use dashboard controls, never the
  deprecated input-control visualization.
- **Data source:** prefer ES|QL panels for new dashboards. Data-view (Lens
  form-based) panels remain acceptable.
- **Metric tiles:** no panel title (the metric label names it); never full
  width.
- **Panels by value:** keep every visualization inline (by value), never as a
  library reference.

### Scope every query to the package's data

- ES|QL: query the package's data streams with a namespace wildcard,
  `FROM logs-<package>.<dataset>-*` (or `metrics-…`). Never hard-code a
  namespace such as `-default`: the dashboard then shows nothing for policies
  that use another namespace. A broad `FROM logs-*` must be followed by
  `WHERE data_stream.dataset == "<package>.<dataset>"`.
- Data-view panels: filter on `data_stream.dataset`, never `event.dataset`.
- **Dashboard-level filter:** also set a dashboard filter on
  `data_stream.dataset`, so the dashboard is scoped as a whole. The
  package-spec validator (`SVR00002`, "no filter found") does not read filters
  inside ES|QL queries, and it only checks by-value panels of type `lens`,
  `map` or `visualization`:
  - ES|QL panels of type `lens` (kb-dashboard output, older exports): without
    a dashboard-level filter `elastic-package check` fails; adding the filter
    is enough to pass.
  - Panels of type `vis` (recent Kibana UI exports): the validator skips them,
    so the check passes without a filter. Add the dashboard-level filter
    anyway.

  Exclude
  `SVR00002` in the package's `validation.yml` only when the panels read
  indices that have no `data_stream.dataset` field, such as transform
  destination indices.

### Settings that need a newer Kibana

Some settings Kibana writes when you build on a newer stack, or that design
skills produce by default, do not exist at the 9.4 floor:

| Setting | Needs Kibana | On an older Kibana | Fallback when the package floor is lower |
|---|---|---|---|
| Options-list control whose values come from an ES\|QL query (`values_source: esql`) | 9.5 | The control is silently dropped: the dashboard loads with no control | Control on a data view field |
| Trend background chart on an ES\|QL metric | 9.6 | The metric shows its value without the trend | Metric without a background chart |
| Gradient area fill (`"areaFill": "gradient"` in saved-object JSON; `styling.areas.fill: gradient` in the Dashboards API) | 9.6 | Ignored; areas render with a solid fill | Solid area fill (omit the setting) |

These were checked by building a dashboard on Kibana 9.6 and importing it into
9.4.2, 9.5.3 and 9.5.6. The `kibana-dashboards` skill in `elastic/agent-skills`
lists the trend background as 9.5; on 9.5.3 and 9.5.6 it did not render.

Use a setting only when the package floor is at or above the version in the
table; otherwise use the fallback. Do not raise the package's Kibana floor
just to use one of these. The Kibana 9.6 Dashboards API sets the gradient fill
on every area layer by default, so remove it from exports when the floor is
lower.

## Naming conventions

- Visualization title:
  - `<Name>` (avoid repeating package name in each panel title)
- Dashboard title:
  - `[<Metrics | Logs> <PACKAGE NAME>] <Name>`
  - examples: `[Metrics System] Host overview`, `[Logs Nginx] Access overview`
  - OTel content packages use `[<Product> OTel] <Name>`
    (example: `[ActiveMQ OTel] Overview`)
  - keep these conventions for 9.4+ dashboards too; do not use other title
    styles (such as `<Vendor Product> - <Name>`) that dashboard generators may
    produce
- Dashboard asset file:
  - `{PACKAGE_NAME}-{identifier}.json`
  - example: `nginx-046212a0-a2a1-11e7-928f-5dbe6f6f5519.json`

## Design and modeling best practices

- Use stable released Kibana versions (avoid SNAPSHOT).
- Keep dashboards focused; split overloaded boards and provide navigation links.
- Prefer by-value panels so dashboards remain self-contained.
- Prefer ES|QL or Lens for new visualizations; never TSVB or aggregation-based
  visualizations.
- Add controls using dashboard-native **Controls** (not deprecated input controls visualization).
- Include dataset-aware filtering to prevent broad `logs-*` / `metrics-*` queries where possible.
  - baseline recommendation: filter by `data_stream.dataset`
- Keep visual hierarchy clear:
  - most important summary panels near the top
  - related charts grouped together, in sections on larger dashboards
  - margins enabled for readability
- Use concise, self-explanatory panel titles and consistent accessible colors.

## Quality checklist before PR

- dashboard assets are in `kibana/dashboard/` and follow expected naming pattern
- YAML sources (if any) and compiled JSON are both committed and in sync
- dashboard content reflects current field names and types
- visualizations are embedded by value unless there is a documented exception
- ES|QL queries use `<type>-<package>.<dataset>-*`, never a fixed namespace
- a dashboard-level `data_stream.dataset` filter is present (or `SVR00002` is
  excluded for a documented reason)
- no setting needs a Kibana version above the package floor
- new dashboards have a description, and sections when they have many panels
- controls/drilldowns/navigation are coherent for multi-dashboard packages
- exported dependencies are committed (dashboards plus required saved objects)
- `elastic-package check` passes for the package

## Common pitfalls

- exporting from an unstable Kibana build and committing incompatible saved object data
- committing a Dashboards API request body instead of saved-object JSON
- using settings from a newer Kibana than the package floor (see the table above)
- hard-coding the `default` namespace in ES|QL `FROM` clauses
- all-ES|QL dashboards without a dashboard-level filter (unscoped, and they
  fail `SVR00002` when the panels are of type `lens`)
- using generic, unfiltered `logs-*`/`metrics-*` queries that cause noisy or slow panels
- keeping stale field references after pipeline/field mapping changes
- overloading one dashboard instead of splitting into overview and deep-dive views
- relying on library visualizations unintentionally, causing hidden dependencies
- inconsistent naming between dashboard title, file name, and package context

## Handoff to other skills

After dashboard updates are in place, continue with:
1. `dashboard-review` for reviewing dashboard JSON changes in a PR or branch
2. `integration-testing` → `references/system-testing.md` for system test validation
3. `elastic-package-cli` for broader check/lint/test command selection
4. `package-spec` when dashboard changes require a release note entry

## References

- `references/dashboard-design.md` — Kibana 9.4+ layout, panel sizes, chart rules, ES|QL patterns
- `references/kibana-assets-layout.md` — `kibana/` layout, saved-object anatomy, YAML sources
