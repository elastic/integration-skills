# TCP and UDP input guide

Complete reference for building and reviewing `tcp.yml.hbs` and `udp.yml.hbs` templates in Elastic integrations. TCP and UDP are listener-based inputs that receive data pushed to the agent over a network socket. They share most structural conventions but differ in transport-layer capabilities.

> **Documentation**: [TCP Input Reference](https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-input-tcp.html) | [UDP Input Reference](https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-input-udp.html)

## File location

```
packages/<package>/data_stream/<data_stream>/agent/stream/tcp.yml.hbs
packages/<package>/data_stream/<data_stream>/agent/stream/udp.yml.hbs
```

## Required structure

### TCP template

```yaml
host: {{listen_address}}:{{listen_port}}

{{#if max_message_size}}
max_message_size: {{max_message_size}}
{{/if}}
{{#if framing}}
framing: {{framing}}
{{/if}}
{{#if line_delimiter}}
line_delimiter: {{line_delimiter}}
{{/if}}

{{#if max_connections}}
max_connections: {{max_connections}}
{{/if}}
{{#if timeout}}
timeout: {{timeout}}
{{/if}}

{{#if ssl}}
ssl: {{ssl}}
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

### UDP template

```yaml
host: {{listen_address}}:{{listen_port}}

{{#if max_message_size}}
max_message_size: {{max_message_size}}
{{/if}}
{{#if read_buffer_size}}
read_buffer: {{read_buffer_size}}
{{/if}}
{{#if timeout}}
timeout: {{timeout}}
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

## TCP vs UDP selection

| Aspect | TCP | UDP |
|---|---|---|
| Reliability | Guaranteed delivery | No delivery guarantee |
| Ordering | Ordered | No ordering guarantee |
| Connection model | Connection-oriented | Connectionless |
| SSL/TLS | Supported | Not supported |
| Framing | Delimiter or RFC 6587 | Datagram boundaries |
| Typical use | Reliable logging, sensitive data | High-volume syslog |

Security-sensitive logs (firewall, authentication, PII) should use TCP with TLS. UDP is appropriate for high-volume, loss-tolerant syslog streams.

## Validation rules

### 1. Host must use variables

The `host` field must reference Handlebars variables, never hardcoded addresses or ports.

```yaml
# correct
host: {{listen_address}}:{{listen_port}}

# wrong -- hardcoded
host: 0.0.0.0:514
host: localhost:9000
```

### 2. Framing must be valid (TCP only)

TCP supports two framing modes. Syslog streams require `rfc6587`.

```yaml
# valid values
framing: delimiter    # line-based, the default
framing: rfc6587      # syslog octet counting

# invalid
framing: json
framing: custom
```

A TCP syslog stream without `framing: rfc6587` is a defect. Delimiter framing will silently corrupt multi-line syslog messages.

### 3. SSL/TLS for sensitive data (TCP only)

TCP templates that carry security-sensitive logs must include the SSL block. UDP does not support SSL.

```yaml
{{#if ssl}}
ssl: {{ssl}}
{{/if}}
```

The corresponding manifest should expose the full SSL configuration: `certificate_authorities`, `certificate`, `key`, and `verification_mode`.

### 4. Buffer sizing for high-volume UDP

UDP sockets drop packets when the kernel receive buffer overflows. High-volume syslog sources must expose a configurable read buffer.

```yaml
{{#if read_buffer_size}}
read_buffer: {{read_buffer_size}}
{{/if}}
```

A reasonable default for high-volume syslog is `100MiB`. Missing buffer configuration on a high-volume UDP stream is a review finding.

### 5. Message size limits

Both TCP and UDP should expose `max_message_size` when messages can exceed the default.

```yaml
{{#if max_message_size}}
max_message_size: {{max_message_size}}
{{/if}}
```

Typical values: `8KiB` for standard syslog, `64KiB` for extended syslog or structured log formats.

### 6. Preserve original event before processing

When the template includes processors that modify the `message` field (especially syslog parsing), the `copy_fields` processor that preserves the original event must appear before any parsing processor.

```yaml
processors:
{{#if preserve_original_event}}
- copy_fields:
    fields:
      - from: message
        to: event.original
{{/if}}
{{#if syslog}}
- syslog:
    {{syslog_options}}
{{/if}}
{{processors}}
```

Reversing the order means `event.original` captures the already-parsed message instead of the raw input.

## Syslog-specific patterns

### Syslog over TCP

```yaml
host: {{listen_address}}:{{listen_port}}
framing: rfc6587
max_message_size: 64KiB

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
{{#if preserve_original_event}}
- copy_fields:
    fields:
      - from: message
        to: event.original
{{/if}}
- syslog:
    field: message
    format: auto
{{#if processors}}
{{processors}}
{{/if}}
```

### Syslog over UDP

```yaml
host: {{listen_address}}:{{listen_port}}
max_message_size: 64KiB
read_buffer: 100MiB

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
{{#if preserve_original_event}}
- copy_fields:
    fields:
      - from: message
        to: event.original
{{/if}}
- syslog:
    field: message
    format: auto
{{#if processors}}
{{processors}}
{{/if}}
```

### Required syslog stream variables

Syslog data streams must expose the following variables in the manifest:

- **`ssl`** (TCP only): Full SSL/TLS configuration object. Type `yaml`. Many syslog sources (firewalls, network devices) transmit over TLS and the integration must support it.
- **`processors`**: Custom processors passthrough. Always present per the common patterns.
- **`syslog_options`** or equivalent: Controls the syslog processor format. At minimum, expose `format: auto` as the default.

### The `tz_offset` variable convention

Syslog messages frequently arrive without timezone information. Integrations should expose a `tz_offset` variable that lets users declare the source device's UTC offset so the ingest pipeline can stamp events with the correct time.

Convention in the manifest:

```yaml
- name: tz_offset
  type: text
  title: Timezone Offset
  description: >-
    IANA time zone or UTC offset for timestamps without timezone information
    (e.g., America/New_York, +02:00, UTC). Defaults to UTC.
  multi: false
  required: false
  show_user: true
  default: UTC
```

The ingest pipeline or a processor uses this value to adjust parsed timestamps. Without it, events from devices in non-UTC zones will have incorrect timestamps.

## Advanced patterns

### Secure TCP with TLS

```yaml
host: {{listen_address}}:{{listen_port}}

{{#if ssl}}
ssl: {{ssl}}
{{/if}}
```

The manifest must expose the SSL block with sub-fields or accept a YAML object. The SSL configuration supports:
- `certificate_authorities`: CA certificates for client verification
- `certificate`: Server certificate
- `key`: Server private key
- `verification_mode`: `full`, `certificate`, `strict`, or `none`

### High-volume TCP listener

```yaml
host: {{listen_address}}:{{listen_port}}
max_connections: {{max_connections}}
max_message_size: {{max_message_size}}
timeout: {{timeout}}
```

### Keep-alive (TCP only)

```yaml
{{#if keep_alive}}
keep_alive: {{keep_alive}}
{{/if}}
```

Persistent connections benefit from keep-alive to detect dead clients without waiting for a timeout.

### Client IP restrictions (TCP only)

```yaml
{{#if include_source_ips}}
include_source_ips:
{{#each include_source_ips as |ip|}}
  - {{ip}}
{{/each}}
{{/if}}
```

### Queue size (UDP only)

```yaml
{{#if queue_size}}
queue_size: {{queue_size}}
{{/if}}
```

### Encoding

```yaml
{{#if encoding}}
encoding: {{encoding}}
{{/if}}
```

Specify when the source sends non-UTF-8 encoded data.

## Parameters reference

### TCP parameters

| Parameter | Type | Description |
|---|---|---|
| `host` | string | Listen address and port (`address:port`) |
| `max_message_size` | size | Maximum message size (e.g., `64KiB`) |
| `framing` | string | `delimiter` or `rfc6587` |
| `line_delimiter` | string | Delimiter character(s) for delimiter framing |
| `max_connections` | int | Maximum concurrent connections |
| `timeout` | duration | Connection timeout |
| `ssl` | object | SSL/TLS configuration |
| `keep_alive` | duration | TCP keep-alive interval |
| `keep_null` | bool | Keep null values in parsed JSON |
| `encoding` | string | Character encoding |
| `include_source_ips` | array | Allowed client IP addresses |

### UDP parameters

| Parameter | Type | Description |
|---|---|---|
| `host` | string | Listen address and port (`address:port`) |
| `max_message_size` | size | Maximum message size (e.g., `64KiB`) |
| `read_buffer` | size | Socket receive buffer size (e.g., `100MiB`) |
| `timeout` | duration | Read timeout |
| `queue_size` | int | Internal message queue size |
| `keep_null` | bool | Keep null values |
| `encoding` | string | Character encoding |

## Review checklist

### Listener configuration
- [ ] `host` uses `{{listen_address}}:{{listen_port}}` variables
- [ ] `max_message_size` exposed when messages may exceed defaults
- [ ] `timeout` configured where appropriate

### TCP-specific
- [ ] `framing` set to `rfc6587` for syslog streams
- [ ] `ssl` block present for security-sensitive data
- [ ] `max_connections` exposed for high-connection-count sources
- [ ] Keep-alive configured for persistent connections
- [ ] Client IP restrictions considered for security-sensitive listeners

### UDP-specific
- [ ] `read_buffer` configured for high-volume sources
- [ ] UDP is appropriate for the data sensitivity level (not used for secrets or PII)
- [ ] Queue size appropriate for message volume

### Syslog streams
- [ ] Syslog processor present with `format: auto`
- [ ] `preserve_original_event` copy occurs before syslog parsing
- [ ] `tz_offset` variable exposed in the manifest for timezone handling
- [ ] `ssl` variable exposed in the manifest (TCP syslog)
- [ ] `processors` passthrough present

### Processing
- [ ] `preserve_original_event` copies message before any parsing
- [ ] Tags block follows common patterns (conditional `preserve_original_event`, `each` tags, `forwarded`/`disable_host` coupling)
- [ ] Processors passthrough at top level
- [ ] Encoding specified for non-UTF-8 data
