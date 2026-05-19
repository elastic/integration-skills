---
name: integration-testing
description: "Use when creating, running, or debugging elastic-package tests — pipeline fixture authoring and expected output, system tests with mock API wiring, and script tests for failure paths and upgrades. Load the reference file for the test type you are working on."
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# integration-testing

## When to use

Load this skill whenever tasks include:
- authoring or debugging pipeline test fixtures (`.log`/`.json` inputs, `*-expected.json` output, config files)
- setting up or debugging system tests (`_dev/test/system/`, `_dev/deploy/`, mock APIs, 0-hits failures)
- writing script tests for failure paths, API error handling, or package upgrades

## When not to use

Do not use this skill as the primary guide for:
- ingest pipeline processor design and architecture (`ingest-pipelines`)
- CEL program development (`cel-programs`)
- broad elastic-package command selection and stack lifecycle (`elastic-package-cli`)

## Reference files — load the one that matches your test type

| Test type | Load when | Reference file |
|-----------|-----------|----------------|
| Pipeline tests | Writing fixtures, config files, expected output, debugging pipeline test failures | `references/pipeline-testing.md` |
| System tests (generic) | Always load for any system test work — config fields, commands, teardown, debugging | `references/system-testing.md` |
| Script tests | txtar failure/error tests, upgrade tests, mock services embedded in txtar | `references/script-testing.md` |

### System test input-specific references

In addition to the generic `system-testing.md`, load the reference file matching your data stream's input type:

| Input type | Reference file |
|------------|----------------|
| `cel` | `references/system-testing-cel.md` |
| `tcp`, `udp` | `references/system-testing-tcp-udp.md` |
| `http_endpoint` | `references/system-testing-http-endpoint.md` |
| `logfile`, `filestream` | `references/system-testing-logfile.md` |
| `kafka`, `gcp-pubsub` | `references/system-testing-kafka-pubsub.md` |
| `aws-s3`, `gcs`, `azure-blob-storage`, `azure-eventhub` | `references/system-testing-cloud-skip.md` |

When an integration supports multiple input types, load the generic reference plus each applicable input-type reference.

When working across multiple test types in one task (e.g. creating a new data stream end-to-end), load all applicable reference files.

## References

- `references/pipeline-testing.md` — directory layout, naming conventions, fixture formats, config options, expected output format and review, core workflow, fixture scenario coverage, data anonymization, troubleshooting
- `references/system-testing.md` — generic system test reference: required layout, config fields, core commands, teardown failures, `sample_event.json` verification, general debugging
- `references/system-testing-cel.md` — CEL mock API wiring, 0-hits debugging for CEL, variable-capture patterns
- `references/system-testing-tcp-udp.md` — TCP/UDP log sender pattern with `elastic/stream`, signal coordination, port alignment
- `references/system-testing-http-endpoint.md` — webhook/HTTP endpoint testing with `STREAM_PROTOCOL=webhook`, auth headers
- `references/system-testing-logfile.md` — Alpine container + `SERVICE_LOGS_DIR` pattern for logfile/filestream inputs
- `references/system-testing-kafka-pubsub.md` — Kafka broker + stream producer, Pub/Sub emulator patterns
- `references/system-testing-cloud-skip.md` — when and why to skip system tests for cloud storage inputs (aws-s3, gcs, azure-blob-storage, azure-eventhub)
- `references/script-testing.md` — txtar format, env smoke test, system-level skeleton, mock service docker-compose and config.yml, upgrade test pattern, pitfalls, full o365 examples
- `references/builder-setup-subagent-guidance.md` — **always-embedded** subagent operating manual for wiring data collection (docker-compose, sample logs, agent stream template, system test config, manifest var cleanup) for non-CEL data streams
- `references/builder-system-test-subagent-guidance.md` — **always-embedded** subagent operating manual for running `elastic-package test system --generate` after pipeline work completes (any testable input)
