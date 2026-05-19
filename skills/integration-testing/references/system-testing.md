# system testing

Everything needed to set up, run, and debug `elastic-package test system` for full end-to-end ingest validation.

## Purpose

System tests validate the complete ingest path: service deployment → Elastic Agent policy → ingest pipeline → indexed documents in Elasticsearch. They also generate `sample_event.json`.

## Required layout

Service deployment config (package-level or stream-level):
- `_dev/deploy/docker/` — Docker Compose service definition

System test configs (per data stream):
- `data_stream/<stream>/_dev/test/system/test-<scenario>-config.yml`

For multi-version or environment variants:
- `_dev/deploy/variants.yml`

## System test config fields

| Field | Description |
|-------|-------------|
| `wait_for_data_timeout` | Max time the test runner waits for expected documents in Elasticsearch. **Always set to `1m`** in every system test config. |
| `input` | Select integration input when multiple exist (e.g. `tcp`, `http_endpoint`, `cel`) |
| `service` | Maps test case to deploy service name |
| `service_notify_signal` | Signal used when service config reload is needed |
| `vars` | Package-level vars for integration policy |
| `data_stream.vars` | Stream-level vars (e.g. `paths`, `hosts`, `listen_port`) |
| `assert.hit_count` | Expected number of indexed events/documents |

Available placeholders in config files:
- `{{Hostname}}`
- `{{Port}}`
- `{{Ports}}` (or indexed forms like `{{Ports.0}}`)
- `{{SERVICE_LOGS_DIR}}`

## Core commands

```bash
# Start stack once
elastic-package stack up -d

# Run all system tests in current package
elastic-package test system

# Scope to specific streams
elastic-package test system --data-streams <stream1>[,<stream2>]

# Run one test config
elastic-package test system --data-streams <stream> --test-config test-default-config.yml

# Run with a specific deploy variant
elastic-package test system --variant <variant-name>

# Generate sample_event.json
elastic-package test system --generate

# Keep resources around for debugging
elastic-package test system --defer-cleanup 10m
```

## Input-type-specific guidance

System test setup varies significantly by input type. Load the appropriate input-specific reference file alongside this generic reference:

| Input type | Reference file |
|------------|----------------|
| `cel` | `system-testing-cel.md` |
| `tcp`, `udp` | `system-testing-tcp-udp.md` |
| `http_endpoint` | `system-testing-http-endpoint.md` |
| `logfile`, `filestream` | `system-testing-logfile.md` |
| `kafka`, `gcp-pubsub` | `system-testing-kafka-pubsub.md` |
| `aws-s3`, `gcs`, `azure-blob-storage`, `azure-eventhub` | `system-testing-cloud-skip.md` |

When an integration supports multiple input types, load the generic reference plus each applicable input-type reference.

## Teardown failures (Fleet / agent policy conflicts)

If system test **teardown** fails with an error that an **agent policy** (or similar Fleet resource) is still in use and cannot be removed, **do not try to fix Fleet state by hand**.

Reset the whole local stack:

```bash
elastic-package stack down
elastic-package stack up -d -v
```

Then rerun `elastic-package test system` (after `elastic-package build` if the package changed). This clears stale policies and agents tied to the previous run.

## Verifying generated `sample_event.json`

`--generate` produces `data_stream/<stream>/sample_event.json` containing one representative event from the indexed results. This is a snapshot of current behavior, not a correctness guarantee.

After generation, verify:
1. Document shape matches expectations (correct ECS fields, correct nesting, expected values)
2. Geo fields appear under the correct parent entity (`source.geo`, `destination.geo`, etc.) — not at document root
3. Dotted field names from source data appear as properly nested objects
4. If the sample event contains unexpected fields or missing values, fix the pipeline and regenerate — do not edit the file manually

## Debugging system test failures — general

### Check the agent log for dropped events

```
build/container-logs/elastic-agent-<ID>.log
```

If the service container log shows successful responses but you still get 0 hits, check the agent log for:

```
"events were dropped! Look at the event log to view the event and cause"
```

This means events were produced by the input and sent to Elasticsearch via bulk API, but **Elasticsearch rejected every document**.

### Check the elastic-agent event log inside the running container

When events are being dropped, the **only** way to see the actual rejection reason is the event log inside the running elastic-agent container:

```
/usr/share/elastic-agent/state/data/logs/events/elastic-agent-event-log-*.ndjson
```

To inspect it during a running system test:

1. **Increase `wait_for_data_timeout`** in the test config (e.g., to `5m`) so the system test stays running long enough to inspect the container.
2. Start the system test and wait for the first "events were dropped" warnings.
3. Find the elastic-agent container:
   ```bash
   docker ps --format '{{.Names}}' | grep elastic-agent
   ```
4. Read the event log:
   ```bash
   docker exec <container-name> tail -20 /usr/share/elastic-agent/state/data/logs/events/elastic-agent-event-log-*.ndjson
   ```
5. Look for entries with `"Cannot index event"` — these contain the **exact Elasticsearch rejection reason**.

Common rejection reasons:

| Rejection | Root cause | Fix |
|-----------|-----------|-----|
| `mapper_parsing_exception` | Field type conflict (e.g. a field mapped as `keyword` receives an object) | Fix field definitions or pipeline |
| `illegal_argument_exception` | Invalid field value (e.g. malformed IP, date parse failure) | Fix the ingest pipeline |
| `Duplicate field '@timestamp'` | Input sets `@timestamp` in event output; framework also adds `@timestamp` → duplicate key | Remove `@timestamp` from event map — only set `{"message": ...}` |

After diagnosing, reduce `wait_for_data_timeout` back to `1m` for the final test run.

### Elasticsearch debugging (last resort)

Only if the above steps reveal nothing: check whether documents arrived but were routed incorrectly or failed in the pipeline. This is rarely needed — the container log and event log almost always reveal the root cause.

## Common failure patterns

- **"field X is undefined" for ECS fields** (e.g. `field "destination.ip" is undefined`):
  - Missing or outdated `_dev/build/build.yml`
  - Fix: add `dependencies.ecs.reference: "git@v9.3.0"`
- **Service not reachable**: wrong ports or placeholders in test config
- **No events ingested**: wrong paths/hosts/input selection
- **Mapping conflicts**: field type mismatches between pipeline output and field definitions
- **Teardown fails**: agent policy still referenced — run `elastic-package stack down` then `elastic-package stack up -d -v` and rerun (see Teardown failures above)

## Data anonymization

**All test data must be fully anonymized before committing.** No real production data, customer data, or identifiable information may appear in system test sample logs (`_dev/deploy/docker/sample_logs/`), mock API response configs (`_dev/deploy/docker/files/`), test config files, or generated `sample_event.json`.

Replace every identifying value with a synthetic example of the same format — IP addresses, hostnames, email addresses, usernames, organization names, account IDs, tokens, and any other value traceable to a real entity. Use RFC 5737 documentation IP ranges, `example.com` domains, and realistic placeholder names. Refer to the `anonymize-logs` skill for the full anonymization policy and placeholder conventions.
