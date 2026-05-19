# Journald input guide

Complete reference for building and reviewing `journald.yml.hbs` templates in Elastic integrations.

The journald input reads log entries from systemd journal files. It supports filtering by systemd unit, syslog identifier, transport, priority, and other journal fields.

## File location

```
packages/<package>/data_stream/<data_stream>/agent/stream/journald.yml.hbs
```

## Required structure

```yaml
{{#if paths}}
paths:
{{#each paths as |path|}}
  - {{path}}
{{/each}}
{{/if}}

{{#if include_matches}}
include_matches:
{{#each include_matches as |match|}}
  - {{match}}
{{/each}}
{{/if}}

{{#if seek}}
seek: {{seek}}
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

### 1. Include matches should be present and use variables

Every journald template should filter journal entries to the relevant systemd unit or syslog identifier. Collecting the entire journal without filtering produces excessive, unrelated data.

```yaml
# correct -- configurable via template variable
{{#if include_matches}}
include_matches:
{{#each include_matches as |match|}}
  - {{match}}
{{/each}}
{{/if}}

# acceptable -- fixed filter for a specific service integration
include_matches:
  - _SYSTEMD_UNIT=nginx.service

# wrong -- hardcoded unit name when the integration should be configurable
include_matches:
  - _SYSTEMD_UNIT=myapp.service
```

When the integration targets a specific, well-known service (e.g., Docker, sshd), a hardcoded unit name is acceptable. When the unit name varies by deployment, it must be a template variable.

### 2. Seek position should be configurable

The `seek` parameter controls where reading begins when no cursor state exists. It should be a template variable so the user can choose between `head`, `tail`, and `cursor`.

```yaml
# correct
{{#if seek}}
seek: {{seek}}
{{/if}}

# wrong -- hardcoded
seek: head
```

Values:

| Value | Behavior |
|---|---|
| `head` | Start from the oldest available entry |
| `tail` | Start from the newest entry (skip history) |
| `cursor` | Resume from the last recorded position (default) |

### 3. Journal paths are optional but must use variables when present

If not specified, the input reads from the default system journal at `/var/log/journal`. Custom paths are needed when journal files are stored in a non-standard location (e.g., container mounts, remote journal directories).

```yaml
# correct -- optional, defaults to system journal
{{#if paths}}
paths:
{{#each paths as |path|}}
  - {{path}}
{{/each}}
{{/if}}

# wrong -- hardcoded path
paths:
  - /var/log/journal
```

### 4. Include match fields must use valid journal field names

Journal field matchers follow the format `FIELD_NAME=value`. Common valid fields are listed in the field mapping section below. Using an invalid field name silently produces no matches.

### 5. No overly broad collection

A journald template without any `include_matches` collects every entry from the journal. This is almost never the intended behavior for an integration data stream. Flag templates that lack filtering.

## Include match fields

These are the standard systemd journal fields used in `include_matches` filters.

| Field | Description | Example value |
|---|---|---|
| `_SYSTEMD_UNIT` | Systemd unit name | `nginx.service` |
| `SYSLOG_IDENTIFIER` | Syslog program identifier | `myapp` |
| `_TRANSPORT` | Journal transport mechanism | `syslog`, `journal`, `stdout`, `kernel` |
| `PRIORITY` | Syslog priority level (0 = emergency, 7 = debug) | `0` through `7` |
| `_UID` | User ID of the logging process | `1000` |
| `_GID` | Group ID of the logging process | `1000` |
| `_COMM` | Process command name | `nginx` |
| `_EXE` | Process executable path | `/usr/sbin/nginx` |
| `_PID` | Process ID | `12345` |

Multiple `include_matches` entries are OR-combined within the same field and AND-combined across different fields.

## Cursor handling

The journald input tracks its reading position using journal cursors. When the agent restarts, it resumes from the last persisted cursor position.

### Seek vs cursor interaction

| Scenario | Behavior |
|---|---|
| First start, no cursor | Uses `seek` value (`head`, `tail`, or default `cursor`) |
| Restart with existing cursor | Resumes from cursor regardless of `seek` value |
| Cursor points to deleted entry | Uses `cursor_seek_fallback` if set, otherwise `head` |

### cursor_seek_fallback

When the cursor references a journal entry that has been rotated out, this setting determines where to resume:

```yaml
{{#if cursor_seek_fallback}}
cursor_seek_fallback: {{cursor_seek_fallback}}
{{/if}}
```

Values: `head`, `tail`. If not set, defaults to `head` (re-read all available entries).

## Field mapping conventions

Journal entries produce fields under the `journald` namespace. The input maps standard journal fields to ECS and Elastic agent fields:

| Journal field | Mapped Elastic field |
|---|---|
| `MESSAGE` | `message` |
| `_HOSTNAME` | `host.name` |
| `_SYSTEMD_UNIT` | `systemd.unit` |
| `SYSLOG_IDENTIFIER` | `syslog.identifier` |
| `PRIORITY` | `syslog.priority` |
| `_TRANSPORT` | `journald.transport` |
| `_PID` | `process.pid` |
| `_UID` | `user.id` |
| `_GID` | `group.id` |
| `_COMM` | `process.name` |
| `_EXE` | `process.executable` |

Custom journal fields (application-defined) appear under `journald.custom`.

## Advanced configuration

### Field filtering

Reduce event size by including or excluding specific journal fields. Useful when the journal entry contains many fields that are not needed for the integration.

```yaml
{{#if include_fields}}
include_fields:
{{#each include_fields as |field|}}
  - {{field}}
{{/each}}
{{/if}}
{{#if exclude_fields}}
exclude_fields:
{{#each exclude_fields as |field|}}
  - {{field}}
{{/each}}
{{/if}}
```

### Kernel messages

Control whether kernel ring buffer messages (`_TRANSPORT=kernel`) are included. Some integrations need kernel logs (e.g., firewall, audit), while others should exclude them to reduce noise.

```yaml
{{#if include_kernel_messages}}
include_kernel_messages: {{include_kernel_messages}}
{{/if}}
```

### Since filter

Only read entries newer than a relative time. Useful for preventing historical replay on first start:

```yaml
{{#if since}}
since: {{since}}
{{/if}}
```

## Common configuration patterns

### System journal for a specific service

```yaml
{{#if include_matches}}
include_matches:
{{#each include_matches as |match|}}
  - {{match}}
{{/each}}
{{/if}}

{{#if seek}}
seek: {{seek}}
{{/if}}
```

### Specific service with fixed unit

```yaml
include_matches:
  - _SYSTEMD_UNIT={{unit_name}}

{{#if seek}}
seek: {{seek}}
{{/if}}
```

### Container runtime logs

```yaml
include_matches:
  - _SYSTEMD_UNIT=docker.service
  - _SYSTEMD_UNIT=containerd.service

{{#if seek}}
seek: {{seek}}
{{/if}}
```

### Syslog identifier filtering

```yaml
include_matches:
  - SYSLOG_IDENTIFIER={{syslog_identifier}}

{{#if seek}}
seek: {{seek}}
{{/if}}
```

## Parameters reference

| Parameter | Type | Description |
|---|---|---|
| `paths` | array | Journal file paths (defaults to `/var/log/journal` if omitted) |
| `include_matches` | array | Journal field matchers in `FIELD=value` format |
| `seek` | string | Start position: `head`, `tail`, `cursor` |
| `cursor_seek_fallback` | string | Fallback when cursor is invalid: `head`, `tail` |
| `since` | duration | Only entries newer than this relative time |
| `include_fields` | array | Journal fields to include in events |
| `exclude_fields` | array | Journal fields to exclude from events |
| `include_kernel_messages` | bool | Include kernel ring buffer messages |

## Error handling considerations

- **Missing journal directories**: The agent tolerates a missing `/var/log/journal` at startup and retries. If the journal uses volatile storage (`/run/log/journal`), entries do not persist across reboots.
- **Permission issues**: Reading the system journal requires membership in the `systemd-journal` group or root access. The agent process must have appropriate permissions.
- **Cursor recovery after agent restart**: If the journal has been rotated between agent stops, the cursor may point to a deleted entry. Configure `cursor_seek_fallback` to control behavior in this case.

## Review checklist

### Filtering

- [ ] `include_matches` present to avoid collecting the entire journal -- **HIGH**
- [ ] Match fields use valid journal field names -- **HIGH**
- [ ] Match values use template variables when the target unit varies by deployment -- **MEDIUM**
- [ ] Not overly broad (no unfiltered collection without justification) -- **HIGH**

### Seek and cursor

- [ ] `seek` position is configurable via template variable -- **MEDIUM**
- [ ] `cursor_seek_fallback` set if journal rotation is expected -- **LOW**
- [ ] Default seek behavior is appropriate for the data stream's use case -- **MEDIUM**

### Paths

- [ ] Paths use template variables when present -- **HIGH**
- [ ] Omitted when the default system journal is the intended source -- **LOW**
- [ ] Journal path accessible by the agent process -- **MEDIUM**

### Advanced settings

- [ ] Field filtering reduces event size when journal entries contain many unused fields -- **LOW**
- [ ] Kernel messages included or excluded as appropriate for the data stream -- **LOW**
- [ ] `since` filter considered for data streams that should not replay history -- **LOW**

### Common patterns

- [ ] `preserve_original_event` is conditional (`{{#if}}`) -- **MEDIUM**
- [ ] `forwarded` tag and `publisher_pipeline.disable_host` are coupled -- **MEDIUM**
- [ ] Custom processors passthrough at top level -- **LOW**
