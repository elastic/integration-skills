# Cloud Ingest Research Checklist

Use this checklist when the product delivers data through a cloud message queue or object store: AWS S3/SQS, Azure Event Hub, Azure Blob Storage, GCP Pub/Sub, GCS, Kafka, or similar.

## Discovery phase

- [ ] Find the vendor's documentation for data export/streaming configuration
- [ ] Identify which cloud delivery mechanisms are supported (some products support multiple)
- [ ] Determine whether the vendor pushes data or the user must configure the export
- [ ] Check for infrastructure-as-code templates (CloudFormation, Terraform, ARM) provided by the vendor
- [ ] Look for data schema documentation or schema registries
- [ ] Check if schema definitions live in a **public git repository** (e.g., AWS OCSF schemas, Azure resource provider schemas, GCP AuditLog protos). If so, clone into `temp/` and analyze programmatically with Python to extract event types, field inventories, and enum values

## Delivery mechanism

### AWS S3 / SQS

- [ ] **Delivery model:** vendor pushes to S3 / user configures export to S3 / built-in AWS service logging
- [ ] **S3 bucket requirements:**
  - Same account or cross-account?
  - Bucket policy needed?
  - Encryption requirements (SSE-S3, SSE-KMS)?
- [ ] **Object path pattern:**
  - Prefix structure (e.g., `AWSLogs/<account-id>/CloudTrail/<region>/YYYY/MM/DD/`)
  - File naming convention
  - Partitioning by date, region, account, event type, or other
- [ ] **SQS notifications:**
  - Does the vendor recommend S3 event notifications to SQS?
  - SNS-to-SQS fanout pattern?
  - SQS queue configuration (visibility timeout, message retention, dead letter queue)
- [ ] **IAM permissions required:**
  - S3: `s3:GetObject`, `s3:ListBucket`, other?
  - SQS: `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes`?
  - KMS: `kms:Decrypt` if encrypted?
  - Exact IAM policy document or link to vendor's recommended policy
- [ ] **Cross-account access:** does collection require `sts:AssumeRole`? ARN format?

### Azure Event Hub

- [ ] **Delivery model:** vendor streams to Event Hub / user configures diagnostic settings / built-in Azure integration
- [ ] **Event Hub setup:**
  - Namespace and hub name conventions
  - Partition count and throughput units
  - Consumer group for the Elastic integration
  - Retention period
- [ ] **Authentication:**
  - Connection string (namespace or entity level)
  - Managed identity
  - SAS token (which claims needed?)
- [ ] **Checkpoint storage:**
  - Storage account for consumer checkpointing
  - Container name convention
  - Permissions needed on storage account
- [ ] **Message format:** see "Data format" section below

### Azure Blob Storage

- [ ] **Delivery model:** vendor writes to blob container / user configures export
- [ ] **Container and path pattern:**
  - Container naming
  - Blob path structure and partitioning
  - Path includes timestamps, categories, etc.?
- [ ] **Authentication:** connection string / SAS token / managed identity
- [ ] **Polling vs event-driven:** does the input poll for new blobs or use Event Grid notifications?

### GCP Pub/Sub

- [ ] **Delivery model:** vendor publishes to topic / user configures export / built-in GCP logging
- [ ] **Pub/Sub setup:**
  - Topic name and project
  - Subscription type (pull recommended for Elastic)
  - Acknowledgement deadline
  - Dead letter topic configuration
- [ ] **Authentication:**
  - Service account JSON key
  - Workload identity federation
  - Required IAM roles
- [ ] **Message attributes:** does the vendor include metadata in Pub/Sub message attributes (vs. body)?

### GCS (Google Cloud Storage)

- [ ] **Delivery model:** export to GCS bucket
- [ ] **Bucket and path pattern:**
  - Object path structure
  - Partitioning scheme
- [ ] **Authentication:** service account with `storage.objects.get` and `storage.objects.list`
- [ ] **Notification:** Pub/Sub notifications for new objects?

### Kafka

