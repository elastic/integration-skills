---
name: ingest-pipelines
description: "Use when designing or modifying Elasticsearch ingest pipelines, including single-path parsing, branching logic, sub-pipelines, enrichment processors, and robust on_failure handling."
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# ingest-pipelines


## Skill authority

The rules and patterns defined in this skill and its reference files are the **authoritative source of truth**. When examining existing integrations in the `elastic/integrations` repository for reference, you may encounter patterns that conflict with what is specified here — many integrations contain legacy patterns that predate current standards. **Always follow this skill over patterns observed in other integrations.** If a reference integration uses a deprecated or prohibited pattern, do not copy it.

## When to use

Use this skill when tasks include:
- building or modifying `elasticsearch/ingest_pipeline/default.yml` for a data stream
- choosing parser and normalization processors (`grok`, `dissect`, `json`, `kv`, `date`, `convert`)
- designing conditional branches and sub-pipeline routing with `pipeline` processors
- implementing resilient error handling with top-level `on_failure`
- tuning processor order for ingest performance and maintainability

## When not to use

Do not use this skill as the primary guide for:
- ECS field selection, categorization values, and field mapping strategy (`ecs-field-mappings`)
- elastic-package command and stack lifecycle workflows (`elastic-package-cli`)
- test fixture authoring and expected output workflows (`integration-testing` → `references/pipeline-testing.md`)

## Pipeline anatomy

In integration packages, ingest pipelines live under:

`data_stream/<stream>/elasticsearch/ingest_pipeline/`

Every stream usually has a `default.yml` with:
- `description`
- `processors` list
- optional pipeline-level `on_failure`

Keep `default.yml` readable and focused. Move large format-specific logic into sub-pipelines where needed.

## ECS version

Set the pipeline ECS reference version explicitly at the top of `processors` (after any introductory processors you already use). **Use `9.3.0`** — do not pin an older ECS version.

```yaml
  - set:
      field: ecs.version
      tag: set_ecs_version
      value: '9.3.0'
```

## Rename vs set (mapping to ECS)

When moving a value from a **custom or vendor field** into an **ECS field**, **prefer the `rename` processor** so the source field is removed and you avoid duplicate data. Use `set` with `copy_from` only when you must keep the source field or when `rename` is not applicable.

## Processor tags

**Every processor** in the pipeline should have a `tag` (not only processors that can fail). Tags make failures and telemetry attributable to a specific step.

## CEL-only opening processors (Agentless metadata and error-only documents)

For **CEL-based** integrations only, include these **before** the standard `message` → `event.original` handling when they apply:

- **`remove`**: drop Agentless metadata fields (`organization`, `division`, `team`) when all are strings, so they do not collide with ECS. Use `ignore_missing: true` and a conditional `if`.
- **`terminate`**: stop processing when the document is an error placeholder from the collector (`ctx.error?.message != null && ctx.message == null && ctx.event?.original == null`).

**Non-CEL** integrations (logs, syslog, filebeat-style inputs) **must not** copy this block blindly — those fields and error shapes are specific to the CEL/Agentless path. See the `create-integration` skill: the orchestrator must only expect this block when the data stream uses CEL input.

## Standard opening: ECS, optional CEL block, JSE00001, then parse `event.original`

After the optional CEL-only processors, the pipeline should follow this shape. **All parsing** (`json`, `csv`, `grok`, etc.) runs on **`event.original`**. **Never overwrite or mutate `event.original`** in later processors — derive structured fields into other paths (for example `json`, `_temp.*`, ECS fields).

