# Azure Event Hub input guide

Complete reference for building and reviewing `azure-eventhub.yml.hbs` templates in Elastic integrations. This input consumes messages from Azure Event Hubs, commonly used for Azure Monitor diagnostic logs, activity logs, and custom application telemetry.

> **Documentation**: [Azure Event Hub Input Reference](https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-input-azure-eventhub.html)

## File location

```
packages/<package>/data_stream/<data_stream>/agent/stream/azure-eventhub.yml.hbs
```

## Required structure

```yaml
eventhub: {{eventhub}}
connection_string: {{connection_string}}

{{#if consumer_group}}
consumer_group: {{consumer_group}}
{{/if}}

{{#if storage_account}}
storage_account: {{storage_account}}
{{/if}}
{{#if storage_account_key}}
storage_account_key: {{storage_account_key}}
{{/if}}
{{#if storage_account_container}}
storage_account_container: {{storage_account_container}}
{{/if}}

{{#if processor_workers}}
processor_workers: {{processor_workers}}
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

### 1. Event Hub name required

The Event Hub name must reference a Handlebars variable.

```yaml
# correct
eventhub: {{eventhub}}

# wrong -- hardcoded
eventhub: my-eventhub

# wrong -- missing
# no eventhub specified
```

### 2. Connection string required and must not be hardcoded

The connection string contains the Event Hub namespace endpoint and shared access key. Hardcoding it is a critical security issue.

```yaml
# correct
connection_string: {{connection_string}}

