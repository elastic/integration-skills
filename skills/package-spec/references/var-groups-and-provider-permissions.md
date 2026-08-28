# `var_groups` and `provider_permissions`

Schema and floors for credential selectors and IAM declarations in `manifest.yml`. This file is the package-spec authority for these constructs.

For the Federated Identity (Cloud Connectors) procedure on an AWS integration, load `input-configurations` -> `references/federated-identity-aws.md`.

## Floors

| Construct | Minimum `format_version` | Notes |
|-----------|--------------------------|-------|
| `var_groups` | 3.6.1 | Credential / setup method selector in Fleet UI |
| `provider_permissions` | 3.6.4 | Declarations that feed IaC Provider IAM role rendering |

Default new packages stay at `3.4.2`. Bump only when introducing these features.

## `var_groups`

Groups related vars into named options so Fleet shows a credential-method selector (e.g. Identity Federation vs access keys).

Typical shape (package level, before `policy_templates:`):

```yaml
var_groups:
  - name: credential_type
    required: true
    title: Setup Access
    selector_title: Preferred method
    options:
      - name: identity_federation
        title: Identity Federation
        vars: [role_arn, external_id, supports_identity_federation]
        hide_in_deployment_modes: [default]
        provider: aws
        iac_template_url: https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate?templateURL=https://elastic-cspm-cft.s3.eu-central-1.amazonaws.com/cloudformation-federated-identity-aws-<KIBANA_FLOOR_MINOR>.yml&param_ElasticResourceId=RESOURCE_ID
      - name: direct_access_key
        title: Direct Access Keys
        vars: [access_key_id, secret_access_key]
```

On `identity_federation`, `iac_template_url` is required for the CloudFormation fallback. Replace `<KIBANA_FLOOR_MINOR>` with the package Kibana floor (e.g. `9.4.0`); keep `RESOURCE_ID` literal. Do **not** copy the `aws` package GuardDuty-only CFT URL — see `input-configurations` -> `references/federated-identity-aws.md`.

Validator rules:
- Every name in `options[].vars` must exist as a var at some level (package, policy template, input, or data stream).
- Vars referenced by a var_group must not have `required: true`.
- Use `hide_in_deployment_modes` so agent-only methods stay hidden in agentless mode (and federation stays hidden in default mode when appropriate).

Related input gating (not part of `var_groups` itself):
- `hide_in_var_group_options` on an input hides that input when a given option is selected.
- Input-level `deployment_modes: ["default"]` pins an input to agent-based mode only.

## `provider_permissions`

Declares the IAM actions (and optional managed roles) the integration needs. The IaC Provider renders the onboard-time IAM role template from these entries. Declare at the narrowest level that needs them (package, policy_template, input, or data_stream); entries accumulate and deduplicate across levels.

```yaml
provider_permissions:
  - provider: aws
    description: Security Hub read access for findings collection.
    permissions:
      - name: securityhub:GetFindings
```

Optional `roles` attach AWS managed policies by ARN alongside inline `permissions`.

Do not guess IAM action names — derive them from the collector's real API calls and verify against the AWS API Reference (authorization names can differ from API operation names).

## Conditions with these features

When a package uses Federated Identity / `auth.aws`:
- `format_version: "3.6.4"`
- `conditions.kibana.version: "^9.4.0"` (or higher)
- `conditions.agent.version: "^9.4.0"` (or higher)

If raising the Kibana floor would abandon a still-supported stack line (e.g. dropping 8.x), escalate — do not silent-bump. See **Floors and hygiene** in `input-configurations` -> `references/federated-identity-aws.md`.

## Handoff

| Need | Where |
|------|-------|
| Schema / floors / validators for these fields | This file + `format-version-features.md` |
| Enable Federated Identity on an AWS package | `input-configurations` -> `references/federated-identity-aws.md` |
| `auth.aws` / `use_cloud_connectors` in stream templates | Same federation reference (**Stream template**); CEL *program* logic stays in `cel-programs` |