```yaml
description: Parse <dataset> events.
processors:
  - set:
      field: ecs.version
      tag: set_ecs_version
      value: '9.3.0'

  # --- CEL input only (omit for log/syslog-only streams) ---
  - remove:
      field:
        - organization
        - division
        - team
      ignore_missing: true
      if: ctx.organization instanceof String && ctx.division instanceof String && ctx.team instanceof String
      tag: remove_agentless_tags
      description: >-
        Removes the fields added by Agentless as metadata,
        as they can collide with ECS fields.
  - terminate:
      tag: data_collection_error
      if: ctx.error?.message != null && ctx.message == null && ctx.event?.original == null
      description: error message set and no data to process.
  # --- end CEL-only ---

  - rename:
      field: message
      tag: rename_message_to_event_original
      target_field: event.original
      ignore_missing: true
      description: Renames the original `message` field to `event.original` to store a copy of the original message. The `event.original` field is not touched if the document already has one; it may happen when Logstash sends the document.
      if: ctx.event?.original == null
  - remove:
      field: message
      tag: remove_message
      ignore_missing: true
      description: The `message` field is no longer required if the document has an `event.original` field.
      if: ctx.event?.original != null

  # Parse (always read from event.original; do not modify event.original)
  - json:
      field: event.original
      target_field: json
      tag: parse_json
      if: ctx.event?.original != null

  # ... normalize, enrich, ECS categorization, cleanup ...

  - append:
      field: tags
      value: preserve_original_event
      allow_duplicates: false
      if: ctx.error?.message != null

on_failure:
  - append:
      field: error.message
      value: >-
        Processor '{{{ _ingest.on_failure_processor_type }}}'
        {{{#_ingest.on_failure_processor_tag}}}with tag '{{{ _ingest.on_failure_processor_tag }}}'
        {{{/_ingest.on_failure_processor_tag}}}failed with message '{{{ _ingest.on_failure_message }}}'
  - set:
      field: event.kind
      tag: set_pipeline_error_to_event_kind
      value: pipeline_error
  - append:
      field: tags
      value: preserve_original_event
      allow_duplicates: false
```

## Single-path pattern (linear pipeline)

Use this pattern when one parser flow handles all events. Combine the **standard opening** (ECS version, optional CEL-only block, JSE00001 rename/remove, parse from `event.original` without mutating it), middle processors with **tags on every step**, and the **pipeline-level `on_failure`** and **conditional `append` for `preserve_original_event`** shown above.

Example middle section (illustrative):

```yaml
  - grok:
      field: event.original
      patterns:
        - '^...$'
      tag: parse_main

  - date:
      field: some.time
      target_field: '@timestamp'
      formats: [ISO8601]
      tag: parse_timestamp
  - convert:
      field: http.response.status_code
      type: long
      ignore_missing: true
      tag: convert_status

  - user_agent:
      field: user_agent.original
      ignore_missing: true
      tag: enrich_user_agent
  - geoip:
      field: source.ip
      target_field: source.geo
      ignore_missing: true
      tag: enrich_source_geo
  - geoip:
      database_file: GeoLite2-ASN.mmdb
      field: source.ip
      target_field: source.as
      properties:
        - asn
        - organization_name
      ignore_missing: true
      tag: enrich_source_asn
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

  - set:
      field: event.kind
      tag: set_event_kind
      value: event
  - append:
      field: event.category
      tag: append_event_category_web
      value: web
  - remove:
      field: temp
      ignore_missing: true
      tag: remove_temp
```

## Branching pattern (router + sub-pipelines)

Use branching when event formats or object models diverge:
- format-based branching (for example JSON vs text)
- class/category-based branching (for example OCSF class/category routing)
- object-presence branching (`ctx.ocsf.user != null`)

Pattern:

```yaml
processors:
  - pipeline:
      name: '{{ IngestPipeline "pipeline_branch_json" }}'
      if: ctx.event?.original != null && ctx.event.original.startsWith('{')
      ignore_missing_pipeline: true
      tag: route_json
  - pipeline:
      name: '{{ IngestPipeline "pipeline_branch_text" }}'
      if: ctx.event?.original != null && !ctx.event.original.startsWith('{')
      ignore_missing_pipeline: true
      tag: route_text
```

In large integrations, keep `default.yml` as the router and put branch logic in files like:
- `pipeline_object_<name>.yml`
- `pipeline_category_<name>.yml`

See `references/branching-patterns.md` for full patterns from `amazon_security_lake`.

## Sub-pipeline routing for multi-log-type integrations

When a data stream receives multiple distinct log types (for example a firewall that emits traffic, auth, and DNS logs in the same stream), **do not implement all parsing in a single monolithic `default.yml`**. Use `default.yml` as a thin router that detects the log type and delegates to a dedicated sub-pipeline per type.

### File layout

```text
elasticsearch/ingest_pipeline/
  default.yml              # router only — detects log type, calls sub-pipelines
  pipeline-<type>.yml      # one file per log type (e.g. pipeline-traffic.yml)
```

### Router pattern in `default.yml`

