# Data Collection Methods

This reference describes the input types available in Elastic Agent integrations, what each is used for, and what research information is needed for each.

Use this to determine which collection method fits the product being researched and what details to investigate.

## Input type decision tree

```
Does the vendor expose a REST/HTTP API for retrieving events?
  YES → CEL input (or httpjson for simple cases)
  NO ↓

Does the product write local log files?
  YES → log file input (filestream)
  NO ↓

Does the product send syslog messages?
  YES → syslog input (tcp/udp)
  NO ↓

Does the vendor deliver data to a cloud message queue or object store?
  S3 bucket → S3/SQS input (aws-s3)
  Azure Event Hub → Azure Event Hub input (azure-eventhub)
  Google Pub/Sub → GCP Pub/Sub input (gcp-pubsub)
  Azure Blob Storage → Azure Blob Storage input (azure-blob-storage)
  GCS bucket → GCS input (gcs)
  Kafka topic → Kafka input
  NO ↓

Does the product expose a streaming/websocket endpoint?
  YES → evaluate CEL with streaming or custom input
  NO ↓

Can data be exported as flat files (CSV, JSON) and dropped to a path?
  YES → log file input (filestream)
  NO → product may not be suitable for direct Elastic ingestion
```

## Input types reference

### CEL (Common Expression Language) -- REST API collection

**When to use:** The product exposes a REST API for retrieving events, logs, or metrics.

**Elastic input type:** `cel`

**What to research:**
- Base URL and API version
- Authentication method and credential types
- All relevant endpoints (list with paths)
- Request parameters: required, optional, filtering, time range
- Response format: JSON structure, envelope vs. array, nested objects
- Pagination: mechanism (offset, cursor, link-header, keyset, page number), field names, termination condition
- Rate limiting: limits, headers, retry-after behavior
- Timestamp handling: format, timezone, field names for time-range queries
- Error response format and status codes
- Webhook alternative (some products offer both pull and push)
- API permissions/scopes required

**Standard configuration variables (API key / Bearer token auth):**
| Variable | Type | Required | Show user | Notes |
|----------|------|----------|-----------|-------|
| `url` | url | yes | yes | API base URL |
| `api_key` or `token` | password | yes | yes | auth credential |
| `interval` | text | yes | yes | polling interval, e.g. `5m` |
| `initial_interval` | text | no | yes | first poll lookback, e.g. `24h` |
| `batch_size` or `page_size` | integer | no | no | pagination page size |
| `http_client_timeout` | text | no | no | request timeout |
| `proxy_url` | url | no | no | HTTP proxy |
| `ssl` | yaml | no | no | TLS configuration |
| `tags` | text | no | yes | user-defined tags |
| `processors` | yaml | no | no | custom processors |

**Additional variables for OAuth2 auth (authorization_code or client_credentials):**
| Variable | Type | Required | Show user | Notes |
|----------|------|----------|-----------|-------|
| `client_id` | text | yes | yes | OAuth2 application client ID |
| `client_secret` | password | yes | yes | OAuth2 application client secret |
| `token_url` | url | yes | yes | OAuth2 token endpoint URL |
| `authorization_url` | url | conditional | yes | OAuth2 authorization endpoint (authorization_code flow only) |
| `scopes` | text | no | yes | OAuth2 scopes (space-separated) |

The CEL input's `auth.oauth2` configuration block natively supports `authorization_code` (including PKCE), `client_credentials`, and automatic token refresh. When the API uses OAuth2, prefer the built-in auth block over manual token management. Research must capture the exact authorization URL, token URL, refresh URL, and required scopes to enable this.

### Filestream -- local log files

**When to use:** The product writes log files to disk on the host where Elastic Agent runs.

**Elastic input type:** `filestream` (preferred) or `log` (legacy)

