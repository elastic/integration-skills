---
name: federate-aws-integration
description: >
  Enable Federated Identity (Cloud Connectors) on an agentless-eligible AWS
  integration package in elastic/integrations. Use when asked to "add federation
  to <package>", "enable Identity Federation on <package>", or to repeat the
  pattern proven on the `aws` package for another AWS integration. Template
  generation is handled by the IaC Provider (IaCP) — no static CFT URL is used.
  Produces manifest edits, provider_permissions declarations, agent-template
  patches, a changelog entry, and a validation checklist.
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# federate-aws-integration

## When to use

Use this skill when tasks include:
- Adding Federated Identity (Cloud Connectors) auth to an agentless AWS integration package
- Enabling agentless deployment on a package as a prerequisite for federation
- Repeating the var_groups / auth.aws / provider_permissions pattern proven on the `aws` package
- Determining whether a package's inputs are eligible for federation

Template generation is IaC Provider (IaCP)-driven. The `cloud-iac-provisioner`
service renders IAM role templates dynamically at onboard time from the
package's declared `provider_permissions`. Do **not** add a static
CloudFormation quick-create URL (`iac_template_url`) for packages added via
this skill — that belongs to the older static-CFT flow.

> **Warning when reading the `aws` package as a reference:** its
> `identity_federation` var_groups option carries an `iac_template_url`
> pointing at a static GuardDuty CFT. That is the legacy flow — do not copy
> that key into new packages.

## Background

