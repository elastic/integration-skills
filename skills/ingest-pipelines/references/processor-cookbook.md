# ingest processor cookbook

Use this cookbook to choose processors quickly while designing integration ingest pipelines.

## Parsing processors

| Processor | Best for | Key parameters | Notes |
| --- | --- | --- | --- |
| `grok` | Variable log formats | `field`, `patterns`, `pattern_definitions`, `ignore_missing`, `tag` | Use when token boundaries vary. Anchor patterns when possible. |
| `dissect` | Stable delimited text | `field`, `pattern`, `ignore_missing`, `tag` | Usually faster than grok for fixed formats. |
| `json` | JSON payload string parsing | `field`, `target_field`, `add_to_root`, `on_failure`, `tag` | Great for logs that embed raw JSON. |
| `csv` | Delimited values | `field`, `target_fields`, `separator`, `quote`, `ignore_missing` | Useful for fixed CSV-like telemetry records. |
| `kv` | `k=v` style logs | `field`, `field_split`, `value_split`, `target_field`, `trim_key`, `trim_value` | Common in firewall and audit-style logs. |

### Example: `grok` + `dissect` fallback

```yaml
- dissect:
    field: event.original
    pattern: "%{source.address} - %{user.name} [%{nginx.access.time}] \"%{http.request.method} %{url.original} HTTP/%{http.version}\" %{http.response.status_code} %{http.response.body.bytes}"
    ignore_failure: true
    tag: dissect_access
- grok:
    field: event.original
    patterns:
      - '^%{IPORHOST:source.address} - %{DATA:user.name} \[%{HTTPDATE:nginx.access.time}\] "%{WORD:http.request.method} %{DATA:url.original} HTTP/%{NUMBER:http.version}" %{NUMBER:http.response.status_code:long} %{NUMBER:http.response.body.bytes:long}$'
    if: ctx.http?.request?.method == null
    tag: grok_access_fallback
```

### Example: `json` parser with local failure handling

```yaml
- json:
    field: event.original
    target_field: json
    tag: parse_json
    on_failure:
      - append:
          field: error.message
          value: '{{{_ingest.on_failure_message}}}'
```

## Normalization processors

| Processor | Best for | Key parameters | Notes |
| --- | --- | --- | --- |
| `rename` | Move parsed fields | `field`, `target_field`, `ignore_missing`, `ignore_failure` | Common for `message -> event.original`. |
| `set` | Add constants/derived values | `field`, `value`, `if`, `copy_from` | Use for ECS categorization and defaults. |
| `remove` | Drop temporary/source fields | `field`, `ignore_missing`, `ignore_failure`, `if` | Keep documents clean after parsing. |
| `convert` | Type coercion | `field`, `type`, `ignore_missing`, `ignore_failure` | Convert before comparisons or aggregation. |
| `date` | Parse timestamps | `field`, `target_field`, `formats`, `timezone`, `on_failure` | Often has multiple format candidates. |
| `lowercase` / `uppercase` / `trim` | String normalization | `field`, `ignore_missing`, `if` | Use after parse, before categorization. |
| `split` | Turn strings into arrays | `field`, `separator`, `ignore_missing` | Useful for multi-IP and list fields. |
| `gsub` | Regex replacement | `field`, `pattern`, `replacement` | Use sparingly for cleanup/transforms. |

### Example: normalize timestamp + status

```yaml
- date:
    field: nginx.access.time
    target_field: '@timestamp'
    formats:
      - dd/MMM/yyyy:H:m:s Z
    tag: parse_timestamp
- convert:
    field: http.response.status_code
    type: long
    ignore_missing: true
    tag: convert_status_code
```

## Enrichment processors

| Processor | Best for | Key parameters | Notes |
| --- | --- | --- | --- |
| `geoip` | IP geolocation + ASN | `field`, `target_field`, `database_file`, `properties`, `ignore_missing`, `if` | Use on validated IP fields. |
| `user_agent` | User agent parsing | `field`, `ignore_missing`, `if` | Adds browser/device metadata. |
| `registered_domain` | Domain decomposition | `field`, `target_field`, `ignore_missing` | Splits FQDN into registered/subdomain pieces. |
| `community_id` | Network flow hashing | `source_ip`, `source_port`, `destination_ip`, `destination_port`, `iana_number`, `target_field` | Useful for flow correlation. |
| `uri_parts` | URL decomposition | `field`, `target_field`, `keep_original`, `ignore_failure` | Parse URL into scheme/host/path/query. |
| `append` | Add related values/tags | `field`, `value`, `allow_duplicates`, `if` | Common for `related.ip` and `tags`. |

