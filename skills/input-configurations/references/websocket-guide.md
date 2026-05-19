# WebSocket input guide

Complete reference for building and reviewing `websocket.yml.hbs` templates in Elastic integrations.

Documentation: [WebSocket Input Reference](https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-input-websocket.html)

## File location

```
packages/<package>/data_stream/<data_stream>/agent/stream/websocket.yml.hbs
```

## Required structure

The WebSocket input maintains a persistent connection to a WebSocket server and processes incoming messages as events. Every template must configure the connection URL and typically includes authentication, SSL, and message handling.

```yaml
url: {{url}}

{{#if auth.basic}}
auth.basic:
  user: {{username}}
  password: {{password}}
{{/if}}
{{#if headers}}
headers:
{{headers}}
{{/if}}

{{#if ssl}}
ssl: {{ssl}}
{{/if}}

{{#if proxy_url}}
proxy_url: {{proxy_url}}
{{/if}}

{{#if program}}
program: |
  {{program}}
{{/if}}
```

## Validation rules

### 1. URL must use a variable

The WebSocket URL must reference a Handlebars variable. Hardcoded URLs prevent users from configuring the endpoint.

```yaml
# Correct
url: {{url}}

# Never acceptable
url: wss://api.example.com/stream

# Wrong protocol -- must be ws:// or wss://, not https://
url: https://api.example.com/stream
```

### 2. Authentication must use variables

All credential values must reference Handlebars variables. Hardcoded credentials are a critical security issue.

```yaml
# Correct -- basic auth
{{#if auth.basic}}
auth.basic:
  user: {{username}}
  password: {{password}}
{{/if}}

# Correct -- token in header
{{#if api_token}}
headers:
  Authorization: Bearer {{api_token}}
{{/if}}

# Never acceptable
auth.basic:
  password: 'my-secret-password'
```

### 3. SSL configuration for WSS URLs

WebSocket connections using `wss://` require SSL/TLS. The SSL configuration block must be available.

```yaml
{{#if ssl}}
ssl: {{ssl}}
{{/if}}
```

### 4. Credential redaction for state

The WebSocket input supports CEL programs and state management. Credentials stored in the `state` block are safe if they are listed in `redact.fields`. The redaction mechanism masks these values in logs and traces.

```yaml
state:
  api_key: '{{api_key}}'

redact:
  fields:
    - api_key
```

Credentials in state **with** a corresponding `redact.fields` entry are not a security issue. Credentials in state **without** a corresponding `redact.fields` entry, or hardcoded credentials not using template variables, are security issues.

### 5. CEL program presence

Many WebSocket integrations require a CEL program to parse incoming messages, filter heartbeats, handle subscription flows, or transform data before it becomes events. When a `program` field is present, the CEL code must be reviewed for correctness.

```yaml
{{#if program}}
program: |
  {{program}}
{{/if}}
```

Inline CEL programs (not using a variable) are also valid:

```yaml
program: |
  state.response.decode_json().as(event, {
    "events": [{"message": event.encode_json()}],
  })
```

Note: older integrations may use `bytes(state.response).decode_json()` instead of `state.response.decode_json()`. The `bytes()` conversion is not required in newer beats versions (same version dependency as the CEL input). Omit it in new integrations.

## URL program

The `url_program` config runs a CEL program **once** before the WebSocket connection is established. It uses the `state` object (including cursor values) to dynamically construct the connection URL. Available from beats 8.15+.

```yaml
url: ws://api.example.com/v1/stream
state:
  initial_start_time: "2022-01-01T00:00:00Z"
url_program: |
  state.url + "?since=" + state.?cursor.since.orValue(state.initial_start_time)
program: |
  state.response.decode_json().as(msg, {
    "events": [{"message": msg.encode_json()}],
    "cursor": {"since": msg.timestamp}
  })
```

Use `url_program` when:
- The WebSocket URL needs a cursor or timestamp parameter to resume from the last position
- The URL varies based on state values set during previous evaluations
- The endpoint requires query parameters derived from runtime context

