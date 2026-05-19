# GCP Pub/Sub input guide

Complete reference for building and reviewing `gcp-pubsub.yml.hbs` templates in Elastic integrations. This input pulls messages from a Google Cloud Pub/Sub subscription.

> **Documentation**: [GCP Pub/Sub Input Reference](https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-input-gcp-pubsub.html)

## File location

```
packages/<package>/data_stream/<data_stream>/agent/stream/gcp-pubsub.yml.hbs
```

## Required structure

```yaml
project_id: {{project_id}}

subscription.name: {{subscription_name}}

{{#if topic}}
subscription.create: true
topic: {{topic}}
{{/if}}

{{#if credentials_file}}
credentials_file: {{credentials_file}}
{{/if}}
{{#if credentials_json}}
credentials_json: {{credentials_json}}
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

## Validation rules

### 1. Project ID required

```yaml
# correct
project_id: {{project_id}}

# wrong -- hardcoded
project_id: my-gcp-project-123

# wrong -- missing
# no project_id specified
```

### 2. Subscription required (not topic alone)

The Pub/Sub input is pull-based and requires a subscription. A topic alone is not sufficient -- you cannot pull messages directly from a topic.

```yaml
# correct -- subscription name
subscription.name: {{subscription_name}}

# correct -- auto-create subscription on a topic
subscription.name: {{subscription_name}}
subscription.create: true
topic: {{topic}}

