# CEL system tests

System tests for CEL-based data streams validate the full ingest path: mock HTTP service → CEL input → ingest pipeline → Elasticsearch. The mock API replaces the real API so the CEL program runs unchanged.

## File layout

```text
packages/<pkg>/
├── _dev/
│   └── deploy/
│       └── docker/
│           ├── docker-compose.yml        # mock service definitions
│           └── files/                    # or root level
│               ├── config.yml            # mock API rules
│               └── config-<stream>.yml   # per-stream mock configs
└── data_stream/
    └── <stream>/
        └── _dev/
            └── test/
                └── system/
                    └── test-default-config.yml   # system test config
```

## System test config

Located at `data_stream/<stream>/_dev/test/system/test-<scenario>-config.yml`.

```yaml
wait_for_data_timeout: 1m
input: cel
service: <docker-compose-service-name>
vars:
  url: http://{{Hostname}}:{{Port}}
  api_key: xxxx
  # auth vars matching what the CEL program expects
data_stream:
  vars:
    interval: 10s
    batch_size: 2
    initial_interval: 720h
    preserve_original_event: true
assert:
  hit_count: <expected number of indexed events>
```

### Key fields


| Field                   | Purpose                                                                               |
| ----------------------- | ------------------------------------------------------------------------------------- |
| `wait_for_data_timeout` | Max time to wait for indexed documents (use `**1m**` in all system test configs here) |
| `input: cel`            | Selects the CEL input when the data stream supports multiple input types              |
| `service`               | Name of the docker-compose service providing the mock API                             |
| `vars`                  | Package-level variables; `url` uses `{{Hostname}}` and `{{Port}}` placeholders        |
| `data_stream.vars`      | Stream-level variables (interval, batch_size, etc.)                                   |
| `assert.hit_count`      | Expected number of documents indexed after the test completes                         |


### Placeholder substitution

`{{Hostname}}` and `{{Port}}` are replaced at runtime with the mock service's actual host and mapped port. Additional placeholders: `{{Ports}}`, `{{Ports.0}}`, `{{SERVICE_LOGS_DIR}}`.

## Mock API with elastic/stream

CEL system tests use the `elastic/stream` docker image as a rule-based HTTP mock server.

### Docker-compose service definition

```yaml
services:
  <service-name>:
    image: docker.elastic.co/observability/stream:v0.22.0
    hostname: <service-name>
    ports:
      - 8090
    volumes:
      - ./files:/files:ro
    environment:
      PORT: '8090'
    command:
      - http-server
      - --addr=:8090
      - --config=/files/config.yml
```

Use a dedicated service per data stream when mock configs differ, or a shared service when one config serves all streams.

Volume-mount the config from `_dev/deploy/docker/files/`. The port number (8090, 8080, etc.) is internal; the test framework maps it automatically.

### Mock config rule format

The config YAML has a `rules` array. Each rule matches incoming requests and returns a canned response.

```yaml
rules:
  - path: /api/v1/items
    methods: ['GET']
    query_params:
      page: '1'
      per_page: '2'
    request_headers:
      Authorization:
        - 'Bearer xxxx'
    responses:
      - status_code: 200
        headers:
          Content-Type:
            - 'application/json'
        body: |
          {"items": [{"id": 1}, {"id": 2}], "total": 4}
```

### Rule matching fields


| Field             | Type         | Purpose                                                                        |
| ----------------- | ------------ | ------------------------------------------------------------------------------ |
| `path`            | string       | URL path; supports `{param}` placeholders                                      |
| `methods`         | list         | HTTP methods to match (e.g., `['GET']`, `['POST']`)                            |
| `query_params`    | map          | Query parameter key-value constraints                                          |
| `request_headers` | map          | Required request header values                                                 |
| `request_body`    | string/regex | Match request body content; prefix with `/` for regex (e.g., `/.*"page":2.*/`) |
| `responses`       | list         | Response definitions with `status_code`, `headers`, `body`                     |


Rules are evaluated in order; the first match wins. Place more specific rules (with query params, body patterns) before catch-all rules.

### Mock API flow design — critical for system test success

The mock config must model the **complete API request flow** the CEL program makes. A poorly designed mock is the #1 cause of system test failures with 0 hits — the CEL program loops indefinitely through time windows without ever terminating because the mock returns data for every request regardless of parameters.

