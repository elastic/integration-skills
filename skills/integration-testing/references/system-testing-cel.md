# system testing — CEL input

Input-specific guidance for system-testing data streams that use the `cel` input. Load `system-testing.md` (generic) first.

## Overview

CEL system tests require a mock HTTP API to stand in for the real vendor API. The mock is an `elastic/stream` http-server container defined in `_dev/deploy/docker/docker-compose.yml` with a rule-based config file.

## Docker Compose pattern

```yaml
version: '2.3'
services:
  <package>-<stream>-mock:
    image: docker.elastic.co/observability/stream:v0.22.0
    volumes:
      - ./files:/files:ro
    command: http-server --addr=:8090 --config=/files/config-<stream>.yml
    ports:
      - 8090
```

The mock config file at `_dev/deploy/docker/files/config-<stream>.yml` contains rule-based request matching with response definitions.

## Test config pattern

```yaml
wait_for_data_timeout: 1m
input: cel
service: <package>-<stream>-mock
data_stream:
  vars:
    url: http://{{Hostname}}:{{Port}}
assert:
  hit_count: <expected_count>
```

## Key patterns

- **Rule-based mock config**: rules match on `path`, `methods`, `query_params`, and `request_headers` (first match wins, top-down ordering)
- **Variable-capture patterns**: use `{varName:regex}` in query param values for dynamic params like timestamps — without these, the mock returns the same data for every time window, causing infinite loops
- **Two-round cursor testing**: set `interval: 2s` in test config so the agent completes one pagination cycle, persists the cursor, then fires a second cycle to verify cursor persistence
- **`assert.hit_count`**: must account for events from both evaluation rounds

## Debugging 0 hits (CEL-specific)

### Step 1: Check the mock container log (always first)

```
build/container-logs/<package_name>-<datastream_name>-<DIGIT>.log
```

This log shows every HTTP request the CEL program makes against the mock API, including which rules matched. **Tail the last 100–200 lines** as the first diagnostic step.

Common patterns:
- **Hundreds of requests with advancing timestamps**: infinite time-window looping — the mock lacks variable-capture catchall rules
- **No requests at all**: the agent never contacted the mock — check `url` and `service:` in the test config
- **Requests with no rule matches**: query param or header mismatch between CEL program and mock rules
- **401/403 responses**: auth rule mismatch in mock config

### Step 2: Check agent log for dropped events

Follow the generic debugging steps in `system-testing.md` → "Debugging system test failures — general".

A CEL-specific rejection reason:
- `Duplicate field '@timestamp'`: the CEL program sets `@timestamp` in event output while the framework also adds it. Fix: only emit `{"message": e.encode_json()}`.

## Additional CEL-specific failure patterns

- **0 hits with CEL input**: check container logs first (Step 1) before any other debugging
- **Infinite time-window looping**: mock config lacks variable-capture catchall rules — fix by adding `startTime: "{startTime:.*}"` patterns

## Detailed mock setup reference

For comprehensive mock API flow design, variable-capture syntax, pagination mocking, and two-round cursor persistence patterns, see the `cel-programs` skill → `references/cel-system-tests.md`.

## Reference integrations

- Any CEL integration in `elastic/integrations` — e.g. `wiz`, `ti_otx`, `canva` — uses `elastic/stream` http-server mocks with rule configs
