---
name: input-configurations
description: >-
  Input template configuration for Elastic integrations. Covers agent stream
  templates (agent/stream/*.yml.hbs) for all non-CEL input types: HTTPJSON,
  AWS S3, CloudWatch, Azure Blob, Azure EventHub, GCS, GCP Pub/Sub, TCP, UDP,
  HTTP Endpoint, Filestream, Logfile, Journald, Winlog, and WebSocket. Also
  covers Federated Identity (Cloud Connectors) for agentless AWS integrations,
  including the auth.aws / use_cloud_connectors block on CEL stream templates.
  For CEL program logic, use the cel-programs skill.
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# input-configurations

## When to use

Load this skill whenever tasks include:
- building, modifying, or reviewing `agent/stream/*.yml.hbs` templates for non-CEL input types
- configuring request, response, pagination, cursor, or authentication blocks in HTTPJSON templates
- wiring up cloud storage inputs (AWS S3, GCS, Azure Blob, Azure EventHub)
- setting up network inputs (TCP, UDP, HTTP Endpoint, WebSocket)
- configuring file-based inputs (Filestream, Logfile, Journald, Winlog)
- enabling Federated Identity (Cloud Connectors) on an AWS integration package

## When not to use

Do not use this skill as the primary guide for:
- CEL *program* development (`cel-programs`) -- CEL program structure, state model, and mito workflow. Exception: the `auth.aws` / `use_cloud_connectors` template block for Federated Identity is owned here via `references/federated-identity-aws.md`
- ingest pipeline processor design (`ingest-pipelines`)
- field mappings and ECS compliance (`ecs-field-mappings`)
- `var_groups` / `provider_permissions` *schema* and `format_version` floors alone (`package-spec`) -- use this skill for the end-to-end federation procedure that applies them

## Mandatory first read

**Always load `references/common-input-patterns.md` first.** It covers patterns that apply to every input type (tags, processors passthrough, variable conventions, `forwarded`/`publisher_pipeline.disable_host` coupling). These patterns are prerequisites for all type-specific guides.

## Type routing table

Detect the input type from the filename pattern in `agent/stream/` or from the data stream manifest `input:` field, then load the matching guide.

| Input type | Filename pattern | Guide |
|---|---|---|
| HTTPJSON | `httpjson.yml.hbs` | `references/httpjson-guide.md` |
| AWS S3 | `aws-s3.yml.hbs` | `references/aws-s3-guide.md` |
| CloudWatch | `aws-cloudwatch.yml.hbs` | `references/aws-cloudwatch-guide.md` |
| Azure Blob Storage | `azure-blob-storage.yml.hbs` | `references/azure-blob-storage-guide.md` |
| Azure Event Hub | `azure-eventhub.yml.hbs` | `references/azure-eventhub-guide.md` |
| GCS | `gcs.yml.hbs` | `references/gcs-guide.md` |
| GCP Pub/Sub | `gcp-pubsub.yml.hbs` | `references/gcp-pubsub-guide.md` |
| TCP | `tcp.yml.hbs` | `references/tcp-udp-guide.md` |
| UDP | `udp.yml.hbs` | `references/tcp-udp-guide.md` |
| HTTP Endpoint | `http_endpoint.yml.hbs` | `references/http-endpoint-guide.md` |
| Filestream | `filestream.yml.hbs` | `references/filestream-logfile-guide.md` |
| Logfile | `log.yml.hbs` | `references/filestream-logfile-guide.md` |
| Journald | `journald.yml.hbs` | `references/journald-guide.md` |
| Winlog | `winlog.yml.hbs` | `references/winlog-guide.md` |
| WebSocket | `websocket.yml.hbs` | `references/websocket-guide.md` |

Load **only** the guide for the detected input type, not all guides.

For **Federated Identity** tasks (any eligible input type, including `cel`), load
`references/federated-identity-aws.md` regardless of which input type is
involved.

## Handoff

- For **CEL program logic**, hand off to the `cel-programs` skill. Keep this skill loaded for Federated Identity `auth.aws` / `use_cloud_connectors` edits on `cel.yml.hbs`.
- For **manifest schema** (`var_groups`, `provider_permissions`, `format_version` / conditions floors), hand off to the `package-spec` skill (`references/var-groups-and-provider-permissions.md`).
- For **pipeline issues** discovered while reviewing input templates, hand off to the `ingest-pipelines` skill.
- For **field mapping issues** found in template variable wiring, hand off to the `ecs-field-mappings` skill.

## References

- `references/common-input-patterns.md` -- tags, processors passthrough, variable conventions, review flags (applies to ALL input types)
- `references/httpjson-guide.md` -- HTTPJSON template syntax, structure, validation rules, pagination patterns, authentication, cursor persistence
- `references/aws-s3-guide.md` -- S3 bucket/SQS notification collection
- `references/aws-cloudwatch-guide.md` -- CloudWatch log group collection
- `references/azure-blob-storage-guide.md` -- Azure Blob Storage collection
- `references/azure-eventhub-guide.md` -- Azure Event Hub collection
- `references/gcs-guide.md` -- Google Cloud Storage collection
- `references/gcp-pubsub-guide.md` -- GCP Pub/Sub collection
- `references/tcp-udp-guide.md` -- TCP and UDP (syslog-style) listeners
- `references/http-endpoint-guide.md` -- HTTP Endpoint (webhook receiver)
- `references/filestream-logfile-guide.md` -- Filestream and legacy Logfile inputs
- `references/journald-guide.md` -- Journald collection
- `references/winlog-guide.md` -- Windows Event Log collection
- `references/websocket-guide.md` -- WebSocket streaming (may embed CEL)
- `references/federated-identity-aws.md` -- end-to-end procedure for enabling Federated Identity (Cloud Connectors) on an AWS integration: pre-flight checks, manifest edits, stream template patch, CFT mirror, and PR checklists