- Pattern source: the `aws` package (var_groups landed in elastic/integrations#19828)
- Kibana IaCP broker route: `POST /internal/fleet/iac_provider/render_template`
- Tracking (2026): elastic/ingest-dev#8812 (per-package rollout), elastic/ingest-dev#8804 (this skill)

---

## 0 — Pre-flight checks

Before touching any file, run these checks and stop with an explanation if any fail.

### 0.1 Fetch the package manifest

```bash
cat packages/<PACKAGE>/manifest.yml
```

Confirm:

| Check | Required | Why |
|---|---|---|
| `format_version` | `>= 3.6.4` | `var_groups` requires 3.6.0; `provider_permissions` requires 3.6.4 |
| `conditions.kibana.version` | `^9.4.0` or higher | `auth.aws` requires Agent 9.4.0+ |
| `conditions.agent.version` | `^9.4.0` or higher | same |

Constraints that are too low get bumped as part of §1 — note them now.

> **Escalation: the bump would abandon users on a supported stack.** If the
> current Kibana constraint covers a stack line that the new `^9.4.0` floor
> drops (e.g. `^8.16.5 || ^9.0.0` — all 8.x users lose updates), do NOT bump
> silently; that is a product decision. Report it and suggest the branching
> strategy from elastic/ingest-dev#8788 ("The Path Forward for Identity
> Federation"), proven on the `aws` package:
>
> 1. Bump the package **major version** on `main`, freeing the previous
>    major's version namespace for a backport branch.
> 2. Cut a long-running `backport-<package>-<N>.x` branch from the last
>    release commit. It keeps the old `format_version` and Kibana floor and
>    carries both patch **and** minor fixes for old-stack users.
> 3. EPR version routing does the rest: old stacks resolve the backport
>    line, new stacks resolve `main`.
> 4. Split the PRs: the major/spec bump lands separately from the
>    federation (`var_groups`) change.
>
> This needs sign-off from every team in the package's CODEOWNERS before any
> constraint changes.

> **Expect new validators to fire on old files.** A `format_version` jump can
> activate stricter semantic validation (e.g. pipeline processors requiring
> `tag`, `on_failure` message format) against files this skill never touches.
> Before making any federation edits, apply only the `format_version` bump
> and run `elastic-package lint` to size the cleanup — on `aws_securityhub`,
> the 3.5.0 → 3.6.4 bump surfaced 514 pre-existing pipeline violations. Land
> those as a separate mechanical "pipeline hygiene" PR first (precedent:
> elastic/integrations#19824 for the `aws` package), then rebase the
> federation change on top.

### 0.2 Identify agentless-eligible inputs

Only these input types can run agentless and therefore support federation:

- `cel`
- `httpjson`
- `aws/metrics` (any `*metrics` variant)
- `aws-cloudwatch`

**Not eligible:** `aws-s3`, `awsfargate/metrics`, and any other unlisted type.

For each policy template, list every input and mark it eligible (E) or
ineligible (I). You will use this list in §2, §3, and §4.

If **no** inputs are eligible, federation cannot be added — stop. The report
must be actionable, not just negative: name each blocking input type and the
upstream dependency that would unblock it. Example, for an `aws-s3`-only
package:

> `<package>` cannot be federated: its only input is `aws-s3`, which does not
> run agentless. Blocked until the `aws-s3` input supports agentless
> deployments; no package-level change can work around that.

### 0.3 Audit the credential vars

Find where the AWS auth vars are declared. Packages differ:

- **Package level** (top-level `vars:`) — e.g. the `aws` package
- **Input level** (`policy_templates[].inputs[].vars`) — e.g. `aws_securityhub`

`var_groups` options may reference vars declared at any of these levels (the
package-spec validator collects package, policy_template, and input vars).
Record which shape this package uses — §1 depends on it.

Then classify every existing credential var into one of four buckets:

| Bucket | Vars | Fate |
|---|---|---|
| **Federation-required** | `role_arn`, `external_id` | Must exist — add any that are missing (§1.1). `supports_identity_federation` is always added new. |
| **Agentless-compatible** | `access_key_id`, `secret_access_key` | Kept; form the `direct_access_key` option, visible in both modes. |
| **Agent-only** | `session_token`, `shared_credential_file`, `credential_profile_name` | Kept; grouped into options with `hide_in_deployment_modes: [agentless]` (§1.2). |
| **Auxiliary / non-credential** | `assume_role_duration`, `assume_role_expiry_window`, `proxy_url`, `ssl`, ... | Left outside `var_groups` entirely — they are tuning knobs, not credential selectors. |

The output of this audit drives §1.1 (what to add) and §1.2 (which var_group
options to emit). If federation-required vars are missing, copy their
definitions from the `aws` package (same names, types, `show_user: false`,
`required: false` — the var_group controls requirement).

**If the audit finds NO AWS credential vars at all** (no access keys, no
`role_arn`, no `auth.aws` block in any stream template), do not proceed
silently and do not hard-abort. First verify whether the underlying input
actually supports AWS authentication:

1. Check the input's beats module / agent implementation: does it consume
   `auth.aws` (or equivalent AWS credential config) at all? An input that
   reads a local endpoint (e.g. `awsfargate/metrics` reading the ECS task
   metadata endpoint from inside the task) makes no AWS API calls — added
   credential vars would be dead configuration.
2. **If the input supports AWS auth** but the package never exposed the
   vars: **ask the user** whether to add the minimum required credential
   var set for agentless + Federated Identity:
   - `role_arn`, `external_id`, `supports_identity_federation`
     (the `identity_federation` option)
   - `access_key_id`, `secret_access_key` (the `direct_access_key` option —
     the only other option visible in agentless mode)

   On yes: add these per §1.1, emit only those two var_group options in
   §1.2, and add the full `auth.aws` block to the stream templates per §4.
3. **If the input does not support AWS auth**: stop with an actionable
   report naming the input and why scaffolding vars would be dead config —
   and flag the package for removal from the rollout scope if an issue
   lists it.

> **Unverified assumption:** the package-spec validator accepts input-level
> var references, but Fleet UI rendering of var_groups against input-level
> vars has not been end-to-end verified. If the UI misbehaves, fall back to
> hoisting the auth vars to the package level.

### 0.4 Check for existing structures

- If `var_groups:` already exists, skip §1.2.
- If `supports_identity_federation` already exists as a var, skip §1.1.
- If `deployment_modes.agentless.enabled: true` already exists on the target
  policy templates, skip §1.4.

---

## 1 — Package `manifest.yml` changes

### 1.1 Add missing federation vars

Add these **alongside the existing auth vars** (same level — package or input,
per §0.3), after the last auth var.

Always add:

```yaml
  - name: supports_identity_federation
    type: bool
    title: Supports Identity Federation
    multi: false
    required: false
    show_user: false
```

If the §0.3 audit found `role_arn` or `external_id` missing, add them too:

```yaml
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

### 1.2 Add `var_groups`

After the `vars:` list (or after `format_version`-level metadata if there are
no package vars) and before `policy_templates:`, add:

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
      - name: direct_access_key
        title: Direct Access Keys
        vars: [access_key_id, secret_access_key]
      - name: temporary_access_key
        title: Temporary Access Keys
        vars: [access_key_id, secret_access_key, session_token]
        hide_in_deployment_modes: [agentless]
      - name: assume_role
        title: Assume Role
        vars: [role_arn]
        hide_in_deployment_modes: [agentless]
      - name: assume_role_external_id
        title: Assume Role with External ID
        vars: [role_arn, external_id]
        hide_in_deployment_modes: [agentless]
      - name: shared_credentials
        title: Shared Credentials
        vars: [shared_credential_file, credential_profile_name]
        hide_in_deployment_modes: [agentless]
```

Build the options list from the §0.3 audit, not by copying blindly:

- Emit only options whose vars the package actually declares (e.g. drop
  `shared_credentials` if there is no `shared_credential_file` var).
- Every **agent-only** option carries `hide_in_deployment_modes: [agentless]`
  — that is the grouping for agent-based deployments. Users on the default
  (agent) path keep every credential method they had before; agentless users
  see only Identity Federation and Direct Access Keys.
- **Auxiliary** vars from the audit (`assume_role_duration`, `proxy_url`,
  `ssl`, ...) stay outside `var_groups` — do not force them into an option.
- If the package has extra credential vars that don't match any canonical
  option (rare), propose a new agent-only option named after the credential
  method, with `hide_in_deployment_modes: [agentless]`, and flag it for
  reviewer attention in the PR.

Rules enforced by the package-spec validator:
- Every name in `options[].vars` must exist as a var (any level).
- Vars referenced by a var_group **must not have `required: true`** —
  requirement is controlled by the var_group itself.

Note: `iac_template_url` is intentionally omitted from `identity_federation`.
Template generation is handled by the IaC Provider at onboard time.

### 1.3 Bump `format_version` and conditions

- `format_version: 3.6.4` (or newer)
- Conditions floor:

```yaml
conditions:
  kibana:
    version: "^9.4.0"
  # auth.aws support in CEL and HTTPJSON inputs requires Elastic Agent 9.4.0+.
  agent:
    version: "^9.4.0"
```

### 1.4 Refactor for agentless deployment (if not already enabled)

Federation is only offered on the agentless path. If the package has no
agentless support yet, refactor it:

**a. Enable agentless on each target policy template:**

```yaml
    deployment_modes:
      default:
        enabled: true
      agentless:
        enabled: true
        release: beta             # or ga; evaluated in Kibana 9.5.0+
        organization: <org>       # e.g. security
        division: engineering
        team: <owning-team>       # from CODEOWNERS
```

Optional fields: `is_default: true` (make agentless the default mode when both
are offered) and `resources.requests.{memory,cpu}` if the workload needs more
than the platform default.

**b. Restrict ineligible inputs to agent-based mode.** When a policy template
mixes eligible and ineligible inputs (per §0.2), pin each ineligible input
with input-level `deployment_modes`:

```yaml
      - type: aws-s3
        title: Collect <Package> logs from AWS S3 or SQS
        description: Collecting <Package> logs via AWS S3/SQS.
        deployment_modes: ["default"]
```

Inputs without this key are offered in all deployment modes — leave eligible
inputs unrestricted.

Enabling agentless is itself a reviewable product decision — the owning team
commits to operating fully-managed deployments of this integration. Call it
out explicitly in the PR description rather than burying it in the federation
change, and get the owning team's sign-off before shipping.

---

## 2 — Policy template input gating

For every **ineligible** input (from §0.2) inside every policy template, add
`hide_in_var_group_options` directly under the input's `description` line:

```yaml
      - type: aws-s3
        title: Collect <Package> logs from AWS S3 or SQS
        description: Collecting <Package> logs via AWS S3/SQS.
        hide_in_var_group_options:
          credential_type: [identity_federation]
```

Leave eligible inputs (`cel`, `httpjson`, `aws/metrics`, `aws-cloudwatch`)
without this key — they must remain visible when Identity Federation is selected.

**Two distinct gates — don't conflate them:**

| Situation | Mechanism |
|---|---|
| Input runs agentless but doesn't support federation (e.g. `aws-s3` with access keys) | `hide_in_var_group_options: credential_type: [identity_federation]` (this section) |
| Input can't run agentless at all | `deployment_modes: ["default"]` on the input (§1.4b) |

An input pinned to `["default"]` never sees the Identity Federation option
anyway (it's hidden in default mode), so it doesn't also need the
`hide_in_var_group_options` gate.

---

## 3 — Declare `provider_permissions`

The IaCP renders the IAM role template from these declarations — they are the
source of truth for what the generated role can do. Requires
`format_version >= 3.6.4`.

`provider_permissions` may be declared at package, policy_template, input, and
data_stream levels; entries across levels are accumulated and deduplicated.
Declare each permission at the **narrowest level that needs it**:

```yaml
# Input-level example (aws_securityhub's cel input):
      - type: cel
        title: Collect AWS Security Hub logs via API
        description: Collecting AWS Security Hub logs via API.
        provider_permissions:
          - provider: aws
            description: Security Hub read access for findings collection.
            permissions:
              - name: securityhub:GetFindings
```

Optional `roles` attach managed policies alongside inline permissions:

```yaml
        provider_permissions:
          - provider: aws
            description: Read-only security auditing.
            roles:
              - name: SecurityAudit
                id: arn:aws:iam::aws:policy/SecurityAudit
            permissions:
              - name: securityhub:GetFindings
```

To determine the correct IAM actions, check the input's actual API calls
(agent stream template, CEL program, or beats module docs) — do not guess.
Prefer the minimal read-only set.

---

## 4 — Agent stream template (`*.yml.hbs`) changes

For each eligible input's agent stream template at
`data_stream/<name>/agent/stream/<input>.yml.hbs`, append the federation hook
at the very end of the `auth.aws:` block:

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

If the template already has an `auth.aws:` block, append only the final
three-line `{{#if supports_identity_federation}}` block. If there is no
`auth.aws:` block, add the entire block, trimming `{{#if}}` clauses for vars
the package doesn't declare.

---

## 5 — Kibana policy-group membership (conditional)

Kibana's Fleet plugin keeps `CLOUD_CONNECTOR_PERMISSION_ALLOWLIST`
(`x-pack/platform/plugins/shared/fleet/common/constants/cloud_connector.ts`).
This is **not a render gate** — a package absent from it still renders fine,
standalone, with its own cloud connector.

What it controls is **connector sharing**: integrations in the same policy
group share one cloud connector, so the rendered template must grant the whole
group's permissions at once.

- **New package should have its own standalone connector** (the default):
  no Kibana change needed. Skip this section.
- **New package should share a connector with an existing group** (e.g. join
  `aws_global_policy_group`): open a Kibana PR adding an entry:

```typescript
aws_global_policy_group: [
  { provider: AWS_CLOUD_PROVIDER, package: 'aws', policyTemplate: 'guardduty' },
  { provider: AWS_CLOUD_PROVIDER, package: '<package>', policyTemplate: '<policy_template>' },
],
```

If in doubt, ship standalone first — group membership can be added later.

---

## 6 — Changelog entry

Bump the package **minor version** (e.g. `1.2.0` → `1.3.0`) and prepend to
`changelog.yml`:

```yaml
- version: "X.Y.0"
  changes:
    - description: Enable Identity Federation (Cloud Connectors) authentication for agentless deployments.
      type: enhancement
      link: https://github.com/elastic/integrations/pull/<PR_NUMBER>
```

Also update `version:` in `manifest.yml` to match. If §1.4 enabled agentless,
add a separate changelog entry for it.

---

## 7 — Validation checklist

- [ ] `elastic-package lint` — no errors (validates var_groups references and provider_permissions shape)
- [ ] `elastic-package build` — package builds cleanly
- [ ] The Fleet UI agentless path shows the Identity Federation credential option
- [ ] The Fleet UI default path hides the Identity Federation option
- [ ] Ineligible inputs (`aws-s3`, etc.) do not appear when Identity Federation is selected
- [ ] On serverless, onboard via Identity Federation: IaCP renders the IAM role template from the declared provider_permissions, user deploys, data arrives in the target data stream
- [ ] Deployed role's policy matches the declared provider_permissions (no missing actions at collection time)

---

## 8 — PR checklist

**elastic/integrations PR:**
- [ ] Title: `[<package>] Enable Identity Federation for agentless deployments`
- [ ] Body links to the tracking issue for the rollout
- [ ] Agentless enablement (if part of this PR) called out explicitly
- [ ] `changelog.yml` entry added with correct version bump
- [ ] CODEOWNERS confirmed for this package

**elastic/kibana PR** (only if joining a policy group, §5):
- [ ] Adds package to `CLOUD_CONNECTOR_PERMISSION_ALLOWLIST`
- [ ] Links to the integrations PR
