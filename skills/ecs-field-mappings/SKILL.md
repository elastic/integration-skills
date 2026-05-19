---
name: ecs-field-mappings
description: "Use when defining field mappings for data streams, populating ecs.yml with ECS field references, selecting ECS categorization values, choosing custom field types, or troubleshooting mapping validation failures."
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# ecs-field-mappings

## When to use

Use this skill when tasks include:
- adding or modifying files under `data_stream/<stream>/fields/`
- populating `ecs.yml` with ECS field references
- selecting `event.kind`, `event.category`, `event.type`, and `event.outcome` values
- choosing field `type` and mapping properties (`metric_type`, `dimension`, `multi_fields`, and related options)
- checking whether a field already exists in ECS before adding custom fields
- troubleshooting mapping validation/build failures from `elastic-package check`, `elastic-package lint`, or pipeline test schema checks

## ECS dependency configuration

Every package needs `_dev/build/build.yml` at the package root. This file pins the ECS schema version used for field resolution.

```yaml
dependencies:
  ecs:
    reference: "git@v9.3.0"
```

This file is **required** whenever the package has any field file. The scaffold does not generate it — create it manually. If it is missing or uses an outdated version, tests report ECS fields as undefined (e.g., `field "destination.ip" is undefined`).

## Field files and roles

A data stream's `fields/` directory contains a small set of YAML files with distinct responsibilities:

### `base-fields.yml`

Fixed routing constants and `@timestamp`. All six fields are ECS fields, so each entry uses `external: ecs`. Override `type` and `value` where the data stream needs a `constant_keyword` with a fixed value — the description is inherited from ECS automatically.

```yaml
- name: data_stream.type
  external: ecs
- name: data_stream.dataset
  external: ecs
- name: data_stream.namespace
  external: ecs
- name: event.module
  external: ecs
  type: constant_keyword
  value: <package_name>
- name: event.dataset
  external: ecs
  type: constant_keyword
  value: <package_name>.<stream_name>
- name: '@timestamp'
  external: ecs
```

Do not add other fields here. Only these routing constants and `@timestamp` belong in `base-fields.yml`.

### `constant_keyword` candidates

Fields that hold a single value for every document in a data stream should use `constant_keyword`. Beyond the routing constants in `base-fields.yml`, evaluate these:

| Field | Why `constant_keyword` |
|-------|------------------------|
| `event.dataset` | One value per data stream by definition |
| `event.module` | One value per package |
| `data_stream.type` | Fixed per stream (`logs`/`metrics`) |
| `data_stream.dataset` | Fixed per stream |
| `data_stream.namespace` | Set at deployment, constant within index |
| `observer.vendor` | Package represents one vendor |
| `observer.product` | Package represents one product |

When a `constant_keyword` field is also an ECS field (e.g., `observer.vendor`), use `external: ecs` with the type override. This inherits the description from ECS and avoids manual duplication. Place the definition in the appropriate field file (`ecs.yml` for most ECS fields, `base-fields.yml` for routing constants):

```yaml
- name: observer.vendor
  external: ecs
  type: constant_keyword
  value: Acme Corp
```

**`remove_from_source` option:** Because `constant_keyword` stores the value once in index metadata, it does not need to appear in every document's `_source`. Elasticsearch handles this automatically — no explicit `_source.excludes` configuration is needed. This saves storage when the value is always the same.

### `ecs.yml`

**Populate this file with every ECS field the pipeline sets.** Use only `name` and `external: ecs` for each entry — no type, no description. The type is resolved from the ECS schema via `_dev/build/build.yml`.

