# CDR field requirements

Cloud Detection & Response (CDR) fields apply **only** to cloud security integrations -- those covering CSPM, CWPP, or vulnerability management use cases (e.g., `aws_security_hub`, `google_scc`, `prisma_cloud`, `wiz`). Do NOT flag missing CDR fields on non-cloud-security integrations such as general logging, metrics, APM, or non-security cloud integrations.

Aligned with: Elastic CDR 3P Developer Guide v1.0

## Finding types and event categorization

| Type | `event.kind` | `event.category` | `event.type` | Key fields |
|------|-------------|------------------|-------------|------------|
| Misconfiguration | `state` | `configuration` | `info` | `result.evaluation`, `resource.*`, `rule.*` |
| Vulnerability | `state` | `vulnerability` | `info` | `vulnerability.*`, `package.*`, `resource.*` |
| Runtime detection | `alert` | varies | varies | `rule.*`, `threat.*` |

## Misconfiguration finding fields

Fields are listed by importance tier. Must Have fields cause critical UI breakage if missing.

### Must Have

| Field | Type | ECS | Purpose |
|-------|------|-----|---------|
| `@timestamp` | date | yes | Base field |
| `event.ingested` | date | yes | Set by Elasticsearch final pipeline -- do NOT set in integration pipeline. Required for transform sync |
| `event.id` | keyword | yes | Unique identifier for grouping by multi-value fields |
| `data_stream.namespace` | keyword | yes | Required for transform uniqueness and Kibana Space support. **Must be `keyword` (not `constant_keyword`) in the latest index** |
| `resource.id` | keyword | no | Cloud resource ID (e.g., ARN). Transform uniqueness relies on it |
| `resource.name` | keyword | no | Human-readable resource name. Default data grid column |
| `result.evaluation` | keyword | no | `passed`, `failed`, or `unknown`. Used for score calculation |
| `rule.name` | keyword | yes | Pretty name of the evaluation rule. Default column, flyout title |
| `rule.uuid` | keyword | yes | Unique rule identifier. Used for transform uniqueness |
| `observer.vendor` | constant_keyword | yes | Vendor name (e.g., Wiz, Amazon). **Use `constant_keyword` for performance** |
| `user.name` | keyword | yes | For user-related findings, enables entity correlation |
| `host.name` | keyword | yes | For host-related findings, enables entity correlation |

### Should Have

| Field | Type | ECS | Purpose |
|-------|------|-----|---------|
| `cloud.account.id` | keyword | yes | Grouping on Findings page |
| `cloud.provider` | keyword | yes | Must be lowercase: `aws`, `gcp`, `azure` |
| `event.category` | keyword | yes | **Must be `configuration`** |
| `event.kind` | keyword | yes | **Must be `state`** |
| `event.type` | keyword | yes | **Must be `info`** |
| `event.outcome` | keyword | yes | `failure`, `success`, or `unknown` (mirrors `result.evaluation`) |
| `event.created` | date | yes | When the finding was created |
| `resource.type` | keyword | no | Resource type identifier (e.g., `identity-management`) |
| `resource.sub_type` | keyword | no | Resource sub-type (e.g., `aws-nacl`). Default column, billing |
| `rule.description` | keyword | yes | Rule description, shown in flyout |
| `rule.version` | keyword | yes | Rule version, used in telemetry |
| `rule.tags` | keyword | no | Tags for rules (e.g., `[gcp, CIS 3.8]`) |
| `rule.impact` | keyword | no | Impact of misconfiguration, shown in flyout |
| `rule.rationale` | keyword | no | Rationale for the rule |
| `rule.reference` | keyword | yes | Links to documentation |
| `rule.remediation` | keyword | no | Remediation steps |
| `result.evidence` | object | no | Arbitrary evidence object, shown as JSON in flyout |
| `orchestrator.cluster.id` | keyword | yes | K8s cluster ID for grouping |
| `orchestrator.cluster.name` | keyword | yes | K8s cluster name for grouping |

### Benchmark fields (Should Have)

Only when mapping a finding to a benchmark makes sense (1:1 or clear primary).

| Field | Type | ECS | Purpose |
|-------|------|-----|---------|
| `rule.benchmark.name` | keyword | no | Benchmark name (e.g., CIS Google Cloud Platform Foundation) |
| `rule.benchmark.version` | keyword | no | Benchmark version (e.g., 1.9.0) |
| `rule.benchmark.rule_number` | keyword | no | Rule number in benchmark. Provide same value in `rule.id` |
| `rule.id` | keyword | yes | Rule number in benchmark |
| `rule.section` | keyword | no | Benchmark section the rule belongs to |

## Vulnerability finding fields

### Must Have

| Field | Type | ECS | Purpose |
|-------|------|-----|---------|
| `@timestamp` | date | yes | Base field |
| `event.ingested` | date | yes | Set by Elasticsearch final pipeline -- do NOT set in integration pipeline. Required for transform sync |
| `event.id` | keyword | yes | Unique identifier for grouping |
| `event.category` | keyword | yes | **Must be `vulnerability`** |
| `data_stream.namespace` | keyword | yes | **Must be `keyword` (not `constant_keyword`) in the latest index** |
| `resource.id` | keyword | no | Vulnerable resource ID |
| `resource.name` | keyword | no | Vulnerable resource name (e.g., FQDN) |
| `observer.vendor` | constant_keyword | yes | Vendor name. **Use `constant_keyword` for performance** |
| `host.name` | keyword | yes | Host name for entity correlation |
| `package.name` | keyword | yes | Affected package name |
| `vulnerability.id` | keyword | yes | CVE ID. Can be multiple values or empty |
| `vulnerability.severity` | keyword | yes | Must be: `Low`, `Medium`, `High`, `Critical`, or `None` |
| `vulnerability.score.base` | float | yes | CVSS base score |
| `vulnerability.title` | keyword | no | Human-readable vulnerability title |

