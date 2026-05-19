# HTTPJSON input guide

Complete reference for building and reviewing `httpjson.yml.hbs` templates in Elastic integrations.

## Template syntax

HTTPJSON templates use Go templates with `[[` `]]` delimiters (not `{{` `}}`, which are reserved for Handlebars). The Go template layer executes at request/response time inside the agent.

### Variable access

| Variable | Description |
|---|---|
| `.cursor` | Map of persisted cursor values from the previous poll cycle |
| `.last_response.body` | Parsed body of the most recent HTTP response |
| `.last_response.header.Get` | Access response headers, e.g. `[[ .last_response.header.Get "Link" ]]` |
| `.last_response.url.params.Get` | Access URL query parameters from the response URL |
| `.last_response.page` | Zero-indexed page counter incremented per pagination step |
| `.last_event` | The last event produced in the current page |
| `.first_event` | The first event produced in the current page |
| `.body` | The request body being constructed (available in request transforms) |
| `.header.Get` | Access request headers (available in request transforms) |

### Date formatting

Go templates use the reference time `2006-01-02T15:04:05Z07:00` (Mon Jan 2 15:04:05 MST 2006) for format strings. Common patterns:

| Format string | Output example |
|---|---|
| `2006-01-02T15:04:05Z` | `2024-03-15T14:30:00Z` |
| `2006-01-02T15:04:05.000Z` | `2024-03-15T14:30:00.000Z` |
| `2006-01-02` | `2024-03-15` |
| `01/02/2006` | `03/15/2024` |
| `1136214245` | Unix epoch seconds |

### Conditionals

```yaml
value: >-
  [[- if .last_response.body.nextPageToken -]]
  [[- .last_response.body.nextPageToken -]]
  [[- end -]]
```

The conditional evaluates the value; when false or empty, it produces an empty string. This pattern is critical for pagination termination.

### Math operations

```yaml
value: '[[ add .last_response.page 1 ]]'
value: '[[ mul .last_response.body.meta.per_page .last_response.page ]]'
```

## Required structure

Every HTTPJSON template must include these top-level keys in order.

### interval

```yaml
interval: {{interval}}
```

Must reference a Handlebars variable, never hardcoded.

### Request tracer

Two valid styles exist. Use the block format for packages targeting 8.15.0+.

Conditional format (pre-8.15.0 compatibility):

```yaml
{{#if enable_request_tracer}}
request.tracer.filename: "../../logs/httpjson/httpjson-<input-type-name>.ndjson"
request.tracer.maxbackups: 5
{{/if}}
```

Block format (8.15.0+):

```yaml
request.tracer:
  filename: "../../logs/httpjson/httpjson-<input-type-name>.ndjson"
  maxbackups: 5
  enabled: {{enable_request_tracer}}
```

The `<input-type-name>` in the tracer path must match the specific input type name for the data stream (e.g., `httpjson-myapi-events`).

### Request configuration

```yaml
request.method: GET
request.url: {{url}}/api/v1/events
{{#if proxy_url}}
request.proxy_url: {{proxy_url}}
{{/if}}
{{#if ssl}}
request.ssl: {{ssl}}
{{/if}}
request.timeout: {{request_timeout}}
```

- `request.method`: GET or POST
- `request.url`: must use a Handlebars variable for the base URL
- Proxy and SSL are conditional blocks
- Timeout references a manifest variable

### Authentication

See the Authentication patterns section below for all supported methods.

### request.transforms

Transforms modify the request before it is sent. Common uses: setting headers, adding query parameters, injecting cursor values.

```yaml
request.transforms:
  - set:
      target: url.params.since
      value: '[[ .cursor.since ]]'
      default: '[[ now (parseDuration "-{{initial_interval}}") ]]'
  - set:
      target: header.Authorization
      value: 'Bearer {{api_token}}'
```

### response.split

Splits the response body into individual events. Always targets the array field containing the records.