`external: ecs` must be used whenever a field name exists in ECS ([wiki reference](https://github.com/elastic/integrations/wiki/Fleet-Package-Code-Review-Comments#defining-an-ecs-field-without-using-an-external-definition)). This applies across field files — `ecs.yml`, `base-fields.yml`, and any file that defines an ECS field. You may override properties (e.g., `type: constant_keyword`, `value:`) while still using `external: ecs` — the description is inherited from ECS. Do not use `external: ecs` in `fields.yml`, `agent.yml`, or `beats.yml` — those files define non-ECS fields.

```yaml
- name: event.kind
  external: ecs
- name: event.category
  external: ecs
- name: event.type
  external: ecs
- name: event.outcome
  external: ecs
- name: event.action
  external: ecs
- name: source.ip
  external: ecs
- name: source.port
  external: ecs
- name: destination.ip
  external: ecs
- name: user.name
  external: ecs
- name: related.ip
  external: ecs
- name: related.user
  external: ecs
```

When attaching extra metadata to an ECS field (for example making a field a TSDB dimension or a constant_keyword with a fixed value), combine `external: ecs` with that metadata. The description is inherited from ECS. Place the definition in `ecs.yml` (or `base-fields.yml` for routing constants):

```yaml
- name: observer.vendor
  external: ecs
  type: constant_keyword
  value: Acme Corp
```

### `fields.yml`

Integration-specific custom (non-ECS) fields only. Use a nested `group` hierarchy for the vendor namespace:

```yaml
- name: acme.firewall
  type: group
  fields:
    - name: rule_id
      type: keyword
    - name: policy_name
      type: keyword
    - name: bytes_in
      type: long
      unit: byte
      metric_type: gauge
```

Groups do not need to be declared as `type: object` — defining a `group` with nested `fields` is sufficient. The object structure is implicit.

#### `labels.*` exception

`labels` is a core ECS object (`type: object`, `object_type: keyword`) designed for ad-hoc key-value metadata. Subkeys under `labels.*` do **not** require vendor namespacing — this is the one exception to the vendor-prefix rule.

Use `labels.*` for simple keyword flags or integration-internal markers (e.g., `labels.is_ioc_transform_source`). Use the vendor namespace for structured or nested data from an upstream source.

#### Flags vs structured data

Boolean flags and simple tags can live flat under the vendor group:

```yaml
- name: acme.firewall
  type: group
  fields:
    - name: is_encrypted
      type: boolean
    - name: policy_name
      type: keyword
```

Structured data from the source should use sub-groups for logical hierarchy:

```yaml
- name: acme.firewall
  type: group
  fields:
    - name: rule
      type: group
      fields:
        - name: id
          type: keyword
        - name: name
          type: keyword
        - name: action
          type: keyword
```

### `agent.yml`

Non-ECS fields populated by the Elastic Agent or Beats framework but not covered by ECS. Include only when the input type emits these fields. Typical fields: `cloud.image.id`, `cloud.instance.id`, `host.containerized`, `host.os.build`, `host.os.codename`, `input.type`, `log.offset`.

See `references/root-and-core-fields.md` for full YAML samples.

### `beats.yml`

Filebeat/Beats-specific fields not covered by ECS. Minimal form contains `input.type` and `log.offset`. Some inputs also emit `log.flags` or `log.file.*` sub-fields.

See `references/root-and-core-fields.md` for full YAML samples.

## ECS field selection

Prefer ECS fields whenever semantics match. If no ECS field exists for the data, add it under the package namespace in `fields.yml`.

### Categorization quick reference

| Field | Type | Notes |
| --- | --- | --- |
| `event.kind` | keyword | Highest-level classification. |
| `event.category` | keyword[] | Broad domain buckets — always an array. |
| `event.type` | keyword[] | Sub-buckets within category — always an array. |
| `event.outcome` | keyword | `success`, `failure`, `unknown`; only set when meaningful. |

- `event.kind`: `alert`, `asset`, `enrichment`, `event`, `metric`, `pipeline_error`, `signal`, `state`
- `event.category`: `api`, `authentication`, `configuration`, `database`, `driver`, `email`, `file`, `host`, `iam`, `intrusion_detection`, `library`, `malware`, `network`, `package`, `process`, `registry`, `session`, `threat`, `vulnerability`, `web`
- `event.type`: `access`, `admin`, `allowed`, `change`, `connection`, `creation`, `deletion`, `denied`, `device`, `end`, `error`, `group`, `indicator`, `info`, `installation`, `protocol`, `start`, `user`

Decision workflow:
1. `event.kind`: `event` for normal logs, `metric` for measurements, `state` for snapshots, `pipeline_error` in `on_failure`
2. `event.category`: one or more values (array) for the broad domain
3. `event.type`: one or more values (array) for operation style
4. `event.outcome`: only when a clear success/failure/unknown applies; omit for informational/metric events
5. If no allowed value fits, leave the field empty — do not invent values

Use `event.action` for source-specific verbs (`blocked`, `dropped`, `authenticated`).

See `references/categorization-cheatsheet.md` for full worked examples.

### Timestamp fields

ECS defines several timestamp fields with distinct semantics. Use them correctly:

| Field | When to use | Set by |
| --- | --- | --- |
| `@timestamp` | The primary event timestamp. Parse from the source event data. Required. | Integration pipeline |
| `event.created` | When the event was first created or recorded by the source system, if different from `@timestamp`. | Integration pipeline |
| `event.start` | When an activity or period began (e.g., session start, connection start). | Integration pipeline |
| `event.end` | When an activity or period ended (e.g., session end, connection close). | Integration pipeline |
| `event.ingested` | When the event was ingested into Elasticsearch. | **Elasticsearch (outside the integration)** |

**`event.ingested` must NEVER be set by an integration pipeline.** It is managed automatically by Elasticsearch's final pipeline. Do not add a `set` processor for `event.ingested`.

When the source data contains multiple timestamps:
1. Map the primary event timestamp to `@timestamp`.
2. If another timestamp represents when the event was first recorded/created, map it to `event.created`.
3. If timestamps represent the start or end of an activity, map them to `event.start` and `event.end`.
4. If a timestamp does not match the semantics of any of the above, map it to a custom field under the vendor namespace with `type: date` in `fields.yml`.

### Reusable fieldset nesting rules

Some ECS field sets must be nested under a parent entity — they are not valid at document root.

**`geo`** — must be nested under: `client.geo`, `destination.geo`, `host.geo`, `observer.geo`, `server.geo`, `source.geo`, `threat.indicator.geo`

Root-level `geo.*` fields are not recognized and will appear unmapped. Always set `target_field` on the `geoip` processor:

```yaml
- geoip:
    field: source.ip
    target_field: source.geo
    ignore_missing: true
```

**`as`** (Autonomous System) — nested under: `client.as`, `destination.as`, `server.as`, `source.as`

When using `geoip` for geolocation, always also perform an ASN lookup using `GeoLite2-ASN.mmdb` and rename the raw output fields to ECS names. The `geoip` ASN processor outputs `asn` and `organization_name`, which must be renamed to `as.number` and `as.organization.name`:

```yaml
- geoip:
    database_file: GeoLite2-ASN.mmdb
    field: source.ip
    target_field: source.as
    properties:
      - asn
      - organization_name
    ignore_missing: true
- rename:
    field: source.as.asn
    target_field: source.as.number
    ignore_missing: true
- rename:
    field: source.as.organization_name
    target_field: source.as.organization.name
    ignore_missing: true
```

See the `ingest-pipelines` skill → `references/processor-cookbook.md` for the full geo+ASN pattern with both source and destination.

**`os`** — nested under: `host.os`, `observer.os`, `user_agent.os`

### Nested (array-of-objects) ECS fields

Some ECS fields use `type: nested`, meaning they hold an **array of objects** where each object groups related sub-fields together. The pipeline must produce this structure — do **not** flatten these into parallel scalar arrays.

**ECS fields that use `nested` type:**

| Field | Contains |
|---|---|
| `email.attachments` | `file.name`, `file.size`, `file.extension`, `file.mime_type`, `file.hash.*` |
| `threat.enrichments` | `indicator.*`, `matched.*` |
| `threat.indicator.file.elf.sections` | `name`, `physical_size`, `virtual_size`, etc. |
| `threat.indicator.file.pe.sections` | `name`, `physical_size`, `virtual_size`, etc. |
| `process.elf.sections` | `name`, `physical_size`, `virtual_size`, etc. |
| `process.pe.sections` | `name`, `physical_size`, `virtual_size`, etc. |

**Anti-pattern — parallel arrays (WRONG):**

```json
{
  "email": {
    "attachments": {
      "file": {
        "name": ["a.pdf", "b.pdf"],
        "size": [1024, 2048]
      }
    }
  }
}
```

This loses the association between each attachment's name and size. Queries cannot isolate individual objects.

**Correct — array of objects:**

```json
{
  "email": {
    "attachments": [
      { "file": { "name": "a.pdf", "size": 1024 } },
      { "file": { "name": "b.pdf", "size": 2048 } }
    ]
  }
}
```

**`ecs.yml` declaration:** declare only the parent `nested` field with `external: ecs`. Child fields (`email.attachments.file.name`, etc.) inherit their types from the ECS schema — do not redeclare them individually.

```yaml
- name: email.attachments
  external: ecs
```

**Pipeline construction:** when source data delivers attachment metadata as separate parallel arrays (e.g., a comma-separated list of filenames and a separate list of sizes), use a `script` processor to zip them into an array of objects. See `ingest-pipelines` → `references/painless-patterns.md` for array construction patterns and `references/processor-cookbook.md` → **Foreach semantics** for iterating over array elements.

```yaml
- script:
    tag: build_email_attachments
    description: Build email.attachments as array of nested objects from parallel source arrays.
    lang: painless
    if: ctx.json?.file_names instanceof List && ctx.json?.file_sizes instanceof List
    source: |-
      def names = ctx.json.file_names;
      def sizes = ctx.json.file_sizes;
      int len = Math.min(names.size(), sizes.size());
      def attachments = new ArrayList(len);
      for (int i = 0; i < len; i++) {
        def attachment = new HashMap();
        def file = new HashMap();
        file.put('name', names.get(i));
        file.put('size', sizes.get(i));
        attachment.put('file', file);
        attachments.add(attachment);
      }
      ctx.email = ctx.email ?: [:];
      ctx.email.attachments = attachments;
```

When source data already delivers each attachment as a separate object (e.g., a JSON array of attachment objects), no zipping is needed — use `rename` or `set` with `copy_from` to place the array at `email.attachments` directly.

## Custom field types

For non-ECS fields in `fields.yml`:
- `keyword` for identifiers and exact-match strings
- `constant_keyword` for fixed values (dataset/module constants)
- `long`, `double`, `scaled_float` for metrics and numeric values
- `date` / `date_nanos` for timestamps (`date_nanos` only when sub-millisecond precision is truly needed)
- `ip` for IP addresses
- `boolean` for true/false (avoid string booleans in pipelines)
- `geo_point` for lat/lon coordinates
- `group` with nested `fields` for logical structure — no need to separately declare intermediate `object` nodes
- `flattened` for arbitrary key/value blobs with unknown keys
- `nested` for arrays of objects requiring per-object query isolation (heavier than group)
- `text` / `match_only_text` for full-text content; add a `keyword` sub-field via `multi_fields` when aggregation is also needed

Useful properties on numeric fields: `metric_type` (`gauge` or `counter`), `unit` (e.g., `byte`, `percent`, `ms`), `dimension` for low-cardinality TSDB fields.

See `references/mapping-type-matrix.md` for the full type reference.

## Field naming conventions

| Rule | DO | DON'T |
|------|-----|-------|
| Use snake_case | `user_name`, `request_count` | `userName`, `RequestCount` |
| Use lowercase | `source_ip` | `Source_IP` |
| No asterisks in names | `network.bytes` | `network.*` (literal asterisk) |
| Use groups for hierarchy | `vendor.module.field` as nested group | `vendor.module.field` as flat dotted name |

Field names must never contain literal `*` characters. An asterisk in a field name is almost always a copy-paste error from documentation or wildcard patterns. Use a `group` with known subfields or `flattened` for dynamic keys instead.

## Dotted field names vs nested groups

Both styles are valid in field files:

```yaml
# Dotted (flat) — common for ECS fields in ecs.yml
- name: source.ip
  external: ecs

# Nested group — common for custom fields
- name: acme.firewall
  type: group
  fields:
    - name: rule_id
      type: keyword
```

Pipeline expected output (`*-expected.json`) always uses nested object form regardless of how the source data represented the field. A source `"host.name": "myhost"` produces `{"host": {"name": "myhost"}}` in the output.

When source data contains literal dotted keys that Elasticsearch would otherwise expand, use `dot_expander`:

```yaml
- dot_expander:
    field: "*"
    override: true
```

## geo_point field handling

In pipeline test expected outputs, `geo_point` fields appear as objects with `lat` and `lon` keys:

```json
"source": {
  "geo": {
    "location": { "lat": 51.5142, "lon": -0.0931 },
    "city_name": "London",
    "country_iso_code": "GB"
  }
}
```

These sub-fields do not need entries in `fields.yml` — they are part of the `geo_point` type mapping. Only the `*.geo.location` field (type `geo_point`) needs to be in `ecs.yml` for non-standard parent prefixes where `ecs@mappings` does not apply.

## Common pipeline categorization patterns

### Web access

```yaml
- set:
    field: event.kind
    value: event
- append:
    field: event.category
    value: web
- append:
    field: event.type
    value: access
```

### Outcome from HTTP status

```yaml
- set:
    field: event.outcome
    value: success
    if: "ctx?.http?.response?.status_code != null && ctx.http.response.status_code < 400"
- set:
    field: event.outcome
    value: failure
    if: "ctx?.http?.response?.status_code != null && ctx.http.response.status_code >= 400"
```

### Pipeline error fallback

```yaml
on_failure:
  - set:
      field: event.kind
      value: pipeline_error
```

## Troubleshooting: "field X is undefined" for ECS fields

When tests report `field "destination.ip" is undefined` for standard ECS fields:

1. Check `_dev/build/build.yml` exists at the package root
2. Check `dependencies.ecs.reference` is set (use `git@v9.3.0`)
3. Check the field is listed in `ecs.yml` with `external: ecs`

Fix the root cause. Do not work around it by:
- Adding ECS fields with full type definitions to `fields.yml` without `external: ecs`
- Skipping `external: ecs` and defining ECS field types/descriptions manually

**Exception:** Custom (non-ECS) fields reported as undefined must be defined in `fields.yml`.

## Common failure patterns

- **missing `_dev/build/build.yml`** — all ECS fields reported undefined; create with `dependencies.ecs.reference`
- **outdated ECS version in `build.yml`** — fields from newer ECS versions undefined; update reference to `git@v9.3.0`
- **ECS field set in pipeline but missing from `ecs.yml`** — field is undefined in test schema validation; add it to `ecs.yml`
- **ECS field defined without `external: ecs`** — descriptions and types diverge from ECS; always use `external: ecs` for ECS fields, with overrides as needed
- **`metric_type` on non-numeric field** — lint error
- **`geo.*` at document root** — unmapped; always nest under a parent entity
- **`event.category` or `event.type` set as scalar** — must use `append` processor, not `set`
- **`nested` ECS field mapped as parallel arrays** — `email.attachments`, `threat.enrichments`, and similar `nested` fields must be arrays of objects, not objects with parallel scalar arrays; see the *Nested (array-of-objects) ECS fields* section above

## Validation loop

```bash
elastic-package lint
elastic-package check
elastic-package test pipeline --data-streams <stream>
```

## References

- `references/mapping-type-matrix.md`
- `references/categorization-cheatsheet.md`
- `references/root-and-core-fields.md`
- `references/fieldset-links.md`
- [ECS field reference](https://www.elastic.co/docs/reference/ecs/ecs-field-reference)