Use the same **`ecs.version`**, **JSE00001** `rename`/`remove` pair for `message`, and **full pipeline-level `on_failure`** as in the standard opening. The router only branches sub-pipelines; it does not parse payloads.

```yaml
processors:
  - set:
      field: ecs.version
      tag: set_ecs_version
      value: '9.3.0'
  - rename:
      field: message
      tag: rename_message_to_event_original
      target_field: event.original
      ignore_missing: true
      if: ctx.event?.original == null
  - remove:
      field: message
      tag: remove_message
      ignore_missing: true
      if: ctx.event?.original != null
  - pipeline:
      name: '{{ IngestPipeline "pipeline-traffic" }}'
      if: 'ctx.event?.original != null && ctx.event.original.contains("TRAFFIC")'
      tag: route_traffic
  - pipeline:
      name: '{{ IngestPipeline "pipeline-auth" }}'
      if: 'ctx.event?.original != null && ctx.event.original.contains("AUTH")'
      tag: route_auth
  - pipeline:
      name: '{{ IngestPipeline "pipeline-dns" }}'
      if: 'ctx.event?.original != null && ctx.event.original.contains("DNS")'
      tag: route_dns
on_failure:
  - append:
      field: error.message
      value: >-
        Processor '{{{ _ingest.on_failure_processor_type }}}'
        {{{#_ingest.on_failure_processor_tag}}}with tag '{{{ _ingest.on_failure_processor_tag }}}'
        {{{/_ingest.on_failure_processor_tag}}}failed with message '{{{ _ingest.on_failure_message }}}'
  - set:
      field: event.kind
      tag: set_pipeline_error_to_event_kind
      value: pipeline_error
  - append:
      field: tags
      value: preserve_original_event
      allow_duplicates: false
```

### Rules

- `default.yml` must contain **only** routing logic and `on_failure` handling — no field parsing.
- Each sub-pipeline handles parsing, ECS mapping, and categorization for its own log type.
- Each sub-pipeline must have its own `on_failure` block.
- Name sub-pipeline files `pipeline-<type>.yml` where `<type>` matches the log type identifier used in the routing condition.
- Each log type gets its own pipeline test fixture file following the naming convention `test-<package>-<datastream>-<type>-sample.log`.

## Processor ordering and performance

- run cheap existence checks before expensive operations
- drop early if records are out of scope
- prefer `dissect` over `grok` for stable delimited formats
- **never use a `script` processor when a built-in processor can do the job** — `set`, `rename`, `remove`, `append`, `convert`, `dissect`, `grok`, `gsub`, `lowercase`, `uppercase`, and `trim` are all faster than Painless and easier to review. See the cost tiers in `references/processor-cookbook.md` → **Processor performance guide**.
- use enrichment processors (`geoip`, `user_agent`) only when needed
- always anchor `grok` patterns with `^` and `$` — without anchors the regex engine scans the entire input string looking for a partial match, which is slow and can produce incorrect results on noisy log lines

## Mustache template syntax in processor values

Ingest pipeline processors use Mustache templates to reference field values in `value`, `message`, and similar string parameters. Use **triple braces** `{{{field}}}` with **single quotes** — never double braces or double quotes:

```yaml
# CORRECT — triple braces, single quotes
- append:
    field: related.user
    value: '{{{user.target.email}}}'
    allow_duplicates: false
    if: ctx.user?.target?.email != null

# WRONG — double braces HTML-escape the value; double quotes
- append:
    field: related.user
    value: "{{user.target.email}}"
    allow_duplicates: false
    if: ctx.user?.target?.email != null
```

Why: Mustache double braces `{{...}}` HTML-encode the value (e.g., `&` becomes `&amp;`), which corrupts data in ingest pipelines. Triple braces `{{{...}}}` emit the raw value. Single quotes prevent YAML from interpreting braces.

**Exception:** `{{ IngestPipeline "..." }}` in `pipeline.name` is a Go template directive processed at build time, not a Mustache template — it correctly uses double braces.

## Error handling essentials

Use pipeline-level `on_failure` as the main error reporting mechanism.

Recommended baseline (order matters):
- **append** contextual `error.message` first using `_ingest.on_failure_*` variables (full template in the standard opening example)
- **set** `event.kind: pipeline_error` (with a `tag` on the `set` processor)
- **append** `preserve_original_event` to `tags` when you need to retain the failed document for triage
- give **every** processor a `tag` (not only processors that can fail)

