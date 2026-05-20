# CEL template examples

> **WARNING — These templates are the FINAL output of the CEL development workflow.** Do NOT write `cel.yml.hbs` first. The mandatory workflow is: create mock → write a standalone `.cel` file → validate with mito → ONLY THEN embed the working program into the template below. If you are writing a new CEL program, start with the mock and mito steps described in the `cel-programs` SKILL.md and `references/mito-reference.md`. Come back to this file only at step 5 when you need the Handlebars wrapper.

All examples below are for **integration packages** (`type: integration`). They do **not** include `data_stream.dataset` — that field is only used by input-type packages (`type: input`) which have no predefined data streams. See the main `cel-programs` skill for details.

## Minimal: simple GET, no pagination

### cel.yml.hbs

```handlebars
interval: {{interval}}
resource.tracer:
  enabled: {{enable_request_tracer}}
  filename: "../../logs/cel/http-request-trace-*.ndjson"
  maxbackups: 5
{{#if proxy_url}}
resource.proxy_url: {{proxy_url}}
{{/if}}
{{#if ssl}}
resource.ssl: {{ssl}}
{{/if}}
{{#if http_client_timeout}}
resource.timeout: {{http_client_timeout}}
{{/if}}
resource.url: {{url}}
{{#if api_key}}
state:
  api_key: {{api_key}}
redact:
  fields:
    - api_key
{{/if}}
program: |
  state.with(
    request("GET", state.url).with({
      "Header": {
        "Content-Type": ["application/json"],
        ?"Api-Key": has(state.api_key) ?
          optional.of([state.api_key])
        :
          optional.none(),
      }
    }).do_request().as(resp,
      resp.StatusCode == 200 ?
        resp.Body.decode_json().as(body, {
          "events": body.?items.orValue([]).map(item, {"message": item.encode_json()}),
        })
      :
        {
          "events": {
            "error": {
              "code": string(resp.StatusCode),
              "id": string(resp.Status),
              "message": "GET " + state.url.trim_right("/") + ": " + (
                size(resp.Body) != 0 ?
                  string(resp.Body)
                :
                  string(resp.Status) + " (" + string(resp.StatusCode) + ")"
              ),
            },
          },
          "want_more": false,
        }
    )
  )

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

### Corresponding manifest.yml (data stream)

```yaml
type: logs
title: Items
streams:
  - input: cel
    template_path: cel.yml.hbs
    title: Items
    description: Collect items from the API.
    vars:
      - name: url
        type: text
        title: URL
        required: true
        show_user: false
        default: https://api.example.com/v1/items
      - name: interval
        type: text
        title: Interval
        required: true
        default: 5m
      - name: http_client_timeout
        type: text
        title: HTTP Client Timeout
        required: false
        show_user: false
      - name: proxy_url
        type: text
        title: Proxy URL
        required: false
        show_user: false
      - name: ssl
        type: yaml
        title: SSL Configuration
        required: false
        show_user: false
      - name: tags
        type: text
        title: Tags
        multi: true
        required: true
        show_user: false
        default:
          - forwarded
      - name: preserve_original_event
        type: bool
        title: Preserve Original Event
        required: true
        show_user: true
        default: false
      - name: enable_request_tracer
        type: bool
        title: Enable Request Tracer
        required: false
        show_user: false
      - name: processors
        type: yaml
        title: Processors
        required: false
        show_user: false
        description: Processors to apply to events.