**Design the mock as a conversation:** trace the exact sequence of HTTP requests the CEL program will make (auth → initial fetch → pagination → next time window → ...) and create rules that make this conversation **terminate within a bounded number of requests**.

#### Variable capture patterns

The `elastic/stream` mock supports **variable capture** in `query_params` values using `{varName:regex}` syntax. Captured variables can be referenced in response bodies with `{{ .request.vars.varName }}`. This is essential for timestamp-based APIs where query parameters are dynamic.

```yaml
query_params:
  startTime: "{startTime:.*}"          # captures any startTime value
  endTime: "{endTime:.*}"              # captures any endTime value
  contentType: "Audit.SharePoint"      # exact match (no capture)
```

In response bodies, reference captured values:

```yaml
body: |-
  [{"contentId":"id1","contentUri":"http://{{ hostname }}:{{ env "PORT" }}/api/content/id1","contentCreated":"{{ .request.vars.endTime }}"}]
```

#### Designing the rule flow

1. **Auth rules first** (if the CEL program authenticates before data fetching):
  ```yaml
   rules:
     - path: /oauth/token
       methods: [POST]
       query_params:
         grant_type: client_credentials
         client_id: test-client-id
         client_secret: test-secret
       request_headers:
         Content-Type:
           - "application/x-www-form-urlencoded"
       responses:
         - status_code: 200
           headers:
             Content-Type:
               - "application/json"
           body: '{"access_token":"test-token","token_type":"Bearer","expires_in":3600}'
  ```
2. **Catchall rules with variable captures** for the main data endpoint. These handle **any** timestamp/cursor values the CEL program sends. The catchall is usually the first rule that hits on the initial request (since timestamps like "now - 1d" are dynamic):
  ```yaml
     # Page 1 — catches any startTime/endTime combination
     - path: /api/v1/events
       methods: ['GET']
       query_params:
         page: '1'
         startTime: "{startTime:.*}"
         endTime: "{endTime:.*}"
       request_headers:
         Authorization:
           - "Bearer test-token"
       responses:
         - status_code: 200
           headers:
             Content-Type:
               - "application/json"
           body: |
             {"events":[{"id":"evt1","timestamp":"2024-01-15T12:00:00Z"},{"id":"evt2","timestamp":"2024-01-15T13:00:00Z"}],"pagination":{"page":1,"hasNextPage":true,"totalPages":2}}

     # Page 2 — last page, catches any startTime/endTime
     - path: /api/v1/events
       methods: ['GET']
       query_params:
         page: '2'
         startTime: "{startTime:.*}"
         endTime: "{endTime:.*}"
       request_headers:
         Authorization:
           - "Bearer test-token"
       responses:
         - status_code: 200
           headers:
             Content-Type:
               - "application/json"
           body: |
             {"events":[{"id":"evt3","timestamp":"2024-01-15T14:00:00Z"}],"pagination":{"page":2,"hasNextPage":false,"totalPages":2}}
  ```
3. **All query params and headers must be specified**: Every rule must include all the `query_params` and `request_headers` the CEL program sends for that request type. Missing params cause silent rule mismatches.
4. **Rule ordering matters**: `elastic/stream` matches top-down, first match wins. Place more specific rules (exact page numbers, specific filter values) before less specific catchall rules for the same path, unless the catchall should handle the initial request.

#### Why catchall rules prevent infinite loops

Without variable captures, a mock with static `page: '1'` and `page: '2'` rules matches **any** request to that path regardless of timestamp parameters. When the CEL program uses timestamp-cursor pagination (advancing through 30-day windows from `initial_interval` to now), the mock returns the same data for every window. The program keeps advancing because it always finds data, and it never terminates within `max_executions` — resulting in 0 indexed hits when the 1-minute test timeout expires.

With variable captures (`startTime: "{startTime:.*}"`), the rules explicitly declare the full parameter set they expect. The response data can use `{{ .request.vars.endTime }}` to echo back timestamps, ensuring the CEL program's cursor advances correctly and pagination terminates.

### Mocking pagination — simple page-number pagination

For APIs where the only dynamic parameter is the page number (no timestamp windows):

```yaml
rules:
  # Page 1 — five events, more pages
  - path: /api/v1/items
    methods: ['GET']
    query_params:
      page: '1'
    responses:
      - status_code: 200
        body: '{"items": [{"id": 1}, {"id": 2}], "next_page": 2, "total": 3}'

  # Page 2 — last page
  - path: /api/v1/items
    methods: ['GET']
    query_params:
      page: '2'
    responses:
      - status_code: 200
        body: '{"items": [{"id": 3}]}'
```

