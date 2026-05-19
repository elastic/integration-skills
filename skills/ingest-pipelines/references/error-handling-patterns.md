# ingest pipeline error handling patterns

This guide focuses on resilient failure behavior and actionable debugging output.

## Recommended top-level `on_failure`

Use this pattern in `default.yml` to ensure all uncaught failures are visible:

```yaml
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

Why:
- Appending `error.message` first preserves the full `_ingest.on_failure_*` context for triage.
- `event.kind: pipeline_error` supports clean filtering and dashboards.
- `preserve_original_event` on failure helps post-failure diagnostics.

## Processor tag requirement

**Every** processor in the pipeline should include a `tag` (not only processors that can fail).

```yaml
- grok:
    field: event.original
    patterns: ['^%{IP:source.ip} %{GREEDYDATA:message}$']
    tag: parse_source_ip
```

Without tags, error messages lose key context and triage becomes slower.

## Processor-level `on_failure`: when and when not

Use processor-level `on_failure` for:
- cleanup (`remove` invalid temporary fields)
- fallback operations on known parse failures
- local annotations that complement top-level errors

Avoid using processor-level `on_failure` as the only error-reporting path.
If a processor `if` expression itself fails, control may bypass that local handler and fall through to top-level `on_failure`.

### Example: date parse fallback detail

```yaml
- date:
    field: nginx.access.time
    target_field: '@timestamp'
    formats:
      - dd/MMM/yyyy:H:m:s Z
    tag: parse_access_time
    on_failure:
      - append:
          field: error.message
          value: '{{{_ingest.on_failure_message}}}'
```

## `ignore_failure` usage

Use `ignore_failure: true` only when failure should not block ingestion.

Good candidates:
- optional enrichment (`geoip`, `user_agent`)
- best-effort cleanup/normalization
- non-critical parsing of auxiliary fields

Example:

```yaml
- geoip:
    field: source.ip
    target_field: source.geo
    ignore_failure: true
    ignore_missing: true
    tag: enrich_source_geo
```

Avoid `ignore_failure` on required parse steps that define event shape.

## `fail` processor usage

Use `fail` for invalid required input or unrecoverable branch conditions.

### Input validation gate

```yaml
- fail:
    if: ctx.json == null || !(ctx.json instanceof Map)
    message: missing json object in input document
    tag: validate_json_input
```

### Critical parser escalation (inside `on_failure`)

```yaml
- kv:
    field: message
    field_split: ' '
    value_split: '='
    tag: parse_kv
    on_failure:
      - fail:
          message: 'unable to parse key-values: {{{ _ingest.on_failure_message }}}'
          tag: fail_parse_kv
```

## Pattern catalog

### 1) Minimal pipeline-level error pattern (lightweight)

```yaml
on_failure:
  - set:
      field: error.message
      value: '{{{_ingest.on_failure_message}}}'
```

Use this only for simple integrations where richer diagnostics are not yet needed.

### 2) Full-context pipeline-level error pattern (preferred)

Use the recommended top-level `on_failure` block from the section above. This is the standard pattern for `default.yml` in all integrations.

### 3) Conditional preserve tag before successful pipeline end

When the collector set an error but ingestion continued, tag the document so operators can find it:

```yaml
processors:
  - append:
      field: tags
      tag: append_preserve_on_collector_error
      value: preserve_original_event
      allow_duplicates: false
      if: ctx.error?.message != null
```

(This is separate from the `on_failure` block; use together with pattern 2.)

### 4) Local cleanup in processor `on_failure`

```yaml
- json:
    field: event.original
    target_field: json
    tag: parse_json
    on_failure:
      - remove:
          field: json
          ignore_missing: true
      - append:
          field: error.message
          value: '{{{_ingest.on_failure_message}}}'
```

## Review checklist

- Top-level `on_failure` exists in every primary ingest pipeline.
- Every processor has a `tag`.
- Required parse steps do not silently ignore failure.
- `ignore_failure` is limited to optional/non-critical operations.
- Error messages include enough context to locate the failed processor.