### Example: common web enrichment path

```yaml
- user_agent:
    field: user_agent.original
    if: ctx.user_agent?.original != null
    ignore_missing: true
    tag: parse_user_agent
- geoip:
    field: source.ip
    target_field: source.geo
    if: ctx.source?.ip != null
    ignore_missing: true
    tag: enrich_source_geo
- append:
    field: related.ip
    value: '{{{source.ip}}}'
    if: ctx.source?.ip != null
```

### IP geolocation and ASN enrichment — full pattern

When the pipeline has IP address fields, always apply **both** the geo lookup and the ASN lookup, followed by the renames to map the raw `geoip` output into ECS field names. This pattern applies to any IP entity (`source`, `destination`, `client`, `server`, etc.).

```yaml
# IP Geolocation Lookup
- geoip:
    field: source.ip
    target_field: source.geo
    ignore_missing: true
    tag: enrich_source_geo
- geoip:
    field: destination.ip
    target_field: destination.geo
    ignore_missing: true
    tag: enrich_destination_geo

# IP Autonomous System (AS) Lookup
- geoip:
    database_file: GeoLite2-ASN.mmdb
    field: source.ip
    target_field: source.as
    properties:
      - asn
      - organization_name
    ignore_missing: true
    tag: enrich_source_asn
- geoip:
    database_file: GeoLite2-ASN.mmdb
    field: destination.ip
    target_field: destination.as
    properties:
      - asn
      - organization_name
    ignore_missing: true
    tag: enrich_destination_asn

# Rename ASN fields to ECS names
- rename:
    field: source.as.asn
    target_field: source.as.number
    ignore_missing: true
    tag: rename_source_asn
- rename:
    field: source.as.organization_name
    target_field: source.as.organization.name
    ignore_missing: true
    tag: rename_source_as_org
- rename:
    field: destination.as.asn
    target_field: destination.as.number
    ignore_missing: true
    tag: rename_destination_asn
- rename:
    field: destination.as.organization_name
    target_field: destination.as.organization.name
    ignore_missing: true
    tag: rename_destination_as_org
```

Key rules:
- The `geoip` processor with `GeoLite2-ASN.mmdb` outputs `asn` (number) and `organization_name` (string). These **must** be renamed to ECS names: `as.number` and `as.organization.name`.
- Always include both geo and ASN lookups when enriching IP fields. Omitting ASN leaves `source.as` / `destination.as` empty.
- Use `ignore_missing: true` on all geo/ASN processors — the IP field may not be present on every event.
- When only one IP entity is present (e.g., only `source.ip`), include only the source block. Add the destination block only when `destination.ip` exists in the pipeline.
- Place these processors **after** all IP fields have been set (after parsing, renaming, and converting IP addresses) and **before** the `related.ip` append processors.

## Flow control processors

| Processor | Best for | Key parameters | Notes |
| --- | --- | --- | --- |
| `drop` | Early discard of unwanted docs | `if` | Put early for performance. |
| `fail` | Stop processing with explicit error | `message`, `if`, `tag` | Use for invalid required input shape. |
| `pipeline` | Sub-pipeline routing | `name`, `if`, `ignore_missing_pipeline`, `tag` | Core branching primitive. |
| `foreach` | Iterate over array items | `field`, `processor`, `if`, `ignore_failure` | Useful for nested OCSF arrays. |
| `script` | Custom logic in Painless | `source`, `lang`, `if`, `params`, `tag` | Use only when processors are insufficient. |

### Example: route to sub-pipelines

```yaml
- pipeline:
    name: '{{ IngestPipeline "pipeline_object_user" }}'
    if: ctx.ocsf?.class_uid != null && ['2005','3001','3002'].contains(ctx.ocsf.class_uid) && ctx.ocsf.user != null
    ignore_missing_pipeline: true
    tag: route_object_user
- pipeline:
    name: '{{ IngestPipeline "pipeline_category_network_activity" }}'
    if: ctx.ocsf?.category_uid == '4'
    ignore_missing_pipeline: true
    tag: route_category_network
```

## Utility processors

