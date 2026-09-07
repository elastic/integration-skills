# Severity rubric — structure

Canonical review guidance for standalone and hosted reviewers. Apply the
[shared definitions and calibration](../severity-core.md) and
[shared conflict resolutions](../conflicts-core.md).

This reference covers package structure; it does not introduce a standalone
`structure` domain tag. Keep manifest, changelog, build, and docs tags.

## Universal rules (same severity regardless of package age)

| Domain | Finding | Severity |
|--------|---------|----------|
| Manifest | format_version too low for features used | HIGH |
| Manifest | conditions.kibana.version too low for agent features used | HIGH |
| Manifest | `format_version: "3.6.4"` / Kibana `^9.6.0` / agent `^9.4.0` on a package that declares `provider_permissions` (Federated Identity) | Not a finding -- required floors, not an unjustified bump |
| Manifest | Data stream duplicates root manifest fields | MEDIUM |

## Rules with new-vs-existing severity adjustment

| Domain | Finding | New package | Existing package |
|--------|---------|------------|-----------------|
| Changelog | Changelog link does not point at the PR or issue that introduces the change (a placeholder was left in; there is no placeholder value to match on -- see `../conflicts-core.md`) | Informational note only (first-version leniency) | LOW (`check_changelog_entries.sh` enforces this on every link the PR adds; flag only what that check cannot see -- an entry this PR did not touch, or a review with no PR context) |

## Version-related rules

Use these new/existing package adjustments for version-related findings.

| Rule | New package | Existing package |
|------|-----------|-----------------|
| `format_version` | Must be `"3.4.2"` -- HIGH if different. **Exception:** `"3.6.4"` when the package declares `provider_permissions` / `var_groups` for Federated Identity (see `../../../../package-spec/references/var-groups-and-provider-permissions.md`) | Any version supporting all features used is acceptable. Only HIGH if features require a higher version than declared. |
| `conditions.kibana.version` | Must be `"^8.19.0 \|\| ^9.1.0"` -- HIGH if different. **Exception:** `"^9.6.0"` plus `conditions.agent.version: "^9.4.0"` when Federated Identity is in scope | Verify constraint supports all agent features used (CEL functions, config options). Only HIGH if features require a higher version. |

For ECS build pins and pipeline version agreement, read
[the fields rubric](../fields/rubric.md#version-related-rules).

## Release context

Internal metadata-only changes, such as `owner.github` or CODEOWNERS entries, do
not require a package version bump or changelog entry. Judge changelog entry types
only when the diff shows an observable compatibility or behavior change; editorial
bugfix/enhancement reclassification is not a finding. Apply the shared conflict
resolution for first-version placeholders and checks already performed by CI.

## Additional review exceptions

- A missing version bump or changelog entry on a PR whose package changes are
  internal metadata only (e.g. `owner.github`, CODEOWNERS entries). Such
  housekeeping does not require a release; absence of a bump is not a finding
  for these diffs.
