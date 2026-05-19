# Mapping type matrix

Use this matrix when selecting field mappings in integration field files.

## Common field types

| Type | Typical use | Notes |
| --- | --- | --- |
| `constant_keyword` | fixed values (`data_stream.*`, module/dataset constants) | can use `value` to enforce a constant |
| `keyword` | IDs, codes, exact-match strings | supports `ignore_above`, `normalizer`, `multi_fields` |
| `wildcard` | high-variance strings searched with wildcards | supports `ignore_above`; more costly than `keyword` |
| `text` / `match_only_text` | full-text content | use `multi_fields` for keyword subfield when aggregation is needed |
| `long` / `integer` / `short` / `byte` | integral numeric values | `metric_type` allowed for numeric metric fields |
| `double` / `float` / `half_float` / `scaled_float` | fractional numeric values | use `scaled_float` when controlled precision/storage tradeoff is useful |
| `unsigned_long` | non-negative large integers | useful for very large counters/IDs |
| `boolean` | true/false values | avoid string booleans in pipelines |
| `date` / `date_nanos` | timestamps | use `date_nanos` only when sub-millisecond precision is required |
| `ip` | IP addresses | can be a TSDB dimension |
| `geo_point` | latitude/longitude | for geospatial queries/maps |
| `group` | logical field grouping in package definitions | requires nested `fields` definitions; intermediate object nodes are implicit |
| `flattened` | arbitrary key/value blobs with unknown keys | simpler than nested object trees for unbounded keys |
| `nested` | arrays of objects requiring per-object query isolation | more complex and heavier than `group`; source data arriving as parallel scalar arrays must be restructured into an array of objects before indexing — see `SKILL.md` → *Nested (array-of-objects) ECS fields* |
| `histogram` / `aggregate_metric_double` | pre-aggregated metric payloads | special-purpose metric storage |
| `alias` | mapped field alias path | requires `path` to target field |
| `version` | semantic version strings | purpose-built version mapping behaviour |

## Property compatibility highlights

| Property | Use with | Notes |
| --- | --- | --- |
| `metric_type` | numeric metric fields, `histogram`, `aggregate_metric_double` | allowed values: `gauge`, `counter` |
| `unit` | numeric fields | examples: `byte`, `percent`, `ms`, `micros` |
| `dimension` | selected low-cardinality fields (TSDB) | pick carefully; affects series cardinality and performance |
| `multi_fields` | `keyword`, `text`, `wildcard` | index same source field in multiple ways |
| `ignore_above` | `keyword`, `wildcard` | default is `1024` in spec |
| `scaling_factor` | `scaled_float` | controls precision/storage tradeoff |
| `external` | ECS references | only use in `ecs.yml` — `external: ecs` |
| `runtime` | selected scalar types | schema-restricted; use only when query-time fields are intended |

## High-signal patterns

### Base stream constants

```yaml
- name: data_stream.type
  external: ecs
- name: data_stream.dataset
  external: ecs
- name: data_stream.namespace
  external: ecs
```

### Custom integration group

```yaml
- name: vendor.product
  type: group
  fields:
    - name: id
      type: keyword
    - name: latency
      type: long
      unit: ms
      metric_type: gauge
```

### ECS reference in ecs.yml

```yaml
- name: source.ip
  external: ecs
- name: observer.vendor
  external: ecs
  type: constant_keyword
  value: Acme Corp
```

### multi_fields patterns

```yaml
# Keyword primary with text sub-field for full-text search
- name: vendor.message
  type: keyword
  description: Raw message from the vendor API.
  multi_fields:
    - name: text
      type: match_only_text
```

```yaml
# Keyword primary with wildcard sub-field for glob-pattern matching
- name: file.path
  type: keyword
  multi_fields:
    - name: text
      type: wildcard
```

```yaml
# Keyword primary with text sub-field for full-text search on long values
- name: request_parameters
  type: keyword
  ignore_above: 8191
  multi_fields:
    - name: text
      type: text
      default_field: false
```

**When to use:**

- keyword + text/match_only_text: when the field needs both exact matching AND full-text search (long error messages, request parameters, descriptive strings)
- keyword + wildcard: when glob-pattern queries are needed (file paths, URLs)
- keyword + long: when a string field may also need numeric range queries

**Properties:**

| Property | When to set | Purpose |
| --- | --- | --- |
| `ignore_above: 1024` | keyword primary when values can be long | prevents indexing of excessively long values |
| `default_field: false` | on sub-fields | excludes from default query expansion |

**When NOT to use:**

- Don't add text sub-fields to short identifiers (IDs, codes, status values) — exact matching is sufficient
- Don't add multi_fields to ECS fields declared with `external: ecs` — they inherit their own multi_fields configuration
- Don't add multi_fields when the primary type already satisfies all query needs

## Selection rules of thumb

- choose the narrowest type that matches real source data
- avoid relying on implicit coercion in ingest for mapping correctness
- use `keyword` by default for string identifiers; only use `text` when full-text search matters
- define timestamps as `date`
- use `group` for explicit structure and docs; use `flattened` for flexible unknown keys
- add `metric_type` and `unit` for metrics intended for TSDB and visualization quality

## Validation loop

After mapping edits:

```bash
elastic-package lint
elastic-package check
elastic-package test pipeline --data-streams <stream>
```
