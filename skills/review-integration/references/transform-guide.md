# Transform configuration guide

Elasticsearch transform configuration for integration packages. Covers source/pivot/latest transform types, sync configuration, field definitions, retention policy, and version increment rules.

## File location and structure

```
elasticsearch/transform/<transform-name>/
  transform.yml          # Transform configuration (source, pivot/latest, sync, dest)
  manifest.yml           # Start flag + destination index template (optional)
  fields/
    fields.yml           # Output field definitions for the transform destination index
```

The `_meta` section in `transform.yml` carries Fleet metadata (`fleet_transform_version`, `managed: true`).

## Transform types

Transforms are Elasticsearch jobs that process data from source indices and output aggregated or deduplicated data. They are NOT data streams themselves.

### Pivot transforms

Define `pivot` with `group_by` and `aggregations`. Most common type. Used for entity-centric or metric summary indices.

```yaml
description: Summarize events per host per hour

source:
  index:
    - "logs-mypackage.events-*"
  query:
    bool:
      filter:
        - term:
            event.kind: event
      must_not:
        - exists:
            field: error.message
        - terms:
            _tier:
              - data_frozen
              - data_cold

pivot:
  group_by:
    host.name:
      terms:
        field: host.name
    "@timestamp":
      date_histogram:
        field: "@timestamp"
        fixed_interval: 1h
  aggregations:
    event.count:
      value_count:
        field: event.id
    bytes.total:
      sum:
        field: network.bytes

dest:
  index: "metrics-mypackage.summary-default"

sync:
  time:
    field: event.ingested
    delay: 120s

frequency: 5m

settings:
  deduce_mappings: false
  unattended: true

_meta:
  fleet_transform_version: "1.0.0"
  managed: true
```

### Latest transforms

Define `latest` with `unique_key` and `sort`. Used for deduplication / latest-state views.

```yaml
description: Keep latest finding per resource and rule

source:
  index:
    - "logs-mypackage.findings-*"
  query:
    bool:
      must_not:
        - exists:
            field: error.message
        - terms:
            _tier:
              - data_frozen
              - data_cold

latest:
  unique_key:
    - resource.id
    - rule.id
  sort: "@timestamp"

dest:
  index: "logs-mypackage.latest_findings-default"
  aliases:
    - alias: "logs-mypackage.latest_findings"
      move_on_creation: true

sync:
  time:
    field: event.ingested

frequency: 5m

settings:
  unattended: true

_meta:
  fleet_transform_version: "1.0.0"
  managed: true
```

## Sort field (latest transforms)

The `sort` field determines which document is "latest" per unique key. The choice is context-specific:

| Sort field | When to use | Example |
|-----------|-------------|---------|
| `@timestamp` | Source data has a meaningful event time (findings, alerts, logs). "Latest" means most recent event. | CDR transforms, github issues, alert tracking |
| `event.ingested` | Source data has no reliable event time, or `@timestamp` defaults to ingest time (inventory scans, endpoint state). "Latest" means most recently received. | tychon device inventory, endpoint state snapshots |

All CDR transforms use `@timestamp`. Evaluate based on what "latest" means for the specific data source.

## Sync configuration

Every transform should have sync config for continuous operation. `event.ingested` is generally preferred for the sync field (separate from the sort field above) because it reflects when ES received the document, ensuring late-arriving data is picked up. `@timestamp` is acceptable when the source has reliable, monotonically increasing timestamps.

Delay is optional; when omitted, ES defaults to 60s. Use `120s` for sources with known ingestion lag.

## Frequency

| Use case | Frequency | Examples |
|----------|-----------|---------|
| Threat intelligence | 30s | ti_opencti, ti_anomali, ti_google_threat_intelligence |
| CDR latest views | 5m | wiz, prisma_cloud, google_scc |
| Entity tracking | 5m | crowdstrike aidmaster, armis devices |
| Aggregation / ML | 30m-1h | beaconing, ded, aws_billing |

## Source query best practices

Always filter the source query to exclude noise and optimize performance:

- **Exclude error documents**: `must_not: exists: field: error.message` prevents ingestion-error documents from appearing in transform output
- **Exclude cold/frozen tiers**: `must_not: terms: _tier: [data_frozen, data_cold]` prevents scanning expensive storage tiers
- **Filter by event type**: use `filter: term: event.kind: state` (CDR) or appropriate event.kind/event.category to limit input scope
- **Time-bound for full-evaluation APIs**: optional `@timestamp` range filter (e.g., `gte: "now-26h"`) limits scan window

## Destination configuration

### `dest.pipeline`

Transforms can route output through an ingest pipeline:

```yaml
dest:
  index: "metrics-mypackage.summary-default"
  pipeline: '{{ ingestPipelineName "my-transform-pipeline" }}'
```

The `{{ ingestPipelineName }}` template resolves to the versioned pipeline name at install time.

### `dest.aliases`

Aliases ensure consumers always read from the current transform destination, even after upgrades that recreate the index:

