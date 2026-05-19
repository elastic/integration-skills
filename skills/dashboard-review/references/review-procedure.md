# Review procedure

Step-by-step workflow for reviewing Kibana dashboard changes using
`kbdash` to extract structured descriptions from the opaque JSON.

## 1. Identify changed dashboard files

Determine the base branch and list changed files under
`*/kibana/dashboard/*.json`.

**From a PR URL or number:**

```bash
gh pr diff <number> --name-only | grep 'kibana/dashboard/.*\.json$'
```

**From a local branch:**

```bash
git diff --name-only <base>...HEAD -- '*/kibana/dashboard/*.json'
```

Classify each file as **added**, **removed**, or **modified** using
`git diff --diff-filter=A`, `--diff-filter=D`, `--diff-filter=M`.

## 2. Extract before/after descriptions

For each **modified** dashboard file:

```bash
git show <base>:<path> > /tmp/kbdash-before.json
kbdash /tmp/kbdash-before.json > /tmp/kbdash-before.txt
kbdash <path> > /tmp/kbdash-after.txt
```

For **added** files, only run `kbdash` on the new version.
For **removed** files, only extract the base version.

When reviewing a PR by URL and you don't have the repo checked out,
clone it into a temp directory or use `gh pr checkout`.

## 3. Compare and summarize

Read both text descriptions and compare them. Report changes in
order of importance:

**Always report (meaningful):**

- Added or removed dashboards (entire files)
- Added or removed panels
- Changed panel type or visualization subtype (e.g. `lnsPie` to
  `lnsXY`, or `lens` to `visualization`)
- Changed data fields — added, removed, or different source fields
- Changed aggregation operations (e.g. `terms` to `count`,
  `average` to `sum`)
- Changed or reorganized layer structure in lens panels
- New, changed, or removed filters (global or per-panel)
- Changed controls (added, removed, different fields or types)
- Changed global query
- New, changed, or removed navigation links
- Changed dashboard title or description

**Downplay (cosmetic):**

- Grid position shifts (`x`, `y` changes) that don't change the
  relative ordering of panels — group these as "position adjustments"
- Small size changes (`w`, `h`) that don't fundamentally change the
  panel's role — mention only in passing
- Panel reordering without any other semantic change

Use judgement: a panel moving from row 0 to the bottom of the
dashboard *is* meaningful (it changes what users see first), but
shifting 2 grid units to the right is not.

## 4. Verify suspected issues against raw JSON

`kbdash` extracts a subset of the dashboard structure. Before
reporting that something is missing (no filters, no fields, empty
configuration), check the raw dashboard JSON for the panel in
question to confirm the issue is real.

For each suspected problem:

1. Find the panel in the raw JSON (match by panel index, title, or
   grid position).
2. Inspect the relevant section — e.g. for a "no filter" finding,
   check `embeddableConfig.attributes.state.datasourceStates`
   column-level `filter` fields, not just panel-level and
   state-level filters.
3. Note the line number(s) in the JSON file where the issue occurs.
4. If the raw JSON confirms the issue, report it with line numbers
   so reviewers can locate it directly.
5. If the raw JSON shows the information *is* present but `kbdash`
   did not surface it, report the review finding as a `kbdash`
   extraction gap instead of a dashboard bug. Note what `kbdash`
   missed so it can be fixed.

This step prevents false positives from incomplete extraction.
Include line numbers in all reported issues — both confirmed
dashboard problems and `kbdash` gaps.

## 5. Structure the output

Write one section per dashboard. Include both the dashboard title and
the filename (from kbdash's `File:` line) in the heading so reviewers
can locate the file. Within each section, list meaningful changes as
bullet points. If a dashboard has only cosmetic changes, say so in a
single line rather than enumerating every position shift.

**Example output:**

```
## Dashboard: "[Logs] Audit Events" (`audit-events-abc123.json`)

- Added panel "Error Rate Over Time" (lens: lnsXY) at row 30
  - Fields: event.outcome (terms), @timestamp (date_histogram)
- Panel "Distribution by Result": changed from lnsPie to lnsXY
- Panel "Top Users": added filter `user.name: exists`
- Removed panel "Legacy Status Table"
- Global query unchanged
- Minor position adjustments to 3 panels (no reordering)

### Guideline notes
- 1 panel uses TSVB (should be Lens)
- Panel "Error Rate Over Time" has no `data_stream.dataset` filter
```

For added dashboards, describe the full dashboard briefly — list of
panel types and what data they show, without exhaustive field lists.
For removed dashboards, note the title and what it covered.

## 6. Edge cases

- **New package (no base version):** All dashboards are new. Describe
  each one briefly rather than comparing.
- **Renamed files:** Check whether a removed + added pair have the
  same dashboard ID or title. If so, treat as a rename and diff the
  content.
- **Many dashboards:** If the package has more than 5 changed
  dashboards, start with a summary table (dashboard name, change
  type, number of meaningful changes) before the per-dashboard
  detail.