# wrong -- topic without subscription
topic: my-topic
# cannot pull messages without a subscription
```

When `subscription.create` is `true`, the input creates the subscription if it does not exist. The `topic` field is required alongside `subscription.create` so the input knows which topic to subscribe to.

### 3. Authentication must be provided

Integrations should support both `credentials_file` and `credentials_json`. Workload Identity is acceptable when running on GCE/GKE.

```yaml
# correct -- both options available
{{#if credentials_file}}
credentials_file: {{credentials_file}}
{{/if}}
{{#if credentials_json}}
credentials_json: {{credentials_json}}
{{/if}}

# acceptable -- workload identity (no explicit credentials)
# when running on GCE/GKE with attached service account

# wrong -- hardcoded credentials
credentials_json: '{"type": "service_account", "project_id": "..."}'
```

Credential fields must use `type: password` in the manifest.

### 4. No hardcoded values

All user-configurable fields must reference Handlebars variables. This includes project ID, subscription name, topic, and credentials.

## Authentication patterns

### Service account credentials file

The user provides a file path on the agent host pointing to a service account JSON key.

```yaml
{{#if credentials_file}}
credentials_file: {{credentials_file}}
{{/if}}
```

### Service account credentials JSON

The user pastes the service account JSON key content directly into the integration configuration.

```yaml
{{#if credentials_json}}
credentials_json: {{credentials_json}}
{{/if}}
```

### Workload Identity

When the agent runs on GCE or GKE with an attached service account, no explicit credentials are needed. The Pub/Sub client library uses Application Default Credentials (ADC) automatically.

If both `credentials_file` and `credentials_json` are omitted, the client falls back to ADC. This is the expected behavior for Workload Identity deployments. The integration documentation should note this as a supported option.

### Credential refresh

Service account key files contain long-lived credentials. For production deployments, Workload Identity or ADC with automatic token refresh is preferred over static key files. Static short-lived tokens (e.g., manually generated access tokens) will expire and cause silent collection failures.

## Subscription configuration

### Basic subscription

```yaml
project_id: {{project_id}}
subscription.name: {{subscription_name}}
```

The subscription must already exist in the GCP project.

### Auto-create subscription

```yaml
project_id: {{project_id}}
subscription.name: {{subscription_name}}
subscription.create: true
topic: {{topic}}
```

The input creates the subscription on startup if it does not exist. The service account must have `pubsub.subscriptions.create` permission on the project or topic.

## Message handling

### Acknowledgment deadline

The acknowledgment deadline controls how long Pub/Sub waits for an ACK before redelivering the message.

```yaml
{{#if subscription.ack_deadline}}
subscription.ack_deadline: {{subscription.ack_deadline}}
{{/if}}
```

- Too short: causes redelivery of messages that are still being processed, leading to duplicates
- Too long: delays reprocessing when a message genuinely fails

The default is typically 10 seconds. Increase for integrations where processing (including ingest pipeline execution) takes longer.

### Message retention

Retention is configured at the subscription level in GCP, not in the input template. If the integration documentation specifies retention requirements, verify they are addressed in the GCP setup instructions rather than the template.

### Message ordering

If ordering is required, the subscription must be configured with ordering enabled (using ordering keys) in GCP. The input preserves order when the subscription provides ordered messages. Flag if ordering requirements are documented but not addressed in the setup guide.

### Flow control

Flow control limits the number of outstanding (unacknowledged) messages the input holds in memory.

```yaml
{{#if subscription.max_outstanding_messages}}
subscription.max_outstanding_messages: {{subscription.max_outstanding_messages}}
{{/if}}
{{#if subscription.max_outstanding_bytes}}
subscription.max_outstanding_bytes: {{subscription.max_outstanding_bytes}}
{{/if}}
```

- `max_outstanding_messages`: maximum number of unacknowledged messages held in memory
- `max_outstanding_bytes`: maximum total bytes of unacknowledged messages

Values should align with the agent's processing capacity and available memory. Too high can cause backpressure and OOM. Too low throttles throughput unnecessarily.

## Performance

### Number of worker goroutines

```yaml
{{#if subscription.num_goroutines}}
subscription.num_goroutines: {{subscription.num_goroutines}}
{{/if}}
```

Controls pull concurrency. The default (1) is sufficient for low to moderate throughput. Increase for high-throughput subscriptions. Each goroutine maintains its own streaming pull connection.

### Subscription type

This input is pull-based. It opens streaming pull connections to the Pub/Sub service. Push subscriptions (where Pub/Sub sends HTTP requests to an endpoint) require a different architecture and are not supported by this input.

### Concurrent acknowledgment

Ensure `subscription.max_outstanding_messages` is at least equal to `queue.mem.flush.min_events` (if configured) to avoid blocking the input. If the outstanding message limit is lower than the flush threshold, the input stalls waiting for the queue to flush while holding unacknowledged messages.

## Common configuration patterns

### Basic Pub/Sub collection

```yaml
project_id: {{project_id}}
subscription.name: {{subscription_name}}

{{#if credentials_file}}
credentials_file: {{credentials_file}}
{{/if}}
{{#if credentials_json}}
credentials_json: {{credentials_json}}
{{/if}}
```

### Auto-create subscription with flow control

```yaml
project_id: {{project_id}}
subscription.name: {{subscription_name}}
subscription.create: true
topic: {{topic}}

{{#if subscription.num_goroutines}}
subscription.num_goroutines: {{subscription.num_goroutines}}
{{/if}}
{{#if subscription.max_outstanding_messages}}
subscription.max_outstanding_messages: {{subscription.max_outstanding_messages}}
{{/if}}
{{#if subscription.max_outstanding_bytes}}
subscription.max_outstanding_bytes: {{subscription.max_outstanding_bytes}}
{{/if}}

{{#if credentials_file}}
credentials_file: {{credentials_file}}
{{/if}}
{{#if credentials_json}}
credentials_json: {{credentials_json}}
{{/if}}
```

## Error handling

### Retry and NACK behavior

Messages should be NACKed on transient failure so Pub/Sub redelivers them. Messages should only be ACKed after successful processing and publication to Elasticsearch. Review that the integration does not ACK messages before they are safely indexed.

### Dead-letter topics

For subscriptions with a dead-letter topic configured in GCP, messages that exceed the maximum delivery attempts are forwarded to the dead-letter topic instead of being retried indefinitely. This is configured in GCP, not in the template, but the integration documentation should note it if applicable.

### Credential refresh

Verify that the credential method supports automatic refresh:
- `credentials_file` pointing to a service account key: long-lived, no refresh needed
- `credentials_json` with a service account key: long-lived, no refresh needed
- Workload Identity / ADC: automatic token refresh
- Manually generated access tokens: will expire, not recommended for production

## Parameters reference

| Parameter | Type | Description |
|---|---|---|
| `project_id` | string | GCP project ID |
| `subscription.name` | string | Pub/Sub subscription name |
| `subscription.create` | bool | Create subscription if it does not exist |
| `topic` | string | Topic name (required when `subscription.create` is true) |
| `subscription.num_goroutines` | int | Number of worker goroutines for pull concurrency |
| `subscription.max_outstanding_messages` | int | Flow control: max unacknowledged messages |
| `subscription.max_outstanding_bytes` | int | Flow control: max unacknowledged bytes |
| `subscription.ack_deadline` | duration | Acknowledgment deadline before redelivery |
| `credentials_file` | string | Path to service account JSON key file |
| `credentials_json` | string | Service account JSON key content |

## Review checklist

### Configuration
- [ ] `project_id` uses a variable
- [ ] `subscription.name` uses a variable
- [ ] `topic` specified when `subscription.create` is true
- [ ] No topic-only configuration without a subscription

### Authentication
- [ ] No hardcoded credentials in the template
- [ ] Both `credentials_file` and `credentials_json` supported
- [ ] Workload Identity documented as an option for GCE/GKE
- [ ] Credential fields use `type: password` in the manifest
- [ ] Credentials support refresh (not static short-lived tokens)

### Message handling
- [ ] Acknowledgment deadline appropriate for expected processing time
- [ ] Retention requirements addressed (in GCP setup, not template)
- [ ] Flow control configured (`max_outstanding_messages`, `max_outstanding_bytes`)
- [ ] Ordering addressed if required

### Performance
- [ ] Worker count (`num_goroutines`) suitable for expected throughput
- [ ] `max_outstanding_messages` >= `queue.mem.flush.min_events` (if applicable)

### Error handling
- [ ] Messages NACKed on transient failure for redelivery
- [ ] Messages ACKed only after successful processing
- [ ] Dead-letter topic noted if applicable

### Tags and processors
- [ ] Tags block follows common patterns
- [ ] Processors passthrough at top level