```

## Paginated: cursor with timestamp

### cel.yml.hbs

```handlebars
interval: {{interval}}
resource.tracer:
  enabled: {{enable_request_tracer}}
  filename: "../../logs/cel/http-request-trace-*.ndjson"
  maxbackups: 5
{{#if proxy_url}}
resource.proxy_url: {{proxy_url}}
{{/if}}
{{#if ssl}}
resource.ssl: {{ssl}}
{{/if}}
{{#if http_client_timeout}}
resource.timeout: {{http_client_timeout}}
{{/if}}
resource.url: {{url}}
state:
  api_key: {{api_key}}
  batch_size: {{batch_size}}
  initial_interval: {{initial_interval}}
redact:
  fields:
    - api_key
program: |
  state.?cursor.last_timestamp.orValue(
    string(now - duration(state.initial_interval))
  ).as(since,
    state.with(
      request("GET", state.url.trim_right("/") + "?" + {
        "since": [since],
        "limit": [string(int(state.batch_size))],
        "sort": ["created_at"],
      }.format_query()).with({
        "Header": {
          "Authorization": ["Bearer " + state.api_key],
          "Content-Type": ["application/json"],
        }
      }).do_request().as(resp,
        resp.StatusCode == 200 ?
          resp.Body.decode_json().as(body, {
            "events": body.map(e, {"message": e.encode_json()}).as(events,
              (size(events) > 0) ? dyn(events) : dyn([{"retry": true}])
            ),
            "cursor": size(body) > 0 ?
              {"last_timestamp": body.map(e, e.created_at).max()}
            :
              state.?cursor.orValue({}),
            "want_more": size(body) == int(state.batch_size),
          })
        :
          {
            "events": {
              "error": {
                "code": string(resp.StatusCode),
                "id": string(resp.Status),
                "message": "GET " + state.url.trim_right("/") + ": " + (
                  size(resp.Body) != 0 ?
                    string(resp.Body)
                  :
                    string(resp.Status) + " (" + string(resp.StatusCode) + ")"
                ),
              },
            },
            "want_more": false,
          }
      )
    )
  )

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
processors:
- drop_event.when.equals.retry: true
{{#if processors}}
{{processors}}
{{/if}}
```

### Corresponding manifest.yml additions

```yaml
vars:
  - name: api_key
    type: password
    title: API Key
    required: true
    show_user: true
  - name: batch_size
    type: integer
    title: Batch Size
    required: true
    default: 100
    show_user: false
  - name: initial_interval
    type: text
    title: Initial Interval
    required: true
    default: 720h
    show_user: false
    description: How far back to look on first run (e.g. 720h for 30 days).
```

## OAuth: client credentials with token URL

### cel.yml.hbs

When using OAuth, the `auth.oauth2` section handles token management outside the CEL program. The CEL program does not need to request tokens itself.

```handlebars
interval: {{interval}}
resource.tracer:
  enabled: {{enable_request_tracer}}
  filename: "../../logs/cel/http-request-trace-*.ndjson"
  maxbackups: 5
{{#if proxy_url}}
resource.proxy_url: {{proxy_url}}
{{/if}}
{{#if ssl}}
resource.ssl: {{ssl}}
{{/if}}
{{#if http_client_timeout}}
resource.timeout: {{http_client_timeout}}
{{/if}}
auth.oauth2:
  client.id: {{client_id}}
  client.secret: {{client_secret}}
  token_url: {{token_url}}
{{#if scope}}
  scopes:
    - {{scope}}
{{/if}}
resource.url: {{url}}
state:
  batch_size: {{batch_size}}
  initial_interval: {{initial_interval}}
redact:
  fields: ~
program: |
  state.?cursor.last_timestamp.orValue(
    string(now - duration(state.initial_interval))
  ).as(since,
    state.with(
      request("GET", state.url.trim_right("/") + "?" + {
        "since": [since],
        "limit": [string(int(state.batch_size))],
      }.format_query()).do_request().as(resp,
        resp.StatusCode == 200 ?
          resp.Body.decode_json().as(body, {
            "events": body.items.map(e, {"message": e.encode_json()}),
            "cursor": size(body.items) > 0 ?
              {"last_timestamp": body.items.map(e, e.updated_at).max()}
            :
              state.?cursor.orValue({}),
            "want_more": size(body.items) == int(state.batch_size),
          })
        :
          {
            "events": {
              "error": {
                "code": string(resp.StatusCode),
                "id": string(resp.Status),
                "message": "GET " + state.url.trim_right("/") + ": " + (
                  size(resp.Body) != 0 ?
                    string(resp.Body)
                  :
                    string(resp.Status) + " (" + string(resp.StatusCode) + ")"
                ),
              },
            },
            "want_more": false,
          }
      )
    )
  )

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

### Corresponding manifest.yml additions

OAuth vars are typically package-level (root `manifest.yml` under `policy_templates[].inputs[].vars`):

```yaml
vars:
  - name: url
    type: text
    title: API URL
    required: true
    show_user: true
    default: https://api.example.com
  - name: client_id
    type: text
    title: Client ID
    required: true
    show_user: true
  - name: client_secret
    type: password
    title: Client Secret
    required: true
    show_user: true
  - name: token_url
    type: text
    title: Token URL
    required: true
    show_user: true
    default: https://api.example.com/oauth/token
  - name: scope
    type: text
    title: OAuth Scope
    required: false
    show_user: false
```

### System test config for OAuth

```yaml
input: cel
service: <service-name>
vars:
  url: http://{{Hostname}}:{{Port}}
  client_id: xxxx
  client_secret: xxxx
  token_url: http://{{Hostname}}:{{Port}}/oauth/token
data_stream:
  vars:
    interval: 10s
    batch_size: 2
    initial_interval: 720h
    preserve_original_event: true
assert:
  hit_count: 4
```

The mock config must include an OAuth token rule:

```yaml
rules:
  - path: /oauth/token
    methods: ['POST']
    responses:
      - status_code: 200
        headers:
          Content-Type:
            - 'application/json'
        body: '{"access_token":"xxxx","token_type":"Bearer","expires_in":3600}'
```

## GraphQL: cursor pagination with POST

### cel.yml.hbs (program section only)

```handlebars
state:
  batch_size: {{batch_size}}
  initial_interval: {{initial_interval}}
  query: >-
    query FindingsQuery($first: Int, $after: String, $filterBy: FindingsFilterInput) {
      findings(first: $first, after: $after, filterBy: $filterBy) {
        nodes { id name severity createdAt }
        pageInfo { hasNextPage endCursor }
      }
    }
program: |
  state.with(
    post_request(
      state.url + "/graphql",
      "application/json",
      {
        "query": state.query,
        "variables": {
          "first": state.batch_size,
          "after": state.?cursor.end_cursor.orValue(null),
          "filterBy": {
            "createdAt": {
              "after": state.?cursor.last_timestamp.orValue(
                string(now - duration(state.initial_interval))
              )
            }
          }
        }
      }.encode_json()
    ).do_request().as(resp,
      resp.StatusCode == 200 ?
        resp.Body.decode_json().as(body,
          body.data.findings.nodes != null ?
            {
              "events": body.data.findings.nodes.map(e, {"message": e.encode_json()}),
              "cursor": {
                "end_cursor": body.data.findings.pageInfo.hasNextPage ?
                  body.data.findings.pageInfo.endCursor
                :
                  optional.none(),
                "last_timestamp": size(body.data.findings.nodes) > 0 ?
                  body.data.findings.nodes.map(e, e.createdAt).max()
                :
                  state.?cursor.last_timestamp.orValue(
                    string(now - duration(state.initial_interval))
                  ),
              },
              "want_more": body.data.findings.pageInfo.hasNextPage,
            }
          :
            {"events": [], "want_more": false}
        )
      :
        {
          "events": {
            "error": {
              "code": string(resp.StatusCode),
              "id": string(resp.Status),
              "message": "POST " + state.url.trim_right("/") + "/graphql: " + (
                size(resp.Body) != 0 ?
                  string(resp.Body)
                :
                  string(resp.Status) + " (" + string(resp.StatusCode) + ")"
              ),
            },
          },
          "want_more": false,
        }
    )
  )
```