Use processor-level `on_failure` for local cleanup or fallback parsing, not as the primary global error message path.

See `references/error-handling-patterns.md` for full examples and tradeoffs (`ignore_failure`, `fail`, processor-level `on_failure`).

## event.original handling (JSE00001)

The `elastic-package build` validator enforces that pipelines correctly handle the `message` to `event.original` rename. This check is known as JSE00001. New packages must comply; some legacy packages exclude it via `validation.yml`.

### Required two-processor pattern

Every pipeline that consumes a `message` field must include both processors (typically **after** `ecs.version` and **after** any CEL-only `remove`/`terminate` steps when applicable):

```yaml
- rename:
    field: message
    tag: rename_message_to_event_original
    target_field: event.original
    ignore_missing: true
    description: Renames the original `message` field to `event.original` to store a copy of the original message. The `event.original` field is not touched if the document already has one; it may happen when Logstash sends the document.
    if: ctx.event?.original == null
- remove:
    field: message
    tag: remove_message
    ignore_missing: true
    description: The `message` field is no longer required if the document has an `event.original` field.
    if: ctx.event?.original != null
```

Step 1 (`rename`): moves `message` into `event.original`, but only when `event.original` is not already populated (idempotent when a prior pipeline or Logstash has already set it).

Step 2 (`remove`): removes the redundant `message` field when `event.original` is present (after rename or from an upstream producer).

### Do NOT add an `event.original` removal processor at the end of the pipeline

Some existing integrations contain a `remove` processor that deletes `event.original` at the end of the pipeline when `preserve_original_event` is not in `tags`. **This pattern is deprecated and must not be used in new pipelines.** The removal of `event.original` for storage optimization is now handled by a separate final pipeline outside the integration. Do not copy this pattern from reference integrations that still have it — it is legacy.

### Reference

The two-processor JSE00001 pattern (rename + remove of `message`) shown above is required and complete. Do not add any additional `event.original` processors beyond those two.

## Timezone handling (`tz_offset`)

For data streams that include the `tz_offset` manifest var (syslog streams where messages lack a timezone), set `event.timezone` from `_conf.tz_offset` early in the pipeline, before any date parsing:

```yaml
- set:
    field: event.timezone
    tag: set_event_timezone
    value: '{{{_conf.tz_offset}}}'
    if: ctx._conf?.tz_offset != null && ctx._conf.tz_offset != ''
```

This ensures date processors can apply the correct timezone when parsing timestamps that have no timezone component.

## Syslog structured data (RFC 5424 SD-ELEMENT) parsing

For vendor `key=value` payloads and RFC 5424 SD-ELEMENT blocks, three strategies are available: KV with `trim_value` (simplest, Strategy 1), `SYSLOG5424SD` grok + KV with regex splits (Strategy 2), and Painless for edge cases with embedded equals or mixed quoting (Strategy 3).

Prefer Strategy 1 or 2; use Painless only when KV edge cases demand it.

See `references/grok-recipes.md` → **Syslog structured data strategies** for full code examples, key settings, and reference implementations.

## Keyword fields delivered as numbers

Fields that carry identifiers, protocol codes, or other opaque values must be declared as `keyword` in `fields.yml` — even when the source data delivers them as numbers. Common examples:

- network protocol numbers (`network.iana_number`)
- port numbers used as identifiers
- error codes, result codes, status codes
- SNMP OIDs, event IDs, object class codes

Do **not** add a `convert` processor to stringify these values. Elasticsearch silently coerces numbers into `keyword` strings at index time, so the pipeline can pass the raw numeric value through unchanged.

The field declaration in `fields.yml`:
```yaml
- name: network.iana_number
  type: keyword
  description: IANA protocol number.
```

Because the test runner compares raw value types against declared field types, it will flag `6` (long) as a mismatch for `keyword`. Declare the field in `numeric_keyword_fields` in the pipeline test config so the runner accepts the numeric representation without requiring the fixture to artificially stringify the value. See `integration-testing/references/pipeline-testing.md` for the config syntax.

## Vendor field naming

Preserve vendor field names exactly as they appear in the source. Do not rename, reformat, or normalize vendor-specific field names — the only permitted renaming is mapping a vendor field to an ECS field (e.g. renaming `src_ip` to `source.ip`). When a vendor field has no ECS equivalent, keep it under a vendor-namespaced prefix (e.g. `vendor.product.field_name`) using the original name from the source.

