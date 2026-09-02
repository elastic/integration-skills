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

### Input packages: the shipped pipeline is not attached automatically

Fleet does not attach an input package's `elasticsearch/ingest_pipeline/` to the
data stream the way it does for an integration package. The pipeline is
installed, but nothing points at it on its own — the wiring is the package's own
`pipeline` variable, written out by the template:

```yaml
{{#if pipeline}}
pipeline: {{pipeline}}
{{/if}}
```

`packages/unifiedlogs` carries exactly this block, and its `pipeline` default
does not resolve to the pipeline as installed, so its shipped ingest logic never
runs. If a package ships a pipeline, check that the variable's default names the
installed pipeline rather than a guessed `logs-<package>.<dataset>-default`.

For inputs that deliver a raw log line in `message` (`tcp`, `udp`, `unix`),
`preserve_original_event` only adds the tag — populating `event.original` is the
template's job:

```yaml
{{#if preserve_original_event}}
processors:
- copy_fields:
    fields:
      - from: message
        to: event.original
{{/if}}
```

This is specific to that shape. `winlog` gets the field from `include_xml: true`,
the object-storage and API inputs carry structured payloads rather than a raw
line, and an integration package normally sets it in the ingest pipeline.

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
| `preserve_original_event` without `copy_fields` in a raw-line input package (`tcp`/`udp`/`unix` shape) | **MEDIUM** | Nothing else writes `event.original` for these. Does not apply to `winlog` (`include_xml`), to structured-payload inputs, or to integration packages that set the field in the ingest pipeline |
| Hardcoded timeouts or intervals | **LOW** | Tuning parameters should be variables with defaults |
