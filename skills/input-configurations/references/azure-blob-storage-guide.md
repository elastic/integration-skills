# Azure Blob Storage input guide

Complete reference for building and reviewing `abs.yml.hbs` templates in Elastic integrations.

Documentation: [Azure Blob Storage Input Reference](https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-input-azure-blob-storage.html)

## File location

```
packages/<package>/data_stream/<data_stream>/agent/stream/abs.yml.hbs
```

## Required structure

The Azure Blob Storage input polls containers for new or updated blobs. Every template must configure a storage account, at least one container, and authentication credentials.

```yaml
account_name: {{account_name}}

containers:
  - name: {{container_name}}
    {{#if file_selectors}}
    file_selectors:
    {{#each file_selectors as |selector|}}
      - regex: "{{selector.regex}}"
    {{/each}}
    {{/if}}

{{#if storage_url}}
storage_url: {{storage_url}}
{{/if}}
{{#if connection_string}}
connection_string: {{connection_string}}
{{/if}}
{{#if sas_token}}
sas_token: {{sas_token}}
{{/if}}
{{#if service_account_key}}
service_account_key: {{service_account_key}}
{{/if}}
{{#if tenant_id}}
tenant_id: {{tenant_id}}
{{/if}}
{{#if client_id}}
client_id: {{client_id}}
{{/if}}
{{#if client_secret}}
client_secret: {{client_secret}}
{{/if}}

{{#if poll_interval}}
poll_interval: {{poll_interval}}
{{/if}}
```

## Validation rules

### 1. Account name required and must use a variable

Every Azure Blob Storage template must include `account_name`. It must reference a Handlebars variable.

```yaml
# Correct
account_name: {{account_name}}

# Never acceptable
account_name: mystorageaccount
```

### 2. Container configuration required and must use a variable

At least one container must be configured with a variable-based name.

```yaml
# Correct
containers:
  - name: {{container_name}}

# Never acceptable
containers:
  - name: my-container
```

### 3. Authentication must be provided and use variables

Templates must include at least one authentication method. All credential values must reference Handlebars variables. Hardcoded connection strings or keys are a critical security issue.

```yaml
# Correct
{{#if connection_string}}
connection_string: {{connection_string}}
{{/if}}

# Never acceptable
connection_string: 'DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...'
```

### 4. Multiple authentication methods should be supported

A template that only supports a single authentication method is limited. Ideally, the template should support connection string, SAS token, and service principal authentication so users can choose the method that fits their security requirements.

```yaml
{{#if connection_string}}
connection_string: {{connection_string}}
{{/if}}
{{#if sas_token}}
sas_token: {{sas_token}}
{{/if}}
{{#if client_id}}
client_id: {{client_id}}
{{/if}}
```

## Authentication patterns

### Connection string

The simplest authentication method. The connection string contains the account name, key, and endpoint information in a single value.

```yaml
{{#if connection_string}}
connection_string: {{connection_string}}
{{/if}}
```

### SAS token

A Shared Access Signature grants limited access to storage resources with fine-grained permissions and expiry times. Requires `account_name` alongside the token.

```yaml
account_name: {{account_name}}
{{#if sas_token}}
sas_token: {{sas_token}}
{{/if}}
```

Note: SAS tokens have expiration dates. Long-running collectors must have a process for token rotation.

### Service principal (Azure AD)

Uses Azure Active Directory application credentials. Requires tenant ID, client ID, and client secret.

```yaml
account_name: {{account_name}}
{{#if tenant_id}}
tenant_id: {{tenant_id}}
{{/if}}
{{#if client_id}}
client_id: {{client_id}}
{{/if}}
{{#if client_secret}}
client_secret: {{client_secret}}
{{/if}}
```

### Managed identity

When the agent runs on an Azure resource (VM, App Service, AKS) with a managed identity assigned, no explicit credentials are needed. The input authenticates using the identity assigned to the host.

```yaml
account_name: {{account_name}}
```

### Multiple authentication with mutual exclusion

When a template supports multiple authentication methods, use `{{#unless}}` blocks to prevent conflicting configurations:

```yaml
account_name: {{account_name}}

containers:
  - name: {{container_name}}

{{#if connection_string}}
connection_string: {{connection_string}}
{{/if}}

{{#unless connection_string}}
{{#if sas_token}}
sas_token: {{sas_token}}
{{/if}}
{{/unless}}

{{#unless connection_string}}
{{#unless sas_token}}
{{#if tenant_id}}
tenant_id: {{tenant_id}}
{{/if}}
{{#if client_id}}
client_id: {{client_id}}
{{/if}}
{{#if client_secret}}
client_secret: {{client_secret}}
{{/if}}
{{/unless}}
{{/unless}}
```

