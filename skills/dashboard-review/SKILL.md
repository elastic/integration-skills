---
name: dashboard-review
description: "Use when reviewing dashboard JSON changes in a PR or branch. Extracts structured descriptions with kbdash, compares before/after, and checks guideline compliance."
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# dashboard-review

## When to use

Use this skill when tasks include:
- reviewing a PR that modifies Kibana dashboard JSON files
- comparing dashboard changes between branches
- summarizing what changed in dashboard exports
- checking dashboard changes against the official dashboard guidelines

## When not to use

Do not use this skill as the primary guide for:
- creating new dashboards or exporting them from Kibana (`dashboard-guidelines`)
- dashboard naming conventions and file layout (`dashboard-guidelines` → `references/kibana-assets-layout.md`)
- package-wide command orchestration (`elastic-package-cli`)
- test suite selection (`integration-testing`)

## Prerequisites

`kbdash` must be installed:

```bash
go install github.com/efd6/kbdash@latest
```

Lines prefixed with `[!]` in the output are warnings about potential
issues in the dashboard JSON (consistency mismatches, incomplete
extraction, parse errors). Run `kbdash -h` for a description of each
warning type.

## Review procedure

Read `references/review-procedure.md` for the full step-by-step
workflow. The high-level flow is:

1. **Identify** changed dashboard files (added, removed, modified).
2. **Extract** before/after descriptions with `kbdash`.
3. **Compare** descriptions and classify changes as meaningful or cosmetic.
4. **Verify** suspected issues against the raw JSON before reporting.
5. **Format** output as one section per dashboard with bullet-pointed changes.
6. **Check** guideline compliance on added or modified dashboards.

## Guideline compliance checks

After summarizing changes, check the final state of every added or
modified dashboard against the [official dashboard guidelines][dg].
Report violations in a "Guideline notes" subsection after the
change summary for each dashboard.

[dg]: https://www.elastic.co/docs/extend/integrations/dashboard-guidelines

**Check for these issues:**

- **TSVB panels:** Flag any `visualization` panel using TSVB. The
  guidelines require Lens (form-based or ES|QL) for all new
  visualizations. Migrating existing TSVB to Lens is encouraged.
- **Missing dataset filter:** Each visualization should filter on
  `data_stream.dataset` or an equivalently specific scope. Flag
  panels that query broad index patterns (`metrics-*`, `logs-*`)
  without scoping. An ES|QL panel is scoped when its `FROM` names the
  package's data streams or a `WHERE` narrows on
  `data_stream.dataset`.
- **By-reference visualizations:** Visualization and lens panels
  should be embedded by value. kbdash flags by-reference `lens`,
  `visualization`, and `map` panels with `[!] <type> ref: …
  (definition not inlined)`. Flag these. Saved searches are
  inherently referenced and carry a separate `[!] saved search ref`
  warning — do not flag those.
- **Deprecated input controls:** The `input-control-vis` type is
  deprecated. Dashboard-native controls should be used instead.
- **Package-name title prefix:** Panel titles matching
  `[<Package Name> ...]` create unnecessary repetition. Flag these.
- **Broad wildcard filters:** Filters using unscoped `-*` patterns
  without further qualification are a performance concern.
- **High panel count:** kbdash includes the count in the panels
  section header — `Panels (N total, …)`. If N exceeds roughly 20,
  note it. The guidelines recommend splitting across dashboards and
  linking with drilldowns.
- **Queries on `event.dataset` instead of `data_stream.dataset`:**
  Saved-object queries (dashboards, saved searches, packaged ML job
  datafeeds) must filter on `data_stream.dataset`. Some inputs
  (e.g. packetbeat) never set `event.dataset`, so an
  `event.dataset` filter silently matches nothing. Flag every
  saved-object query in a diff that renames or re-maps fields.