| Processor | Best for | Key parameters | Notes |
| --- | --- | --- | --- |
| `dot_expander` | Expand dotted field names into objects | `field`, `path`, `ignore_failure` | Useful when source keys contain dots. |
| `fingerprint` | Stable IDs or dedupe keys | `fields`, `target_field`, `method`, `ignore_missing` | Useful for TSDS and correlation identifiers. |
| `bytes` | Human-readable size to numeric | `field`, `target_field`, `ignore_missing` | Converts values like `1kb` to bytes. |
| `html_strip` | Remove HTML tags | `field`, `target_field`, `ignore_missing` | For message text sanitation. |
| `sort` | Order array values deterministically | `field`, `order`, `target_field` | Useful for stable outputs and tests. |

## ECS categorization mapping patterns

Map source event types/actions to `event.category`, `event.type`, `event.outcome`, and `event.action` using these patterns. Choose the pattern that fits the number of mappings.

### Pattern A: Script with `params` lookup table (recommended for 5+ mappings)

Put all mapping data in `params` so the Painless script body stays generic and benefits from compilation caching. The script source is short and identical regardless of how many mappings exist.

**Single-key lookup** (mapping from one source field):

```yaml
  - script:
      lang: painless
      tag: set_ecs_categorization
      description: Map event type to ECS categorization fields.
      if: ctx.json?.event_type != null
      params:
        process_start:
          category: [process]
          type: [start]
        process_end:
          category: [process]
          type: [end]
        network_connection:
          category: [network]
          type: [connection]
        file_creation:
          category: [file]
          type: [creation]
        file_modification:
          category: [file]
          type: [change]
        user_login:
          category: [authentication]
          type: [start]
          outcome: success
        user_login_failed:
          category: [authentication]
          type: [start]
          outcome: failure
      source: |-
        def mapping = params[ctx.json.event_type];
        if (mapping == null) {
          return;
        }
        ctx.event.category = mapping.category;
        ctx.event.type = mapping.type;
        if (mapping.containsKey('outcome')) {
          ctx.event.outcome = mapping.outcome;
        }
```

**Composite-key lookup** (mapping from two or more source fields combined):

```yaml
  - script:
      lang: painless
      tag: set_ecs_categorization
      description: Map target type and action to ECS categorization fields.
      if: ctx.vendor?.target_type != null && ctx.event?.action != null
      params:
        "device:create":
          category: [host]
          type: [creation]
          outcome: success
        "device:delete":
          category: [host]
          type: [deletion]
          outcome: success
        "device:update":
          category: [host]
          type: [change]
          outcome: success
        "api_token:create":
          category: [iam, configuration]
          type: [creation]
          outcome: success
        "api_token:delete":
          category: [iam, configuration]
          type: [deletion]
          outcome: success
        "blueprint:update":
          category: [configuration]
          type: [change]
          outcome: success
      source: |-
        String key = ctx.vendor.target_type + ':' + ctx.event.action;
        def mapping = params[key];
        if (mapping == null) {
          return;
        }
        ctx.event.category = mapping.category;
        ctx.event.type = mapping.type;
        if (mapping.containsKey('outcome')) {
          ctx.event.outcome = mapping.outcome;
        }
```

**Merge variant** (when categorization fields may already have values from earlier processors and you need to add to them rather than overwrite):

```yaml
      source: |-
        def addUnique(List dst, List src) {
          HashSet s = new HashSet(dst != null ? dst : []);
          s.addAll(src != null ? src : []);
          return new ArrayList(s);
        }
        def mapping = params[ctx.json.event_type];
        if (mapping == null) {
          return;
        }
        ctx.event.type = addUnique(ctx.event.type, mapping.type);
        ctx.event.category = addUnique(ctx.event.category, mapping.category);
```

**Why `params`?** Elasticsearch compiles and caches Painless scripts by their `source` text. When the mapping data is in `params` rather than inlined in the script body, the same compiled script handles all event types. Inline `if`/`else` chains produce a unique script body that cannot be shared, defeating the cache.

Reference integrations using this pattern:
- `carbon_black_cloud` (endpoint_event) — single-key lookup by `json.type`
- `okta` (system) — merge variant with large params table in dedicated sub-pipeline
- `thycotic_ss` (logs) — single-key lookup by `cef.name`
- `zeronetworks` (audit) — composite fields with `action`, `outcome`, `type`, `category` per entry

### Pattern B: Set processors with conditionals (fewer than 5 mappings)

For simple cases with only 2–4 distinct mappings, `set` processors with `if` conditions are clearer than a script:

```yaml
  - set:
      field: event.category
      tag: set_category_auth
      value: [authentication]
      if: ctx.json?.event_type == 'login' || ctx.json?.event_type == 'logout'
  - set:
      field: event.type
      tag: set_type_start
      value: [start]
      if: ctx.json?.event_type == 'login'
  - set:
      field: event.type
      tag: set_type_end
      value: [end]
      if: ctx.json?.event_type == 'logout'
  - set:
      field: event.outcome
      tag: set_outcome_success
      value: success
      if: ctx.json?.result == 'success'
  - set:
      field: event.outcome
      tag: set_outcome_failure
      value: failure
      if: ctx.json?.result == 'failure'
```

Use this pattern when the mapping is straightforward and adding a `script` processor would be overkill. Once the number of conditions exceeds ~4 distinct event types, switch to Pattern A.

### Pattern C: Sub-pipeline for large mapping tables (100+ mappings)

For very large mapping tables (like Okta with 500+ event types), extract the categorization into a dedicated sub-pipeline file to keep `default.yml` readable:

```yaml
# In default.yml — route to categorization sub-pipeline:
  - pipeline:
      name: '{{ IngestPipeline "ecs-categorization" }}'
      tag: route_ecs_categorization
```

```yaml
# In ecs-categorization.yml — single script processor with large params table:
---
description: Map event types to ECS categorization fields.
processors:
  - script:
      lang: painless
      tag: set_ecs_categorization
      description: Map event type to ECS categorization fields.
      if: ctx.vendor?.event_type != null
      params:
        # ... hundreds of entries ...
      source: |-
        def mapping = params[ctx.vendor.event_type];
        if (mapping == null) {
          return;
        }
        ctx.event.category = mapping.category;
        ctx.event.type = mapping.type;
on_failure:
  - append:
      field: error.message
      value: >-
        Processor '{{{ _ingest.on_failure_processor_type }}}'
        {{{#_ingest.on_failure_processor_tag}}}with tag '{{{ _ingest.on_failure_processor_tag }}}'
        {{{/_ingest.on_failure_processor_tag}}}failed with message '{{{ _ingest.on_failure_message }}}'
```

Reference: `okta` (system) uses `ecs_category_type.yml` as a dedicated sub-pipeline.

### Anti-patterns — do NOT use these

**Bulk `append` processors:** Using 2 `append` processors per event type (one for `event.category`, one for `event.type`) creates 50+ processors for 25 event types. The pipeline becomes hard to read, review, and maintain. Each processor re-evaluates its `if` condition against the same field. Use Pattern A instead.

**Inline Painless `if`/`else` chains without `params`:** Writing hardcoded string comparisons directly in the script `source` (e.g., `if ('login'.equals(act)) { ctx.event.category = ['authentication']; }`) defeats Painless compilation caching because the script body is unique to the integration. It is also harder to maintain than a data-driven `params` table. Always put lookup data in `params`.

## Selection tips

- **Do not use `script` when a built-in processor can do the job** — see `SKILL.md` → *Painless script best practices* for the mandatory checklist.
- Add `tag` on **every** processor (not only processors that can fail).
- For optional data paths, prefer guarded `if` over `ignore_missing`.
- Keep parsing, normalization, and enrichment stages visually grouped.

## Processor performance guide

### Processor cost ordering

Processors vary dramatically in cost. Order pipelines so cheap operations run first and expensive ones run only when needed.

| Tier | Processors | Notes |
| --- | --- | --- |
| Fastest | `set`, `rename`, `remove` | Simple field manipulation, near-zero overhead. |
| Fast | `convert`, `lowercase`, `uppercase`, `trim` | String/type operations, still very cheap. |
| Moderate | `date`, `grok`, `dissect` | Parsing involves format matching; grok is regex-heavy. |
| Slow | `script` | Painless compilation + execution; avoid when a built-in suffices. |
| Expensive | `geoip`, `user_agent` | Database/cache lookups on every invocation. |

### Always guard `geoip` and `user_agent` with an `if` condition

Even with `ignore_missing: true`, the `geoip` processor performs expensive database setup and lookup before checking whether the source field exists. This is an Elasticsearch performance issue where the missing-field check happens too late in the execution path. Always add an `if` condition to check field existence before the processor runs:

```yaml
- geoip:
    tag: geoip_source_ip
    if: ctx.source?.ip != null
    field: source.ip
    target_field: source.geo
    ignore_missing: true
```

The `if` guard prevents the expensive lookup from executing at all. Without it, every document pays the lookup cost regardless of whether the field exists.

### Skip enrichment when results already exist