```yaml
dest:
  aliases:
    - alias: "logs-mypackage.latest_findings"
      move_on_creation: true
```

Two variants:
- `move_on_creation: true` -- moves the alias to the new index when the transform is recreated. Only the latest version has the alias.
- `move_on_creation: false` -- additive alias that persists across versions. Used for ML/beaconing transforms where historical indices should remain searchable.

## Settings

- `unattended: true` -- auto-recovers from transient failures. Required for all transforms.
- `deduce_mappings: false` -- prevents auto-creating mappings that conflict with Fleet-managed templates. Mainly needed for non-CDR transforms with explicit field definitions.

## `_meta` fields

```yaml
_meta:
  fleet_transform_version: "1.0.0"
  managed: true
```

- `fleet_transform_version` -- required. Bump on any transform code change to trigger delete + reinstall + restart during package upgrade.
- `managed: true` -- Fleet manages the transform lifecycle (start/stop/delete). Used for CDR transforms. `managed: false` means the user manages the transform; used for TI, ML, and custom transforms.
- `run_as_kibana_system: false` -- controls execution privileges. When `false`, the transform runs under the installing user's credentials rather than `kibana_system`. Used by 70+ transforms in the repo.

## Transform manifest.yml

The optional `manifest.yml` alongside `transform.yml` configures installation behavior and the destination index template:

```yaml
start: true
destination_index_template:
  settings:
    index:
      mode: lookup          # For lookup-optimized indices (e.g., crowdstrike aidmaster)
      sort:
        field: ["@timestamp"]
        order: [desc]       # For TI transforms that need reverse-time ordering
      mapping:
        total_fields:
          limit: 2000       # For transforms with many output fields
  mappings:
    dynamic: true
    dynamic_templates:      # For transforms that accept dynamic fields
      - strings_as_keyword:
          match_mapping_type: string
          mapping:
            ignore_above: 1024
            type: keyword
```

Common settings:
- `start: true` -- transform starts automatically on install
- `index.mode: lookup` -- optimized for key-value lookups (enrichment transforms)
- `index.sort` -- physical sort order for read-optimized access patterns
- `total_fields.limit` -- increase for wide output schemas
- `dynamic_templates` -- map dynamic fields to appropriate types

## Retention policy

Deletes documents from the destination index older than `max_age`.

```yaml
retention_policy:
  time:
    field: "@timestamp"
    max_age: "2160h"         # 90 days
```

The retention field can be any date field, not just `@timestamp`. TI transforms use custom expiry fields for record-level deletion:

```yaml
retention_policy:
  time:
    field: opencti.indicator.invalid_or_revoked_from
    max_age: 1m
```

Common `max_age` values: 26h (full-evaluation CDR APIs), 90d (incremental CDR APIs), 30d (TI/entity transforms).

## Transform output field definitions

Transform output fields live at `elasticsearch/transform/<name>/fields/fields.yml`. Latest transforms require explicit field definitions for every output field. Transform-specific attributes: `normalize: [array]`, `object_type_mapping_type`.

## Version increment rules

- Changes to `pivot`/`source`/`latest` config require a bump in `_meta.fleet_transform_version`
- Field-only changes may not require a bump
- Breaking changes require changelog documentation

## CDR transforms

For CDR (cloud security) integrations, see `cdr-transform-requirements.md` in this skill's references.

## Review checklist

- [ ] Transform type matches purpose (pivot for aggregation, latest for dedup/current-state) -- **MEDIUM** if wrong
- [ ] `description` field present -- **LOW**
- [ ] `sync.time.field` configured -- **HIGH** if missing. Delay is optional (ES defaults to 60s) -- **LOW** if omitted
- [ ] `_meta.fleet_transform_version` present and incremented -- **HIGH** if missing/stale
- [ ] Source index pattern matches expected data stream -- **HIGH** if wrong
- [ ] Source query excludes `error.message` documents -- **MEDIUM**
- [ ] Source query excludes cold/frozen tiers (`_tier` must_not) -- **MEDIUM**
- [ ] Pivot `group_by` fields appropriate -- **MEDIUM**
- [ ] Aggregation types match field semantics -- **MEDIUM**
- [ ] Output field definitions exist with correct types -- **HIGH** if missing
- [ ] `normalize: [array]` for array output fields -- **MEDIUM**
- [ ] `settings.unattended: true` -- **MEDIUM** if missing
- [ ] `dest.aliases` configured with correct `move_on_creation` -- **HIGH** for CDR, **MEDIUM** for others
- [ ] `_meta.run_as_kibana_system` set appropriately -- **LOW**
- [ ] Transform manifest.yml has appropriate `destination_index_template` -- **MEDIUM**
- [ ] No hardcoded index names bypassing data stream routing -- **HIGH**
- [ ] CDR naming conventions followed when applicable -- **MEDIUM**
- [ ] Changelog entry for transform changes -- **MEDIUM**
