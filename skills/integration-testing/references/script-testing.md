# script testing

Everything needed to write `elastic-package test script` txtar tests covering failure paths, error handling, and package upgrades.

See also: [elastic-package script testing docs](https://github.com/elastic/elastic-package/blob/main/docs/howto/script_testing.md) · [with_script example package](https://github.com/elastic/elastic-package/tree/main/test/packages/other/with_script)

## What script tests cover

Script tests are [txtar](https://pkg.go.dev/golang.org/x/tools/txtar#hdr-Txtar_format) files in `<package>/data_stream/<ds>/_dev/test/scripts/`. They run via `elastic-package test script` and complement pipeline and system tests by covering cases those tools cannot:

- **Failure paths** — API errors, invalid credentials, partial failures where some sub-requests fail while others succeed
- **Invalid configuration** — bad config values, missing required fields, unsupported options
- **Package upgrades** — data collection survives an in-place upgrade from a previous release
- **Environment smoke tests** — cheapest verification that the script testing infrastructure is wired correctly

They are **not** a replacement for system tests; they augment them.

## Analyse the package first

Before writing any test, read and understand:

1. **Input program** (`agent/stream/cel.yml.hbs`, `agent/stream/httpjson.yml.hbs`, etc.) — map out how it calls the upstream API, which HTTP status codes it treats as success vs failure. This is critical: CEL programs often treat some non-200 codes as expected conditions (e.g. 400 = "already subscribed"); only status codes the program routes to error-handling will work for error-path tests.

2. **Ingest pipeline** (`elasticsearch/ingest_pipeline/default.yml`) — identify field renames and transformations. `get_docs` returns post-pipeline documents; assert against **indexed** field names, not the field names the input produces.

3. **Existing system test configs** (`_dev/test/system/`) — reuse credential values, tenant IDs, and other config values for consistency.

4. **Existing deploy config** (`_dev/deploy/docker/`) — the existing mock may already handle some endpoints. Script tests embed their own mocks in the txtar file, but copying the pattern keeps things consistent.

5. **Changelog** (`changelog.yml`) — read `CURRENT_VERSION` and `PREVIOUS_VERSION`. Check whether the latest change is a breaking change (needed for upgrade test guards).

## Directory layout

```
<package>/data_stream/<ds>/_dev/test/scripts/
  env.txt                        # smoke test (write first)
  <scenario>.txt                 # one file per scenario
```

## Environment smoke test (env.txt) — write first

Write this first for any new package. It verifies the script testing infrastructure populates environment variables without touching the stack:

```txtar
[!exec:echo] skip 'Skipping test requiring absent echo command'

exec echo ${CONFIG_ROOT}
stdout '/\.elastic-package$'

exec echo ${CONFIG_PROFILES}
stdout '/\.elastic-package/profiles$'

exec echo ${PACKAGE_NAME}
stdout '^o365$'

exec echo ${PACKAGE_ROOT}
stdout '/packages/o365$'

exec echo ${DATA_STREAM}
stdout '^audit$'

exec echo ${DATA_STREAM_ROOT}
stdout '/packages/o365/data_stream/audit$'

exec echo ${CURRENT_VERSION}
stdout '^[0-9]+\.[0-9]+\.[0-9]+$'

exec echo ${PREVIOUS_VERSION}
stdout '^[0-9]+\.[0-9]+\.[0-9]+$'
```

Use regex for version assertions so the test doesn't break on every release.

## System-level test skeleton

Every system-level script test follows this structure:

```txtar
# Description of what this test verifies.

[!external_stack] skip 'Skipping external stack test.'
[!exec:jq] skip 'Skipping test requiring absent jq command'

# 1. Connect.
use_stack -profile ${CONFIG_PROFILES}/${PROFILE}
install_agent -profile ${CONFIG_PROFILES}/${PROFILE} -network_name NETWORK_NAME

# 2. Start mock service.
docker_up -profile ${CONFIG_PROFILES}/${PROFILE} -network ${NETWORK_NAME} <mock-name>

# 3. Install package and create policy.
add_package -profile ${CONFIG_PROFILES}/${PROFILE}
add_package_policy -profile ${CONFIG_PROFILES}/${PROFILE} test_config.yaml DATA_STREAM_NAME

# 4. Assert.
get_docs -profile ${CONFIG_PROFILES}/${PROFILE} -want <N> -timeout 5m ${DATA_STREAM_NAME}
cp stdout got_docs.json
exec jq '<query>' got_docs.json
stdout '<expected>'

# 5. Clean up.
remove_package_policy -profile ${CONFIG_PROFILES}/${PROFILE} ${DATA_STREAM_NAME}
uninstall_agent -profile ${CONFIG_PROFILES}/${PROFILE} -timeout 1m
docker_down <mock-name>
```

## Embedded files in the txtar

The `-- filename --` sections at the bottom of each txtar file contain:

- **`test_config.yaml`** — package policy config (input type and vars). Point the integration at the mock service and set short intervals/windows.
- **`<mock-name>/docker-compose.yml`** — Docker Compose for the mock service.
- **`<mock-name>/config.yml`** — `elastic/stream` mock rules.

## test_config.yaml

```yaml
input: cel
vars: ~
data_stream:
  vars:
    url: http://<mock-name>:8080
    interval: 30s
    initial_interval: 1h
    preserve_original_event: true
    # ... other required vars with test values ...
```

Set `interval` and `initial_interval` to small values. Large defaults (e.g. 168h lookback) cause many API calls against the mock, slowing the test and making assertions harder to predict.

## Upgrade test pattern

```txtar
[!external_stack] skip 'Skipping external stack test.'
[!has_previous_release] skip 'No previous release to upgrade from.'
[breaking_change] skip 'Cannot upgrade across breaking change.'
[!exec:jq] skip 'Skipping test requiring absent jq command'

# ... setup, add_package, add_package_policy, verify initial data ...

upgrade_package_latest -profile ${CONFIG_PROFILES}/${PROFILE}
stdout 'upgraded package '${PACKAGE_NAME}

# ... verify data still present after upgrade ...

# ... cleanup ...
```

The `[!has_previous_release]` and `[breaking_change]` guards skip automatically when appropriate.

## Mock service setup

Use the `elastic/stream` Docker image (`docker.elastic.co/observability/stream`). Match the version used in the package's existing `_dev/deploy/docker/` config.

### docker-compose.yml

```yaml
version: '2.3'
services:
  <mock-name>:
    image: docker.elastic.co/observability/stream:v0.22.0
    hostname: <mock-name>
    ports:
      - 8080
    environment:
      PORT: "8080"
    volumes:
      - ./config.yml:/config.yml
    command:
      - http-server
      - --addr=:8080
      - --config=/config.yml
```

Always set `hostname: <mock-name>` explicitly. Without it the container defaults to the container ID, which the agent cannot resolve on the Docker network.

### config.yml structure

Rules are matched top-down. Each rule specifies path, methods, optional query params, optional request headers, and responses:

```yaml
rules:
  - path: /api/v1/items
    methods: [GET]
    query_params:
      api_key: test-key
    responses:
      - status_code: 200
        headers:
          Content-Type:
            - "application/json"
        body: |-
          {"items": [...]}
```

Template variables available in response bodies:
- **`{{ hostname }}`** — Docker container hostname (required for self-referential URLs, e.g. next-page links)
- **`{{ env "PORT" }}`** — value of the PORT environment variable
- **`{varName:regex}`** — in `query_params` values, captures variable request parameters (e.g. `startTime: "{startTime:.*}"`)
- **`{{ .request.vars.varName }}`** — references a captured query param in the response body

**Variable-capture catchall rules** are essential for APIs with dynamic query parameters (timestamps, cursor tokens). Without them, CEL programs with timestamp-cursor pagination loop indefinitely. Always include `{varName:.*}` captures for all dynamic query params:

```yaml
- path: /api/v1/events
  methods: ['GET']
  query_params:
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
      body: |-
        {"events":[...], "nextPage": "http://{{ hostname }}:{{ env "PORT" }}/api/v1/events?cursor={{ .request.vars.endTime }}"}
```

Put more specific rules (with `query_params` or `request_headers`) before less specific ones for the same path.

## Running script tests

```bash
# Run all script tests for a data stream:
elastic-package test script -v --data-streams <data_stream>

# Run a single test:
elastic-package test script -v --data-streams <data_stream> --run <test_name>

# Keep work directory for debugging:
elastic-package test script -v --data-streams <data_stream> --work

# Verbose script output:
elastic-package test script -v --data-streams <data_stream> --verbose-scripts
```

Tests require a running Elastic stack (`--external-stack`, which is the default).

## Pitfalls and hard-won lessons

### Assert against indexed fields, not input fields

`get_docs` returns post-pipeline documents. If the ingest pipeline renames `foobar` to `foo.bar`, assert against `foo.bar`. Always check the pipeline first.

### Do NOT call `remove_package` in cleanup

For real packages, Kibana often refuses removal because Fleet hasn't finished cascading the agent policy deletion to package policies. The script test runner's automatic cleanup handles package removal. **Omit `remove_package`** from cleanup.

### Read the input's error-handling logic before choosing mock responses

CEL and httpjson programs often treat some non-200 HTTP codes as expected, non-error conditions (e.g. 400 = "already subscribed", 404 = "no new data"). A mock returning such a code won't trigger the error path. Read the program to find which status codes actually reach error-handling code, then mock those.

### Use `-confirm` with `get_docs` for exact-count assertions

When asserting that exactly N documents arrive and no more, add `-confirm 15s`:

```txtar
get_docs -profile ${CONFIG_PROFILES}/${PROFILE} -want 1 -confirm 15s -timeout 5m ${DATA_STREAM_NAME}
```

This waits an extra 15 seconds after reaching N to confirm no additional documents arrive.

### Minimise polling and batch windows in test configs

Set short `initial_interval`, `interval`, and `batch_size` values in `test_config.yaml` so each test cycle makes a predictable, minimal number of API requests.

### Set `hostname` in docker-compose for mock services

Without an explicit `hostname: <mock-name>` in docker-compose, the container defaults to its container ID. Agents on the Docker network cannot resolve container IDs.

## Full examples (o365 integration)

### Partial API failure — subscription_permission_error.txt

Tests that a permission error (401 AF10001) for one content type does not prevent collection from other content types. Three content types configured; one rejected by the mock. Expects 1 error event + 2 data events.

Key decisions:
- Uses **401** (not 400) because the CEL program treats 400 as success ("already subscribed").
- Asserts against `.o365.audit` (post-pipeline name), not `.o365audit`.
- No `remove_package` in cleanup.

```txtar
# Test that a subscription permission error (AF10001) for one content type
# does not prevent collection from other content types.

[!external_stack] skip 'Skipping external stack test.'
[!exec:jq] skip 'Skipping test requiring absent jq command'

use_stack -profile ${CONFIG_PROFILES}/${PROFILE}
install_agent -profile ${CONFIG_PROFILES}/${PROFILE} -network_name NETWORK_NAME
docker_up -profile ${CONFIG_PROFILES}/${PROFILE} -network ${NETWORK_NAME} o365-mock
add_package -profile ${CONFIG_PROFILES}/${PROFILE}
add_package_policy -profile ${CONFIG_PROFILES}/${PROFILE} test_config.yaml DATA_STREAM_NAME

# Wait for documents: 1 error event + 2 data events = 3.
get_docs -profile ${CONFIG_PROFILES}/${PROFILE} -want 3 -timeout 5m ${DATA_STREAM_NAME}
cp stdout got_docs.json

# Verify error event mentions the rejected content type.
exec jq -r '[.hits.hits[]._source.error.message // empty] | flatten | .[]' got_docs.json
stdout 'Audit.TypeRequiringAdditionalPermissions'

# Verify 2 normal data events from the working content types.
exec jq '[.hits.hits[]._source | select(.o365.audit != null)] | length' got_docs.json
stdout '^2$'

# Clean up.
remove_package_policy -profile ${CONFIG_PROFILES}/${PROFILE} ${DATA_STREAM_NAME}
uninstall_agent -profile ${CONFIG_PROFILES}/${PROFILE} -timeout 1m
docker_down o365-mock
```

### Total API failure — invalid_content_type.txt

Tests that a single invalid content type results in exactly one error event and no data. Uses **403** (not 400) to trigger the error path. Uses `-confirm 15s` to verify no extra documents arrive.

```txtar
# Test that configuring a single invalid content type results in an error
# event and no data collection.

[!external_stack] skip 'Skipping external stack test.'
[!exec:jq] skip 'Skipping test requiring absent jq command'

use_stack -profile ${CONFIG_PROFILES}/${PROFILE}
install_agent -profile ${CONFIG_PROFILES}/${PROFILE} -network_name NETWORK_NAME
docker_up -profile ${CONFIG_PROFILES}/${PROFILE} -network ${NETWORK_NAME} o365-mock
add_package -profile ${CONFIG_PROFILES}/${PROFILE}
add_package_policy -profile ${CONFIG_PROFILES}/${PROFILE} test_config.yaml DATA_STREAM_NAME

get_docs -profile ${CONFIG_PROFILES}/${PROFILE} -want 1 -confirm 15s -timeout 5m ${DATA_STREAM_NAME}
cp stdout got_docs.json

exec jq -r '[.hits.hits[]._source.error.message // empty] | flatten | .[]' got_docs.json
stdout 'Audit.Nonexistent'

exec jq '[.hits.hits[]._source | select(.o365.audit != null)] | length' got_docs.json
stdout '^0$'

remove_package_policy -profile ${CONFIG_PROFILES}/${PROFILE} ${DATA_STREAM_NAME}
uninstall_agent -profile ${CONFIG_PROFILES}/${PROFILE} -timeout 1m
docker_down o365-mock
```

### Package upgrade — upgrade.txt

Tests that upgrading the package doesn't break data collection. Skips automatically if there's no previous release or if the latest change is a breaking change.

```txtar
[!external_stack] skip 'Skipping external stack test.'
[!has_previous_release] skip 'No previous release to upgrade from.'
[breaking_change] skip 'Cannot upgrade across breaking change.'
[!exec:jq] skip 'Skipping test requiring absent jq command'

use_stack -profile ${CONFIG_PROFILES}/${PROFILE}
install_agent -profile ${CONFIG_PROFILES}/${PROFILE} -network_name NETWORK_NAME
docker_up -profile ${CONFIG_PROFILES}/${PROFILE} -network ${NETWORK_NAME} o365-mock
add_package -profile ${CONFIG_PROFILES}/${PROFILE}
add_package_policy -profile ${CONFIG_PROFILES}/${PROFILE} test_config.yaml DATA_STREAM_NAME

# Verify initial data collection.
get_docs -profile ${CONFIG_PROFILES}/${PROFILE} -want 2 -timeout 5m ${DATA_STREAM_NAME}
cp stdout got_pre_upgrade.json
exec jq '.hits.total.value' got_pre_upgrade.json
stdout '^2$'

# Upgrade.
upgrade_package_latest -profile ${CONFIG_PROFILES}/${PROFILE}
stdout 'upgraded package '${PACKAGE_NAME}

# Verify data survives the upgrade.
get_docs -profile ${CONFIG_PROFILES}/${PROFILE} -want 2 -timeout 2m ${DATA_STREAM_NAME}
cp stdout got_post_upgrade.json
exec jq '.hits.total.value >= 2' got_post_upgrade.json
stdout '^true$'

remove_package_policy -profile ${CONFIG_PROFILES}/${PROFILE} ${DATA_STREAM_NAME}
uninstall_agent -profile ${CONFIG_PROFILES}/${PROFILE} -timeout 1m
docker_down o365-mock
```

### Mock config.yml — o365 full example

Handles OAuth token exchange, subscription endpoints with per-content-type routing, content listing with variable-capture, and content fetch:

```yaml
rules:
  # OAuth token endpoint.
  - path: /test-cel-tenant-id/oauth2/v2.0/token
    methods: [POST]
    query_params:
      client_id: test-cel-client-id
      client_secret: test-cel-client-secret
      grant_type: client_credentials
      scope: https://manage.office.com/.default
    request_headers:
      Content-Type:
        - "application/x-www-form-urlencoded"
    responses:
      - status_code: 200
        headers:
          Content-Type:
            - "application/json"
        body: |-
          {"access_token":"test-token","token_type":"Bearer","expires_in":3600}

  # Subscribe -- success.
  - path: /api/v1.0/test-cel-tenant-id/activity/feed/subscriptions/start
    methods: [POST]
    query_params:
      contentType: "Audit.SharePoint"
      PublisherIdentifier: test-cel-tenant-id
    request_headers:
      Authorization:
        - "Bearer test-token"
    responses:
      - status_code: 200
        headers:
          Content-Type:
            - "application/json"
        body: |-
          {"contentType":"Audit.SharePoint","status":"enabled","webhook":null}

  # Subscribe -- error (permission denied for this content type).
  - path: /api/v1.0/test-cel-tenant-id/activity/feed/subscriptions/start
    methods: [POST]
    query_params:
      contentType: "Audit.TypeRequiringAdditionalPermissions"
      PublisherIdentifier: test-cel-tenant-id
    request_headers:
      Authorization:
        - "Bearer test-token"
    responses:
      - status_code: 401
        headers:
          Content-Type:
            - "application/json"
        body: |-
          {"error":{"code":"AF10001","message":"Permission denied."}}

  # List content -- variable-capture for dynamic time params + self-referential URL.
  - path: /api/v1.0/test-cel-tenant-id/activity/feed/subscriptions/content
    methods: [GET]
    query_params:
      contentType: "Audit.SharePoint"
      startTime: "{startTime:.*}"
      endTime: "{endTime:.*}"
      PublisherIdentifier: test-cel-tenant-id
    request_headers:
      Authorization:
        - "Bearer test-token"
    responses:
      - status_code: 200
        headers:
          Content-Type:
            - "application/json"
        body: |-
          [{"contentType":"Audit.SharePoint","contentId":"sp-1","contentUri":"http://{{ hostname }}:{{ env "PORT" }}/api/v1.0/test-cel-tenant-id/activity/feed/audit/sp-1","contentCreated":"{{ .request.vars.endTime }}","contentExpiration":"2199-12-31T23:59:59.000Z"}]

  # Fetch content.
  - path: /api/v1.0/test-cel-tenant-id/activity/feed/audit/sp-1
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
          [{"Id":"sp-event-001","CreationTime":"2020-02-07T16:43:53","Workload":"SharePoint","Operation":"PageViewed","RecordType":4}]
```

Key patterns:
- **`{{ hostname }}`** — resolves to the Docker container hostname (set via `hostname:` in docker-compose). Required for self-referential URLs such as next-page links.
- **`{{ env "PORT" }}`** — resolves to the PORT environment variable.
- **`{varName:regex}`** — captures variable request values in query params.
- **`{{ .request.vars.endTime }}`** — references a captured query param in the response body.
- Rules are matched top-down; put more specific rules before less specific ones on the same path.

### test_config.yaml — o365 example

```yaml
input: cel
vars: ~
data_stream:
  vars:
    url: http://o365-mock:8080
    token_url: http://o365-mock:8080
    preserve_original_event: true
    client_id: test-cel-client-id
    client_secret: test-cel-client-secret
    azure_tenant_id: test-cel-tenant-id
    content_types: "Audit.SharePoint, Audit.General"
    interval: 30s
    initial_interval: 1h
    enable_request_tracer: false
```

`initial_interval: 1h` with `interval: 30s` gives one listing batch per content type per cycle. Longer values generate many batches and produce more documents than the assertion expects.
