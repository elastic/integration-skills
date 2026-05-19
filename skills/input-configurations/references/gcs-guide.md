# Google Cloud Storage input guide

Complete reference for building and reviewing `gcs.yml.hbs` templates in Elastic integrations. This input polls Google Cloud Storage buckets for objects and processes them as log events.

> **Documentation**: [GCS Input Reference](https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-input-gcs.html)

## File location

```
packages/<package>/data_stream/<data_stream>/agent/stream/gcs.yml.hbs
```

## Required structure

```yaml
project_id: {{project_id}}

buckets:
  - name: {{bucket_name}}
    {{#if file_selectors}}
    file_selectors:
    {{#each file_selectors as |selector|}}
      - regex: "{{selector.regex}}"
    {{/each}}
    {{/if}}

{{#if credentials_file}}
credentials_file: {{credentials_file}}
{{/if}}
{{#if credentials_json}}
credentials_json: {{credentials_json}}
{{/if}}

{{#if poll_interval}}
poll_interval: {{poll_interval}}
{{/if}}
{{#if parse_json}}
parse_json: {{parse_json}}
{{/if}}
{{#if timestamp_epoch}}
timestamp_epoch: {{timestamp_epoch}}
{{/if}}

tags:
{{#if preserve_original_event}}
  - preserve_original_event
{{/if}}
{{#each tags as |tag|}}
  - {{tag}}
{{/each}}
{{#contains "forwarded" tags}}
publisher_pipeline.disable_host: true
{{/contains}}

{{#if processors}}
processors:
{{processors}}
{{/if}}
```

## Validation rules

### 1. Project ID required

Every GCS template must specify the GCP project ID via a variable.

```yaml
# correct
project_id: {{project_id}}

# wrong -- hardcoded
project_id: my-project-12345

# wrong -- missing
# no project_id specified
```

### 2. Bucket name required and variable

At least one bucket must be specified, and the name must reference a Handlebars variable.

```yaml
# correct
buckets:
  - name: {{bucket_name}}

# wrong -- hardcoded
buckets:
  - name: my-hardcoded-bucket
```

### 3. Authentication must be provided

Integrations should support both `credentials_file` and `credentials_json` to cover different deployment models. Workload Identity (no explicit credentials) is acceptable when running on GCE/GKE with an attached service account.

```yaml
# correct -- both options available
{{#if credentials_file}}
credentials_file: {{credentials_file}}
{{/if}}
{{#if credentials_json}}
credentials_json: {{credentials_json}}
{{/if}}

# acceptable -- workload identity (no explicit credentials needed)
# when running on GCE/GKE with attached service account

# wrong -- hardcoded credentials
credentials_json: '{"type": "service_account", "project_id": "..."}'
```

### 4. File selectors must use variables

When file filtering is needed, the regex patterns must be user-configurable, not hardcoded.

```yaml
# correct
{{#if file_selectors}}
file_selectors:
{{#each file_selectors as |selector|}}
  - regex: "{{selector.regex}}"
{{/each}}
{{/if}}

# wrong -- hardcoded patterns
file_selectors:
  - regex: ".*\\.log$"
```

## Authentication patterns

### Service account credentials file

The user provides a path to a service account JSON key file on the agent host.

```yaml
{{#if credentials_file}}
credentials_file: {{credentials_file}}
{{/if}}
```

### Service account credentials JSON

The user pastes the service account JSON content directly into the integration configuration. The manifest should use `type: password` for this field.

```yaml
{{#if credentials_json}}
credentials_json: {{credentials_json}}
{{/if}}
```

### Workload Identity

When the agent runs on GCE or GKE with an attached service account, no explicit credentials are needed. The GCS client library uses Application Default Credentials automatically. The integration documentation should mention this as a supported option.

If both `credentials_file` and `credentials_json` are omitted, the client falls back to ADC. This is the expected behavior for Workload Identity deployments.

## Polling and content handling

### Poll interval

```yaml
{{#if poll_interval}}
poll_interval: {{poll_interval}}
{{/if}}
```

Controls how frequently the input checks the bucket for new or modified objects. The default varies by implementation. Set appropriately based on how often new objects appear in the bucket.

### JSON parsing

```yaml
{{#if parse_json}}
parse_json: {{parse_json}}
{{/if}}
```