**What to research:**
- Default log file paths per OS (Linux, Windows, macOS)
- Log format: syslog, JSON/NDJSON, CSV, key-value, multiline, custom delimited
- Log rotation behavior (size, time, naming pattern)
- Character encoding
- Multiline patterns (if applicable): start/end patterns, what constitutes a single event
- All distinct log types/files and what events each contains
- Timestamp format within log lines
- Sample log lines for each event type

**Standard configuration variables:**
| Variable | Type | Required | Show user | Notes |
|----------|------|----------|-----------|-------|
| `paths` | text (list) | yes | yes | log file glob paths |
| `exclude_files` | text (list) | no | no | patterns to exclude |
| `tags` | text | no | yes | user-defined tags |
| `processors` | yaml | no | no | custom processors |
| `preserve_original_event` | bool | no | yes | keep raw event |

### TCP/UDP -- syslog collection

**When to use:** The product sends syslog messages over the network to a collector.

**Elastic input type:** `tcp` and/or `udp`

**What to research:**
- Syslog RFC version: 3164 (BSD) or 5424 (IETF)
- Message format inside syslog envelope: CEF, LEEF, key-value, free text, JSON
- Syslog facility and severity usage
- Default source port(s)
- Whether the product supports TLS for syslog
- Timezone handling: are timestamps in UTC or local? Does the message include timezone?
- Message structure and delimiter patterns
- All distinct event types by facility, severity, or message ID
- Sample syslog lines for each event type

**Standard configuration variables:**
| Variable | Type | Required | Show user | Notes |
|----------|------|----------|-----------|-------|
| `listen_address` | text | yes | yes | e.g. `localhost` |
| `listen_port` | integer | yes | yes | e.g. `9001` |
| `tz_offset` | text | yes | yes | default: `Local`, for messages without timezone |
| `ssl` | yaml | conditional | no | TLS config (TCP only) |
| `tags` | text | no | yes | user-defined tags |
| `processors` | yaml | no | no | custom processors |
| `preserve_original_event` | bool | no | yes | keep raw event |

### AWS S3 / SQS -- cloud object store

**When to use:** The vendor or cloud service delivers data as objects in an S3 bucket, optionally with SQS notifications.

**Elastic input type:** `aws-s3`

**What to research:**
- Object format: JSON, NDJSON, CSV, gzip-compressed, Parquet
- Object path/prefix pattern and partitioning scheme
- Whether objects contain single events or batches
- Object naming convention and timestamp encoding in path
- SQS notification configuration (if used)
- IAM permissions required
- Cross-account access patterns
- Data retention and lifecycle policies
- Sample object content

**Standard configuration variables:**
| Variable | Type | Required | Show user | Notes |
|----------|------|----------|-----------|-------|
| `queue_url` | url | conditional | yes | SQS queue URL (if SQS mode) |
| `bucket_arn` | text | conditional | yes | S3 bucket ARN (if polling mode) |
| `access_key_id` | password | conditional | yes | AWS credential |
| `secret_access_key` | password | conditional | yes | AWS credential |
| `session_token` | password | no | yes | for temporary credentials |
| `role_arn` | text | no | yes | for cross-account assume role |
| `bucket_list_prefix` | text | no | yes | filter objects by prefix |
| `number_of_workers` | integer | no | no | concurrent processing |
| `file_selectors` | yaml | no | no | content-type routing |
| `tags` | text | no | yes | user-defined tags |
| `processors` | yaml | no | no | custom processors |

### Azure Event Hub

**When to use:** The vendor or Azure service streams data through Azure Event Hubs.

**Elastic input type:** `azure-eventhub`

**What to research:**
- Event Hub namespace and hub name configuration
- Consumer group setup
- Message format: JSON envelope, nested records, batch arrays
- Authentication: connection string, managed identity, SAS token
- Partitioning scheme
- Schema of individual events within the Event Hub message
- Storage account for checkpointing
- Sample event content