## related.ip population

**Every IP address present in the document must be appended to `related.ip`.** This includes source, destination, client, server, host, and any other IP fields — whatever applies to the event type.

Use one `append` processor per IP field, with `ignore_missing: true` so it is a no-op when the field is absent. Place these processors after all IP fields have been set (for example after `geoip`, `convert`, and any ECS rename steps) and before the cleanup `remove` processors.

```yaml
  - append:
      field: related.ip
      tag: append_source_ip_to_related
      value: '{{{source.ip}}}'
      allow_duplicates: false
      if: ctx.source?.ip != null
  - append:
      field: related.ip
      tag: append_destination_ip_to_related
      value: '{{{destination.ip}}}'
      allow_duplicates: false
      if: ctx.destination?.ip != null
  # repeat the same pattern for client.ip, server.ip, host.ip, and any other IP fields the pipeline sets
```

Rules:
- Use `allow_duplicates: false` on every append to avoid repeated values.
- Add an `if` guard on every processor so it skips fields absent in the event.
- Add one `append` per IP field the pipeline actually writes — do not add processors for fields the pipeline never sets.

## Painless script best practices

**Before writing any `script` processor, you MUST check whether a built-in processor can do the same job.** `script` is the slowest general-purpose processor (Painless compilation + per-document execution). The following operations have dedicated processors that are cheaper and easier to review:

| If you need to … | Use this processor, not `script` |
|---|---|
| Copy, move, or rename a field | `rename` or `set` with `copy_from` |
| Set a constant or derived value | `set` |
| Add a value to a list | `append` |
| Change a field's type | `convert` |
| Extract a substring from a delimited string | `dissect` |
| Extract a substring with regex | `grok` |
| Replace characters in a string | `gsub` |
| Normalize case | `lowercase` / `uppercase` |

Only reach for `script` when no combination of built-in processors can express the logic — for example, ECS categorization lookup tables with 5+ entries (Pattern A), complex conditional arithmetic, or edge-case string parsing that `dissect` and `grok` genuinely cannot handle.

**Case-insensitive comparisons — use `equalsIgnoreCase()` when casing is unpredictable**

Syslog and vendor devices are often inconsistent about casing, so Painless scripts comparing vendor-specific free-text fields should use `equalsIgnoreCase()` rather than `==`. However, **apply this judgement contextually, not blanket:**

- **Use `equalsIgnoreCase()`** when the vendor field value may vary in casing between devices, firmware versions, or log sources (e.g. action fields like `allow/Allow/ALLOW`, severity strings, free-text status fields).
- **Use `==`** when the API or spec defines a fixed lowercase enum and the values are always delivered as-specified (e.g. ECS categorization fields, API response fields documented as lowercase-only enums). Adding `equalsIgnoreCase()` to fixed-enum fields adds noise without value.

```painless
// Correct for unpredictable vendor casing
if (ctx.vendor?.action?.equalsIgnoreCase('allow')) { ... }

// Correct for a fixed lowercase API enum — == is appropriate here
if (ctx.json?.event_type == 'login') { ... }

// Incorrect for unpredictable casing — breaks on "Allow", "ALLOW"
if (ctx.vendor?.action == 'allow') { ... }
```

**Access `ctx` directly in script bodies — no null-safe operators**

In `script` processor `source` blocks, access `ctx` fields directly. Use explicit null checks instead of the null-safe `?.` operator.

```painless
// Correct — direct access with explicit null check
if (ctx.source != null && ctx.source.ip != null) { ... }

// Incorrect — null-safe operator in a script body
if (ctx.source?.ip != null) { ... }
```

Note: null-safe `?.` is acceptable in processor `if` conditions (YAML), which are a different Painless execution context:
```yaml
- append:
    field: related.ip
    value: '{{{source.ip}}}'
    if: ctx.source?.ip != null
```

**Other rules**
- Every `script` processor must have a `tag` and a `description`.
- Keep scripts short and scoped — move complex logic into helper variables inside the script, not across multiple script processors.
- **Do not use `script` when built-in processors suffice** — see the mandatory checklist table at the top of this section.

## ECS categorization mapping