### Mocking pagination — timestamp-cursor with page pagination (comprehensive example)

This example models a real API that uses both time-windowed cursoring and page-level pagination within each window. Based on production-quality patterns:

```yaml
rules:
  # Auth: OAuth token endpoint
  - path: /tenant-id/oauth2/token
    methods: [POST]
    query_params:
      grant_type: client_credentials
      client_id: test-client-id
      client_secret: test-secret
    request_headers:
      Content-Type:
        - "application/x-www-form-urlencoded"
    responses:
      - status_code: 200
        headers:
          Content-Type:
            - "application/json"
        body: '{"access_token":"test-token","token_type":"Bearer","expires_in":3600}'

  # Data: page 1 for any time window — returns data + next page link
  - path: /api/v1/content
    methods: [GET]
    query_params:
      contentType: "Audit.Events"
      startTime: "{startTime:.*}"
      endTime: "{endTime:.*}"
      PublisherIdentifier: test-tenant-id
    request_headers:
      Authorization:
        - "Bearer test-token"
    responses:
      - status_code: 200
        headers:
          Content-Type:
            - "application/json"
          NextPageUri:
            - 'http://{{ hostname }}:{{ env "PORT" }}/api/v1/content?contentType=Audit.Events&startTime={{ .request.vars.startTime }}&endTime={{ .request.vars.endTime }}&nextpage=page2token'
        body: |-
          [{"contentId":"id1","contentUri":"http://{{ hostname }}:{{ env "PORT" }}/api/v1/audit/id1","contentCreated":"{{ .request.vars.endTime }}","contentExpiration":"2199-12-31T00:00:00.000Z"}]

  # Data: page 2 (next page via token) — last page, no NextPageUri
  - path: /api/v1/content
    methods: [GET]
    query_params:
      contentType: "Audit.Events"
      startTime: "{startTime:.*}"
      endTime: "{endTime:.*}"
      nextpage: "page2token"
    request_headers:
      Authorization:
        - "Bearer test-token"
    responses:
      - status_code: 200
        headers:
          Content-Type:
            - "application/json"
        body: |-
          [{"contentId":"id2","contentUri":"http://{{ hostname }}:{{ env "PORT" }}/api/v1/audit/id2","contentCreated":"{{ .request.vars.endTime }}","contentExpiration":"2199-12-31T00:00:00.000Z"}]

  # Content fetch: individual content items
  - path: /api/v1/audit/id1
    methods: [GET]
    request_headers:
      Authorization:
        - "Bearer test-token"
    responses:
      - status_code: 200
        headers:
          Content-Type:
            - "application/json"
        body: |-
          {{ minify_json `
          [
            {"Id":"evt-001","CreationTime":"2024-01-15T12:30:00","Operation":"UserLoggedIn","UserId":"alice@example.com"},
            {"Id":"evt-002","CreationTime":"2024-01-15T14:00:00","Operation":"FileAccessed","UserId":"bob@example.com"}
          ]
          ` }}

  - path: /api/v1/audit/id2
    methods: [GET]
    request_headers:
      Authorization:
        - "Bearer test-token"
    responses:
      - status_code: 200
        headers:
          Content-Type:
            - "application/json"
        body: |-
          {{ minify_json `
          [
            {"Id":"evt-003","CreationTime":"2024-01-16T09:00:00","Operation":"RoleChanged","UserId":"admin@example.com"}
          ]
          ` }}
```

### Mocking pagination — GraphQL cursor

For POST-based pagination (e.g., GraphQL), use `request_body` regex:

```yaml
rules:
  # First page: after is null
  - path: /graphql
    methods: ['POST']
    request_body: /.*"after":null.*/
    responses:
      - status_code: 200
        body: |
          {"data":{"items":{"nodes":[{"id":1},{"id":2}],"pageInfo":{"hasNextPage":true,"endCursor":"abc123"}}}}

  # Second page: after is "abc123"
  - path: /graphql
    methods: ['POST']
    request_body: /.*"after":"abc123".*/
    responses:
      - status_code: 200
        body: |
          {"data":{"items":{"nodes":[{"id":3}],"pageInfo":{"hasNextPage":false,"endCursor":"def456"}}}}
```

### Mocking OAuth token endpoints

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

The test config must provide matching auth vars:

```yaml
vars:
  url: http://{{Hostname}}:{{Port}}
  client_id: xxxx
  client_secret: xxxx
  token_url: http://{{Hostname}}:{{Port}}/oauth/token
```

### Response templating

The `elastic/stream` server supports Go template syntax in response bodies:

```yaml
body: |
  {{ if eq .req_num 1 }}
  {"items": [{"id": 1}], "has_more": true}
  {{ else }}
  {"items": [], "has_more": false}
  {{ end }}
```

Use `{{ minify_json }}` to compact inline JSON when needed.

## Calculating hit_count

The `assert.hit_count` value must match the total number of events the CEL program produces across all paginated evaluations given the mock responses.

Example: mock returns 2 items on page 1 and 2 items on page 2 → `hit_count: 4`.

If the CEL program transforms one API response item into multiple events (e.g., nested arrays flattened), count the final events, not API items.

## Cleaning up prototype files before validation

The CEL development workflow may create a `_dev/cel-prototype/` directory inside the package tree (for standalone `.cel` files and `state.json` test inputs). **This directory is not a recognized package folder** and causes `elastic-package lint` and `elastic-package check` to fail with an "unrecognized folder" error.

**Remove the prototype directory before running any validation commands:**

```bash
rm -rf packages/<package_name>/_dev/cel-prototype/
```

Alternatively, keep prototype files outside the package tree entirely (e.g., in `/tmp/cel-work/` or a sibling directory) so they never interfere with package validation. Either approach is fine — the key rule is that no prototype artifacts remain inside `packages/<package_name>/` when you run `elastic-package lint`, `elastic-package check`, or `elastic-package test`.

## Running CEL system tests

```bash
cd packages/<package_name>

# start the Elastic stack
elastic-package stack up -d

# run system tests for a specific stream
elastic-package test system --data-streams <stream>

# generate sample_event.json from system test output
elastic-package test system --data-streams <stream> --generate

# keep resources for debugging
elastic-package test system --data-streams <stream> --defer-cleanup 10m
```

If **teardown** fails because an **agent policy** (or other Fleet resource) is still in use, reset the stack rather than cleaning Fleet manually: `elastic-package stack down` then `elastic-package stack up -d -v`, then rerun the test. Full guidance is in `integration-testing/references/system-testing.md` (Teardown failures section).

## Debugging system test failures — 0 hits

The system test runs for approximately **1 minute** (`wait_for_data_timeout: 1m`). When the result is 0 hits, the **first and most important** diagnostic is the mock container log:

```
build/container-logs/<package_name>-<datastream_name>-<DIGIT>.log
```

This log shows every HTTP request the CEL program makes against the mock, including which rules matched, full request paths with query parameters, and request headers. **Tail the last 100-200 lines** of this file as your first debugging step. Do NOT start with Elasticsearch queries, pipeline debugging, or index inspection.

### What to look for in container logs


