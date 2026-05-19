# Common input patterns

Patterns that appear in virtually every Elastic integration input template regardless of input type. Load this file before any type-specific guide.

## Tags

### `preserve_original_event`

The `preserve_original_event` tag must be conditional so users can opt in or out:

```yaml
{{#if preserve_original_event}}
  - preserve_original_event
{{/if}}
```

### User-defined tags

User-defined tags from the manifest variable are iterated with an `{{#each}}` block:

```yaml
{{#each tags as |tag|}}
  - {{tag}}
{{/each}}
```

### `forwarded` tag and `publisher_pipeline.disable_host`

When the default tags in the data stream manifest include `forwarded`, the template must include the corresponding `publisher_pipeline.disable_host` directive. These two are always coupled:

```yaml
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
```

The manifest `vars` section should define `tags` with a default that includes both `forwarded` and the dataset tag:

```yaml
- name: tags
  type: text
  title: Tags
  multi: true
  required: true
  show_user: false
  default:
    - forwarded
    - <package>-<datastream>
```

## Custom processors passthrough

Integration templates must pass through user-defined processors with a top-level conditional block:

```yaml
{{#if processors}}
processors:
{{processors}}
{{/if}}
```

This block must be at the top level of the input configuration, not nested inside another key. Integration-specific processors (e.g., `script` processors that transform data before indexing) are separate from this passthrough and appear elsewhere in the template.

## Variables over hardcoded values

All user-configurable values must use Handlebars variables sourced from the data stream manifest. Nothing that a user might need to change should be hardcoded in the template.

Applies to:
- API endpoints, base URLs, resource paths
- Credentials, tokens, API keys
- Bucket names, queue URLs, topic IDs, container names
- Timeouts, intervals, batch sizes, and other tuning parameters
- Proxy URLs and SSL configuration

Each variable must have a sensible default defined in the manifest `vars` section. Sensitive values (credentials, tokens) should use `type: password` and `show_user: true` in the manifest.

## What to flag during review

| Issue | Severity | Description |
|---|---|---|
| Hardcoded credentials or tokens | **CRITICAL** | Credentials must always be manifest variables with `type: password` |
| Hardcoded API URLs or endpoints | **MEDIUM** | URLs should be variables so users can point to different environments |
| Hardcoded bucket/queue/topic IDs | **MEDIUM** | Cloud resource identifiers must be user-configurable |
| Missing `forwarded` / `publisher_pipeline.disable_host` coupling | **MEDIUM** | If default tags include `forwarded`, the `publisher_pipeline.disable_host` block must be present, and vice versa |
| Processors passthrough not at top level | **LOW** | The `{{#if processors}}` block must not be nested inside another key |
| Missing `preserve_original_event` conditional | **MEDIUM** | The tag should be conditional, not hardcoded |
| Hardcoded timeouts or intervals | **LOW** | Tuning parameters should be variables with defaults |