- [ ] **Topic name(s) and naming convention**
- [ ] **Partitioning strategy**
- [ ] **Message format:** JSON / Avro / Protobuf
- [ ] **Schema registry:** URL and compatibility mode (if Avro/Protobuf)
- [ ] **Authentication:** SASL (PLAIN, SCRAM, GSSAPI) / mTLS / none
- [ ] **Consumer group configuration**
- [ ] **Offset management**

## Data format

Regardless of delivery mechanism, investigate the format of individual data records:

### Object/message envelope

- [ ] **Wrapper structure:** are events wrapped in an envelope?
  - Single object per file/message: `{ "event": {...} }`
  - Array of objects: `{ "Records": [...] }` or `{ "records": [...] }`
  - NDJSON (one JSON object per line, no wrapper)
  - Array at top level: `[{...}, {...}]`
- [ ] **Envelope field name** for the event array (e.g., `Records`, `records`, `data`, `events`, `logs`)
- [ ] **Metadata in envelope:** request ID, account ID, region, delivery timestamp, etc.

### Compression and encoding

- [ ] **Compression:** gzip / none / snappy / lz4
- [ ] **File extension pattern** that indicates format: `.json.gz`, `.csv`, `.log`
- [ ] **Content-Type** in object metadata or message attributes
- [ ] **Encoding:** UTF-8 / other

### Event structure

- [ ] **Schema documentation:** link to official schema reference
- [ ] **Schema versioning:** does the schema change between versions? Is there a version field?
- [ ] **Event type discrimination:** which field indicates the event type/category?
- [ ] **Nested depth:** how deeply nested are the objects?
- [ ] **Array fields:** which fields contain arrays (important for pipeline flattening decisions)?
- [ ] **Dynamic keys:** any fields where the key name varies (maps, labels, custom attributes)?
- [ ] **Large schema handling:** if the schema has hundreds of fields, download the schema definition (JSON Schema, Protobuf, Avro, or vendor schema repo) into `temp/` and use Python to extract the full field inventory. Write results to `references/field-schema-analysis.md`

### Batch considerations

- [ ] **Events per object/message:** single event or batch?
- [ ] **If batched:** typical batch size, maximum batch size
- [ ] **Ordering:** are events within a batch ordered by time?
- [ ] **Deduplication:** unique event ID field for cross-batch deduplication?

## Event types and field schema

Same as the general checklist -- capture for each event type:

- [ ] **Complete event type list** with descriptions
- [ ] **Field inventory** per event type (name, type, description, example, always present?)
- [ ] **Enumeration values** for categorical fields
- [ ] **Timestamp fields** and formats
- [ ] **IP, user, hostname, hash fields** for ECS mapping
- [ ] **Sample events** saved to `references/sample-events/`

## Volume and performance

- [ ] **Expected data volume:** events per second/minute/hour in typical deployment
- [ ] **Object/message size:** typical and maximum sizes
- [ ] **Delivery latency:** how soon after event occurrence does data appear?
- [ ] **Backfill:** can historical data be replayed/reprocessed?
- [ ] **Retention:** how long does data remain in the delivery mechanism?

## Infrastructure setup guide

- [ ] **Step-by-step vendor-side configuration** to enable data export (or link to vendor guide)
- [ ] **Cloud-side infrastructure** needed (S3 bucket, SQS queue, Event Hub namespace, etc.)
- [ ] **Recommended resource sizing** (SQS visibility timeout, Event Hub partition count, etc.)
- [ ] **Network requirements:** VPC endpoints, private endpoints, firewall rules?
- [ ] **Cost considerations:** storage costs, message delivery costs, cross-region data transfer

## Pipeline implications

After gathering the above, note:

- [ ] **Unwrap/flatten needed:** does the pipeline need to split batch arrays into individual events?
- [ ] **Routing logic:** do different event types in the same stream need different parsing branches?
- [ ] **Shared fields vs type-specific:** can a single pipeline handle all event types or are sub-pipelines needed?
- [ ] **Content type handling:** does the input need `file_selectors` or similar to handle mixed content types?
- [ ] **Large event handling:** are there events that exceed typical size limits?
