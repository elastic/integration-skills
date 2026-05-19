# AWS S3 input guide

Complete reference for building and reviewing `aws-s3.yml.hbs` templates in Elastic integrations.

Documentation: [AWS S3 Input Reference](https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-input-aws-s3.html)

## File location

```
packages/<package>/data_stream/<data_stream>/agent/stream/aws-s3.yml.hbs
```

## Required structure

The AWS S3 input supports two operating modes: SQS-based collection (recommended) and direct S3 polling. Every template must configure exactly one source, authentication, and optional tuning parameters.

### SQS-based collection (recommended)

SQS-based collection uses an SQS queue that receives S3 event notifications. The agent polls the queue, downloads the referenced objects, and processes them.

```yaml
queue_url: {{queue_url}}

{{#if credential_profile_name}}
credential_profile_name: {{credential_profile_name}}
{{/if}}
{{#if shared_credential_file}}
shared_credential_file: {{shared_credential_file}}
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

{{#if endpoint}}
endpoint: {{endpoint}}
{{/if}}
{{#if default_region}}
default_region: {{default_region}}
{{/if}}
{{#if fips_enabled}}
fips_enabled: {{fips_enabled}}
{{/if}}

{{#if visibility_timeout}}
visibility_timeout: {{visibility_timeout}}
{{/if}}
{{#if api_timeout}}
api_timeout: {{api_timeout}}
{{/if}}
{{#if max_number_of_messages}}
max_number_of_messages: {{max_number_of_messages}}
{{/if}}
{{#if number_of_workers}}
number_of_workers: {{number_of_workers}}
{{/if}}

{{#if proxy_url}}
proxy_url: {{proxy_url}}
{{/if}}
```

### Direct S3 polling (alternative)

Direct polling lists objects in a bucket on a schedule. Use when SQS is not available. Only one of the three polling sources may be set:

| Source | Mode | Notes |
|---|---|---|
| `bucket_arn` | S3 polling | Direct bucket listing |
| `access_point_arn` | S3 polling via Access Point | Must be a valid access point ARN |
| `non_aws_bucket_name` | Non-AWS S3 polling | Requires `region` and `endpoint` |

```yaml
bucket_arn: {{bucket_arn}}
```

```yaml
access_point_arn: {{access_point_arn}}
```

```yaml
non_aws_bucket_name: {{non_aws_bucket_name}}
```

## Validation rules

### 1. Exactly one source must be specified