Beyond guarding with a null check on the source field, skip enrichment entirely when the target is already populated. This avoids redundant lookups on documents that were pre-enriched upstream.

```yaml
- geoip:
    tag: geoip_source_ip
    if: ctx.source?.ip != null && ctx.source.geo == null
    field: source.ip
    target_field: source.geo
```

### Batch remove operations

Use a single `remove` with a field list instead of multiple separate processors. Each processor invocation has fixed overhead; batching eliminates it.

```yaml
- remove:
    field: [_tmp, json, message]
    ignore_missing: true
    tag: cleanup_temp_fields
```

### Use `equalsIgnoreCase` instead of `toLowerCase`

In Painless `if` conditions, `equalsIgnoreCase` avoids allocating a throwaway lowercase string on every document.

```java
// Preferred -- no allocation
if (ctx.event?.action?.equalsIgnoreCase('login') == true)

// Avoid -- allocates a new string per document
if (ctx.event?.action?.toLowerCase() == 'login')
```

### Prefer `rename` over `set` + `remove`

`rename` is a single atomic operation. Using `set` with `copy_from` followed by `remove` requires two processors and introduces a window where both source and target fields coexist.

```yaml
# Preferred -- single operation
- rename:
    tag: rename_json_user
    field: json.user
    target_field: user.name
    ignore_missing: true

# Avoid -- two operations for the same result
- set:
    tag: set_user_name
    field: user.name
    copy_from: json.user
- remove:
    tag: remove_json_user
    field: json.user
    ignore_missing: true
```

## Foreach semantics and `_ingest._value`

### How foreach works

The `foreach` processor iterates over elements of an array field. Inside the inner processor, `_ingest._value` is a loop variable representing the current element -- it is not a real document field.

```yaml
- foreach:
    tag: foreach_event_items
    field: event.items
    processor:
      append:
        tag: append_related_user
        field: related.user
        value: '{{{_ingest._value.name}}}'
```

### Resolving `_ingest._value` references

To understand the actual data flow, resolve `_ingest._value` back to the `foreach` field:

| foreach field | Processor reference | Resolved field |
| --- | --- | --- |
| `event.items` | `_ingest._value.name` | `event.items[*].name` |
| `event.items` | `_ingest._value.id` | `event.items[*].id` |
| `json.tags` | `_ingest._value` | `json.tags[*]` (scalar element) |

### Subfield access within foreach

When iterating over an array of objects, access subfields with dot notation after `_ingest._value`:

```yaml
- foreach:
    tag: foreach_json_network_connections
    field: json.network_connections
    processor:
      convert:
        tag: convert_port
        field: _ingest._value.port
        type: long
        ignore_missing: true
```

The actual field being converted is `json.network_connections[*].port`.

### Painless scripts inside foreach

In a `script` processor nested inside `foreach`, access the current element via `ctx._ingest._value` (not `ctx.field[i]`):

```painless
def val = ctx._ingest._value;
if (val.containsKey('ip')) {
    // val.ip refers to foreach_field[*].ip
}
```

Modifications to `_ingest._value` subfields mutate the original array element in place.

### Common mistakes

- Treating `_ingest._value` as a real document field path outside a foreach context.
- Forgetting that writes to `_ingest._value` subfields modify the source array element in place.
- Using `ctx._ingest._value` outside a `foreach` block (it does not exist there).

## Condition patterns

### If-clause fields as implicit inputs

Fields referenced in processor `if` conditions are implicit inputs that influence whether a transformation runs. They must be tracked alongside explicit source/target fields for data lineage.

```yaml
- set:
    tag: set_event_category
    field: event.category
    value: [authentication]
    if: ctx.json?.event_type == 'login'
```

Here `json.event_type` is an input -- it determines whether `event.category` gets written.

### Painless null-safe condition patterns

| Pattern | Meaning |
| --- | --- |
| `ctx.field != null` | Field exists and is non-null |
| `ctx?.field == 'value'` | Null-safe access, compare value |
| `ctx.containsKey('field')` | Field key exists in the document map (even if null) |
| `ctx.field instanceof List` | Field is an array |
| `ctx.field?.size() != 0` | Non-empty collection (use `!=`, not `>`) |

Do not use inequality operators (`<`, `>`, `<=`, `>=`) with null-safe `?.` results. The `?.` operator returns a `def` type when the path is missing, and `def` is not an orderable type -- inequality comparisons fail. Equality checks (`==`, `!=`) work because all types support equality. Use `!=` or add an explicit null guard before any inequality.