- **YAML dashboard sources out of sync:** When a package keeps YAML
  dashboard sources in `_dev/shared/kibana/*.yaml` (compiled to
  `kibana/dashboard/*.json` with kb-dashboard), BOTH must be
  committed and in sync. Flag JSON-only edits when a YAML source
  exists for that dashboard.
- **Regeneration diffs:** A recompile PR is expected to change only
  `state.adHocDataViews`, `state.internalReferences`, and per-layer
  `index` keys (the ES|QL/Discover fix on Kibana 9.3+). Diffs beyond
  those keys in a "regenerate" PR deserve inspection.
- **Settings above the package's Kibana floor:** Take the floor from
  `conditions.kibana.version` in the package `manifest.yml` (the
  lowest version the constraint admits). Flag settings that need a
  newer Kibana than the floor (see `dashboard-guidelines`, "Settings
  that need a newer Kibana"). In saved-object JSON look for:
  - an options-list control in `pinned_panels` with
    `"values_source": "esql"` (needs 9.5)
  - an `lnsMetric` panel on the `textBased` (ES|QL) datasource whose
    visualization state has a `trendlineLayerId` (trend background,
    needs 9.5)
  - `"areaFill": "gradient"` in an XY visualization state (needs 9.6)

  Dashboards built through the 9.6 Dashboards API set the gradient
  fill on every area layer by default, so expect it in exports from
  newer stacks.
- **Hard-coded namespace in ES|QL:** Flag `FROM` clauses that name a
  concrete namespace, such as `FROM logs-<pkg>.<dataset>-default`.
  The panel then shows nothing for policies using another namespace.
  Expect `logs-<pkg>.<dataset>-*`, or a broad pattern followed by
  `WHERE data_stream.dataset == "…"`.
- **All-ES|QL dashboard without a dashboard-level filter:** The
  package-spec validator does not read filters inside ES|QL queries,
  so it needs a `data_stream.dataset` filter at dashboard level
  (`kibanaSavedObjectMeta.searchSourceJSON.filter`) or it fails with
  `SVR00002`. Flag a new `SVR00002` exclusion in `validation.yml`
  unless the panels read indices without `data_stream.dataset`
  (for example transform destination indices).
- **Dashboards API body committed as an asset:** A file in
  `kibana/dashboard/` with top-level `panels`, `pinned_panels` or
  panel `config.data_source` keys is a Kibana Dashboards API request
  body, not a saved object. Flag it; it must be exported from Kibana
  or compiled from YAML.
- **Dashboard title convention:** Dashboard titles follow
  `[<Logs|Metrics> <Package>] <Name>`. Flag other styles such as
  `<Vendor Product> - <Name>`.
- **Layout of new dashboards (packages with a 9.4+ floor):** New
  dashboards should have a description and, with roughly 6 or more
  visualization panels, collapsible sections. Note their absence
  (LOW). Do not ask existing dashboards to be redesigned.
- **Missing Kibana asset tags:** kbdash shows a `Tags:` section for
  each dashboard (resolved from `kibana/tag/` when run on a package
  directory). New content-pack dashboards are expected to carry
  Kibana asset tags — note their absence (LOW).
- **Navigation link completeness:** If a dashboard has a links panel,
  verify that every dashboard in the package has a corresponding
  entry. Run `kbdash <package-dir>` to see all dashboard titles
  (the `=== … ===` headers) alongside each links panel's `Link:`
  lines. Note any dashboard whose title has no matching link.

Only report issues that actually exist — skip passing checks. For
pre-existing violations in unchanged panels, mention them once
briefly ("N existing panels also use TSVB") rather than listing
each one. Focus review attention on newly added or modified panels.

## Handoff to other skills

After the review is complete:
1. `dashboard-guidelines` for creation or export guidance if the review surfaces structural issues
2. `package-spec` when dashboard changes require a release note entry
3. `elastic-package-cli` for validation commands

## References

- `references/review-procedure.md` — full extraction, comparison, and output formatting workflow