The program must evaluate to a valid URL string. It has access to `state.url` (the configured base URL), `state.cursor` (persisted cursor values), and any custom state fields.

## Authentication patterns

### Basic authentication

Standard HTTP basic auth sent during the WebSocket handshake.

```yaml
{{#if auth.basic}}
auth.basic:
  user: {{username}}
  password: {{password}}
{{/if}}
```

### Token-based authentication via headers

API tokens or bearer tokens sent as HTTP headers during the handshake.

```yaml
{{#if api_token}}
headers:
  Authorization: Bearer {{api_token}}
{{/if}}
```

Headers can also carry additional metadata:

```yaml
{{#if api_token}}
headers:
  Authorization: Bearer {{api_token}}
  X-API-Version: {{api_version}}
{{/if}}
```

### Authentication via CEL state

When authentication tokens need to be used within the CEL program (e.g., for subscription messages sent after connection), they are placed in the `state` block with redaction.

```yaml
state:
  api_key: '{{api_key}}'

redact:
  fields:
    - api_key

program: |
  // CEL program that uses state.api_key for subscription
```

## Reconnection and keepalive

### Retry settings

WebSocket connections may drop due to network issues or server restarts. Retry parameters control automatic reconnection behavior.

| Parameter | Type | Description |
|---|---|---|
| `retry.wait_min` | duration | Minimum wait before reconnecting |
| `retry.wait_max` | duration | Maximum wait before reconnecting |
| `retry.max_attempts` | int | Maximum number of reconnection attempts |

These parameters should be appropriate for the target API. Aggressive retry settings may trigger rate limiting; overly conservative settings increase data loss during outages.

### Ping interval and wait timeout

Long-lived WebSocket connections need keepalive mechanisms to detect dead connections.

```yaml
{{#if ping_interval}}
ping_interval: {{ping_interval}}
{{/if}}
{{#if wait_timeout}}
wait_timeout: {{wait_timeout}}
{{/if}}
```

`ping_interval` controls how often the client sends WebSocket ping frames. `wait_timeout` controls how long the client waits for a message before considering the connection dead.

## CEL program patterns

The WebSocket input uses CEL programs for message processing. The program receives each message in `state.response` and must return a map containing an `events` array.

### Basic message handling

Decode the JSON message and emit it as a single event:

```yaml
program: |
  state.response.decode_json().as(msg, {
    "events": [{"message": msg.encode_json()}],
  })
```

### Conditional message filtering

Skip non-data messages (heartbeats, acknowledgements) and only emit data events:

```yaml
program: |
  state.response.decode_json().as(msg,
    has(msg.type) && msg.type == "data" ?
      {
        "events": [{"message": msg.payload.encode_json()}],
      }
    :
      {
        "events": [],
      }
  )
```

### Heartbeat filtering

Many streaming APIs send periodic heartbeat messages that should be discarded:

```yaml
program: |
  state.response.decode_json().as(msg,
    msg.type == "heartbeat" ?
      {"events": []}
    :
      {"events": [{"message": msg.encode_json()}]}
  )
```

### Batch message handling

When a single WebSocket message contains an array of events:

```yaml
program: |
  state.response.decode_json().as(msg,
    msg.type == "batch" ?
      {"events": msg.data.map(e, {"message": e.encode_json()})}
    :
      {"events": [{"message": msg.encode_json()}]}
  )
```

### Subscription messages

Some WebSocket APIs require sending a subscription message after the connection is established. This is typically handled within the CEL program or through initial state configuration.

## CEL program detection

When a WebSocket template contains a `program` field with CEL code, the CEL code itself may need review according to CEL-specific validation rules. Look for:

- `state.response` access patterns for message parsing
- `encode_json()` / `decode_json()` for serialization
- Conditional logic for message type filtering
- State mutations that carry values between messages
- Subscription or authentication flows embedded in the program

