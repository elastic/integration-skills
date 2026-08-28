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
  guidelines require Lens for all new visualizations. Migrating
  existing TSVB to Lens is encouraged.
- **Missing dataset filter:** Each visualization should filter on
  `data_stream.dataset` or an equivalently specific scope. Flag
  panels that query broad index patterns (`metrics-*`, `logs-*`)
  without scoping.
- **By-reference visualizations:** Visualization and lens panels
  should be embedded by value. In the raw JSON, `references` entries
  with a `panelRefName` indicate by-reference panels. Flag these
  only when the reference type is `visualization`, `lens`, or `map`.
  Saved searches (`search` type) are inherently referenced and
  should not be flagged.
- **Deprecated input controls:** The `input-control-vis` type is
  deprecated. Dashboard-native controls should be used instead.
- **Package-name title prefix:** Panel titles matching
  `[<Package Name> ...]` create unnecessary repetition. Flag these.
- **Broad wildcard filters:** Filters using unscoped `-*` patterns
  without further qualification are a performance concern.
- **High panel count:** If a dashboard has more than roughly 20
  panels, note it. The guidelines recommend splitting across
  dashboards and linking with drilldowns.
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
- **Missing Kibana asset tags:** New content-pack dashboards are
  expected to carry Kibana asset tags — note their absence (LOW).

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
