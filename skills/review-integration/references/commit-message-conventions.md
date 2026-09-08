# Commit-message conventions for integrations PRs

Integrations PRs squash-merge: the PR title becomes the commit-message
subject on merge, and the PR description becomes the commit body. Judge
PR titles and descriptions against these conventions.

## Subject (the PR title)

Format: `<package>: <summary>`

- Prefix with the affected package's directory name under `packages/`
  (e.g. `cisco_ios:`, `aws:`). A change spanning several packages lists
  them comma-separated without spaces (`aws,azure:`). A repo-wide or
  non-package change uses the affected area instead (`ci:`, `docs:`,
  `all:`).
- The summary completes the sentence: "This change modifies the
  integration to ___."
- Lowercase after the prefix; no trailing period; not a complete
  sentence.
- Describe the result, not the activity: "improve TLS error reporting",
  not "improved" or "improving".
- Keep the whole line under ~72 characters where practical, but never
  abbreviate or rename a package to make it fit.

## Description (becomes the commit body)

- Explain WHAT changed and WHY in complete sentences a maintainer can
  follow without opening the diff.
- Name user-visible behavior changes, new or changed config options,
  and breaking changes explicitly.
- Reference the issue the change addresses (`Fixes #N` / `Closes #N`)
  when one exists.
- Template checklists and screenshots are fine, but the prose must
  stand on its own without them.

## Examples

Conforming:

```text
cisco_ios: parse VLAN tags from syslog messages
aws: add firehose support to the cloudwatch data stream
ti_anyrun,ti_opencti: pin ECS reference to git@v9.5.0
```

Not conforming:

```text
Fix bug                      (no package prefix; says nothing)
Updated the pipeline.        (activity phrasing; trailing period)
CISCO: Fixed The Parser      (wrong case; activity phrasing)
```
