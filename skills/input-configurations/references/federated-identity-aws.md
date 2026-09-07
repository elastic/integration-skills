# Federated Identity for AWS integrations

Procedure for enabling Federated Identity (Cloud Connectors) on an
agentless-eligible, **single-provider (AWS-only)** integration. Pattern:
`aws` package (elastic/integrations#19828, #20527, #20529); end state on
standalone packages: `aws_logs` (#20823), `aws_mq` (#20817),
`aws_bedrock` (#20822). Rollout: elastic/ingest-dev#8812.

Multi-cloud packages (e.g. `kubernetes`, elastic/integrations#20824) hit
platform limits tracked in elastic/ingest-dev#9382 — out of scope here.

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

> **Legacy CFT URL.** #19828 shipped `cloudformation-cloud-connectors-guardduty-*.yml`
> with `&param_ElasticResourceId=RESOURCE_ID`. elastic/integrations#20527 replaced it
> with `cloudformation-federated-identity-aws-<version>.yml` and dropped the parameter
> (external ID removed; elastic/cloudbeat#7637, elastic/kibana#284522). Every shipped
> package now uses the new URL — if you see the GuardDuty URL, replace it.

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
| **Not agentless** | Needs a local agent/runtime, or no Cloud Connectors support | `aws-s3`, `awsfargate/metrics` | `deployment_modes: ["default"]` (`aws_logs` #20823, `aws_bedrock_agentcore` #20821) |

If **no** input is federation-eligible, stop. Name the blocking type and the
upstream dependency (e.g. `aws-s3` has no `auth.aws` / Cloud Connectors yet).
Agentless-with-access-keys does not make the package federation-eligible.

### Audit credential vars

Auth vars live at package level (`aws`) or input level (`aws_securityhub`).
Record which, then classify:

| Bucket | Vars | Fate |
|--------|------|------|
| **Federation-required** | `role_arn` | Add if missing. Always add `supports_identity_federation`. Do **not** add `external_id` — removed with the external-ID-free trust model (elastic/integrations#20527). |
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
`var-groups-and-provider-permissions.md`. Then run `elastic-package lint`.
A jump to 3.6.x turns on pipeline `tag` / `on_failure` validators; land
hygiene as a **separate** PR if lint fails on files this change does not own
(precedent: elastic/integrations#19824).

**Escalation — do not silent-bump** if the Kibana floor (`^9.6.0`; agent `^9.4.0`,
elastic/integrations#21007) would drop a still-supported stack line (e.g.
`^8.16.5 || ^9.0.0`). That is a product decision — every shipped 2.0 package took
this route (`aws_logs` #20823, `aws_mq` #20817, `aws_bedrock` #20822). Suggest:

1. Major-version bump on `main`.
2. Long-running `backport-<package>-<N>.x` from the last release, old floor kept.
3. EPR routes old stacks to the backport, new stacks to `main`.
4. Split PRs: spec bump first, federation second.

Requires CODEOWNERS sign-off before any constraint change. See
elastic/ingest-dev#8788.

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
this package declares (shipped set: `aws_logs` #20823, `aws_mq` #20817):

| Option | Vars | Visibility |
|--------|------|------------|
| `identity_federation` | `role_arn`, `supports_identity_federation` | `hide_in_deployment_modes: [default]`; `provider: aws` |
| `direct_access_key` | `access_key_id`, `secret_access_key` | Always visible |
| `temporary_access_key` | + `session_token` | Hide in agentless |
| `assume_role` | `role_arn` | Hide in agentless |
| `shared_credentials` | `shared_credential_file`, `credential_profile_name` | Hide in agentless |
| `default_credentials` | *(none — SDK default chain)* | Hide in agentless; optional, present on `aws` `main` |

`assume_role_external_id` was removed with the external ID (elastic/integrations#20527); do not emit it.

On `identity_federation`, set `iac_template_url` (replace
`<KIBANA_FLOOR_MINOR>` with the package Kibana floor, currently `9.6.0`).
No `param_ElasticResourceId` — the external ID / `RESOURCE_ID` pre-fill was
removed in elastic/integrations#20527 (elastic/kibana#284522, elastic/cloudbeat#7637):

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
— this is what `aws_logs` (elastic/integrations#20823) and `aws_bedrock_agentcore`
(#20821) ship.

### Input gating

`hide_in_var_group_options` hides an input when a given `var_groups` option is
selected. #19828 used it on 13 `aws` inputs; #20527 removed every instance once
those inputs became federation-eligible. No shipped package uses it today. Reach
for it only for an input that is agentless-capable but cannot use Cloud
Connectors — and flag that in the PR, since it is an unproven path:

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

**`cel` / `httpjson`** — nested `auth.aws:` block (`aws` `config` CEL and
`guardduty` / `inspector` / `securityhub_*` HTTPJSON; elastic/integrations#19828,
#20527, #20529). If `auth.aws:` exists, append only the `supports_identity_federation`
clause; otherwise add the block, dropping `{{#if}}` clauses for undeclared vars:

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
the existing `role_arn` (`aws_logs` #20823, `aws_mq` #20817, `aws` #20527, #21058):

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
error wrapper (not environment-dependent AWS exception text). Regenerate
policy snapshots after hbs changes. Follow `integration-testing` for how to
author those tests.

Changelog: `enhancement`. **Minor** bump when the Kibana/agent floors do not
change. **Major** bump when the floor jump drops a still-supported stack line
(shipped: `aws` 6.20.3 → 7.0.0 #19828; `aws_logs` 1.8.3 → 2.0.0 #20823;
`aws_mq` 1.0.0 → 2.0.0 #20817; `aws_bedrock` #20822), paired with a
`backport-<package>-<N>.x` branch per elastic/ingest-dev#8788. Follow the
`package-spec` skill. Call out first-time agentless enablement separately.

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
- [ ] Changelog bump matches the floor change (minor if floors unchanged; major + `backport-<package>-<N>.x` if a stack line is dropped, see #20823 / #20817); CODEOWNERS confirmed
- [ ] Integrations PR title `[<package>] Enable Identity Federation for agentless deployments`; link elastic/ingest-dev#8812; note the cloudbeat CFT publish dependency
- [ ] IAM actions match real API calls (and the cloudbeat CFT, if that PR exists)
- [ ] E2E on real AWS (mocks do not verify SigV4); include a regression line for legacy credential paths