```yaml
response.split:
  target: body.data
  type: array
  ignore_empty_value: true
```

### Pagination

See the Pagination patterns section below.

### Cursor

See the Cursor persistence section below.

### Tags and processors

Follow the common patterns from `common-input-patterns.md`:

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
{{#if processors}}
processors:
{{processors}}
{{/if}}
```

## Validation rules

These nine rules apply to every HTTPJSON template.

### 1. Interval must use a variable

`interval` must reference `{{interval}}`, not a hardcoded value like `60s`.

### 2. Tracer path must match input type name

The tracer filename must contain the specific input type identifier for the data stream. Two valid styles:

- Conditional: `{{#if enable_request_tracer}}request.tracer.filename: "../../logs/httpjson/httpjson-<name>.ndjson"{{/if}}`
- Block: `request.tracer:` with `filename:` and `enabled: {{enable_request_tracer}}`

### 3. response.split on array field with ignore_empty_value

The split must target the correct array field from the API response and include `ignore_empty_value: true` to handle empty responses gracefully:

```yaml
response.split:
  target: body.results
  type: array
  ignore_empty_value: true
```

### 4. Pagination must terminate

Every pagination block must contain a conditional that evaluates to an empty string when there are no more pages. Without this, the agent loops indefinitely.

```yaml
response.pagination:
  - set:
      target: url.params.cursor
      value: >-
        [[- if .last_response.body.meta.next_cursor -]]
        [[- .last_response.body.meta.next_cursor -]]
        [[- end -]]
      fail_on_template_error: true
```

When the API returns no `next_cursor`, the template produces an empty string, which (combined with `fail_on_template_error: true`) stops pagination.

### 5. fail_on_template_error required on pagination sets

All `set` transforms in `response.pagination` that use Go template conditionals must include `fail_on_template_error: true`. This ensures that an empty value (from a termination conditional) correctly signals the end of pagination rather than silently continuing.

### 6. Cursor ignore_empty_value: true

Cursor entries should include `ignore_empty_value: true` so the cursor is not overwritten with empty values on pages that lack the tracked field:

```yaml
cursor:
  since:
    value: '[[ .last_event.timestamp ]]'
    ignore_empty_value: true
```

### 7. No hardcoded credentials

Authentication credentials (tokens, API keys, client secrets, passwords) must always reference Handlebars variables. Hardcoded credentials in templates are a critical security issue.

### 8. Preserve time parameters during pagination

When the request uses time-range parameters (e.g., `since`, `until`, `start_time`, `end_time`), these parameters must be preserved during pagination. If pagination modifies the URL parameters, it must not overwrite existing time bounds. Use `default` to set initial values and cursor values to maintain them:

```yaml
request.transforms:
  - set:
      target: url.params.since
      value: '[[ .cursor.since ]]'
      default: '[[ now (parseDuration "-{{initial_interval}}") ]]'
  - set:
      target: url.params.until
      value: '[[ now ]]'
```

### 9. POST must set response.request_body_on_pagination

When `request.method` is POST, the template must include:

```yaml
response.request_body_on_pagination: true
```

This ensures the original POST body is preserved during pagination requests. Without it, pagination requests revert to empty bodies.

## Pagination patterns

### Cursor-based pagination

The API returns a cursor token; the next request includes it to fetch the next page.

```yaml
response.pagination:
  - set:
      target: url.params.cursor
      value: >-
        [[- if .last_response.body.meta.next_cursor -]]
        [[- .last_response.body.meta.next_cursor -]]
        [[- end -]]
      fail_on_template_error: true
```

### Offset-based pagination

The API accepts an offset parameter. Increment by page size each iteration.

```yaml
response.pagination:
  - set:
      target: url.params.offset
      value: '[[ add .last_response.body.meta.offset .last_response.body.meta.limit ]]'
  - set:
      target: url.params.limit
      value: '[[ .last_response.body.meta.limit ]]'
  - set:
      target: url.params.offset
      value: >-
        [[- if gt (len .last_response.body.data) 0 -]]
        [[- add .last_response.body.meta.offset .last_response.body.meta.limit -]]
        [[- end -]]
      fail_on_template_error: true
```

### Page number pagination

The API accepts a page number parameter.

```yaml
response.pagination:
  - set:
      target: url.params.page
      value: >-
        [[- if .last_response.body.has_more -]]
        [[- add .last_response.page 2 -]]
        [[- end -]]
      fail_on_template_error: true
```

Note: `.last_response.page` is zero-indexed, so add 2 to get the next 1-indexed page number.

### Link-based pagination (Link header)

The API returns a `Link` header with a `next` URL.

```yaml
response.pagination:
  - set:
      target: url.value
      value: >-
        [[- if .last_response.header.Get "Link" -]]
          [[- with (parseLinkHeader (.last_response.header.Get "Link")) -]]
            [[- .next -]]
          [[- end -]]
        [[- end -]]
      fail_on_template_error: true
```

### POST body pagination

For POST APIs where pagination tokens go in the request body. Requires `response.request_body_on_pagination: true`.

```yaml
response.request_body_on_pagination: true
response.pagination:
  - set:
      target: body.pagination_token
      value: >-
        [[- if .last_response.body.pagination_token -]]
        [[- .last_response.body.pagination_token -]]
        [[- end -]]
      fail_on_template_error: true
```

### Sync ID pattern

Some APIs use a two-phase sync model: an initial call returns a sync ID, subsequent calls use it to poll for changes.

```yaml
response.pagination:
  - set:
      target: url.params.sync_id
      value: '[[ .last_response.body.sync_id ]]'
  - set:
      target: url.params.cursor
      value: >-
        [[- if .last_response.body.has_more -]]
        [[- .last_response.body.cursor -]]
        [[- end -]]
      fail_on_template_error: true
```

## Advanced patterns

### Complex POST body with JSON filters

Some APIs require complex JSON bodies with filters, date ranges, and nested structures:

```yaml
request.method: POST
request.body:
  query:
    filters:
      - field: "created_at"
        operator: "gte"
        value: '[[ .cursor.since ]]'
    sort:
      - field: "created_at"
        order: "asc"
    limit: {{batch_size}}
response.request_body_on_pagination: true
```

### Advanced security authentication

For APIs requiring multi-step authentication (e.g., token exchange before data requests), use `request.transforms` to manage the auth flow:

```yaml
auth:
  oauth2:
    client:
      id: '{{client_id}}'
      secret: '{{client_secret}}'
    token_url: '{{token_url}}'
    scopes:
      - '{{scope}}'
```

### Nested response splits

When the response contains nested arrays (e.g., events inside records inside pages):

```yaml
response.split:
  target: body.records
  type: array
  ignore_empty_value: true
  split:
    target: body.records.events
    type: array
    keep_parent: true
    ignore_empty_value: true
```

Use `keep_parent: true` on nested splits to preserve parent fields in child events.

### Map type split

When the response is a map (object) rather than an array, use `type: map`:

```yaml
response.split:
  target: body.data
  type: map
  ignore_empty_value: true
```

Each key-value pair becomes a separate event. The key is available as `.key` and the value as `.value` in subsequent transforms.

### Handlebars array parameters

When a manifest variable is an array (e.g., multiple endpoints or resource types), iterate with Handlebars:

```yaml
{{#each resource_types}}
- request.url: {{../url}}/api/v1/{{this}}
  request.method: GET
{{/each}}
```

### Rate limiting configuration

```yaml
request.rate_limit:
  limit: '[[ .last_response.header.Get "X-RateLimit-Limit" ]]'
  remaining: '[[ .last_response.header.Get "X-RateLimit-Remaining" ]]'
  reset: '[[ .last_response.header.Get "X-RateLimit-Reset" ]]'
```

### Cursor update only on first page

When the cursor should only update from the first page of results (to avoid advancing the cursor past unpaginated data):

```yaml
cursor:
  since:
    value: >-
      [[- if eq .last_response.page 0 -]]
      [[- .first_event.timestamp -]]
      [[- end -]]
    ignore_empty_value: true
```

## Authentication patterns

### Basic authentication

```yaml
auth.basic:
  user: '{{username}}'
  password: '{{password}}'
```

### API key header

```yaml
request.transforms:
  - set:
      target: header.Authorization
      value: '{{api_key_prefix}} {{api_key}}'
```

Or using a dedicated header name:

```yaml
request.transforms:
  - set:
      target: header.X-API-Key
      value: '{{api_key}}'
```

### OAuth2 client credentials

```yaml
auth.oauth2:
  client.id: '{{client_id}}'
  client.secret: '{{client_secret}}'
  token_url: '{{token_url}}'
```

### OAuth2 with custom provider

```yaml
auth.oauth2:
  client.id: '{{client_id}}'
  client.secret: '{{client_secret}}'
  token_url: '{{token_url}}'
  scopes:
{{#each oauth_scopes}}
    - {{this}}
{{/each}}
  endpoint_params:
    resource:
      - '{{resource}}'
```

### Mutual exclusion

When an integration supports multiple authentication methods, use Handlebars conditionals to select one:

```yaml
{{#if auth_method_basic}}
auth.basic:
  user: '{{username}}'
  password: '{{password}}'
{{/if}}
{{#if auth_method_oauth2}}
auth.oauth2:
  client.id: '{{client_id}}'
  client.secret: '{{client_secret}}'
  token_url: '{{token_url}}'
{{/if}}
{{#if auth_method_api_key}}
request.transforms:
  - set:
      target: header.Authorization
      value: 'Bearer {{api_key}}'
{{/if}}
```

Only one `auth_method_*` variable should be true at a time. The manifest should enforce this with `show_user` and conditional `required` settings, or by using a single `auth_type` select variable that controls which credential fields are shown.

## Cursor persistence

### How cursor persistence works

The HTTPJSON input persists cursor values between poll cycles. Cursor values are only saved when events have been successfully published to Elasticsearch. If the agent restarts, it resumes from the last persisted cursor.

### ignore_empty_value semantics

When `ignore_empty_value: true` is set on a cursor entry, the cursor retains its previous value if the current evaluation produces an empty string. This is essential for:
- Responses that do not contain the tracked field on every page
- Empty responses where no events are produced
- First-page-only cursor updates

### Empty response handling with pipeline drop

Some APIs return cursor tokens even with empty data arrays. If the pipeline uses a `drop` processor to discard empty events, no events are published, and the cursor is not updated. This creates an infinite loop where the agent keeps requesting the same empty page.

To handle this, ensure the `response.split` has `ignore_empty_value: true` so empty arrays produce no events (and no phantom events that need dropping), and the cursor tracks a field that only appears when real data exists.

## API conformance table

Mapping from common API pagination styles to the appropriate HTTPJSON pattern.

| API pagination style | HTTPJSON pattern | Key fields |
|---|---|---|
| Returns `next_cursor` / `cursor` token | Cursor-based | `response.pagination` with cursor conditional |
| Returns total count + accepts offset | Offset-based | `response.pagination` with add/limit math |
| Returns `has_more` + page number | Page number | `response.pagination` with page increment |
| Returns `Link` header with rel="next" | Link-based | `response.pagination` with `parseLinkHeader` |
| POST body with pagination token | POST body | `response.request_body_on_pagination: true` |
| Sync ID + incremental cursor | Sync ID | Two-step: sync_id preserved, cursor conditional |
| Returns `next_url` in body | Cursor-based (URL variant) | Set `url.value` from response body field |
| Returns results until empty page | Offset or page with length check | Terminate when `len .last_response.body.data` is 0 |
