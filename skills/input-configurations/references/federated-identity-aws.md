# Federated Identity for AWS integrations

Procedure for enabling Federated Identity (Cloud Connectors) on an
agentless-eligible, **single-provider (AWS-only)** integration. The `aws`
package is where the pattern started, but the end state to copy is a standalone
2.0 package — `aws_logs` ([elastic/integrations#20823](https://github.com/elastic/integrations/pull/20823)),
`aws_mq`, `aws_bedrock`, `aws_securityhub`.

Multi-cloud packages (e.g. `kubernetes`) hit platform limits that are still
being worked through upstream — out of scope here.

**Do not duplicate other skills.** Load these first and follow them for their
domains:

| Topic | Authority |
|-------|-----------|
| `var_groups` / `provider_permissions` schema, floors, validators | `package-spec` -> `references/var-groups-and-provider-permissions.md` |
| `format_version` / 3.6.0 pipeline validators | `package-spec` -> `references/format-version-features.md` |
| Changelog and semver | `package-spec` skill |
| Tests (`_dev/test/`) | `integration-testing` skill |
| CEL *program* logic | `cel-programs` skill |

This file covers only what those do not: input classification, federation vars,
`iac_template_url`, `auth.aws` / `use_cloud_connectors`, and input gating.

Kibana renders the IAM role via IaC Provider from `provider_permissions`. The
static `federated-identity-aws.yml` CFT in elastic/cloudbeat is the **fallback**
when IaCP returns 422/502. Both must grant the same actions.

> **Legacy CFT URL.** The first `aws` rollout shipped
> `cloudformation-cloud-connectors-guardduty-*.yml` with
> `&param_ElasticResourceId=RESOURCE_ID`. Once the external ID left the trust
> model, that was replaced by
> `cloudformation-federated-identity-aws-<version>.yml` with no parameter. Every
> shipped package now uses the new URL — if you see the GuardDuty URL, replace it.

---

## Pre-flight

Read `packages/<PACKAGE>/manifest.yml`. Record `format_version` and Kibana/agent
conditions against the floors in `var-groups-and-provider-permissions.md`.
Shortfalls are bumped under **Floors and hygiene**, not blockers here.

### Classify inputs

Federation and agentless are different gates. Bucket every input:

| Bucket | Meaning | Examples | Action |
|--------|---------|----------|--------|
| **Federation-eligible** | Agentless **and** Identity Federation (`use_cloud_connectors`) | `cel`, `httpjson`, `aws/metrics` (`*metrics`), `aws-cloudwatch` | Stay visible under Identity Federation |
| **Not agentless** | Needs a local agent/runtime, or no Cloud Connectors support | `aws-s3`, `awsfargate/metrics` | `deployment_modes: ["default"]` |

If **no** input is federation-eligible, stop. Name the blocking type and the
upstream dependency (e.g. `aws-s3` has no `auth.aws` / Cloud Connectors yet).
Agentless-with-access-keys does not make the package federation-eligible.

> **`aws` is the origin, not the reference.** On `main` it still has `aws-s3`
> unpinned inside agentless policy templates (`ec2`, `elb`, `s3`, `guardduty`)
> and declares `provider_permissions` on one input out of ~25 — the rest lean
> on the static cloudbeat CFT. Copy the standalone 2.0 packages (`aws_logs`,
> `aws_mq`, `aws_bedrock`, `aws_securityhub`) for structure; use `aws` only for
> the `cel` / `httpjson` `auth.aws` migrations.

### Audit credential vars

Auth vars live at package level (`aws`) or input level (`aws_securityhub`).
Record which, then classify:

| Bucket | Vars | Fate |
|--------|------|------|
| **Federation-required** | `role_arn` | Add if missing. Always add `supports_identity_federation`. Do **not** add `external_id` — removed with the external-ID-free trust model. |
| **Agentless-compatible** | `access_key_id`, `secret_access_key` | Keep; `direct_access_key` option |
| **Agent-only** | `session_token`, `shared_credential_file`, `credential_profile_name` | Keep; `hide_in_deployment_modes: [agentless]` |
| **Auxiliary** | `assume_role_duration`, `proxy_url`, `ssl`, ... | Leave outside `var_groups` |

If the package has **no** AWS credential vars: confirm the input actually calls
AWS (a local metadata endpoint does not). If it does, ask whether to add the
minimum set (`identity_federation` + `direct_access_key`) and the full
`auth.aws` block. If it does not, stop and flag the package out of rollout.

> Fleet UI rendering of **input-level** vars inside package-level `var_groups`
> is not end-to-end verified. If the UI misbehaves, hoist auth vars to package
> level.

Skip work that is already done: an `identity_federation` option, an existing
`supports_identity_federation` var, or `deployment_modes.agentless.enabled: true`.
Check content, not just key presence.

---

## Floors and hygiene

Bump `format_version` and conditions **before** adding `var_groups` or
`provider_permissions` — exact values are in
`var-groups-and-provider-permissions.md`. Every shipped package carries the
same comment above `conditions.agent.version` — keep it, it explains why the
agent floor is lower than the Kibana floor:

```yaml
  # auth.aws + libbeat cloud connectors on the current ExternalID contract ship in Elastic Agent 9.4.0 (elastic/beats#47260, elastic/beats#47587, elastic/beats#48956).
  agent:
    version: "^9.4.0"
```

Then run `elastic-package lint`.
A jump to 3.6.x turns on pipeline `tag` / `on_failure` validators; land
hygiene as a **separate** PR if lint fails on files this change does not own.

**Escalation — do not silent-bump** if the Kibana floor (`^9.6.0`; agent
`^9.4.0`) would drop a still-supported stack line (e.g. `^8.16.5 || ^9.0.0`).
That is a product decision — every shipped 2.0 package took this route. Suggest:

1. Major-version bump on `main`.
2. Long-running `backport-<package>-<N>.x` from the last release, old floor kept.
3. EPR routes old stacks to the backport, new stacks to `main`.
4. Split PRs: spec bump first, federation second.

Requires CODEOWNERS sign-off before any constraint change. The branching
strategy is written up in the `aws_logs` 2.0.0 PR description.

---

## Manifest changes

### Federation vars

Add next to existing auth vars (same level as the audit):

```yaml
  - name: supports_identity_federation
    type: bool
    title: Supports Identity Federation
    multi: false
    required: false
    show_user: false
  - name: role_arn
    type: text
    title: Role ARN
    multi: false
    required: false
    show_user: false
```

Skip `role_arn` if already declared. Schema for grouping is in
`var-groups-and-provider-permissions.md`. Emit only options whose vars
this package declares:

| Option | Vars | Visibility |
|--------|------|------------|
| `identity_federation` | `role_arn`, `supports_identity_federation` | `hide_in_deployment_modes: [default]`; `provider: aws` |
| `direct_access_key` | `access_key_id`, `secret_access_key` | Always visible |
| `temporary_access_key` | + `session_token` | Hide in agentless |
| `assume_role` | `role_arn` | Hide in agentless |
| `shared_credentials` | `shared_credential_file`, `credential_profile_name` | Hide in agentless |
| `default_credentials` | *(none — SDK default chain)* | Hide in agentless; optional, present on `aws` `main` |

`assume_role_external_id` was removed with the external ID; do not emit it.

On `identity_federation`, set `iac_template_url` (replace
`<KIBANA_FLOOR_MINOR>` with the package Kibana floor, currently `9.6.0`).
No `param_ElasticResourceId` — the external ID / `RESOURCE_ID` pre-fill was
removed with the external-ID-free trust model:

```text
https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate?templateURL=https://elastic-cspm-cft.s3.eu-central-1.amazonaws.com/cloudformation-federated-identity-aws-<KIBANA_FLOOR_MINOR>.yml
```

The URL 404s until cloudbeat publishes the template — note that in the
integrations PR. Extra credential vars that match no row: propose an
agent-only option and flag for review.

### Agentless deployment

Skip if already enabled. Enabling it is a product decision — get owning-team
sign-off. On each target policy template:

```yaml
    deployment_modes:
      default:
        enabled: true
      agentless:
        enabled: true
        release: beta             # or ga; evaluated in Kibana 9.5.0+
        organization: <org>
        division: engineering
        team: <owning-team>
```

Pin **Not agentless** inputs (including `aws-s3`) with `deployment_modes: ["default"]`
— this is what the shipped packages do.

### Input gating

`hide_in_var_group_options` hides an input when a given `var_groups` option is
selected. The first `aws` rollout used it on 13 inputs, then removed every
instance once those inputs became federation-eligible. No shipped package uses
it today. Reach for it only for an input that is agentless-capable but cannot
use Cloud Connectors — and flag that in the PR, since it is an unproven path:

```yaml
      - type: <input>
        hide_in_var_group_options:
          credential_type: [identity_federation]
```

Never combine it with `deployment_modes: ["default"]` — a pinned input never
sees the Identity Federation option.

### `provider_permissions`

Declare at the narrowest level; schema is in
`var-groups-and-provider-permissions.md`. Derive actions from the collector's
real API calls — authorization names can differ from operation names.

> `aws_securityhub` calls `GetFindingsV2` but IAM is `securityhub:GetFindings`.
> "Correcting" it to `securityhub:GetFindingsV2` breaks the role.

Prefer the minimal read-only set. Cite the AWS API Reference in the PR.

---

## Stream template

Two shapes, decided by input type. Both gate `use_cloud_connectors` on
`supports_identity_federation`.

**`cel` / `httpjson`** — nested `auth.aws:` block (as in the `aws` `config` CEL
stream and its `guardduty` / `inspector` / `securityhub_*` HTTPJSON streams).
If `auth.aws:` exists, append only the `supports_identity_federation` clause;
otherwise add the block, dropping `{{#if}}` clauses for undeclared vars:

```handlebars
auth.aws:
{{#if access_key_id}}
  access_key_id: {{access_key_id}}
{{/if}}
{{#if secret_access_key}}
  secret_access_key: {{secret_access_key}}
{{/if}}
{{#if session_token}}
  session_token: {{session_token}}
{{/if}}
{{#if shared_credential_file}}
  shared_credential_file: {{shared_credential_file}}
{{/if}}
{{#if credential_profile_name}}
  credential_profile_name: {{credential_profile_name}}
{{/if}}
{{#if role_arn}}
  role_arn: {{role_arn}}
{{/if}}
{{#if assume_role_duration}}
  assume_role.duration: {{assume_role_duration}}
{{/if}}
{{#if assume_role_expiry_window}}
  assume_role.expiry_window: {{assume_role_expiry_window}}
{{/if}}
{{#if supports_identity_federation}}
  use_cloud_connectors: {{supports_identity_federation}}
{{/if}}
```

**`aws-cloudwatch` / `aws/metrics`** — no `auth.aws:` block. These inputs read
credentials at the top level (Beats shared `ConfigAWS`); add one clause next to
the existing `role_arn`:

```handlebars
{{#if role_arn}}
role_arn: {{role_arn}}
{{/if}}
{{#if supports_identity_federation}}
use_cloud_connectors: {{supports_identity_federation}}
{{/if}}
```

Do not wrap CloudWatch or metrics credentials in `auth.aws:` — those inputs
expect them at the top level.

---

## Tests and changelog

Search `_dev/test/` for credential-gate assertions and rendered `policy/`
snapshots. Tests that asserted a hand-rolled "access_key required" message
break when `auth.aws` removes that gate — rewrite to the program's stable
error wrapper (not environment-dependent AWS exception text). Follow
`integration-testing` for how to author those tests.

**Policy test per federated stream.** Add
`_dev/test/policy/test-<input>-agentless-cloud-connector.yml` for every
stream that gained `use_cloud_connectors`, then generate the `.expected`
snapshot (`aws_logs`, `aws_mq` ship one per stream; the `aws` package has them
only for `guardduty` / `securityhub_*`):

```yaml
input: aws-cloudwatch
vars:
  role_arn: arn:aws:iam::123456789012:role/ElasticAwsLogsReadOnly
  supports_identity_federation: true
  default_region: us-east-1
data_stream:
  vars:
    log_group_name_prefix: /aws/custom/logs
    region_name: us-east-1
```

A `test-<input>-legacy-credentials.yml` sibling (access keys, no federation)
is optional but cheap — `aws` `guardduty` / `securityhub_*` have them.
Regenerate all existing policy snapshots after hbs changes.

**Completeness check before opening the PR:** list every stream template under
every agentless-enabled policy template. Each **federation-eligible** one
(`cel`, `httpjson`, `aws-cloudwatch`, `aws/metrics`) must render
`use_cloud_connectors`; pinned inputs such as `aws-s3` must not. Sampling is
how `aws` 7.2.0 missed two `aws/metrics` streams and shipped an AccessDenied
regression
([elastic/integrations#21058](https://github.com/elastic/integrations/pull/21058)).

Changelog on a **major** bump is two entries: a `breaking-change` for the
floors ("Raise the minimum required Kibana version to 9.6.0 and Elastic Agent
version to 9.4.0 … the 1.x line is reserved for backports serving older
stacks") and an `enhancement` for the Identity Federation enablement — every
2.0 package uses this pair. State both floors with their own values: the 2.0.0
packages wrote "Kibana and Elastic Agent versions to 9.6.0" and then needed a
2.0.1 `bugfix` entry when the agent floor was lowered to 9.4.0. **Minor** bump,
`enhancement` only, when the Kibana/agent floors do not change. **Major** when
the floor jump drops a still-supported stack line, paired with a
`backport-<package>-<N>.x` branch. Follow the `package-spec` skill. Call out
first-time agentless enablement separately.

---

## Out of repo (conditional)

**elastic/cloudbeat** — mirror `provider_permissions` into
`deploy/cloudformation/federated-identity-aws.yml` as a **separate** PR (one
per integration, incremental, never granting ahead of a declaration). Inline
`permissions` become `AWS::IAM::Policy` resources (`Elastic` prefix);
`roles` append to `ManagedPolicyArns`. Validate with `cfn-lint`. Do not make
the integrations PR depend on an unpublished template.

**elastic/kibana** — skip by default (standalone connector). Only add the
package to `CLOUD_CONNECTOR_PERMISSION_ALLOWLIST` in
`x-pack/platform/plugins/shared/fleet/common/constants/cloud_connector.ts`
if it must **share** a connector with an existing policy group.

---

## Checklist

- [ ] `elastic-package lint` and `build` clean
- [ ] Fleet UI: Identity Federation visible in agentless, hidden in default
- [ ] Ineligible inputs (e.g. `aws-s3`) pinned with `deployment_modes: ["default"]`, so they never appear in agentless
- [ ] Every federation-eligible stream template (`cel`, `httpjson`, `aws-cloudwatch`, `aws/metrics`) under every agentless policy template renders `use_cloud_connectors`; pinned inputs (`aws-s3`) do not (enumerate, do not sample)
- [ ] `provider_permissions` declared on every federation-eligible input (or at the narrowest covering level)
- [ ] One `test-<input>-agentless-cloud-connector.yml` policy fixture per federated stream, `.expected` regenerated
- [ ] Changelog bump matches the floor change (minor if floors unchanged; major + `backport-<package>-<N>.x` if a stack line is dropped); CODEOWNERS confirmed
- [ ] Integrations PR title `[<package>] Enable Identity Federation for agentless deployments`; link a shipped reference PR; note the cloudbeat CFT publish dependency
- [ ] IAM actions match real API calls (and the cloudbeat CFT, if that PR exists)
- [ ] E2E on real AWS (mocks do not verify SigV4); include a regression line for legacy credential paths