When enabled, the input parses each object as JSON. Useful for structured log files (e.g., Cloud Audit Logs exported to GCS in JSON format). When disabled, each line of the object becomes a separate event.

### Timestamp epoch

```yaml
{{#if timestamp_epoch}}
timestamp_epoch: {{timestamp_epoch}}
{{/if}}
```

Sets a starting point for object processing. Objects with a last-modified time before this epoch are skipped. Useful to avoid reprocessing historical data on first startup.

## Common configuration patterns

### Basic GCS collection

```yaml
project_id: {{project_id}}

buckets:
  - name: {{bucket_name}}

{{#if credentials_file}}
credentials_file: {{credentials_file}}
{{/if}}
{{#if credentials_json}}
credentials_json: {{credentials_json}}
{{/if}}
```

### With file filtering

```yaml
project_id: {{project_id}}

buckets:
  - name: {{bucket_name}}
    {{#if file_selectors}}
    file_selectors:
    {{#each file_selectors as |selector|}}
      - regex: "{{selector.regex}}"
    {{/each}}
    {{/if}}
    {{#if max_workers}}
    max_workers: {{max_workers}}
    {{/if}}

{{#if credentials_file}}
credentials_file: {{credentials_file}}
{{/if}}
```

### With object prefix filtering

```yaml
project_id: {{project_id}}

buckets:
  - name: {{bucket_name}}
    {{#if bucket_list_prefix}}
    bucket_list_prefix: {{bucket_list_prefix}}
    {{/if}}

{{#if credentials_file}}
credentials_file: {{credentials_file}}
{{/if}}
{{#if credentials_json}}
credentials_json: {{credentials_json}}
{{/if}}
```

`bucket_list_prefix` limits the bucket listing to objects whose key starts with the given prefix. This is more efficient than `file_selectors` when the filtering can be expressed as a prefix, because it reduces the number of objects the GCS API returns.

### JSON log processing

```yaml
project_id: {{project_id}}

buckets:
  - name: {{bucket_name}}
    parse_json: true

{{#if credentials_file}}
credentials_file: {{credentials_file}}
{{/if}}
{{#if credentials_json}}
credentials_json: {{credentials_json}}
{{/if}}
```

## Advanced patterns

### Encoding and content type

```yaml
{{#if encoding}}
encoding: {{encoding}}
{{/if}}
{{#if content_type}}
content_type: {{content_type}}
{{/if}}
```

Specify encoding for objects that are not UTF-8. Content type can override automatic detection when needed.

### Parallel workers per bucket

```yaml
buckets:
  - name: {{bucket_name}}
    {{#if max_workers}}
    max_workers: {{max_workers}}
    {{/if}}
```

Controls how many objects are processed in parallel within a single bucket. Higher values improve throughput for buckets with many small objects but increase memory usage.

## Parameters reference

| Parameter | Type | Description |
|---|---|---|
| `project_id` | string | GCP project ID |
| `buckets` | array | List of bucket configurations |
| `buckets[].name` | string | Bucket name |
| `buckets[].file_selectors` | array | Regex patterns for filtering objects |
| `buckets[].max_workers` | int | Parallel workers per bucket |
| `buckets[].bucket_list_prefix` | string | Object key prefix filter |
| `credentials_file` | string | Path to service account JSON key file |
| `credentials_json` | string | Service account JSON key content |
| `poll_interval` | duration | Polling interval for new objects |
| `parse_json` | bool | Parse objects as JSON |
| `timestamp_epoch` | int | Starting timestamp (epoch seconds) |
| `encoding` | string | Character encoding for object content |
| `content_type` | string | Content type override |

## Review checklist

### Configuration
- [ ] `project_id` uses a variable
- [ ] `buckets[].name` uses a variable
- [ ] File selectors are configurable (not hardcoded regex)
- [ ] Poll interval is configurable with a sensible default

### Authentication
- [ ] No hardcoded credentials in the template
- [ ] Both `credentials_file` and `credentials_json` supported
- [ ] Workload Identity documented as an option for GCE/GKE deployments
- [ ] Credential fields use `type: password` in the manifest

### File processing
- [ ] Object prefix filtering (`bucket_list_prefix`) used when applicable
- [ ] Encoding specified for non-UTF-8 content
- [ ] JSON parsing configurable where applicable
- [ ] `timestamp_epoch` available to control initial processing window

### Tags and processors
- [ ] Tags block follows common patterns
- [ ] Processors passthrough at top level
