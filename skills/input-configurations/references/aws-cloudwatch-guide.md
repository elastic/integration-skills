# AWS CloudWatch input guide

Complete reference for building and reviewing `aws-cloudwatch.yml.hbs` templates in Elastic integrations. This input polls AWS CloudWatch Logs for log events from one or more log groups.

> **Documentation**: [AWS CloudWatch Input Reference](https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-input-aws-cloudwatch.html)

## File location

```
packages/<package>/data_stream/<data_stream>/agent/stream/aws-cloudwatch.yml.hbs
```

## Required structure

```yaml
{{#if log_group_arn}}
log_group_arn: {{log_group_arn}}
{{/if}}
{{#if log_group_name}}
log_group_name: {{log_group_name}}
{{/if}}
{{#if log_group_name_prefix}}
log_group_name_prefix: {{log_group_name_prefix}}
{{/if}}

{{#if credential_profile_name}}
credential_profile_name: {{credential_profile_name}}
{{/if}}
{{#if access_key_id}}
access_key_id: {{access_key_id}}
{{/if}}
{{#if secret_access_key}}
secret_access_key: {{secret_access_key}}
{{/if}}
{{#if session_token}}
session_token: {{session_token}}
{{/if}}
{{#if role_arn}}
role_arn: {{role_arn}}
{{/if}}

{{#if region_name}}
region_name: {{region_name}}
{{/if}}

{{#if log_streams}}
log_streams:
{{#each log_streams as |stream|}}
  - {{stream}}
{{/each}}
{{/if}}
{{#if log_stream_prefix}}
log_stream_prefix: {{log_stream_prefix}}
{{/if}}
{{#if start_position}}
start_position: {{start_position}}
{{/if}}

{{#if scan_frequency}}
scan_frequency: {{scan_frequency}}
{{/if}}
{{#if api_timeout}}
api_timeout: {{api_timeout}}
{{/if}}
{{#if latency}}
latency: {{latency}}
{{/if}}

{{#if number_of_workers}}
number_of_workers: {{number_of_workers}}
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

### 1. At least one log group identifier required

Every template must specify one of the three log group options. They are mutually exclusive in practice, but all should be conditional so the manifest controls which is active.

```yaml
# by ARN -- most specific, preferred for single-group collection
log_group_arn: {{log_group_arn}}

# by name
log_group_name: {{log_group_name}}