For nested fields, chain null-safe access: `ctx.source?.geo?.country_name != null`.

### Use `.contains()` instead of chained OR conditions

When checking a field against multiple values, use `.contains()` instead of chained `||`. For 3+ values, define the list in `params` to avoid allocating a new array on every document:

```yaml
- script:
    tag: check_user_role
    params:
      privileged_names:
        - "admin"
        - "system"
        - "root"
        - "service"
    source: |
      if (params.privileged_names.contains(ctx.user?.name)) {
        ctx.user.privileged = true;
      }
```

For 1-2 values, inline comparison is fine -- the allocation overhead is negligible:

```painless
if (ctx.event?.action == 'login' || ctx.event?.action == 'logout') { ... }
```

Avoid long chained OR conditions regardless of approach:

```painless
// Avoid -- verbose and error-prone
ctx.user?.name == 'admin' || ctx.user?.name == 'system' || ctx.user?.name == 'root' || ctx.user?.name == 'service'
```

### Mustache field references in conditions

In `set` and `append` processor `value` fields, Mustache `{{{field}}}` references are inputs that provide the value being written. Use triple braces to disable HTML escaping.

```yaml
- set:
    tag: set_host_id
    field: host.id
    value: '{{{crowdstrike.aid}}}'
```

`crowdstrike.aid` is the input, `host.id` is the output.

### Nested condition and value references

When a processor has both an `if` condition and a Mustache value reference, both are inputs:

```yaml
- append:
    tag: append_related_ip
    field: related.ip
    value: '{{{source.ip}}}'
    if: ctx.source?.ip != null
```

Inputs: `source.ip` (from both the condition and the value reference). Output: `related.ip`.

## Field transform pitfalls

### `set` with `copy_from` vs Mustache value

Prefer `copy_from` over a Mustache `value` when copying fields -- it avoids string coercion and preserves the original type (objects, arrays, numbers):

```yaml
- set:
    tag: set_event_original
    field: event.original
    copy_from: message
    if: ctx.tags?.contains('preserve_original_event') == true
```

Guard `copy_from` usage to avoid overwriting an existing value. The `event.original` preservation pattern should check whether the target is already set:

```yaml
- rename:
    tag: rename_message
    field: message
    target_field: event.original
    ignore_missing: true
    if: ctx.event?.original == null
- remove:
    tag: remove_message
    field: message
    ignore_missing: true
    if: ctx.event?.original != null
```

### `convert` with `type: ip` must have a downstream consumer

A `convert` to IP type is not useful unless something downstream consumes the result (GeoIP enrichment, `community_id`, or an IP-typed mapping). A bare in-place conversion with no consumer is dead code -- or is missing a `target_field` that feeds enrichment.

```yaml
# Correct -- conversion feeds GeoIP enrichment downstream
- convert:
    tag: convert_source_ip
    field: source.ip
    type: ip
    ignore_missing: true
    on_failure:
      - append:
          field: error.message
          value: >-
            Processor {{{_ingest.on_failure_processor_type}}}
            with tag '{{{_ingest.on_failure_processor_tag}}}'
            failed: {{{_ingest.on_failure_message}}}
- geoip:
    tag: geoip_source_ip
    field: source.ip
    target_field: source.geo
    if: ctx.source?.ip != null
```

### Empty string guard before `convert`

An empty string fails `convert` with a confusing error. Always guard:

```yaml
- convert:
    field: json.severity
    type: long
    ignore_missing: true
    if: ctx.json?.severity != ''
    tag: convert_severity
```

### `append` for `related.*` fields

Always set `allow_duplicates: false` when appending to `related.*` arrays to avoid bloated documents:

```yaml
- append:
    tag: append_related_ip
    field: related.ip
    value: '{{{source.ip}}}'
    allow_duplicates: false
    if: ctx.source?.ip != null
```

## Non-grok parsing processors

### `dissect` vs `grok` decision criteria

Use `dissect` when the delimiter structure is fixed and predictable -- it is faster because it does not use regex. Use `grok` when token boundaries vary or when you need regex-based extraction.

```yaml
# Dissect -- fixed delimiters, faster
- dissect:
    tag: dissect_message
    field: message
    pattern: "%{ts} %{+ts} %{log_level} [%{thread}] %{class} - %{msg}"

# Grok -- variable format, regex needed
- grok:
    tag: grok_message
    field: message
    patterns:
      - '^%{TIMESTAMP_ISO8601:ts} %{LOGLEVEL:level} \[%{DATA:component}\] %{GREEDYDATA:msg}'
```