# critical security issue -- hardcoded connection string
connection_string: 'Endpoint=sb://namespace.servicebus.windows.net/;SharedAccessKeyName=...;SharedAccessKey=...'
```

The manifest must declare this field with `type: password`.

### 3. Storage account for checkpointing

Without checkpoint storage, the input loses its position on restart and may reprocess events. The storage account configuration should always be present.

Two approaches are supported:

Individual fields:

```yaml
{{#if storage_account}}
storage_account: {{storage_account}}
{{/if}}
{{#if storage_account_key}}
storage_account_key: {{storage_account_key}}
{{/if}}
{{#if storage_account_container}}
storage_account_container: {{storage_account_container}}
{{/if}}
```

Connection string:

```yaml
{{#if storage_account_connection_string}}
storage_account_connection_string: {{storage_account_connection_string}}
{{/if}}
```

Either approach is acceptable. Both the storage account key and connection string are secrets and must use variables.

### 4. Consumer group must be configurable

```yaml
{{#if consumer_group}}
consumer_group: {{consumer_group}}
{{/if}}
```

The default consumer group is `$Default`. Custom consumer groups prevent conflicts when multiple consumers read from the same Event Hub. The manifest should document the default and recommend creating a dedicated consumer group for the Elastic integration.

### 5. No hardcoded secrets

All fields that contain secrets must use Handlebars variables:
- `connection_string`
- `storage_account_key`
- `storage_account_connection_string`

The manifest must declare these with `type: password` and `show_user: true`.

## Authentication

### Connection string authentication

The primary authentication method uses a connection string from the Event Hub's Shared Access Policy.

```yaml
connection_string: {{connection_string}}
```

The connection string format is:
```
Endpoint=sb://<namespace>.servicebus.windows.net/;SharedAccessKeyName=<policy>;SharedAccessKey=<key>
```

The SAS policy must have at minimum the **Listen** permission.

### SAS token considerations

When using SAS tokens instead of connection strings:
- The token has an expiry time that must be monitored for long-running collectors
- Expired tokens cause silent collection failures
- The integration documentation should note the need to refresh tokens before expiry

### Storage account authentication

Checkpoint storage requires its own credentials, separate from the Event Hub connection string.

```yaml
# option 1: account name + key
{{#if storage_account}}
storage_account: {{storage_account}}
{{/if}}
{{#if storage_account_key}}
storage_account_key: {{storage_account_key}}
{{/if}}
{{#if storage_account_container}}
storage_account_container: {{storage_account_container}}
{{/if}}

# option 2: connection string
{{#if storage_account_connection_string}}
storage_account_connection_string: {{storage_account_connection_string}}
{{/if}}
```

## Partition handling

Azure Event Hubs distribute messages across partitions. The input automatically claims partitions using the checkpoint store. Key considerations:

- Multiple agent instances reading the same Event Hub should use the same consumer group and storage account so partitions are balanced across instances
- `processor_workers` controls how many partitions are processed in parallel within a single agent instance
- The number of workers should not exceed the number of partitions

```yaml
{{#if processor_workers}}
processor_workers: {{processor_workers}}
{{/if}}
```

## Common configuration patterns

### Basic Event Hub collection

```yaml
eventhub: {{eventhub}}
connection_string: {{connection_string}}

{{#if consumer_group}}
consumer_group: {{consumer_group}}
{{/if}}

{{#if storage_account}}
storage_account: {{storage_account}}
{{/if}}
{{#if storage_account_key}}
storage_account_key: {{storage_account_key}}
{{/if}}
{{#if storage_account_container}}
storage_account_container: {{storage_account_container}}
{{/if}}
```

### With storage connection string

```yaml
eventhub: {{eventhub}}
connection_string: {{connection_string}}

{{#if consumer_group}}
consumer_group: {{consumer_group}}
{{/if}}

{{#if storage_account_connection_string}}
storage_account_connection_string: {{storage_account_connection_string}}
{{/if}}
```

### Azure Monitor diagnostic logs

Azure Monitor sends diagnostic logs to Event Hub as JSON. These typically need `decode_json_fields` processing.

```yaml
eventhub: {{eventhub}}
connection_string: {{connection_string}}

{{#if consumer_group}}
consumer_group: {{consumer_group}}
{{/if}}

{{#if storage_account}}
storage_account: {{storage_account}}
{{/if}}
{{#if storage_account_key}}
storage_account_key: {{storage_account_key}}
{{/if}}
{{#if storage_account_container}}
storage_account_container: {{storage_account_container}}
{{/if}}

processors:
- decode_json_fields:
    fields: [message]
    target: ""
{{#if processors}}
{{processors}}
{{/if}}
```

## Advanced configuration

### Batch size

```yaml
{{#if batch_size}}
batch_size: {{batch_size}}
{{/if}}
```

Controls how many events are fetched per receive call. Larger batches improve throughput at the cost of latency.

### Consumer group conflicts

If multiple consumers use the same consumer group without shared checkpoint storage, they will compete for partition ownership and cause unstable behavior. Each distinct consumer application should have its own consumer group.

### Error handling considerations

Templates should account for:
- Connection string format validation (malformed strings cause startup failures)
- Checkpoint storage access errors (permissions, network connectivity)
- Consumer group conflicts (multiple consumers on the same group without shared storage)
- SAS token expiry for long-running collectors

## Parameters reference

| Parameter | Type | Description |
|---|---|---|
| `eventhub` | string | Event Hub name |
| `connection_string` | string | Event Hub connection string (secret) |
| `consumer_group` | string | Consumer group name (default: `$Default`) |
| `storage_account` | string | Azure Storage account name for checkpoints |
| `storage_account_key` | string | Storage account access key (secret) |
| `storage_account_container` | string | Blob container name for checkpoints |
| `storage_account_connection_string` | string | Storage account connection string (secret) |
| `processor_workers` | int | Number of parallel partition processors |
| `batch_size` | int | Events per receive call |

## Review checklist

### Event Hub configuration
- [ ] `eventhub` uses a variable
- [ ] `connection_string` uses a variable
- [ ] No hardcoded secrets anywhere in the template

### Consumer group
- [ ] Consumer group is configurable via variable
- [ ] Default value documented in the manifest

### Checkpointing
- [ ] Storage account configuration present (account+key or connection string)
- [ ] Storage account key uses a variable
- [ ] Storage container is configurable
- [ ] All storage secrets use `type: password` in the manifest

### Security
- [ ] `connection_string` declared with `type: password` in manifest
- [ ] `storage_account_key` declared with `type: password` in manifest
- [ ] No hardcoded connection strings or access keys
- [ ] SAS token expiry considerations documented if applicable

### Partition and performance
- [ ] `consumer_group` not left as `$Default` without documentation
- [ ] `processor_workers` configurable and does not exceed partition count
- [ ] Batch size appropriate for message volume

### Tags and processors
- [ ] Tags block follows common patterns
- [ ] Processors passthrough at top level
- [ ] `decode_json_fields` present for Azure Monitor diagnostic logs
