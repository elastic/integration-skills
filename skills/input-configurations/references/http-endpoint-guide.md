# HTTP Endpoint input guide

Complete reference for building and reviewing `http_endpoint.yml.hbs` templates in Elastic integrations.

Documentation: [HTTP Endpoint Input Reference](https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-input-http_endpoint.html)

## File location

```
packages/<package>/data_stream/<data_stream>/agent/stream/http_endpoint.yml.hbs
```

## Required structure

The HTTP Endpoint input receives data by listening for incoming HTTP requests (webhooks). Every template must configure listener settings and should include authentication and SSL/TLS.

```yaml
listen_address: {{listen_address}}
listen_port: {{listen_port}}

{{#if url}}
url: {{url}}
{{/if}}

{{#if ssl}}
ssl: {{ssl}}
{{/if}}

{{#if secret_header}}
secret.header: {{secret_header}}
{{/if}}
{{#if secret_value}}
secret.value: {{secret_value}}
{{/if}}
{{#if basic_auth}}
basic_auth: {{basic_auth}}
{{/if}}

{{#if content_type}}
content_type: {{content_type}}
{{/if}}
{{#if prefix}}
prefix: {{prefix}}
{{/if}}

{{#if response_code}}
response_code: {{response_code}}
{{/if}}
{{#if response_body}}
response_body: {{response_body}}
{{/if}}

{{#if enable_request_tracer}}
tracer.filename: "../../logs/http_endpoint/http-request-trace-*.ndjson"
tracer.maxbackups: 5
{{/if}}
```

## Validation rules

### 1. Listen address and port must use variables

The bind address and port must never be hardcoded. They must reference Handlebars variables so users can configure them through the manifest.

```yaml
# Correct
listen_address: {{listen_address}}
listen_port: {{listen_port}}

# Never acceptable
listen_address: 0.0.0.0
listen_port: 8080
```

### 2. URL path should be specific

The endpoint path should identify the integration or data source. Generic paths like `/` or `/webhook` create conflicts when multiple integrations run on the same agent.

```yaml
{{#if url}}
url: {{url}}
{{/if}}
```

Good defaults: `/webhooks/vendor-name`, `/api/v1/events`. Avoid: `/`, `/webhook`.

### 3. SSL/TLS should be available

Production webhook endpoints should support HTTPS. The SSL configuration block must be present as a conditional.

```yaml
{{#if ssl}}
ssl: {{ssl}}
{{/if}}
```

The SSL object typically includes:

```yaml
ssl:
  enabled: true
  certificate: /path/to/cert.pem
  key: /path/to/key.pem
```

### 4. Authentication recommended

A webhook endpoint without authentication is a security risk. Templates should support at least one authentication method: secret header validation, HMAC signature verification, or basic authentication.

```yaml
{{#if secret_header}}
secret.header: {{secret_header}}
{{/if}}
{{#if secret_value}}
secret.value: {{secret_value}}
{{/if}}
```

### 5. Content type handling

The expected content type should be configurable when the webhook may send different formats.

```yaml
{{#if content_type}}
content_type: {{content_type}}
{{/if}}
```

Common values: `application/json`, `application/x-ndjson`, `application/x-www-form-urlencoded`.

### 6. Credential redaction with state

The HTTP Endpoint input supports CEL programs and state management. Credentials stored in the `state` block are safe if they are listed in `redact.fields`. The redaction mechanism masks these values in logs and request traces.

```yaml
state:
  api_key: '{{api_key}}'

redact:
  fields:
    - api_key
```

Credentials in state **with** a corresponding `redact.fields` entry are not a security issue. Credentials in state **without** a corresponding `redact.fields` entry, or hardcoded credentials not using template variables, are security issues.

### 7. Request tracer path must match input type name