When mapping source event types or actions to `event.category`, `event.type`, `event.outcome`, and `event.action`, use the patterns in `references/processor-cookbook.md` → **ECS categorization mapping patterns**:

- **Pattern A** (script with `params` lookup table): recommended for **5+ mappings**. Mapping data in `params` enables Painless compilation caching and keeps the script body generic.
- **Pattern B** (`set` processors with conditionals): for **fewer than 5 mappings** where a script is overkill.
- **Pattern C** (sub-pipeline): for **100+ mappings**, extract the categorization into a dedicated sub-pipeline file.

**Do NOT** use bulk `append` processors (2 per event type = 50+ processors for 25 types) or inline Painless `if`/`else` chains without `params` (defeats compilation caching). These are explicit anti-patterns — see the cookbook for details.

## Grok best practices

- prefer `dissect` when structure is fixed
- use simpler grok patterns where possible
- always anchor grok patterns with `^` and `$`:
  ```yaml
  # Correct — anchored, fails fast on non-matching lines
  patterns:
    - '^%{IPORHOST:source.ip} %{USER:user.name} %{DATA:message}$'

  # Incorrect — unanchored, scans the whole string for a partial match
  patterns:
    - '%{IPORHOST:source.ip} %{USER:user.name} %{DATA:message}'
  ```
- avoid unnecessary backtracking-heavy custom regex
- add a `tag` to every grok (and every other) processor

For grok syntax (three expression forms, inline regex, type coercion, `pattern_definitions`), syslog header splitting recipes, and common mistakes, see `references/grok-recipes.md`.

## Prohibited patterns

These patterns exist in many legacy integrations but **must not** be used in new or updated pipelines. Do not copy them from reference integrations.

### Never set `event.ingested`

The `event.ingested` field is managed by Elasticsearch outside the integration pipeline. **Do not** add a `set` processor for `event.ingested` in any integration pipeline. This includes patterns like:

```yaml
# PROHIBITED — do not use
- set:
    field: event.ingested
    value: '{{{_ingest.timestamp}}}'
```

The pipeline **should** set `@timestamp` from the original event's timestamp. When the source data contains multiple timestamps, map them as follows:

- **`@timestamp`**: the primary event timestamp parsed from the source data. This is required.
- **`event.created`**: when the event was first created or recorded by the source system (if different from `@timestamp`).
- **`event.start`**: when an activity or period began (e.g., session start, connection start).
- **`event.end`**: when an activity or period ended (e.g., session end, connection close).

If a source timestamp does not match the semantics of `event.created`, `event.start`, or `event.end`, map it to a custom field under the vendor namespace with `type: date` in `fields.yml` and use a `date` processor with the appropriate `target_field`.

### Never use `preserve_duplicate_custom_fields`

The `preserve_duplicate_custom_fields` tag pattern — where source fields are copied to ECS fields using `set` with `copy_from` and the originals are conditionally retained — is a legacy anti-pattern. **Do not use it in any new or updated pipeline.** Do not add a `preserve_duplicate_custom_fields` manifest variable, tag, or conditional logic.

Instead, follow these field mapping rules:
- When a source field maps to an ECS field, use `rename` to move it directly. The source field is removed and no duplicate exists.
- When a type conversion is needed (e.g., string to date, string to long), use the appropriate processor (`date`, `convert`, `set` with `copy_from`) to populate the ECS target field, then `remove` the source field in the cleanup section at the end of the pipeline.
- **Never design a pipeline that needs to preserve both the original vendor field and the ECS copy.** The ECS field is the canonical location.

If you encounter this pattern in a reference integration, ignore it — it is legacy.

### Never add an `event.original` removal processor at the end

As documented in the JSE00001 section above: do not add a `remove` processor for `event.original` at the end of the pipeline. This is handled by a separate final pipeline.

## References

- `references/processor-cookbook.md` — processor selection, parsing/normalization/enrichment examples, ECS categorization mapping patterns (Pattern A/B/C + anti-patterns)
- `references/branching-patterns.md`
- `references/error-handling-patterns.md`
- `references/grok-recipes.md` — grok syntax, type coercion, syslog header recipes, common mistakes, pattern library link
- `references/builder-subagent-guidance.md` — **always-embedded** subagent operating manual: scope boundaries, skill-load sequence, input data paths (CEL-first vs Direct), 9-step pipeline build workflow, "review generated output, never hand-edit expected JSON", reporting contract

