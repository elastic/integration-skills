# CDR pipeline requirements

Cloud Detection & Response (CDR) integrations handle findings from cloud security posture management (CSPM), cloud workload protection (CWPP), and vulnerability management tools. This reference covers the pipeline-side requirements for CDR compliance.

Aligned with: Elastic CDR 3P Developer Guide v1.0

## Event categorization

Correct `event.*` values are critical -- the Kibana Findings page filters on them.

| Finding type | `event.kind` | `event.category` | `event.type` |
|-------------|-------------|------------------|-------------|
| Misconfiguration | `state` | `configuration` | `info` |
| Vulnerability | `state` | `vulnerability` | `info` |
| Runtime detection | `alert` | varies | varies |

Use `append` for `event.category` and `event.type` (they are arrays in ECS). Use `set` for `event.kind` (single value).

## Must Have fields (pipeline must populate)

Missing these causes critical issues in the Kibana Findings UI.

| Field | Purpose |
|-------|---------|
| `resource.id` | Cloud resource ID (e.g., ARN). Transform uniqueness depends on it |
| `resource.name` | Human-readable resource name. Default data grid column |
| `result.evaluation` | `passed`, `failed`, or `unknown` (misconfiguration only) |
| `rule.name` | Rule name for misconfiguration findings |
| `rule.uuid` | Unique rule identifier for transform uniqueness |
| `observer.vendor` | Vendor name (e.g., Wiz, Amazon) |
| `event.id` | Unique event identifier for multi-value grouping |
| `user.name` | For user-related findings (entity correlation) |
| `host.name` | For host-related findings (entity correlation) |

For vulnerability findings additionally:

| Field | Purpose |
|-------|---------|
| `vulnerability.id` | CVE ID |
| `vulnerability.severity` | `Low`, `Medium`, `High`, `Critical`, or `None` |
| `vulnerability.score.base` | CVSS base score |
| `vulnerability.title` | Human-readable vulnerability title |
| `package.name` | Affected package name |

## Should Have fields

| Field | Purpose |
|-------|---------|
| `cloud.provider` | Lowercase: `aws`, `gcp`, `azure` |
| `cloud.account.id` | Account/project/subscription ID |
| `cloud.region` | Region or location |
| `cloud.service.name` | Service generating the finding |
| `event.outcome` | `failure`, `success`, or `unknown` (mirrors `result.evaluation`) |
| `resource.type` | Resource type identifier |
| `resource.sub_type` | Resource sub-type |
| `rule.description` | Rule description for flyout |
| `rule.remediation` | Remediation steps |

## Correlation fields

CDR integrations MUST populate `related.*` fields for threat hunting:

- `related.ip` -- resource IPs, actor IPs
- `related.user` -- IAM users, service accounts
- `related.hash` -- artifact hashes (for CWPP findings)

## Value transformations

- **Severity** -- must be lowercase: `CRITICAL` -> `critical`, `VERY_HIGH` -> `critical`, `MODERATE` -> `medium`
- **Status** -- map vendor values: `ACTIVE` -> `failed`, `INACTIVE`/`ARCHIVED` -> `passed`/`resolved`
- **Account IDs** -- extract from resource paths: `projects/my-project` -> `my-project`

## Pipeline patterns

### Event categorization for misconfiguration

```yaml
- set:
    tag: set_event_kind
    field: event.kind
    value: state
- append:
    tag: append_event_category
    field: event.category
    value: configuration
- append:
    tag: append_event_type
    field: event.type
    value: info
```

### Event categorization for vulnerability

```yaml
- set:
    tag: set_event_kind
    field: event.kind
    value: state
- append:
    tag: append_event_category
    field: event.category
    value: vulnerability
- append:
    tag: append_event_type
    field: event.type
    value: info
```

### Result evaluation mapping

```yaml
- set:
    tag: set_result_evaluation
    field: result.evaluation
    value: failed
    if: ctx.json?.compliance_status == "NON_COMPLIANT"
- set:
    tag: set_result_evaluation
    field: result.evaluation
    value: passed
    if: ctx.json?.compliance_status == "COMPLIANT"
```

### Observer vendor (constant per integration)

```yaml
- set:
    tag: set_observer_vendor
    field: observer.vendor
    value: "Wiz"
```

### Cloud context

```yaml
- set:
    tag: set_cloud_provider
    field: cloud.provider
    value: aws
- set:
    tag: set_cloud_account_id
    field: cloud.account.id
    value: '{{{json.account_id}}}'
```

### Vulnerability fields (conditional on finding type)

```yaml
- set:
    tag: set_vulnerability_id
    field: vulnerability.id
    copy_from: json.cve_id
    if: ctx.json?.finding_type == 'VULNERABILITY'
- set:
    tag: set_vulnerability_severity
    field: vulnerability.severity
    value: '{{{json.severity}}}'
```

## Known CDR integrations

`aws_security_hub`, `google_scc`, `azure_security_center`, `azure_defender`, `prisma_cloud`, `crowdstrike`, `wiz`, `orca`, `snyk`, `lacework`, `tenable`, `qualys`, `rapid7`, `sentinelone`, `sysdig`

Detection indicators in file paths or package names: `security_hub`, `securityhub`, `security_center`, `scc`, `defender`, `cloud_security`, `cspm`, `cnvm`, `cwpp`, `cdr`, `finding`, `findings`, `vulnerability`, `compliance`, `posture`

## CDR pipeline review checklist

### What to flag

- [ ] Missing `event.category`/`event.kind`/`event.type` or wrong values for the finding type -- **HIGH**
- [ ] Missing `resource.id` or `resource.name` (breaks transform and UI) -- **HIGH**
- [ ] Missing `result.evaluation` for misconfiguration findings -- **HIGH**
- [ ] Missing `rule.uuid` (breaks transform uniqueness) -- **HIGH**
- [ ] `event.kind` not set to `state` for posture findings -- **HIGH**
- [ ] No `related.*` fields populated -- **MEDIUM**
- [ ] Missing `observer.vendor` -- **HIGH**
- [ ] Severity not lowercase -- **MEDIUM**
- [ ] Vulnerability fields applied to non-vulnerability findings (must be conditional) -- **MEDIUM**
- [ ] Using `cloud.detection.*` (NOT part of CDR spec -- use `rule.*`, `result.*`) -- **MEDIUM**

### What NOT to flag

CDR pipeline requirements are NOT applicable to:

- General logging or metrics integrations
- APM integrations
- Non-security cloud integrations (e.g., billing, resource inventory without security posture)
- Integrations that do not produce security findings (misconfiguration, vulnerability, or runtime detection)

Do not flag missing CDR fields on these integration types.