The tracer log directory must match the input type name. A mismatch causes the agent to fail at startup with a path validation error ([elastic/integrations#17619](https://github.com/elastic/integrations/pull/17619)).

For `http_endpoint`, the directory is `http_endpoint`. Tracer support was added in 8.12 ([elastic/beats#36957](https://github.com/elastic/beats/pull/36957)).

Two configuration styles exist:

| Style | Min version | Notes |
|---|---|---|
| `{{#if enable_request_tracer}}` conditional | 8.12.0+ | Wraps `filename` + `maxbackups` in a Handlebars guard |
| `tracer:` block with `enabled:` field | 8.15.0+ | Allows trace log cleanup when disabled ([elastic/beats#40005](https://github.com/elastic/beats/pull/40005)) |

Conditional format (pre-8.15.0 compatibility):

```yaml
{{#if enable_request_tracer}}
tracer.filename: "../../logs/http_endpoint/http-request-trace-*.ndjson"
tracer.maxbackups: 5
{{/if}}
```

Block format (8.15.0+):

```yaml
tracer:
  enabled: {{enable_request_tracer}}
  filename: "../../logs/http_endpoint/http-request-trace-*.ndjson"
  maxbackups: 5
```

Invalid examples:

```yaml
# Directory does not match input type
tracer.filename: "../../logs/webhook/http-request-trace-*.ndjson"

# Relative path outside logs directory
tracer.filename: "./logs/trace.log"
```

## Authentication patterns

### Secret header validation

The webhook sender includes a secret value in a specific HTTP header. The input validates the header value before accepting the request.

```yaml
{{#if secret_header}}
secret.header: {{secret_header}}
{{/if}}
{{#if secret_value}}
secret.value: {{secret_value}}
{{/if}}
```

Example: the webhook sends `X-Webhook-Secret: my-secret-token`. The template sets `secret.header` to the header name and `secret.value` to the expected value.

### HMAC signature validation

For webhooks that sign the request body with HMAC (e.g., GitHub webhooks). The input computes the HMAC of the body and compares it to the signature in the header.

```yaml
{{#if hmac_header}}
hmac.header: {{hmac_header}}
{{/if}}
{{#if hmac_key}}
hmac.key: {{hmac_key}}
{{/if}}
{{#if hmac_type}}
hmac.type: {{hmac_type}}
{{/if}}
{{#if hmac_prefix}}
hmac.prefix: {{hmac_prefix}}
{{/if}}
```

GitHub webhook example:

```yaml
hmac.header: X-Hub-Signature-256
hmac.key: {{hmac_key}}
hmac.type: sha256
hmac.prefix: "sha256="
```

### Basic authentication

Standard HTTP basic authentication.

```yaml
{{#if username}}
basic_auth.username: {{username}}
{{/if}}
{{#if password}}
basic_auth.password: {{password}}
{{/if}}
```

### CRC token verification

Some webhook providers (e.g., Twitter/X) send a CRC challenge request that the endpoint must respond to before the provider starts sending events.

```yaml
crc.provider: {{crc_provider}}
crc.secret: {{crc_secret}}
```

## Response configuration

The response sent back to the webhook caller can be customized. This is useful for webhook verification handshakes or for providers that expect a specific response format.

```yaml
{{#if response_code}}
response_code: {{response_code}}
{{/if}}
{{#if response_body}}
response_body: {{response_body}}
{{/if}}
```

Example with a custom response:

```yaml
response_code: 200
response_body: '{"status": "received"}'
```

## Request limits

Large payloads or slow clients can be constrained with body size and timeout limits.

```yaml
{{#if max_body_size}}
max_body_size: {{max_body_size}}
{{/if}}
{{#if timeout}}
timeout: {{timeout}}
{{/if}}
```

## CEL program support

The HTTP Endpoint input supports optional CEL programs for request processing. When a `program` field is present, the input uses CEL to transform incoming requests before they become events.

```yaml
{{#if program}}
program: |
  // CEL program for request processing
{{/if}}
```

When CEL is used with state and credentials, the redaction rules from validation rule 6 apply.

## Common configuration patterns

### Basic webhook receiver

```yaml
listen_address: {{listen_address}}
listen_port: {{listen_port}}
url: {{url}}

{{#if secret_header}}
secret.header: {{secret_header}}
{{/if}}
{{#if secret_value}}
secret.value: {{secret_value}}
{{/if}}

{{#if ssl}}
ssl: {{ssl}}
{{/if}}
```

### GitHub webhook with HMAC

```yaml
listen_address: {{listen_address}}
listen_port: {{listen_port}}
url: /webhooks/github

content_type: application/json

{{#if hmac_key}}
hmac.header: X-Hub-Signature-256
hmac.key: {{hmac_key}}
hmac.type: sha256
hmac.prefix: "sha256="
{{/if}}

{{#if ssl}}
ssl: {{ssl}}
{{/if}}
```

### Streaming API with CEL and state

```yaml
listen_address: {{listen_address}}
listen_port: {{listen_port}}
url: {{url}}

state:
  api_key: '{{api_key}}'

redact:
  fields:
    - api_key

{{#if ssl}}
ssl: {{ssl}}
{{/if}}
```

## Parameters reference

| Parameter | Type | Description |
|---|---|---|
| `listen_address` | string | Bind address for the listener |
| `listen_port` | int | Port to listen on |
| `url` | string | URL path to listen on |
| `ssl` | object | SSL/TLS configuration |
| `secret.header` | string | Header name containing the secret value |
| `secret.value` | string | Expected secret value |
| `basic_auth.username` | string | Basic auth username |
| `basic_auth.password` | string | Basic auth password |
| `hmac.header` | string | Header containing the HMAC signature |
| `hmac.key` | string | HMAC secret key |
| `hmac.type` | string | Hash algorithm (sha256, sha1) |
| `hmac.prefix` | string | Signature prefix string |
| `content_type` | string | Expected content type of incoming requests |
| `prefix` | string | JSON key prefix for incoming data |
| `response_code` | int | HTTP status code to return |
| `response_body` | string | Response body to return |
| `max_body_size` | string | Maximum allowed request body size |
| `timeout` | duration | Request timeout for slow clients |
| `crc.provider` | string | CRC challenge provider name |
| `crc.secret` | string | CRC challenge secret |
| `tracer.enabled` | bool | Enable/disable request tracing (8.15.0+) |
| `tracer.filename` | string | Trace log file path (8.12.0+) |
| `tracer.maxbackups` | int | Maximum number of trace log backup files |

## Review checklist

### Listener configuration

- [ ] `listen_address` uses a Handlebars variable -- **HIGH**
- [ ] `listen_port` uses a Handlebars variable -- **HIGH**
- [ ] URL path is specific, not generic (`/` or `/webhook`) -- **MEDIUM**

### Security

- [ ] At least one authentication method configured (secret header, HMAC, or basic auth) -- **HIGH**
- [ ] No hardcoded secrets or credentials -- **CRITICAL**
- [ ] SSL/TLS configuration block available -- **HIGH**
- [ ] Webhook signature validation present when the provider supports it (e.g., HMAC for GitHub) -- **MEDIUM**
- [ ] Credentials in `state` have corresponding `redact.fields` entries -- **HIGH**

### Content handling

- [ ] Content type configurable when the webhook may send different formats -- **MEDIUM**
- [ ] Response code and body customizable when the provider requires specific responses -- **LOW**

### Request processing

- [ ] Max body size configured when large payloads are expected -- **LOW**
- [ ] Request timeout set -- **LOW**
- [ ] CEL program validated if present -- **MEDIUM**

### Request tracer

- [ ] Tracer directory matches `http_endpoint` -- **HIGH**
- [ ] Tracer format correct for target stack version (conditional vs block) -- **LOW**