**Standard configuration variables:**
| Variable | Type | Required | Show user | Notes |
|----------|------|----------|-----------|-------|
| `eventhub` | text | yes | yes | Event Hub name |
| `connection_string` | password | yes | yes | namespace connection string |
| `consumer_group` | text | yes | yes | default: `$Default` |
| `storage_account` | text | yes | yes | for checkpointing |
| `storage_account_key` | password | yes | yes | storage credential |
| `storage_account_container` | text | no | yes | checkpoint container |
| `tags` | text | no | yes | user-defined tags |
| `processors` | yaml | no | no | custom processors |

### GCP Pub/Sub

**When to use:** The vendor or GCP service streams data through Google Cloud Pub/Sub.

**Elastic input type:** `gcp-pubsub`

**What to research:**
- Pub/Sub topic and subscription configuration
- Message format and attributes
- Authentication: service account JSON key, workload identity
- Ordering requirements
- Dead letter topic setup
- Schema of individual messages
- Sample message content

**Standard configuration variables:**
| Variable | Type | Required | Show user | Notes |
|----------|------|----------|-----------|-------|
| `project_id` | text | yes | yes | GCP project |
| `topic` | text | yes | yes | Pub/Sub topic |
| `subscription_name` | text | yes | yes | subscription |
| `credentials_file` | text | conditional | yes | service account key path |
| `credentials_json` | password | conditional | yes | inline service account key |
| `tags` | text | no | yes | user-defined tags |
| `processors` | yaml | no | no | custom processors |

### HTTP Endpoint -- webhook receiver

**When to use:** The vendor pushes data to a webhook URL that the Elastic Agent listens on.

**Elastic input type:** `http_endpoint`

**What to research:**
- Webhook payload format (JSON body, form data)
- Authentication of incoming requests (HMAC signature, shared secret, mTLS)
- Event delivery guarantees (at-least-once, retry behavior)
- Webhook registration/configuration on the vendor side
- Payload structure for each event type
- Rate and size limits on the vendor side
- Sample webhook payloads

**Standard configuration variables:**
| Variable | Type | Required | Show user | Notes |
|----------|------|----------|-----------|-------|
| `listen_address` | text | yes | yes | bind address |
| `listen_port` | integer | yes | yes | port to listen on |
| `url` | text | yes | yes | URL path to listen on |
| `secret_header` | text | no | yes | header name for HMAC |
| `secret_value` | password | no | yes | HMAC shared secret |
| `ssl` | yaml | no | no | TLS configuration |
| `tags` | text | no | yes | user-defined tags |
| `processors` | yaml | no | no | custom processors |

### Azure Blob Storage

**When to use:** Data is delivered as blobs in Azure Storage containers.

**Elastic input type:** `azure-blob-storage`

**What to research:**
- Container name and blob path/prefix patterns
- Blob format: JSON, NDJSON, CSV, gzip
- Authentication: connection string, SAS token, managed identity
- Blob naming convention and partitioning
- Poll interval and change detection
- Sample blob content

### GCS (Google Cloud Storage)

**When to use:** Data is delivered as objects in GCS buckets.

**Elastic input type:** `gcs`

**What to research:**
- Bucket name and object prefix patterns
- Object format and compression
- Authentication: service account
- Object naming and partitioning
- Sample object content

### Kafka

**When to use:** Data is available on Kafka topics.

**Elastic input type:** `kafka`

**What to research:**
- Topic name(s) and partitioning
- Message format (JSON, Avro, Protobuf)
- Authentication: SASL, mTLS, no auth
- Consumer group configuration
- Schema registry (if Avro/Protobuf)
- Sample messages

## Multiple collection methods

Many products support more than one collection method. When this is the case:

1. Document all available methods.
2. Recommend the best method based on:
   - **Completeness**: which method provides the most event types and field detail
   - **Timeliness**: which has the lowest latency from event occurrence to collection
   - **Reliability**: which has the best delivery guarantees
   - **Simplicity**: which requires the least user configuration
   - **Standard practice**: which method is most commonly used by the Elastic community (check existing `integrations/packages/` for precedent)
3. If two methods are close in quality, consider supporting both as separate data streams within the same integration.
