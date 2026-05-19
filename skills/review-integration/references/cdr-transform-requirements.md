# CDR transform requirements

Cloud security integrations must implement "latest" transforms that maintain a current-state view of findings. Each CDR data stream needs a latest transform for its finding type.

Aligned with: Elastic CDR 3P Developer Guide v1.0

## Misconfiguration latest transform

### Destination index

```yaml
dest:
  index: "security_solution-<integration>.misconfiguration_latest-<version>"
  aliases:
    - alias: "security_solution-<integration>.misconfiguration_latest"
      move_on_creation: true
```

The alias with `move_on_creation` is required so Kibana always reads from the latest version when the transform is recreated during upgrades.

### Unique key and sort

```yaml
latest:
  unique_key:
    - resource.id
    - rule.uuid
    - data_stream.namespace
  sort: "@timestamp"
```

The combination of `resource.id` + `rule.uuid` + `data_stream.namespace` aligns with the native CSP integration. `rule.uuid` is chosen over `rule.id` because the identifier must be unique across all benchmarks.

The fields above are the baseline. Some integrations vary: google_scc and microsoft_defender_cloud add `event.id` as a fourth key. Evaluate unique key composition case by case based on the source data's natural identity.

### Frequency

5m

### Sync

```yaml
sync:
  time:
    field: event.ingested
```

CDR transforms sync on `event.ingested` (not `@timestamp`) because the fleet final pipeline guarantees this field is set on ingestion. The `delay` field is optional; when omitted, ES defaults to 60s. Most real CDR transforms omit it.

### Retention policy

```yaml
retention_policy:
  time:
    field: "@timestamp"
    max_age: "2160h"
```

CDR sources always have a meaningful `@timestamp` (the finding's event time), so retention uses `@timestamp` to expire findings whose event time is stale. If `@timestamp` were absent, `event.ingested` would be the fallback.

The retention value depends on the data source:

- **Full-evaluation APIs**: use the evaluation interval
- **Incremental APIs**: use 90d (2160h) as an interim solution
- **Custom interval**: must not exceed the `retention_policy` `max_age`

### Settings

```yaml
settings:
  unattended: true
_meta:
  fleet_transform_version: "0.1.0"
  managed: true
```

`unattended: true` is required for auto-recovery. Without it, a failed transform stays stopped and findings go stale without operator intervention.

Bump `fleet_transform_version` when any transform code changes to trigger delete + reinstall + restart during package upgrade.

### Source query patterns

CDR transforms should filter the source to exclude error documents and cold/frozen tiers:

```yaml
source:
  index:
    - "logs-<integration>.<datastream>-*"
  query:
    bool:
      filter:
        - term:
            event.kind: state
      must_not:
        - exists:
            field: error.message
        - terms:
            _tier:
              - data_frozen
              - data_cold
```

- `error.message` exclusion prevents ingestion-error documents from appearing in the latest view
- `_tier` exclusion prevents scanning cold/frozen storage (performance)
- For full-evaluation APIs, an optional `@timestamp` range filter (e.g., `gte: "now-26h"`) limits the scan window to match the evaluation interval

## Vulnerability latest transform

### Destination index

```yaml
dest:
  index: "security_solution-<integration>.vulnerability_latest-<version>"
  aliases:
    - alias: "security_solution-<integration>.vulnerability_latest"
      move_on_creation: true
```

### Unique key, sort, and remaining config

```yaml
latest:
  unique_key:
    - vulnerability.id
    - resource.id
    - package.name
    - package.version
    - data_stream.namespace
  sort: "@timestamp"
```

The combination of `vulnerability.id` + `resource.id` + `package.name` + `package.version` + `data_stream.namespace` aligns with native CSP. Some integrations vary: Wiz uses `vulnerability.package.name` and `vulnerability.package.version` instead of `package.name`/`package.version`. AWS Inspector uses a custom `aws.inspector.transform_unique_id`. Evaluate case by case based on the source data.

Frequency, sync, retention, and settings are the same as misconfiguration transforms (see above).

## Field mapping for latest index

The latest index needs explicit field definitions. Key type overrides:

```yaml
- name: data_stream.namespace
  type: keyword           # NOT constant_keyword -- accommodates multiple namespaces
  external: ecs
- name: observer.vendor
  type: constant_keyword   # Performance optimisation for constant values
  external: ecs
- name: vulnerability.scanner.vendor
  type: constant_keyword
  external: ecs
- name: vulnerability.published_date
  type: date               # Not covered by ecs@mappings
```

From stack version 8.19/9.1, the `ecs@mappings` component template applies to both source and destination index templates. Before 8.19, ECS fields must be explicitly mapped with `external: ecs` in the destination index fields.

## Known CDR integrations

Packages with `cloudsecurity_cdr` manifest category: `aws_securityhub`, `cloud_asset_inventory`, `cloud_security_posture`, `google_scc`, `m365_defender`, `microsoft_defender_cloud`, `microsoft_defender_endpoint`, `prisma_cloud`, `qualys_vmdr`, `rapid7_insightvm`, `snyk`, `tenable_io`, `tetragon`, `wiz`

## CDR transform review checklist

- [ ] Destination index follows `security_solution-{integration}.{type}_latest-{version}` pattern -- **HIGH** if wrong
- [ ] Alias defined with `move_on_creation: true` -- **HIGH** if missing
- [ ] Unique key matches finding type (`resource.id` + `rule.uuid` + `namespace` for misconfiguration; `vulnerability.id` + `resource.id` + `package.name` + `package.version` + `namespace` for vulnerability) -- **HIGH** if wrong
- [ ] Sort on `@timestamp` -- **MEDIUM**
- [ ] Source query excludes `error.message` documents and cold/frozen tiers -- **MEDIUM**
- [ ] Frequency is 5m -- **LOW**
- [ ] Sync on `event.ingested` -- **HIGH** if wrong field. Delay is optional (ES defaults to 60s) -- **LOW** if omitted
- [ ] `retention_policy` present on `@timestamp` with appropriate `max_age` -- **HIGH** if missing
- [ ] `unattended: true` in settings -- **HIGH** if missing
- [ ] `fleet_transform_version` in `_meta` -- **HIGH** if missing
- [ ] `data_stream.namespace` mapped as `keyword` (not `constant_keyword`) -- **HIGH** if wrong type
- [ ] `observer.vendor` mapped as `constant_keyword` -- **MEDIUM**
