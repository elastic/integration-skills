# system testing — HTTP endpoint (webhook) input

Input-specific guidance for system-testing data streams that use the `http_endpoint` input. Load `system-testing.md` (generic) first.

## Overview

HTTP endpoint system tests use `elastic/stream` as an HTTP client that posts NDJSON log data to the Elastic Agent's `http_endpoint` listener. The `stream` tool sends data as webhook-style HTTP POST requests using `STREAM_PROTOCOL=webhook`.

## Docker Compose pattern

### HTTP

```yaml
version: '2.3'
services:
  <package>-<stream>-webhook-http:
    image: docker.elastic.co/observability/stream:v0.20.0
    volumes:
      - ./sample_logs:/sample_logs:ro
    environment:
      - STREAM_PROTOCOL=webhook
      - STREAM_WEBHOOK_PROBE=false
      - STREAM_ADDR=http://elastic-agent:<port>/<url_path>
      - STREAM_WEBHOOK_HEADER=Authorization=<auth_value>
    command: log --start-signal=SIGHUP --delay=5s /sample_logs/<logfile>.log
```

### HTTPS

```yaml
  <package>-<stream>-webhook-https:
    image: docker.elastic.co/observability/stream:v0.20.0
    volumes:
      - ./sample_logs:/sample_logs:ro
    environment:
      - STREAM_PROTOCOL=webhook
      - STREAM_WEBHOOK_PROBE=false
      - STREAM_INSECURE=true
      - STREAM_ADDR=https://elastic-agent:<port>/<url_path>
      - STREAM_WEBHOOK_HEADER=Authorization=<auth_value>
    command: log --start-signal=SIGHUP --delay=5s /sample_logs/<logfile>.log
```

### With basic auth

```yaml
    environment:
      - STREAM_PROTOCOL=webhook
      - STREAM_WEBHOOK_PROBE=false
      - STREAM_ADDR=http://elastic-agent:<port>/<url_path>
      - STREAM_WEBHOOK_USERNAME=abc123
      - STREAM_WEBHOOK_PASSWORD=abc123
```

## Test config pattern

```yaml
wait_for_data_timeout: 1m
service: <package>-<stream>-webhook-http
service_notify_signal: SIGHUP
input: http_endpoint
data_stream:
  vars:
    listen_address: 0.0.0.0
    listen_port: <port>
    url: /<url_path>
    secret_value: <auth_value>
    preserve_original_event: true
assert:
  hit_count: <line_count>
```

## Key patterns

- **`STREAM_PROTOCOL=webhook`**: tells `stream` to POST data as HTTP webhook requests instead of raw TCP/UDP
- **`STREAM_WEBHOOK_PROBE=false`**: disables the probe request that some webhook receivers expect
- **`STREAM_ADDR`**: full URL including protocol, host (`elastic-agent`), port, and path. The path must match `url` in the test config vars.
- **`STREAM_WEBHOOK_HEADER`**: sets custom headers on each POST request — used for auth tokens, API keys. Format: `HeaderName=value`.
- **`STREAM_INSECURE=true`**: required for HTTPS when using self-signed certificates
- **Auth alignment**: the auth value in `STREAM_WEBHOOK_HEADER` (or `STREAM_WEBHOOK_USERNAME`/`PASSWORD`) must match the auth config in the test config vars (`secret_value`, `basic_auth`, etc.)
- **Sample log file**: place NDJSON files in `_dev/deploy/docker/sample_logs/`. Each line is posted as one HTTP request body.
- **Content-Type**: set `STREAM_WEBHOOK_HEADER=Content-Type=application/json` when the endpoint expects JSON

## Reference integrations

- [`zoom`](https://github.com/elastic/integrations/tree/main/packages/zoom) — HTTP and HTTPS webhook test configs
- [`cloudflare_logpush`](https://github.com/elastic/integrations/tree/main/packages/cloudflare_logpush) — multiple data streams with webhook tests
- [`http_endpoint`](https://github.com/elastic/integrations/tree/main/packages/http_endpoint) — reference implementation with basic auth and ack modes