The input accepts exactly one of four sources ([config.go validation](https://github.com/elastic/beats/blob/main/x-pack/filebeat/input/awss3/config.go#L82-L86)). Zero or more than one is an error at startup.

| Source | Mode |
|---|---|
| `queue_url` | SQS-based (recommended) |
| `bucket_arn` | S3 polling |
| `access_point_arn` | S3 polling via Access Point |
| `non_aws_bucket_name` | Non-AWS S3 polling |

When the manifest only exposes a single source variable (e.g., only `queue_url`), a plain `{{#if}}` guard is sufficient:

```yaml
{{#if queue_url}}
queue_url: {{queue_url}}
{{/if}}
```

When the manifest exposes more than one source option, the template must use nested `{{#unless}}` blocks to guarantee mutual exclusivity. Reference pattern from [aws_bedrock](https://github.com/elastic/integrations/blob/main/packages/aws_bedrock/data_stream/invocation/agent/stream/aws-s3.yml.hbs#L3-L13):

```yaml
{{#unless bucket_arn}}
{{#unless non_aws_bucket_name}}
{{#unless access_point_arn}}
{{#if queue_url}}
queue_url: {{queue_url}}
{{/if}}
{{/unless}}
{{/unless}}
{{/unless}}

{{#unless queue_url}}
{{#unless non_aws_bucket_name}}
{{#unless access_point_arn}}
{{#if bucket_arn}}
bucket_arn: {{bucket_arn}}
{{/if}}
{{/unless}}
{{/unless}}

{{#unless bucket_arn}}
{{#unless access_point_arn}}
{{#if non_aws_bucket_name}}
non_aws_bucket_name: {{non_aws_bucket_name}}
{{/if}}
{{/unless}}

{{#unless non_aws_bucket_name}}
{{#if access_point_arn}}
access_point_arn: {{access_point_arn}}
{{/if}}
{{/unless}}
{{/unless}}
```

### 2. Authentication must be complete and use variables

Templates must support multiple authentication methods and never hardcode credentials. All credential values must reference Handlebars variables.

Valid authentication patterns:

```yaml
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
```

A template that only supports access key + secret key without profile, role, or session token options is incomplete. All five credential fields should be conditionally present.

Hardcoded credentials are a critical security issue:

```yaml
# Never acceptable
access_key_id: AKIAIOSFODNN7EXAMPLE
secret_access_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### 3. Visibility timeout must be configurable

The SQS visibility timeout determines how long a message is hidden from other consumers after being received. The default is 30 seconds, which may be insufficient for large log files. Templates should expose this as a configurable parameter.

```yaml
{{#if visibility_timeout}}
visibility_timeout: {{visibility_timeout}}
{{/if}}
```

Guidance:
- Must be longer than the expected processing time for the largest objects
- Default 30s is often too low; typical values for large log files are 300s-900s
- If the timeout expires before processing completes, the message reappears in the queue and is processed again, causing duplicates

### 4. Worker configuration

`number_of_workers` controls how many S3 objects are processed in parallel. More workers increases throughput but also increases memory consumption.

`max_number_of_messages` is ignored from Beats 8.15 onwards ([elastic/integrations#12101](https://github.com/elastic/integrations/issues/12101)). Only include it when targeting versions before 8.15.

```yaml
{{#if number_of_workers}}
number_of_workers: {{number_of_workers}}
{{/if}}
{{#if max_number_of_messages}}
max_number_of_messages: {{max_number_of_messages}}
{{/if}}
```

### 5. Region must be configurable for cross-region access

When the SQS queue or S3 bucket may be in a different region from the agent, `default_region` must be present and configurable.

```yaml
{{#if default_region}}
default_region: {{default_region}}
{{/if}}
```

## Authentication patterns

### Profile-based authentication

Uses a named profile from the AWS credentials file.

```yaml
{{#if credential_profile_name}}
credential_profile_name: {{credential_profile_name}}
{{/if}}
{{#if shared_credential_file}}
shared_credential_file: {{shared_credential_file}}
{{/if}}
```

### Access key authentication

Direct access key and secret key. Session token supports temporary credentials from STS.

```yaml
{{#if access_key_id}}
access_key_id: {{access_key_id}}
{{/if}}
{{#if secret_access_key}}
secret_access_key: {{secret_access_key}}
{{/if}}
{{#if session_token}}
session_token: {{session_token}}
{{/if}}
```

### IAM role assumption

The agent assumes a role in the target account. Used for cross-account access. Typically combined with access key credentials or a profile for the initial authentication.

```yaml
{{#if role_arn}}
role_arn: {{role_arn}}
{{/if}}
```

### Cross-account access

Combines primary credentials with role assumption to access resources in a different AWS account.

```yaml
queue_url: {{queue_url}}

{{#if access_key_id}}
access_key_id: {{access_key_id}}
{{/if}}
{{#if secret_access_key}}
secret_access_key: {{secret_access_key}}
{{/if}}

{{#if role_arn}}
role_arn: {{role_arn}}
{{/if}}

{{#if default_region}}
default_region: {{default_region}}
{{/if}}
```

## Custom notification parsing

When S3 event notifications arrive through a non-standard path (SNS-wrapped, EventBridge, or a custom application), the built-in parser cannot extract the bucket name and object key. A custom parsing script handles these cases.

### Notification sources

| Source | Format | Parsing required |
|---|---|---|
| S3 -> SQS | Standard S3 event | Built-in (no custom script needed) |
| S3 -> SNS -> SQS | Wrapped in SNS `Message` field | Custom |
| S3 -> EventBridge -> SQS | EventBridge detail format | Custom |
| Custom application | Varies | Custom |

### Parsing script structure

The script defines a `parse(notification)` function that returns an array of `S3EventV2` objects. Each event must set at minimum the bucket name and object key.

```yaml
sqs.notification_parsing_script.source: |
  function parse(n) {
    var m = JSON.parse(n);
    var evts = [];

    // Standard S3 notification
    if (m.Records != null && m.Records.length > 0) {
      m.Records.forEach(function(r) {
        if (r.s3 && r.s3.bucket && r.s3.object) {
          var evt = new S3EventV2();
          evt.SetS3BucketName(r.s3.bucket.name);
          evt.SetS3ObjectKey(r.s3.object.key);
          if (r.s3.bucket.arn) {
            evt.SetS3BucketARN(r.s3.bucket.arn);
          }
          if (r.awsRegion) {
            evt.SetAWSRegion(r.awsRegion);
          }
          evts.push(evt);
        }
      });
    }
    // SNS wrapped notification
    else if (m.Message != null && m.TopicArn != null) {
      var p = JSON.parse(m.Message);
      // Process p.Records the same way as standard notifications
    }
    // EventBridge notification
    else if (m.detail != null && m.detail.bucket != null) {
      var evt = new S3EventV2();
      evt.SetS3BucketName(m.detail.bucket.name);
      evt.SetS3ObjectKey(m.detail.object.key);
      evts.push(evt);
    }

    return evts;
  }

  function test() {
    // Test cases for the parser
  }
```

Key requirements for custom parsers:
- Must handle all expected notification formats
- Must include a `test()` function for validation
- Must call `SetS3BucketName()` and `SetS3ObjectKey()` at minimum
- Should call `SetS3BucketARN()` and `SetAWSRegion()` when available

## File processing

### Content type and encoding

When S3 objects contain non-default content types or encodings, these must be configurable:

```yaml
{{#if file_content_type}}
content_type: {{file_content_type}}
{{/if}}
{{#if encoding}}
encoding: {{encoding}}
{{/if}}
```

### Multiline log handling

For log files with multiline entries (stack traces, multi-line JSON):

```yaml
{{#if multiline_pattern}}
parsers:
  - multiline:
      pattern: '{{multiline_pattern}}'
      negate: {{multiline_negate}}
      match: {{multiline_match}}
{{/if}}
```

### File filtering

When the bucket contains mixed content and only specific files should be processed, use `bucket_list_prefix` or `file_selectors` to limit scope:

```yaml
{{#if bucket_list_prefix}}
bucket_list_prefix: {{bucket_list_prefix}}
{{/if}}
```

## Parameters reference

| Parameter | Type | Description |
|---|---|---|
| `queue_url` | string | SQS queue URL |
| `bucket_arn` | string | S3 bucket ARN |
| `access_point_arn` | string | S3 Access Point ARN |
| `non_aws_bucket_name` | string | Non-AWS S3-compatible bucket name |
| `credential_profile_name` | string | AWS profile name from credentials file |
| `shared_credential_file` | string | Path to shared credentials file |
| `access_key_id` | string | AWS access key ID |
| `secret_access_key` | string | AWS secret access key |
| `session_token` | string | AWS session token for temporary credentials |
| `role_arn` | string | IAM role ARN to assume |
| `default_region` | string | AWS region |
| `endpoint` | string | Custom endpoint URL (for VPC endpoints or non-AWS S3) |
| `fips_enabled` | bool | Use FIPS-compliant endpoints |
| `visibility_timeout` | duration | SQS visibility timeout (default 30s) |
| `api_timeout` | duration | API call timeout |
| `max_number_of_messages` | int | Max messages per SQS receive (ignored in 8.15+) |
| `number_of_workers` | int | Number of parallel processing workers |
| `proxy_url` | string | HTTP proxy URL |
| `content_type` | string | Content type of S3 objects |
| `encoding` | string | File encoding |

## Review checklist

### Source configuration

- [ ] Exactly one source set (`queue_url` / `bucket_arn` / `access_point_arn` / `non_aws_bucket_name`) -- **CRITICAL**
- [ ] Mutual exclusivity enforced with `{{#unless}}` guards when multiple sources are exposed -- **HIGH**
- [ ] `non_aws_bucket_name` accompanied by `region` and `endpoint` -- **HIGH**

### Authentication

- [ ] Multiple auth methods supported (profile, access keys, role assumption) -- **HIGH**
- [ ] Session token supported for temporary credentials -- **MEDIUM**
- [ ] Role assumption available for cross-account access -- **MEDIUM**
- [ ] No hardcoded credentials -- **CRITICAL**

### SQS settings

- [ ] Visibility timeout configurable -- **HIGH**
- [ ] Worker count configurable -- **MEDIUM**
- [ ] `max_number_of_messages` only included when targeting pre-8.15 -- **LOW**

### AWS settings

- [ ] Region configurable (`default_region`) -- **HIGH**
- [ ] Endpoint configurable for VPC/FIPS use cases -- **MEDIUM**
- [ ] Proxy support present -- **LOW**

### Custom notification parsing

- [ ] Notification format documented if non-standard -- **MEDIUM**
- [ ] Parser handles all expected notification sources (direct S3, SNS-wrapped, EventBridge) -- **HIGH**
- [ ] Parser includes `test()` function -- **MEDIUM**
- [ ] Error handling present in parser -- **MEDIUM**

### File processing

- [ ] Content type and encoding configurable when needed -- **MEDIUM**
- [ ] Multiline configuration present for structured/multi-line logs -- **MEDIUM**
- [ ] Visibility timeout sufficient for the largest expected files -- **HIGH**