## Polling and filtering

### Poll interval

Controls how frequently the input checks for new blobs. Must be configurable.

```yaml
{{#if poll_interval}}
poll_interval: {{poll_interval}}
{{/if}}
```

### File selectors

Regex-based filtering that restricts which blobs are processed. Useful when a container holds mixed content and only specific files are relevant.

```yaml
containers:
  - name: {{container_name}}
    {{#if file_selectors}}
    file_selectors:
    {{#each file_selectors as |selector|}}
      - regex: "{{selector.regex}}"
    {{/each}}
    {{/if}}
```

### Worker parallelism

Controls how many blobs are processed in parallel within a container.

```yaml
containers:
  - name: {{container_name}}
    {{#if max_workers}}
    max_workers: {{max_workers}}
    {{/if}}
```

## Content type handling

### Encoding and content type

When blobs contain non-UTF-8 content or a specific format, these must be configurable:

```yaml
{{#if encoding}}
encoding: {{encoding}}
{{/if}}
{{#if content_type}}
content_type: {{content_type}}
{{/if}}
```

### Custom storage URL

For sovereign clouds or private endpoints, a custom storage URL overrides the default Azure public endpoint:

```yaml
{{#if storage_url}}
storage_url: {{storage_url}}
{{/if}}
```

## Common configuration patterns

### Basic blob collection

```yaml
account_name: {{account_name}}

containers:
  - name: {{container_name}}

{{#if connection_string}}
connection_string: {{connection_string}}
{{/if}}
```

### Filtered collection with file selectors

```yaml
account_name: {{account_name}}

containers:
  - name: {{container_name}}
    {{#if file_selectors}}
    file_selectors:
    {{#each file_selectors as |selector|}}
      - regex: "{{selector.regex}}"
    {{/each}}
    {{/if}}
    {{#if max_workers}}
    max_workers: {{max_workers}}
    {{/if}}

{{#if connection_string}}
connection_string: {{connection_string}}
{{/if}}
```

## Parameters reference

| Parameter | Type | Description |
|---|---|---|
| `account_name` | string | Azure storage account name |
| `storage_url` | string | Custom storage URL (for sovereign clouds or private endpoints) |
| `containers` | array | List of container configurations |
| `containers[].name` | string | Container name |
| `containers[].file_selectors` | array | Regex patterns for blob filtering |
| `containers[].max_workers` | int | Parallel processing workers per container |
| `connection_string` | string | Azure storage connection string |
| `sas_token` | string | Shared Access Signature token |
| `service_account_key` | string | Storage account key |
| `tenant_id` | string | Azure AD tenant ID |
| `client_id` | string | Service principal application (client) ID |
| `client_secret` | string | Service principal client secret |
| `poll_interval` | duration | Polling interval for new blobs |
| `encoding` | string | Blob content encoding |
| `content_type` | string | Blob content type |

## Review checklist

### Configuration

- [ ] `account_name` uses a Handlebars variable -- **HIGH**
- [ ] `containers[].name` uses a Handlebars variable -- **HIGH**
- [ ] File selectors configurable when the container holds mixed content -- **MEDIUM**
- [ ] Poll interval configurable -- **MEDIUM**
- [ ] Custom storage URL available for sovereign clouds -- **LOW**

### Authentication

- [ ] No hardcoded credentials -- **CRITICAL**
- [ ] Multiple auth methods supported (connection string, SAS token, service principal) -- **HIGH**
- [ ] Connection string option present -- **MEDIUM**
- [ ] SAS token option present -- **MEDIUM**
- [ ] Service principal option present -- **MEDIUM**
- [ ] Managed identity documented as an option (no explicit credentials) -- **LOW**
- [ ] Mutual exclusion enforced when multiple auth methods are exposed -- **MEDIUM**

### File processing

- [ ] Blob filtering configured (file selectors or prefix-based) -- **MEDIUM**
- [ ] Encoding specified for non-UTF-8 content -- **LOW**
- [ ] Content type specified when needed -- **LOW**
- [ ] Worker parallelism configurable -- **LOW**

### Error handling

- [ ] Container access errors handled -- **MEDIUM**
- [ ] Credential/SAS token refresh considered for long-running collectors -- **MEDIUM**