If the CEL program is complex (pagination, state management, multi-step flows), it should be reviewed against the CEL program skill's rules in addition to the WebSocket input rules.

## Common configuration patterns

### Basic WebSocket connection

```yaml
url: {{url}}

{{#if api_token}}
headers:
  Authorization: Bearer {{api_token}}
{{/if}}

{{#if ssl}}
ssl: {{ssl}}
{{/if}}
```

### With basic authentication

```yaml
url: {{url}}

auth.basic:
  user: {{username}}
  password: {{password}}

{{#if ssl}}
ssl: {{ssl}}
{{/if}}
```

### With CEL message processing

```yaml
url: {{url}}

{{#if api_token}}
headers:
  Authorization: Bearer {{api_token}}
{{/if}}

program: |
  state.response.decode_json().as(msg,
    has(msg.type) && msg.type == "data" ?
      {
        "events": [{"message": msg.payload.encode_json()}],
      }
    :
      {
        "events": [],
      }
  )

{{#if ssl}}
ssl: {{ssl}}
{{/if}}
```

### Streaming API with proxy

```yaml
url: {{url}}

{{#if api_token}}
headers:
  Authorization: Bearer {{api_token}}
  X-API-Version: {{api_version}}
{{/if}}

{{#if proxy_url}}
proxy_url: {{proxy_url}}
{{/if}}

{{#if ssl}}
ssl: {{ssl}}
{{/if}}
```

## Parameters reference

| Parameter | Type | Description |
|---|---|---|
| `url` | string | WebSocket URL (`ws://` or `wss://`) |
| `program` | string | CEL program for message handling |
| `state` | object | Initial state passed to the CEL program |
| `redact.fields` | array | State fields to mask in logs and traces |
| `auth.basic.user` | string | Basic auth username |
| `auth.basic.password` | string | Basic auth password |
| `headers` | map | Additional HTTP headers sent during handshake |
| `ssl` | object | SSL/TLS configuration |
| `proxy_url` | string | HTTP proxy URL |
| `ping_interval` | duration | WebSocket ping frame interval |
| `wait_timeout` | duration | Maximum wait time for a message |
| `retry.wait_min` | duration | Minimum reconnection wait |
| `retry.wait_max` | duration | Maximum reconnection wait |
| `retry.max_attempts` | int | Maximum reconnection attempts |

## Review checklist

### Connection

- [ ] URL uses a Handlebars variable -- **HIGH**
- [ ] URL protocol is correct (`ws://` or `wss://`, not `http://` or `https://`) -- **HIGH**
- [ ] SSL configuration available for `wss://` connections -- **HIGH**

### Authentication

- [ ] No hardcoded credentials -- **CRITICAL**
- [ ] Auth method appropriate for the target API (basic, header token, or CEL state) -- **HIGH**
- [ ] Token-based auth uses headers with Handlebars variables -- **MEDIUM**
- [ ] Credentials in `state` have corresponding `redact.fields` entries -- **HIGH**

### Message handling

- [ ] CEL program present when message parsing/filtering is needed -- **HIGH**
- [ ] Heartbeat/ping messages filtered in the CEL program -- **MEDIUM**
- [ ] Batch messages unpacked into individual events -- **MEDIUM**
- [ ] Subscription messages handled if the API requires them -- **MEDIUM**

### Reconnection

- [ ] Retry settings appropriate for the target API -- **MEDIUM**
- [ ] `ping_interval` configured for long-lived connections -- **LOW**
- [ ] `wait_timeout` set to detect dead connections -- **LOW**
- [ ] Proxy configuration available -- **LOW**

### CEL program (when present)

- [ ] `state.response` correctly accessed and decoded -- **HIGH**
- [ ] Events array properly constructed in all code paths -- **HIGH**
- [ ] Non-data messages (heartbeats, acks) produce empty events arrays -- **MEDIUM**
- [ ] Complex CEL programs reviewed against CEL skill rules -- **MEDIUM**
