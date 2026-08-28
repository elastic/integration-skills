# elastic/integrations repo conventions

**Verified as of: 2026-08-12** (elastic/integrations main, ~525 commits surveyed
2026-06-01 → 2026-08-12). These conventions are born in the repo's CI and
automation and change faster than skill files — when this date is stale,
re-verify against the cited specs/PRs before flagging. The repo's own
`docs/extend/` lags these conventions; cite the spec or PR, not repo docs.

This file is always loaded. Each section states what a reviewer should START
flagging and STOP flagging.

## `group:` manifest field (marketplace grouping)

Package-spec **3.6.6** (elastic/package-spec#1213) added an optional top-level
`group:` field to integration, input, and content package manifests, placed
immediately after `type:`. elastic/integrations is rolling it out per
technology family (mysql, nginx, kafka, redis, prometheus, apache, iis,
docker; tracking: elastic/ingest-dev#8085). Pattern: **patch** bump +
changelog entry `Add group field to package manifest.` (enhancement).

- FLAG: sibling packages of one technology (base + `_otel` + `_input_otel` +
  content pack) with inconsistent `group` values; a `group` addition missing
  its patch bump/changelog entry.
- DO NOT FLAG: a missing `format_version` bump for it (not required — packages
  on 3.0.2 carry `group:` today); absence of `group` on packages outside a
  multi-package family.

## Agentless → "Elastic Managed" + mandatory `release` field

- All user-facing text renamed Agentless → **Elastic Managed**
  (elastic/integrations#19756, #20084). FLAG remaining "Agentless" wording in
  NEW or CHANGED READMEs, titles, and descriptions.
- `deployment_modes.agentless.release: beta|ga` (spec 3.6.3,
  elastic/package-spec#1130) is now set on all agentless-enabled packages
  (#18552 baseline; #20421/#20463 GA'd security/SSI families). FLAG a
  new/changed agentless block that omits `release`; expect `beta` for new
  packages. The block also carries `organization`/`division`/`team`.
- The agentless-enabled condition (`deployment_modes.agentless.enabled: true`)
  is what gates the CEL-opening `remove_agentless_tags` block check — see
  `checklists/pipeline-review-checklist.md`.
- DO NOT FLAG: agentless blocks on OS/endpoint packages that read host
  kernels/event logs/files/NICs — those packages must NOT have agentless at
  all; flag the block's presence instead.

## `owner.type: elastic` reversal

elastic/integrations#20381 (2026-07-28) moved 14 security packages from
`partner`/`community` to `elastic`, explicitly reversing the 2023 policy, each
with a **minor** bump ("owner type is part of published package metadata").

- FLAG: `community`/`partner` owner.type on a package whose `owner.github` is
  an Elastic team; an `owner.type` change shipped as a patch (it needs minor).
- DO NOT FLAG: a pure `owner.github` change with no bump — internal metadata
  needs none.

## Changelog-link CI + backport automation

Enforced by CI — calibrate, do not duplicate:

- `.buildkite/scripts/check_changelog_entries.sh`: every ADDED changelog
  `link:` must equal the current PR URL; `/issues/<n>` links are allowed
  (skipped); `REPLACE_ME` is reported as a failed auto-fix sentinel; the skip
  label is `changelog-link-check:skip`.
- Commenting `/sync-changelog` on a MERGED PR retries the changelog sync
  (#20578); sync branches `changelog/pr-<N>` are machine-owned.
- Backport checklist comments are auto-generated and auto-updated (#20605:
  "Backport a change when it fixes behavior a branch already has; leave new
  behavior on main"); `.backports.yml` is the branch inventory; cherry-pick,
  version bump, and PR creation are automated.

- FLAG: a backport PR that adds new behavior rather than a fix; manual edits
  to the auto-generated backport checklist.
- DO NOT FLAG / DO NOT ASK: authors to hand-create backport PRs or hand-sync
  changelogs (point at the checklist / `/sync-changelog`); bot-authored
  changelog-sync entries.

## Version-constraint hygiene

- Intermediate `kibana.version` ranges use **tilde**, caret only on the last:
  `'^8.19.7 || ~9.1.7 || ~9.2.1 || ^9.3.0'` (#19872). A caret on an
  intermediate range makes later ranges redundant — FLAG it.
- `kibana.version` constraint updates are NOT breaking changes (#19531
  removed them from the breaking-change detector) — never demand a
  breaking-change entry for one.

## Spec 3.6.x feature gates + category parity

- A package's `format_version` must be >= the version introducing any spec
  feature it uses: `var_groups`/named inputs/`sections`/`show_divider` >=
  3.6.1, agentless `release` >= 3.6.3 (advisory — older declarations exist in
  the wild), `provider_permissions` >= 3.6.4, `group:` >= 3.6.6. Pipeline
  processor-tag and global-`on_failure` validations are BREAKING since 3.6.0.
- Data-stream manifest categories must match policy-template categories
  (semantic validation since 3.6.1; repo-wide sync #19911/#17523) — a
  category added to one side only is a finding.
- There is NO format_version normalization wave (values range 3.0.2 → 3.6.x;
  new packages land anywhere from 3.4.x to 3.6.x) — "could be newer" remains
  a non-finding.

## Bot-authored changes (non-findings)

Weekday-scheduled `requires:` dependency bumps in input-package consumers
(`requires-update.yml`), issue-template package-list updates, updatecli
snapshot bumps, renovate/dependabot bumps. Never ask a human to redo, justify,
or re-word these.

## Dashboards

YAML sources in `_dev/shared/kibana/*.yaml` compile to
`kibana/dashboard/*.json` and both must be committed in sync
(`validate-yaml-dashboards.yml`). Regeneration PRs are expected to touch only
`adHocDataViews`/`internalReferences`/layer `index`. Saved-object queries must
filter on `data_stream.dataset`, never `event.dataset`. Full checks live in
`dashboard-review/SKILL.md`.

## Secrets

Credential-shaped policy vars must carry `secret: true` (recent sweeps mask
even indirect values like policy-variable AWS key ids, #20615). CEL programs
can use `secret_state` for encrypted credential state from beats
v8.19.14 / v9.2.8 / v9.3.3 / v9.4.0 (#18834, beats#49207); templating Fleet
`secret: true` vars into it needs the string-unpack fix, v8.19.16 / v9.3.5 /
v9.4.2, never on 9.2.x (beats#50508). Preferred for new packages whose stack
floor allows it, not a finding for existing redact-based ones. See
`checklists/pipeline-review-checklist.md` (security section) and
`checklists/cel-review-checklist.md`.
