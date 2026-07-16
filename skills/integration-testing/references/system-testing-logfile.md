# system testing — logfile/filestream input

Input-specific guidance for system-testing data streams that use `logfile` or `filestream` inputs. Load `system-testing.md` (generic) first.

## Overview

Log file system tests use a lightweight Alpine container that copies sample log files into a shared volume (`SERVICE_LOGS_DIR`). The Elastic Agent then reads the files using the `logfile` or `filestream` input with glob paths.

## Docker Compose pattern

```yaml
version: '2.3'
services:
  <package>-<stream>-logfile:
    image: alpine
    volumes:
      - ./sample_logs:/sample_logs:ro
      - ${SERVICE_LOGS_DIR}:/var/log
    command: /bin/sh -c "cp /sample_logs/* /var/log/"
```

The Alpine container runs `cp` to copy all sample log files into the `SERVICE_LOGS_DIR` volume, then exits. The Elastic Agent detects the new files and processes them.

For integrations that also support network inputs (TCP/UDP), combine both service types in the same docker-compose:

```yaml
version: '2.3'
services:
  <package>-<stream>-logfile:
    image: alpine
    volumes:
      - ./sample_logs:/sample_logs:ro
      - ${SERVICE_LOGS_DIR}:/var/log
    command: /bin/sh -c "cp /sample_logs/* /var/log/"

  <package>-<stream>-tcp:
    image: docker.elastic.co/observability/stream:v0.22.0
    volumes:
      - ./sample_logs:/sample_logs:ro
    command: log --start-signal=SIGHUP --delay=5s --addr elastic-agent:<port> -p=tcp /sample_logs/<logfile>.log
```

## Test config pattern

```yaml
wait_for_data_timeout: 1m
service: <package>-<stream>-logfile
input: logfile
vars:
  paths:
    - "{{SERVICE_LOGS_DIR}}/*.log"
```

With additional options:

```yaml
wait_for_data_timeout: 1m
service: <package>-<stream>-logfile
input: logfile
data_stream:
  vars:
    preserve_original_event: true
vars:
  paths:
    - "{{SERVICE_LOGS_DIR}}/*<stream>*.log"
  tz_offset: "+0500"
```

## Key patterns

- **`${SERVICE_LOGS_DIR}`**: environment variable populated by the test runner, points to a shared volume between the Alpine container and the Elastic Agent
- **`{{SERVICE_LOGS_DIR}}`**: the Handlebars placeholder used in the test config (resolves to the same path at runtime)
- **Alpine `cp` command**: the simplest approach — just copies files. The container exits after the copy, which is fine since the agent reads the files afterward.
- **Glob paths**: use `{{SERVICE_LOGS_DIR}}/*.log` for all log files, or `{{SERVICE_LOGS_DIR}}/*<name>*.log` to select specific files
- **Sample log placement**: place log files in `_dev/deploy/docker/sample_logs/`
- **No `service_notify_signal`**: unlike TCP/UDP, logfile tests do not need signal coordination — the agent detects files via filesystem polling
- **`tz_offset`**: if the data stream manifest includes `tz_offset` for timezone handling, include it in test vars

## Reference integrations

- [`checkpoint`](https://github.com/elastic/integrations/tree/main/packages/checkpoint) — Alpine container pattern with TCP/UDP/TLS alongside
- [`panw`](https://github.com/elastic/integrations/tree/main/packages/panw) — logfile with specific glob patterns
- [`f5_bigip`](https://github.com/elastic/integrations/tree/main/packages/f5_bigip) — combines logfile (Alpine) and http_endpoint in one compose