Dissect supports modifiers: `%{+field}` (append), `%{+field/order}` (ordered append), `%{?skip}` (discard), `%{*key}`/`%{&value}` (dynamic key-value).

### `json` processor: `add_to_root` and conflict strategy

When the parsed JSON should merge into the document root rather than a namespace, use `add_to_root`. Control collision behavior with `add_to_root_conflict_strategy`:

```yaml
- json:
    field: message
    add_to_root: true
    add_to_root_conflict_strategy: replace
    tag: json_merge_to_root
```

Prefer `target_field` over `add_to_root` in most integrations to avoid polluting the root namespace and accidentally overwriting fields. Use `add_to_root` only when the JSON payload IS the event structure.

### `date` timezone patterns

Avoid short timezone abbreviations (PST, EST) -- they are ambiguous across JDKs. Use full IANA names or UTC offsets.

```yaml
- date:
    tag: date_json_local_time
    field: json.local_time
    target_field: '@timestamp'
    formats:
      - "dd/MM/yyyy HH:mm:ss"
    timezone: "Europe/Amsterdam"
    if: ctx.json?.local_time != null
```

Dynamic timezone from a document field:

```yaml
- date:
    tag: date_json_timestamp
    field: json.timestamp
    formats: [ISO8601]
    timezone: '{{{json.tz}}}'
```

Multiple format arrays let the processor try each format in order:

```yaml
- date:
    tag: date_json_timestamp
    field: json.timestamp
    target_field: '@timestamp'
    formats:
      - ISO8601
      - "yyyy-MM-dd HH:mm:ss"
      - UNIX
    if: ctx.json?.timestamp != null
```

### `date` with `on_failure`

Date parsing failures should capture the error and remove the unparseable field to prevent downstream confusion:

```yaml
- date:
    field: json.eventTime
    tag: date_parse_eventTime
    formats: [ISO8601]
    on_failure:
      - remove:
          field: json.eventTime
      - append:
          field: error.message
          value: >-
            Processor {{{_ingest.on_failure_processor_type}}}
            with tag '{{{_ingest.on_failure_processor_tag}}}'
            failed: {{{_ingest.on_failure_message}}}
```

### `kv` processor patterns

Use `field_split` and `value_split` to define the delimiters. Use `target_field` to namespace the output and `prefix` to avoid field name collisions:

```yaml
- kv:
    tag: kv_json_data
    if: ctx.json?.data != null && ctx.json.data != ''
    field: json.data
    target_field: parsed
    field_split: '&'
    value_split: '='
    trim_value: '"'

- kv:
    tag: kv_message
    field: message
    field_split: ' '
    value_split: '='
    prefix: 'vendor.product.'
    target_field: _temp.kv
```

### `uri_parts` usage

Decomposes a URL string into scheme, host, port, path, query, and fragment:

```yaml
- uri_parts:
    tag: uri_parts_url_original
    field: url.original
    target_field: url
    keep_original: true
    if: ctx.url?.original != null
```

### `dot_expander` usage

Expands field names containing literal dots into nested objects. Required when source data uses dotted keys (e.g., `host.name` as a flat key rather than a nested object):

```yaml
- dot_expander:
    tag: dot_expander_json
    field: '*'
    path: json
    if: ctx.json != null
```

Use `path` to scope expansion to a specific sub-tree and avoid unintended side effects on the root document.

## Enrichment depth

### `community_id` implicit inputs

The `community_id` processor reads several fields by convention without an explicit `field` parameter. All must be populated before the processor runs:

- `source.ip`, `source.port`
- `destination.ip`, `destination.port`
- `network.transport` (protocol name) or `network.iana_number` (protocol number)

```yaml
- community_id:
    ignore_missing: true
    if: ctx.source?.ip != null && ctx.destination?.ip != null
    tag: add_community_id
```

Missing transport/iana_number fields cause the processor to fall back to a default protocol, which may produce incorrect hashes.

### `registered_domain` targeting and output structure

The processor splits an FQDN into its registered domain, top-level domain, and subdomain. Point `field` at the FQDN source and `target_field` at the parent object that should receive the decomposed fields:

```yaml
- registered_domain:
    tag: registered_domain_dns_question_name
    field: dns.question.name
    target_field: dns.question
    if: ctx.dns?.question?.name != null
```

Output fields written under `target_field`:
- `registered_domain` -- the registered domain (e.g., `example.com`)
- `top_level_domain` -- the TLD (e.g., `com`)
- `subdomain` -- the subdomain portion (e.g., `www`)

