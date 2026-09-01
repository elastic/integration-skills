# Severity rubric -- structure domain

> **Not for single-pass reviews.** This file is one domain's slice of
> `../../severity-rubric.md`, written for a reviewer that owns only this
> domain within a larger, domain-split review. If you are running the
> `review-integration` skill end to end, read the monolith instead -- it
> carries every domain's rows and is the authoritative copy.

Severity definitions and the new-vs-existing calibration note live in
`../severity-core.md`. Read that file first, then the rows below.
Conflicts for this domain: core only (`../conflicts-core.md`); there is no
structure-specific conflict file. The first-version-leniency entry in the
core file matters most to this domain.

> **Maintenance:** these rows mirror the manifest and changelog rows in
> `../../severity-rubric.md`. A PR that changes a row must change both
> files in the same PR.

## Universal rules (same severity regardless of package age)

| Domain | Finding | Severity |
|--------|---------|----------|
| Manifest | format_version too low for features used | HIGH |
| Manifest | conditions.kibana.version too low for agent features used | HIGH |
| Manifest | Data stream duplicates root manifest fields | MEDIUM |

## Rules with new-vs-existing severity adjustment

| Domain | Finding | New package | Existing package |
|--------|---------|------------|-----------------|
| Changelog | Changelog link does not point at the PR or issue that introduces the change (a placeholder was left in; there is no placeholder value to match on -- see `conflict-resolutions.md`) | Informational note only (first-version leniency) | LOW (`check_changelog_entries.sh` enforces this on every link the PR adds; flag only what that check cannot see -- an entry this PR did not touch, or a review with no PR context) |
