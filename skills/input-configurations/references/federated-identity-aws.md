# Federated Identity for AWS integrations

Procedure for enabling Federated Identity (Cloud Connectors) on an
agentless-eligible AWS integration. Pattern: `aws` package
(elastic/integrations#19828). Rollout: elastic/ingest-dev#8812.

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

> **Do not copy the `aws` package `iac_template_url`.** It still points at the
> legacy GuardDuty-only CFT (`cloudformation-cloud-connectors-guardduty-*.yml`).
> New packages use `cloudformation-federated-identity-aws-<version>.yml`.

---

## Pre-flight

Read `packages/<PACKAGE>/manifest.yml`. Record `format_version` and Kibana/agent
conditions against the floors in `var-groups-and-provider-permissions.md`.
Shortfalls are bumped under **Floors and hygiene**, not blockers here.

### Classify inputs

Federation and agentless are different gates. Bucket every input:

| Bucket | Meaning | Examples | Action |
|--------|---------|----------|--------|
| **Federation-eligible** | Agentless **and** Identity Federation (`auth.aws`) | `cel`, `httpjson`, `aws/metrics` (`*metrics`), `aws-cloudwatch` | Stay visible under Identity Federation |
| **Agentless, not federation** | Agentless with other creds, not Identity Federation | `aws-s3` | **Input gating** — do **not** pin to `deployment_modes: ["default"]` |
| **Not agentless** | Needs a local agent/runtime | `awsfargate/metrics` | `deployment_modes: ["default"]` |

If **no** input is federation-eligible, stop. Name the blocking type and the
upstream dependency (e.g. `aws-s3` has no `auth.aws` / Cloud Connectors yet).
Agentless-with-access-keys does not make the package federation-eligible.

### Audit credential vars

Auth vars live at package level (`aws`) or input level (`aws_securityhub`).
Record which, then classify:

| Bucket | Vars | Fate |
|--------|------|------|
| **Federation-required** | `role_arn`, `external_id` | Add if missing. Always add `supports_identity_federation`. |
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

**Escalation — do not silent-bump** if `^9.4.0` would drop a still-supported
stack line (e.g. `^8.16.5 || ^9.0.0`). That is a product decision. Suggest:

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
  - name: external_id
    type: text
    title: External ID
    multi: false
    required: false
    show_user: false
    secret: true
    description: External ID to use when assuming a role in another account, see [the AWS documentation for use of external IDs](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-user_externalid.html)
```

Skip `role_arn` / `external_id` if already declared. Schema for grouping them
is in `var-groups-and-provider-permissions.md`. Emit only options whose vars
this package declares:

| Option | Vars | Visibility |
|--------|------|------------|
| `identity_federation` | `role_arn`, `external_id`, `supports_identity_federation` | `hide_in_deployment_modes: [default]`; `provider: aws` |
| `direct_access_key` | `access_key_id`, `secret_access_key` | Always visible |
| `temporary_access_key` | + `session_token` | Hide in agentless |
| `assume_role` | `role_arn` | Hide in agentless |
| `assume_role_external_id` | `role_arn`, `external_id` | Hide in agentless |
| `shared_credentials` | `shared_credential_file`, `credential_profile_name` | Hide in agentless |

On `identity_federation`, set `iac_template_url` (replace
`<KIBANA_FLOOR_MINOR>` with the package floor, e.g. `9.4.0`). Keep
`RESOURCE_ID` literal — Kibana substitutes it:

```text
https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate?templateURL=https://elastic-cspm-cft.s3.eu-central-1.amazonaws.com/cloudformation-federated-identity-aws-<KIBANA_FLOOR_MINOR>.yml&param_ElasticResourceId=RESOURCE_ID
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

Pin **Not agentless** inputs with `deployment_modes: ["default"]`. Do **not**
use that pin for **Agentless, not federation** inputs (`aws-s3`).

### Input gating

Hide **Agentless, not federation** inputs when Identity Federation is selected:

```yaml
      - type: aws-s3
        hide_in_var_group_options:
          credential_type: [identity_federation]
```

Leave federation-eligible inputs ungated. An input already pinned to
`["default"]` never sees the Identity Federation option — do not also add
`hide_in_var_group_options`.

### `provider_permissions`

Declare at the narrowest level; schema is in
`var-groups-and-provider-permissions.md`. Derive actions from the collector's
real API calls — authorization names can differ from operation names.

> `aws_securityhub` calls `GetFindingsV2` but IAM is `securityhub:GetFindings`.
> "Correcting" it to `securityhub:GetFindingsV2` breaks the role.

Prefer the minimal read-only set. Cite the AWS API Reference in the PR.

---

## Stream template

For each federation-eligible `data_stream/<name>/agent/stream/<input>.yml.hbs`:

- If `auth.aws:` exists, append only the `supports_identity_federation` block.
- If not, add the block below, dropping `{{#if}}` clauses for undeclared vars.

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
{{#if external_id}}
  external_id: {{external_id}}
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

---

## Tests and changelog

Search `_dev/test/` for credential-gate assertions and rendered `policy/`
snapshots. Tests that asserted a hand-rolled "access_key required" message
break when `auth.aws` removes that gate — rewrite to the program's stable
error wrapper (not environment-dependent AWS exception text). Regenerate
policy snapshots after hbs changes. Follow `integration-testing` for how to
author those tests.

Changelog: minor bump, `enhancement`. Follow the `package-spec` skill. Call
out first-time agentless enablement separately.

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
- [ ] Ineligible inputs hidden when Identity Federation is selected
- [ ] Changelog minor bump; CODEOWNERS confirmed
- [ ] Integrations PR title `[<package>] Enable Identity Federation for agentless deployments`; link elastic/ingest-dev#8812; note the cloudbeat CFT publish dependency
- [ ] IAM actions match real API calls (and the cloudbeat CFT, if that PR exists)
- [ ] E2E on real AWS (mocks do not verify SigV4); include a regression line for legacy credential paths
