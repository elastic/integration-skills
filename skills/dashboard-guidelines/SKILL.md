---
name: dashboard-guidelines
description: "Use when creating or reviewing Kibana assets in packages, including dashboard export structure, naming, and data stream alignment."
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
2. Kibana/Elastic services are available for editing and exporting assets
3. sample data exists and dashboards can be validated against realistic events/metrics
4. package `manifest.yml` compatibility constraints (`conditions.kibana.version`) are understood

## Workflow: create, export, validate

1. Build or update dashboards in Kibana.
   - Prefer Lens for new visualizations.
   - Keep panels in the dashboard itself (by value) unless shared-library behavior is intentionally required.
2. Export assets back into the package.

```bash
# from package root
elastic-package export
```

3. If you need to modify installed managed dashboards before exporting:

```bash
elastic-package edit dashboards
elastic-package export dashboards
```

4. Review exported files under `kibana/`:
   - file names match package spec
   - no stale field names after mapping changes
   - dashboard filters are scoped to integration datasets

5. Run package validation commands before opening a PR:

```bash
elastic-package check
```

## Naming conventions

Use naming conventions from dashboard creation guidance:

- Visualization title:
  - `<Name>` (avoid repeating package name in each panel title)
- Dashboard title:
  - `[<Metrics | Logs> <PACKAGE NAME>] <Name>`
  - examples: `[Metrics System] Host overview`, `[Logs Nginx] Access overview`
- Dashboard asset file:
  - `{PACKAGE_NAME}-{identifier}.json`
  - example: `nginx-046212a0-a2a1-11e7-928f-5dbe6f6f5519.json`

## Design and modeling best practices

- Use stable released Kibana versions (avoid SNAPSHOT).
- Keep dashboards focused; split overloaded boards and provide navigation links.
- Prefer by-value panels so dashboards remain self-contained.
- Prefer Lens over TSVB for new visualizations.
- Add controls using dashboard-native **Controls** (not deprecated input controls visualization).
- Include dataset-aware filtering to prevent broad `logs-*` / `metrics-*` queries where possible.
  - baseline recommendation: filter by `data_stream.dataset`
- Keep visual hierarchy clear:
  - most important summary panels near the top
  - related charts grouped together
  - margins enabled for readability
- Use concise, self-explanatory panel titles and consistent accessible colors.

## Quality checklist before PR

- dashboard assets are in `kibana/dashboard/` and follow expected naming pattern
- dashboard content reflects current field names and types
- visualizations are embedded by value unless there is a documented exception
- dashboard or panel queries include integration-relevant filters (`data_stream.dataset` when applicable)
- controls/drilldowns/navigation are coherent for multi-dashboard packages
- exported dependencies are committed (dashboards plus required saved objects)
- `elastic-package check` passes for the package

## Common pitfalls

- exporting from an unstable Kibana build and committing incompatible saved object data
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

- `references/kibana-assets-layout.md`
