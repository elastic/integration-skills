# system testing — TCP/UDP input

Input-specific guidance for system-testing data streams that use `tcp` or `udp` inputs. Load `system-testing.md` (generic) first.

## Overview

TCP/UDP system tests use `elastic/stream` as a log sender that replays sample log files to the Elastic Agent's listening port. The `stream` tool sends lines over TCP, UDP, or TLS, coordinated with `service_notify_signal: SIGHUP` so the agent starts listening before the sender starts transmitting.

## Docker Compose pattern

```yaml
version: '2.3'
services:
  <package>-<stream>-tcp:
    image: docker.elastic.co/observability/stream:v0.18.0
    volumes:
      - ./sample_logs:/sample_logs:ro
    command: log --start-signal=SIGHUP --delay=5s --addr elastic-agent:<port> -p=tcp /sample_logs/<logfile>.log

  <package>-<stream>-udp:
    image: docker.elastic.co/observability/stream:v0.18.0
    volumes:
      - ./sample_logs:/sample_logs:ro
    command: log --start-signal=SIGHUP --delay=5s --addr elastic-agent:<port> -p=udp /sample_logs/<logfile>.log
```

For TLS-over-TCP, use `-p=tls --insecure`:

```yaml
  <package>-<stream>-tls:
    image: docker.elastic.co/observability/stream:v0.18.0
    volumes:
      - ./sample_logs:/sample_logs:ro
    command: log --start-signal=SIGHUP --delay=5s --addr elastic-agent:<port> -p=tls --insecure /sample_logs/<logfile>.log
```

## Test config pattern

### TCP

```yaml
wait_for_data_timeout: 1m
service: <package>-<stream>-tcp
service_notify_signal: SIGHUP
input: tcp
data_stream:
  vars:
    listen_address: 0.0.0.0
    listen_port: <port>
    preserve_original_event: true
assert:
  hit_count: <line_count>
```

### UDP

```yaml
wait_for_data_timeout: 1m
service: <package>-<stream>-udp
service_notify_signal: SIGHUP
input: udp
data_stream:
  vars:
    listen_address: 0.0.0.0
    listen_port: <port>
assert:
  hit_count: <line_count>
```

## Key patterns

- **`service_notify_signal: SIGHUP`**: required so the `stream` tool waits for the agent to be ready before sending. The `--start-signal=SIGHUP` flag on the `stream` command listens for this signal.
- **`--delay=5s`**: adds a small delay after receiving the signal before sending, giving the agent time to fully initialize.
- **Port alignment**: the port in `--addr elastic-agent:<port>` must match `listen_port` in the test config. Use unique ports per service to avoid collisions.
- **Sample log file**: place log files in `_dev/deploy/docker/sample_logs/`. Each line in the file becomes one event.
- **`assert.hit_count`**: should match the number of non-empty lines in the sample log file.
- **Multiple test configs**: create separate `test-tcp-config.yml` and `test-udp-config.yml` files to test both protocols against the same data stream.

## Skipping tests

If sample logs are not yet available, a test config can be marked as skipped:

```yaml
service: <package>-<stream>-tcp
skip:
  reason: "No sample logs available"
  link: https://github.com/elastic/integrations/issues/<number>
service_notify_signal: SIGHUP
input: tcp
data_stream:
  vars:
    listen_address: 0.0.0.0
    listen_port: <port>
```

## Reference integrations

- [`vectra_detect`](https://github.com/elastic/integrations/tree/main/packages/vectra_detect) — TCP, UDP, and TLS test configs
- [`watchguard_firebox`](https://github.com/elastic/integrations/tree/main/packages/watchguard_firebox) — UDP with `assert.hit_count`
- [`zscaler_zia`](https://github.com/elastic/integrations/tree/main/packages/zscaler_zia) — TCP across multiple data streams