| Pattern                                                                                                                   | Diagnosis                                                                                                                                  | Fix                                                                                                                                                                             |
| ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hundreds of requests with advancing `startTime`/`endTime` values, request numbers climbing (e.g. request #50, #100, #136) | **Infinite time-window looping** — the mock returns data for every time window so the CEL program never terminates within `max_executions` | Add variable-capture catchall rules with `startTime: "{startTime:.*}"` patterns. The mock must model the full API flow so pagination terminates in a bounded number of requests |
| No requests logged at all                                                                                                 | Agent never contacted the mock                                                                                                             | Check `url` in test config points to `http://{{Hostname}}:{{Port}}` and `service:` matches docker-compose service name                                                          |
| Requests logged but no rule matched                                                                                       | Query param or header mismatch between CEL program and mock rules                                                                          | Compare the logged request params/headers with mock rule definitions — add missing `query_params` or `request_headers` to rules                                                 |
| 401/403 responses in the log                                                                                              | Auth rule mismatch                                                                                                                         | Verify mock auth rules match exactly what the CEL program sends (credentials, Content-Type, etc.)                                                                               |
| Only a few requests then silence                                                                                          | CEL program hit an error and stopped with `want_more: false`                                                                               | Check the agent log (`build/container-logs/elastic-agent-*.log`) for error events                                                                                               |


### Common root cause: infinite time-window looping

This is the most frequent 0-hits failure for timestamp-cursor CEL programs. Symptoms in container logs:

- Request numbers climb to 50+ or 100+ within seconds
- Each request has a different `startTime`/`endTime` advancing by the window size (e.g. 30-day jumps)
- The mock returns 200 with data on every request

**Why it happens**: The mock uses static page rules without variable captures (e.g. `page: '1'` and `page: '2'`). These match ANY request to the path regardless of timestamps. With `initial_interval: 720h`, the CEL program walks through ~24 monthly windows, each returning 2 pages of data. It never catches up to "now" before `max_executions` is exhausted, and the 1-minute timeout expires with 0 indexed hits.

**Fix**: Replace static pagination rules with catchall rules using `{varName:.*}` variable captures for all dynamic query parameters. See the **Mock API flow design** section above.

## Common issues


| Symptom                                                                             | Cause                                                                     | Fix                                                                                                                                                            |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0 events indexed, hundreds of requests in container log                             | Infinite time-window looping — mock lacks variable-capture catchall rules | Redesign mock config with `startTime: "{startTime:.*}"` catchall patterns (see Mock API flow design)                                                           |
| 0 events indexed, no requests in container log                                      | Agent never contacted mock                                                | Verify `url` and `service:` in test config match docker-compose                                                                                                |
| 0 events indexed, mock shows rule mismatches                                        | Query param or header name mismatch                                       | Compare CEL program requests with mock rule `query_params`/`request_headers`                                                                                   |
| Connection refused                                                                  | Service name in test config doesn't match docker-compose                  | Verify `service:` matches the docker-compose service key                                                                                                       |
| OAuth errors                                                                        | Token URL not pointing to mock                                            | Set `token_url: http://{{Hostname}}:{{Port}}/oauth/token` in test vars                                                                                         |
| Wrong hit count                                                                     | Pagination mock returns unexpected pages                                  | Check mock rule order and add `-log_requests` tracer in test config                                                                                            |
| Mapping conflicts                                                                   | CEL events have fields not in `fields/*.yml`                              | Add missing field definitions or adjust the CEL program                                                                                                        |
| 0 hits with `data_stream.dataset` override                                          | `cel.yml.hbs` sets `data_stream.dataset`, routing docs to wrong index     | Remove `data_stream.dataset` from `cel.yml.hbs` and manifest vars — integration packages must not override dataset routing (only input-type packages use this) |
| 0 events indexed, agent log says "events were dropped" but mock shows 200 responses | Elasticsearch rejecting documents — see Debugging dropped events below    | Check the event log inside the running elastic-agent container for the rejection reason                                                                        |


## Debugging dropped events

When the mock container log shows successful 200 responses and the agent log reports `"events were dropped"`, the CEL program is producing events correctly but Elasticsearch is rejecting every document on bulk index. The agent log does not show the rejection reason — it is only visible in the **event log** inside the running elastic-agent container.

### How to inspect the event log

1. **Increase `wait_for_data_timeout`** in the test config to `5m` temporarily so the system test stays alive long enough.
2. Start the system test and wait for the first `"events were dropped"` warnings in the terminal.
3. Find and inspect the event log:
  ```bash
   # Find the container
   docker ps --format '{{.Names}}' | grep elastic-agent

   # Read the event log — look for "Cannot index event" entries
   docker exec <container-name> tail -20 /usr/share/elastic-agent/state/data/logs/events/elastic-agent-event-log-*.ndjson
  ```
4. The `"Cannot index event"` entries show the **exact ES rejection** (e.g., `Duplicate field '@timestamp'`, `mapper_parsing_exception`) and the full rejected document.

### Most common cause: duplicate `@timestamp`

The CEL program sets `@timestamp` in the event output alongside `message`:

```cel
// WRONG — causes duplicate @timestamp
items.map(e, {"message": e.encode_json(), "@timestamp": e.timestamp})
```

The Elastic Agent framework also adds its own `@timestamp` (ingestion time). The resulting document has two `@timestamp` keys, and ES 9.x rejects it: `x_content_parse_exception: Duplicate field '@timestamp'`.

**Fix:** Only set `"message"` in event output. The ingest pipeline parses the timestamp from `message` via the `date` processor.

```cel
// CORRECT
items.map(e, {"message": e.encode_json()})
```

After fixing, reduce `wait_for_data_timeout` back to `1m`.

## Reference patterns

The mock API and system test patterns shown in this file are based on production-quality integrations in the upstream `elastic/integrations` repository. The `cel-template-examples.md` file contains complete self-contained code examples for each pattern type (simple GET, paginated, OAuth, GraphQL cursor) that you can use directly without needing external references.