### Enrich policy lookup

The `enrich` processor joins external data into the document via a pre-built enrich policy. Always guard with an `if` condition and use a temporary target to control which fields are promoted:

```yaml
- enrich:
    tag: enrich_host_ip
    policy_name: hosts-policy
    field: host.ip
    target_field: _temp.enrich
    if: ctx.host?.ip != null
```

After the enrich processor, selectively copy needed fields from `_temp.enrich` into their final locations and remove the temporary object.

## Control flow semantics

### `terminate` processor for failure paths

Use `terminate` to stop the pipeline chain early for documents marked as failures. Without it, failed documents continue through expensive enrichment processors and produce confusing partial output.

```yaml
- set:
    tag: set_event_kind
    field: event.kind
    value: pipeline_error
- terminate:
    tag: terminate_pipeline_error
    if: ctx.event?.kind == 'pipeline_error'
```

Place `terminate` immediately after setting the failure marker in `on_failure` blocks.

### `drop` conditional patterns

`drop` silently discards the document. Always guard with an `if` condition -- an unconditional `drop` deletes everything.

```yaml
- drop:
    if: ctx.event?.action == 'heartbeat'
    tag: drop_heartbeat
    description: Discard periodic heartbeat events
```

Common uses: filtering out health-check events, deduplication markers, or noise events that provide no analytical value.

### `fail` for input validation

Use `fail` to enforce preconditions early in the pipeline. This produces a clear error message rather than letting the document fail cryptically downstream.

```yaml
- fail:
    if: ctx.event?.kind == null
    message: 'event.kind is required but missing'
    tag: require_event_kind
```

### Foreach and pipeline chaining edge cases

When a `foreach` contains a `pipeline` processor call, each array element is processed by the full sub-pipeline. Be aware that:

- The sub-pipeline sees the entire document context, not just the array element.
- `_ingest._value` is accessible in the sub-pipeline's processors.
- Errors in the sub-pipeline for one element do not automatically skip remaining elements unless `ignore_failure: true` is set on the `foreach`.
- Deeply nested foreach-pipeline chains are hard to debug; prefer flattening where possible.

## Special processors

### `fingerprint`

Generates a deterministic hash from one or more fields. Commonly used to set `_id` for deduplication.

```yaml
- fingerprint:
    tag: fingerprint_event_id
    fields:
      - event.id
      - '@timestamp'
    target_field: _id
    method: SHA-256
```

Key considerations:
- `fields` is an array -- field order matters (changing order changes the hash).
- If any field in `fields` is missing, the hash changes compared to when it is present. Guard with `if` or ensure fields always exist.
- `target_field: _id` enables upsert-style deduplication in Elasticsearch.
- Prefix `_id` with a timestamp for better index write performance when using time-series data.

### `html_strip`

Removes HTML tags from a field value.

```yaml
- html_strip:
    tag: html_strip_message
    field: message
    target_field: message_clean
    if: ctx.message != null
```

When `target_field` is absent, the processor writes back to `field`, destroying the original HTML. Use a separate `target_field` if the raw value must be preserved.

### `url_decode`

Decodes percent-encoded URL strings (e.g., `%20` becomes a space).

```yaml
- url_decode:
    tag: url_decode_url_query
    field: url.query
    if: ctx.url?.query != null
```

Like `html_strip`, writes back to `field` when no `target_field` is set.

### `network_direction`

Determines whether network traffic is `inbound`, `outbound`, or `internal` based on source/destination IPs and configured internal networks.

Implicit input fields (must be populated before the processor runs):
- `source.ip`
- `destination.ip`
- `network.type` (optional -- IPv4 vs IPv6 hint)

```yaml
- network_direction:
    tag: network_direction
    internal_networks:
      - loopback
      - private
    if: ctx.source?.ip != null && ctx.destination?.ip != null
```

Output defaults to `network.direction`. Use `internal_networks_field` to read the network list from a document field instead of hardcoding it.

### `set_security_user`

Copies the authenticated user's information from the Elasticsearch security context into a document field. There is no explicit input field -- the processor reads from the indexing user's auth context.

```yaml
- set_security_user:
    tag: set_security_user
    field: user
    properties:
      - username
      - roles
      - full_name
```

Typically used in monitoring or audit pipelines where the indexing user's identity must be recorded. The `properties` list controls which attributes are copied; omitting it copies all available properties.
