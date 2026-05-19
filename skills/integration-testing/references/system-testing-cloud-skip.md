# system testing — cloud storage inputs (skip guidance)

Guidance for data streams that use `aws-s3`, `gcs`, `azure-blob-storage`, or `azure-eventhub` inputs. Load `system-testing.md` (generic) first.

## When to skip system tests

Cloud storage and cloud message bus inputs (`aws-s3`, `gcs`, `azure-blob-storage`, `azure-eventhub`) currently **do not have a standard docker-based system test pattern**. These inputs require cloud infrastructure (S3 buckets, SQS queues, GCS buckets, Azure Blob containers, Event Hubs) that cannot be reliably emulated in a local Docker environment.

Some integrations in the official repo use Terraform-based system tests (`_dev/deploy/tf/`) that provision real AWS/GCP/Azure resources in CI, but these are:
- Not part of the standard `elastic-package test system` docker workflow
- Require cloud credentials and infrastructure
- Not suitable for local development or standard CI pipelines

## What to do instead

1. **Focus on pipeline tests**: create thorough pipeline test fixtures (`_dev/test/pipeline/`) covering all event types, edge cases, and error paths. Pipeline tests validate the ingest pipeline independently of the input.

2. **Skip system test setup**: do not create `_dev/deploy/docker/docker-compose.yml` or `_dev/test/system/` test configs for cloud storage inputs unless a docker-based mock is available.

3. **`sample_event.json` generation**: since `elastic-package test system --generate` cannot run without a system test, `sample_event.json` must be created through alternative means:
   - Run the pipeline against a representative fixture using `elastic-package test pipeline`, then construct `sample_event.json` from the expected output
   - Or set up a temporary local stack run with real cloud credentials to generate it

4. **Note in the report**: when the orchestrator skips system tests for cloud inputs, include this in the final report: "System tests skipped for `<input>` data stream — no docker-based mock available for cloud storage inputs. Pipeline tests provide coverage."

## Integrations with Terraform-based tests (for reference)

Some integrations use `_dev/deploy/tf/` with Terraform and real cloud resources:

- `crowdstrike` (FDR) — uses `{{TF_OUTPUT_queue_url}}` with real AWS SQS
- `github` (audit) — combines TF for S3 with Docker for GCS mock and Azurite

These patterns require cloud credentials (`AWS_ACCESS_KEY_ID`, etc.) and are only suitable for CI environments with cloud access.

## Partial docker-based mocks (advanced)

A few integrations use docker-based mocks for cloud storage:

- **GCS**: `shourieg/gcs-mock-service` provides a basic GCS-compatible API
- **Azure Blob**: `mcr.microsoft.com/azure-storage/azurite` emulates Azure Blob Storage locally

These are not widely adopted and require additional setup (uploading test data, configuring endpoints). If the integration warrants it, examine `google_cloud_storage` or `symantec_endpoint_security` in the official repo for working examples.

## Reference integrations

- [`crowdstrike`](https://github.com/elastic/integrations/tree/main/packages/crowdstrike) (FDR) — TF-based aws-s3 tests
- [`google_cloud_storage`](https://github.com/elastic/integrations/tree/main/packages/google_cloud_storage) — docker GCS mock
- [`symantec_endpoint_security`](https://github.com/elastic/integrations/tree/main/packages/symantec_endpoint_security) — aws-s3, GCS, and Azure Blob test configs