# by prefix -- matches multiple groups
log_group_name_prefix: {{log_group_name_prefix}}
```

A template with none of these is broken. A template that hardcodes a log group name is a review finding.

### 2. Authentication must use variables

All credential fields must reference Handlebars variables. Hardcoded AWS credentials are a critical security issue.

```yaml
# correct -- all credential fields are variables
{{#if access_key_id}}
access_key_id: {{access_key_id}}
{{/if}}
{{#if secret_access_key}}
secret_access_key: {{secret_access_key}}
{{/if}}
{{#if role_arn}}
role_arn: {{role_arn}}
{{/if}}

# wrong -- hardcoded
access_key_id: AKIAIOSFODNN7EXAMPLE
```

Templates should support multiple authentication methods: access key pair, credential profile, session token, and IAM role assumption. Users running on EC2/ECS with instance roles may not provide any explicit credentials.

### 3. Region must be configurable

```yaml
# correct
{{#if region_name}}
region_name: {{region_name}}
{{/if}}

# wrong -- hardcoded region
region_name: us-east-1
```

### 4. Start position should be explicit

The default start position is `beginning`, which causes the input to read all historical logs on first startup. This can be expensive and slow for large log groups.

```yaml
{{#if start_position}}
start_position: {{start_position}}
{{/if}}
```

Valid values: `beginning` and `end`. The manifest should document which default is set and why.

### 5. Worker count must be configurable with care

Each worker consumes API quota and memory. Hardcoded high worker counts can cause CloudWatch API throttling.

```yaml
# correct -- configurable
{{#if number_of_workers}}
number_of_workers: {{number_of_workers}}
{{/if}}

# problematic -- hardcoded high value
number_of_workers: 50
```

The manifest should document the recommended range and default.

## Log group patterns

### Single log group by ARN

```yaml
log_group_arn: {{log_group_arn}}
```

ARN is the most specific identifier and avoids ambiguity across regions or accounts.

### Single log group by name

```yaml
log_group_name: {{log_group_name}}
```

### Multiple log groups by prefix

```yaml
log_group_name_prefix: {{log_group_name_prefix}}
```

Example: prefix `/aws/lambda/` matches all Lambda function log groups in the account. The input discovers new groups matching the prefix on each scan cycle.

### Filtering to specific log streams

```yaml
log_group_name: {{log_group_name}}
{{#if log_streams}}
log_streams:
{{#each log_streams as |stream|}}
  - {{stream}}
{{/each}}
{{/if}}

{{#if log_stream_prefix}}
log_stream_prefix: {{log_stream_prefix}}
{{/if}}
```

Use `log_streams` for an explicit list of stream names. Use `log_stream_prefix` to match streams by prefix within the log group.

## API mode and CloudWatch Logs Insights

The `aws-cloudwatch` input uses the CloudWatch Logs `FilterLogEvents` API by default. This is suitable for most use cases.

CloudWatch Logs Insights (`StartQuery` / `GetQueryResults`) is an alternative that supports more complex query patterns but has different pricing and rate-limiting characteristics. The input type supports both, controlled by the `api_mode` field when available:

```yaml
{{#if api_mode}}
api_mode: {{api_mode}}
{{/if}}
```

Review considerations:
- `FilterLogEvents` is simpler and suitable for tailing log groups
- Insights queries incur per-query charges and have concurrency limits
- If the integration uses Insights, the query must be exposed as a variable

## Common configuration patterns

### Lambda logs

```yaml
log_group_name: /aws/lambda/{{function_name}}

{{#if credential_profile_name}}
credential_profile_name: {{credential_profile_name}}
{{/if}}
{{#if access_key_id}}
access_key_id: {{access_key_id}}
{{/if}}
{{#if secret_access_key}}
secret_access_key: {{secret_access_key}}
{{/if}}
{{#if role_arn}}
role_arn: {{role_arn}}
{{/if}}

{{#if region_name}}
region_name: {{region_name}}
{{/if}}

{{#if scan_frequency}}
scan_frequency: {{scan_frequency}}
{{/if}}

start_position: {{start_position}}
```

### VPC Flow Logs

```yaml
log_group_arn: {{log_group_arn}}

{{#if access_key_id}}
access_key_id: {{access_key_id}}
{{/if}}
{{#if secret_access_key}}
secret_access_key: {{secret_access_key}}
{{/if}}
{{#if role_arn}}
role_arn: {{role_arn}}
{{/if}}

{{#if region_name}}
region_name: {{region_name}}
{{/if}}

start_position: {{start_position}}
{{#if latency}}
latency: {{latency}}
{{/if}}
```

The `latency` parameter adds a delay before reading events, which helps when CloudWatch Logs delivers events out of order. VPC Flow Logs benefit from a small latency value (e.g., `1m`).

### ECS/Fargate logs

```yaml
log_group_name: {{log_group_name}}
log_stream_prefix: {{log_stream_prefix}}

{{#if access_key_id}}
access_key_id: {{access_key_id}}
{{/if}}
{{#if secret_access_key}}
secret_access_key: {{secret_access_key}}
{{/if}}

{{#if scan_frequency}}
scan_frequency: {{scan_frequency}}
{{/if}}
{{#if number_of_workers}}
number_of_workers: {{number_of_workers}}
{{/if}}
```

### Multi-account collection

```yaml
log_group_arn: {{log_group_arn}}

{{#if access_key_id}}
access_key_id: {{access_key_id}}
{{/if}}
{{#if secret_access_key}}
secret_access_key: {{secret_access_key}}
{{/if}}

{{#if role_arn}}
role_arn: {{role_arn}}
{{/if}}

{{#if region_name}}
region_name: {{region_name}}
{{/if}}
```

The `role_arn` field enables cross-account collection by assuming a role in the target account.

## Performance and rate limiting

### Scan frequency

```yaml
{{#if scan_frequency}}
scan_frequency: {{scan_frequency}}
{{/if}}
```

Controls how often the input polls for new log events. Aggressive values increase API calls and risk throttling. The default is typically `1m`.

### API sleep

```yaml
{{#if api_sleep}}
api_sleep: {{api_sleep}}
{{/if}}
```

Adds a delay between API calls to reduce throttling risk. Useful when collecting from many log groups or streams simultaneously.

### Filter patterns

CloudWatch supports server-side filter patterns that reduce the volume of data transferred:

```yaml
{{#if filter_pattern}}
filter_pattern: "{{filter_pattern}}"
{{/if}}
```

Filter patterns follow CloudWatch filter syntax. Using server-side filters reduces both API costs and network transfer.

### API timeout

```yaml
{{#if api_timeout}}
api_timeout: {{api_timeout}}
{{/if}}
```

Sets the timeout for individual CloudWatch API calls. Increase for large log groups or slow regions.

## Parameters reference

### Core parameters

| Parameter | Type | Description |
|---|---|---|
| `log_group_arn` | string | CloudWatch log group ARN |
| `log_group_name` | string | CloudWatch log group name |
| `log_group_name_prefix` | string | Prefix to match multiple log groups |
| `log_streams` | array | Specific log stream names to collect |
| `log_stream_prefix` | string | Log stream name prefix filter |
| `start_position` | string | `beginning` or `end` |
| `scan_frequency` | duration | Polling interval for new events |
| `api_timeout` | duration | API call timeout |
| `api_sleep` | duration | Delay between API calls |
| `latency` | duration | Delay before reading (helps with ordering) |
| `number_of_workers` | int | Parallel workers for log group processing |
| `filter_pattern` | string | CloudWatch server-side filter expression |
| `region_name` | string | AWS region |

### Authentication parameters

| Parameter | Type | Description |
|---|---|---|
| `credential_profile_name` | string | AWS credential profile name |
| `access_key_id` | string | AWS access key ID |
| `secret_access_key` | string | AWS secret access key |
| `session_token` | string | Temporary session token |
| `role_arn` | string | IAM role ARN for cross-account assume-role |

## Review checklist

### Log group configuration
- [ ] At least one log group option specified (`log_group_arn`, `log_group_name`, or `log_group_name_prefix`)
- [ ] Log group identifiers use variables, not hardcoded values
- [ ] Choice of identifier is appropriate (ARN for single group, prefix for multi-group)

### Authentication
- [ ] No hardcoded credentials anywhere in the template
- [ ] Multiple authentication methods supported (access key, profile, role)
- [ ] `role_arn` available for cross-account collection
- [ ] Credential fields use `type: password` in the manifest

### Region and positioning
- [ ] Region is configurable via variable
- [ ] `start_position` is explicit with a documented default
- [ ] Latency configured if event ordering matters

### Performance
- [ ] `scan_frequency` is configurable with a reasonable default
- [ ] `number_of_workers` is configurable (not hardcoded to a high value)
- [ ] `api_timeout` is configurable
- [ ] Filter patterns used where applicable to reduce data volume
- [ ] API rate limiting considered (scan frequency, api_sleep, worker count)

### Tags and processors
- [ ] Tags block follows common patterns
- [ ] Processors passthrough at top level