### Should Have

| Field | Type | ECS | Purpose |
|-------|------|-----|---------|
| `cloud.account.id` | keyword | yes | Grouping on Findings page |
| `cloud.provider` | keyword | yes | Must be lowercase: `aws`, `gcp`, `azure` |
| `event.kind` | keyword | yes | **Must be `state`** |
| `event.type` | keyword | yes | **Must be `info`** |
| `package.version` | keyword | yes | Current package version |
| `package.fixed_version` | keyword | no | Version where vulnerability was fixed |
| `vulnerability.description` | keyword | yes | Vulnerability description |
| `vulnerability.reference` | keyword | yes | Link to vulnerability details |
| `vulnerability.published_date` | date | no | **Needs explicit `date` type mapping** (not covered by `ecs@mappings`) |
| `vulnerability.score.version` | keyword | yes | CVSS version (e.g., 3.1) |
| `vulnerability.scanner.vendor` | constant_keyword | yes | **Use `constant_keyword` for performance** |

## Correlation fields

CDR integrations MUST populate `related.*` fields for threat hunting:

- `related.ip` -- resource IPs, actor IPs
- `related.user` -- IAM users, service accounts
- `related.hash` -- artifact hashes (for CWPP findings)

These are set by the pipeline via `append` processors and auto-mapped from ECS -- they typically do NOT need `fields.yml` entries.

## Field definition examples (fields.yml)

Most CDR fields are set by the pipeline and auto-mapped via ECS. Only define fields in `fields.yml` when they need explicit declaration:

```yaml
# ecs.yml -- ECS fields via external reference
- name: cloud.provider
  external: ecs
- name: cloud.account.id
  external: ecs
- name: rule.name
  external: ecs
- name: rule.uuid
  external: ecs
- name: vulnerability.id
  external: ecs
- name: vulnerability.severity
  external: ecs
- name: observer.vendor
  external: ecs
  type: constant_keyword
- name: vulnerability.scanner.vendor
  external: ecs
  type: constant_keyword

# fields.yml -- non-ECS fields only (no external: ecs here)
- name: vulnerability
  type: group
  fields:
    - name: published_date
      type: date
      description: When the vulnerability was published.
- name: resource
  type: group
  fields:
    - name: id
      type: keyword
      description: Cloud resource ID (e.g., ARN).
    - name: name
      type: keyword
      description: Human-readable resource name.
    - name: type
      type: keyword
      description: Resource type identifier.
    - name: sub_type
      type: keyword
      description: Resource sub-type.
- name: result
  type: group
  fields:
    - name: evaluation
      type: keyword
      description: Evaluation result (passed, failed, unknown).
    - name: evidence
      type: flattened
      description: Arbitrary evidence object for the finding.
- name: rule
  type: group
  fields:
    - name: benchmark
      type: group
      fields:
        - name: name
          type: keyword
          description: Benchmark name (e.g., CIS Google Cloud Platform Foundation).
        - name: version
          type: keyword
          description: Benchmark version.
        - name: rule_number
          type: keyword
          description: Rule number within the benchmark.
    - name: section
      type: keyword
      description: Benchmark section the rule belongs to.
    - name: impact
      type: keyword
      description: Impact of the misconfigured rule.
    - name: rationale
      type: keyword
      description: Rationale for the rule.
    - name: remediation
      type: keyword
      description: Remediation steps for the finding.
- name: package
  type: group
  fields:
    - name: fixed_version
      type: keyword
      description: Package version where the vulnerability was fixed.
```

## CDR field review checklist

### Misconfiguration findings

- [ ] Must Have fields present: `resource.id`, `resource.name`, `result.evaluation`, `rule.name`, `rule.uuid`, `event.id`, `observer.vendor` -- **HIGH** if missing
- [ ] `event.category` set to `configuration`, `event.kind` to `state`, `event.type` to `info` -- **HIGH** if wrong
- [ ] `data_stream.namespace` mapped as `keyword` (not `constant_keyword`) in latest index -- **HIGH** if wrong type
- [ ] `observer.vendor` uses `constant_keyword` type -- **MEDIUM**
- [ ] Benchmark fields present if applicable (`rule.benchmark.name`/`version`/`rule_number`) -- **MEDIUM**
- [ ] `related.*` fields populated by pipeline -- **MEDIUM**

### Vulnerability findings

- [ ] Must Have fields present: `vulnerability.id`, `vulnerability.severity`, `vulnerability.score.base`, `vulnerability.title`, `resource.id`, `resource.name`, `package.name`, `observer.vendor`, `event.id` -- **HIGH** if missing
- [ ] `event.category` set to `vulnerability`, `event.kind` to `state`, `event.type` to `info` -- **HIGH** if wrong
- [ ] `vulnerability.published_date` mapped as `date` type (not covered by `ecs@mappings`) -- **MEDIUM**
- [ ] `vulnerability.scanner.vendor` uses `constant_keyword` type -- **MEDIUM**
- [ ] `package.fixed_version` defined if available from vendor -- **LOW**
- [ ] `data_stream.namespace` mapped as `keyword` in latest index -- **HIGH** if wrong type

### When CDR fields are NOT required

Do NOT flag CDR field issues for:
- General logging or metrics integrations
- APM integrations
- Non-security cloud integrations (e.g., billing, resource inventory without security posture)
- Integrations that do not produce security findings (misconfiguration, vulnerability, or runtime detection)
