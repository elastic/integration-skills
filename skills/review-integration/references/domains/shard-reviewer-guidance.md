# Domain-scoped integration reviewer guidance

> **Not for single-pass reviews.** This file is the operating manual for a
> reviewer that owns one domain of a domain-split review. A subagent
> running a whole review follows `../reviewer-subagent-guidance.md`
> instead.

Operating manual for a reviewer that owns ONE domain of a larger review of
an Elastic integration — pipeline, fields, input, tests, transform,
dashboard, or structure — rather than the whole review. Read it end to end
before inspecting any file.

Whoever dispatches you tells you **which package** to review, **which
files are in your scope**, **which domain you own**, and **which skills
and references to read**. This file tells you **how to operate** inside
that assignment. Follow both.

## Relationship to `reviewer-subagent-guidance.md`

`../reviewer-subagent-guidance.md` is the operating manual for a subagent
that runs a whole review on behalf of the `create-integration` or
`maintain-integration` orchestrator. This file is the domain-scoped
variant of it. The two are kept as separate files on purpose so they can
be diffed deliberately.

Carried over from that file: skill authority, determining new vs existing
first, reading full files rather than diffs, first-version leniency, and
the data-anonymization findings.

Deliberately not carried over:

- **Trusting the orchestrator's validation results.** There is no
  orchestrator here; whoever dispatches you states what has already been
  validated.
- **The skill-load sequence** (including which CEL references to load).
  Each caller curates the load list for the domain it is dispatching.
- **The per-issue output format and the verdict rules.** Output contracts
  belong to the caller.
- **The "what to return" reporting contract**, for the same reason.

## Skill authority

The rules and patterns defined in the `review-integration` skill and all
the domain skills it routes to are the **authoritative source of truth**.
When examining existing integrations in the `elastic/integrations`
repository for patterns, many contain legacy patterns that predate current
standards — **always judge the integration under review against the
skills, not against patterns observed in other integrations**. If a
reference integration uses a deprecated or prohibited pattern, flag any
reproduction of it.

## Determine new vs existing first

Before inspecting any file, read `changelog.yml` and decide whether this is
a **new package** or an **existing package**. Nobody will tell you: making
this determination is your job.

- **One entry** (version `0.0.1` or `1.0.0`): this is a new package. Apply
  new-package standards.
- **Multiple entries**: this is an existing package. Apply the
  existing-package adjustments.

For a PR that adds a **new data stream** to an existing package, apply
new-package standards to the new stream's files and existing-package
standards to unchanged files.

The `review-integration` skill's "Reviewing new vs existing integrations"
table and the new-vs-existing adjustments in your domain's `rubric.md`
**must** be applied to every version, manifest, and pattern-related
finding. Calibrating these wrong is the most common review error.

## Stay inside your scope

- Findings land only on files in your assigned scope. A file outside your
  scope is context, not a target.
- Reading beyond your scope to verify a suspicion is expected and
  encouraged — you cannot judge whether a pipeline-set field is declared
  without opening the field files, even when field files are not yours.
- When reading outside your scope surfaces a problem in someone else's
  domain, record it for whoever owns that domain instead of reporting it
  as your own finding. How that record is passed on is the caller's
  contract, not this file's concern.

## Stay consistent with the other reviewers

- Never contradict a finding another domain reviewer has already
  published. If your reading of a file disagrees with theirs, say what you
  observed and leave the contradiction for the caller to settle.
- Do not suppress a finding merely because it might overlap with another
  domain's. Duplicates are resolved by the caller; a silently dropped
  finding is not recoverable.

## Read full files, not just diffs

For every file in scope, read it **end to end** before recording findings.
Reviews based on diffs alone miss prohibited patterns and ECS violations
elsewhere in the same file. When you are given a diff, also read the
unchanged surrounding context — the recommendation in each finding has to
fit the actual file shape.

## Apply first-version leniency where the rule says so

`conflicts-core.md` resolves the first-version-leniency conflict: for
first-version packages (`0.0.1` / `1.0.0` with a single changelog entry),
placeholder changelog links (`pull/99999` is the recommended placeholder,
but any fake number behaves the same; `elastic-package lint` rejects
`pull/0`) and placeholder logos/icons are **informational notes only, not
findings**. Do not flag them at MEDIUM or HIGH. For subsequent versions,
the same placeholders are real findings (MEDIUM or HIGH as appropriate).

**Do not hunt for placeholder numbers.** There is no value to match on.
`elastic-package lint` only checks that a github.com link ends in a
positive integer, so `pull/99999`, `pull/12345`, and any other invented
number pass identically. The property that matters is whether the link
points at the PR or issue that introduces the change, and in
`elastic/integrations` that is already a deterministic CI check:
`check_changelog_entries.sh` compares every link a PR adds against the
PR's own URL, exempts `/issues/<n>` links, and is bypassed only by the
`changelog-link-check:skip` label. Do not duplicate it. Flag a link only
where that check cannot see it -- an entry this PR did not touch, or a
review with no PR context -- and then at **LOW** (the severity rubric's
changelog row). CI failing on an unreplaced link pre-merge is expected
behavior, not a finding to report.

**Exception -- the `pull/0` placeholder.** Leniency never applies to
`pull/0`, at any package version: `elastic-package lint` rejects it
outright, so the package does not lint until it is fixed. Flag it
whenever you see it. The fix, here and for any stale placeholder, is to
replace the link with the real PR number once the PR exists -- see the
`package-spec` skill's "Updating the changelog link after PR creation".

## Data anonymization findings

Treat any real production data, customer data, or identifiable information
in committed files as a finding under `domain:anonymization`:

- IP addresses outside RFC 5737 (`198.51.100.x`, `203.0.113.x`,
  `192.0.2.x`) / RFC 3849 (`2001:db8::/32`)
- Hostnames outside `example.com` / `example.org` / `example.local`
- Real email addresses, person names, organisation names, tenant or
  account IDs, API keys, tokens, credentials
- Real vendor URLs with customer-specific subdomains in default manifest
  var values

Flag at **Critical** when found. Placeholder values must preserve the
format/structure of the data they replace (a synthetic UUID for a UUID,
not `REDACTED`). Refer to the `anonymize-logs` skill for the full
placeholder convention list before deciding whether a value is synthetic
enough.

This check applies to whatever files are in your scope. It is not one
domain's job — every reviewer runs it on its own files.
