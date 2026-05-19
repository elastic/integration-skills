# Windows Event Log (winlog) input guide

Complete reference for building and reviewing `winlog.yml.hbs` templates in Elastic integrations.

The winlog input reads from Windows Event Log channels. It supports filtering by event ID, provider, level, and advanced XML queries.

## File location

```
packages/<package>/data_stream/<data_stream>/agent/stream/winlog.yml.hbs
```

## Required structure

```yaml
name: {{channel_name}}

{{#if event_id}}
event_id: {{event_id}}
{{/if}}
{{#if ignore_older}}
ignore_older: {{ignore_older}}
{{/if}}
{{#if level}}
level: {{level}}
{{/if}}
{{#if provider}}
provider:
{{#each provider as |p|}}
  - {{p}}
{{/each}}
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

### 1. Channel name must be specified

Every winlog template must have a `name` field identifying the Windows Event Log channel. This is the only strictly required field.

```yaml
# correct -- configurable via variable
name: {{channel_name}}

# correct -- fixed channel for a well-known log source
name: Security
name: Microsoft-Windows-Sysmon/Operational

# wrong -- missing
# (no name field)
```

### 2. Event ID filtering should be configurable

For channels that produce large volumes of events (especially Security), event ID filtering prevents ingesting irrelevant data. The filter should be a template variable so users can customize it.

```yaml
# correct -- configurable
{{#if event_id}}
event_id: {{event_id}}
{{/if}}

# acceptable -- fixed IDs for a specific use case
event_id: 4624, 4625, 4634

# concern -- Security channel without any event_id filter collects all security events
name: Security
# (no event_id)
```

The `event_id` value is a comma-separated string of event IDs. Ranges are not supported at the input level.

### 3. Ignore older for large logs

High-volume channels (Security, Sysmon) can accumulate millions of events. Without `ignore_older`, the agent processes the entire backlog on first start.

```yaml
# correct -- configurable
{{#if ignore_older}}
ignore_older: {{ignore_older}}
{{/if}}
```

### 4. Provider filtering narrows collection scope

When a channel contains events from multiple providers but only a subset is relevant, use the `provider` filter.

```yaml
# correct -- filter to specific providers
{{#if provider}}
provider:
{{#each provider as |p|}}
  - {{p}}
{{/each}}
{{/if}}
```

### 5. Channel names must be exact

Windows Event Log channel names are case-sensitive and must match exactly. Common errors include missing the `/Operational` suffix on Microsoft channels or using forward slashes vs backslashes.

```yaml
# correct
name: Microsoft-Windows-Sysmon/Operational
name: Microsoft-Windows-PowerShell/Operational

# wrong -- missing suffix
name: Microsoft-Windows-Sysmon
```

## Event log channels

### Standard channels

| Channel | Description | Typical volume |
|---|---|---|
| `Security` | Security and audit events (logon, privilege use, policy changes) | Very high |
| `System` | System-level events (services, drivers, hardware) | Medium |
| `Application` | Application-level events | Medium |

### Common Microsoft channels

| Channel | Description |
|---|---|
| `Microsoft-Windows-Sysmon/Operational` | Sysmon process, network, file events |
| `Microsoft-Windows-PowerShell/Operational` | PowerShell script execution |
| `Microsoft-Windows-Windows Defender/Operational` | Defender detections and status |
| `Microsoft-Windows-WMI-Activity/Operational` | WMI activity events |
| `Microsoft-Windows-TaskScheduler/Operational` | Scheduled task events |
| `Microsoft-Windows-Windows Firewall With Advanced Security/Firewall` | Firewall rule changes |
| `Microsoft-Windows-TerminalServices-LocalSessionManager/Operational` | RDP session events |

### Forwarded events

The `ForwardedEvents` channel contains events forwarded from other machines via Windows Event Forwarding (WEF):

```yaml
name: ForwardedEvents

{{#if forwarded}}
forwarded: {{forwarded}}
{{/if}}
```

When reading forwarded events, set `forwarded: true` so the input correctly handles the forwarded event format, which wraps the original event XML in an additional envelope.

## Providers

Providers identify the source component that generated an event within a channel. Filtering by provider is useful when a channel aggregates events from multiple sources.

```yaml
provider:
  - Microsoft-Windows-Security-Auditing
  - Microsoft-Windows-Eventlog
```

Common provider names by channel:

| Channel | Notable providers |
|---|---|
| Security | `Microsoft-Windows-Security-Auditing` |
| System | `Microsoft-Windows-Kernel-General`, `Service Control Manager`, `Microsoft-Windows-WindowsUpdateClient` |
| Application | Varies by installed applications |
| Sysmon/Operational | `Microsoft-Windows-Sysmon` |
| PowerShell/Operational | `Microsoft-Windows-PowerShell` |

## Event IDs

### Security channel key event IDs

| Event ID | Description |
|---|---|
| 4624 | Successful logon |
| 4625 | Failed logon |
| 4634 | Logoff |
| 4648 | Logon with explicit credentials |
| 4672 | Special privileges assigned |
| 4688 | Process creation |
| 4689 | Process termination |
| 4697 | Service installation |
| 4720 | User account created |
| 4722 | User account enabled |
| 4732 | Member added to security group |
| 4768 | Kerberos TGT requested |
| 4769 | Kerberos service ticket requested |
| 4776 | NTLM authentication |

### Sysmon key event IDs

| Event ID | Description |
|---|---|
| 1 | Process creation |
| 2 | File creation time change |
| 3 | Network connection |
| 5 | Process terminated |
| 7 | Image loaded |
| 8 | CreateRemoteThread |
| 10 | Process access |
| 11 | File create |
| 12, 13, 14 | Registry events |
| 15 | FileCreateStreamHash |
| 22 | DNS query |

## XML rendering

Windows Event Log events have an underlying XML structure. The `include_xml` option controls whether the raw XML is included in the output event.

```yaml
{{#if include_xml}}
include_xml: {{include_xml}}
{{/if}}
```

When `include_xml: true`, the full event XML is stored in `winlog.xml`. This is useful for:
- Integrations that need fields not extracted by default
- Forensic or compliance use cases requiring the original event format
- Debugging event parsing issues

The trade-off is increased event size. Only enable when the downstream pipeline or use case requires the raw XML.

## Forwarded events

Windows Event Forwarding (WEF) collects events from remote machines into a central `ForwardedEvents` channel. Templates reading forwarded events need special handling:

```yaml
name: ForwardedEvents
forwarded: true
```

Key considerations:
- The `forwarded` flag tells the input to unwrap the forwarding envelope and extract the original event.
- The `Computer` field in forwarded events reflects the originating machine, not the collector.
- Event rendering may fail if the collecting machine lacks the provider manifest for the original event source. See the language handling section.

## Language handling

Windows renders event messages using provider-specific message DLLs. The language of the rendered message depends on the system locale unless overridden.

```yaml
{{#if language}}
language: {{language}}
{{/if}}
```

Language codes use the IETF BCP 47 format (e.g., `en-US`, `de-DE`, `ja-JP`). The default is the system locale.

When to configure language explicitly:
- **Forwarded events**: The collecting machine may have a different locale than the originating machine. Setting `language: 0` uses the system default, while a specific locale ensures consistent rendering.
- **Multi-language environments**: When agents run on machines with varying locales but events should be in a consistent language for analysis.
- **Missing message DLLs**: On forwarded event collectors that lack the provider message tables, rendered messages may be empty or contain only parameter substitution placeholders.

## API type

The winlog input supports two API implementations:

```yaml
{{#if api}}
api: {{api}}
{{/if}}
```

| API | Description |
|---|---|
| `wineventlog` | Default Windows Event Log API. Stable, broadly compatible. |
| `wineventlog-experimental` | Experimental implementation with improved performance for high-volume channels. |

Use the default unless the integration documentation specifically requires the experimental API.

## Advanced configuration

### Batch read size

Controls how many events are read from the channel in a single API call. Higher values improve throughput but increase memory usage.

```yaml
{{#if batch_read_size}}
batch_read_size: {{batch_read_size}}
{{/if}}
```

Default is 100. For high-volume channels (Security on domain controllers), values of 500-1000 may improve performance.

### Level filtering

Filter events by severity level. Only events at or above the specified level are collected.

```yaml
{{#if level}}
level: {{level}}
{{/if}}
```

| Level | Numeric value | Description |
|---|---|---|
| `critical` | 1 | Critical errors |
| `error` | 2 | Errors |
| `warning` | 3 | Warnings |
| `information` | 4 | Informational |
| `verbose` | 5 | Verbose/debug |

Setting `level: warning` collects warning, error, and critical events.

### Multiple channels

Each winlog template handles a single channel. To collect from multiple channels, create separate stream files:

```
agent/stream/winlog-security.yml.hbs    -> name: Security
agent/stream/winlog-system.yml.hbs      -> name: System
agent/stream/winlog-application.yml.hbs -> name: Application
```

Each file follows the same template structure independently.

## Common configuration patterns

### Security events

```yaml
name: Security

{{#if event_id}}
event_id: {{event_id}}
{{/if}}

{{#if ignore_older}}
ignore_older: {{ignore_older}}
{{/if}}

{{#if processors}}
processors:
{{processors}}
{{/if}}
```

### Sysmon events

```yaml
name: Microsoft-Windows-Sysmon/Operational

{{#if event_id}}
event_id: {{event_id}}
{{/if}}
```

### PowerShell events

```yaml
name: Microsoft-Windows-PowerShell/Operational

{{#if event_id}}
event_id: {{event_id}}
{{/if}}
```

### Forwarded events with language override

```yaml
name: ForwardedEvents
forwarded: true
language: 0

{{#if event_id}}
event_id: {{event_id}}
{{/if}}

{{#if ignore_older}}
ignore_older: {{ignore_older}}
{{/if}}
```

## Parameters reference

| Parameter | Type | Description |
|---|---|---|
| `name` | string | Event log channel name (required) |
| `event_id` | string | Comma-separated event IDs to collect |
| `ignore_older` | duration | Ignore events older than this duration |
| `level` | string | Minimum event level (`critical`, `error`, `warning`, `information`, `verbose`) |
| `provider` | array | Event provider names to filter |
| `include_xml` | bool | Include raw event XML in output |
| `forwarded` | bool | Enable forwarded event handling |
| `language` | string/int | Language for event message rendering (BCP 47 or `0` for system default) |
| `api` | string | API type: `wineventlog` or `wineventlog-experimental` |
| `batch_read_size` | int | Events per batch read (default 100) |

## Error handling considerations

- **Missing event log channels**: Custom application channels may not exist on all machines. The agent logs a warning but continues. Templates for vendor-specific channels should document this.
- **Permission issues**: Reading the Security event log requires `SeSecurityPrivilege` or membership in the `Event Log Readers` group. Standard Application and System channels are readable by all authenticated users.
- **Large batch sizes and memory**: Setting `batch_read_size` too high on high-volume channels can cause memory pressure. Start with the default and increase only if throughput is insufficient.
- **Message rendering failures**: On forwarded event collectors or minimal Windows installations, provider message DLLs may be absent. Events will have populated `winlog.event_id` and `winlog.event_data` fields but empty or placeholder `message` fields.

## Review checklist

### Channel configuration

- [ ] `name` field present with correct channel name -- **HIGH**
- [ ] Channel name exact and correctly cased (including `/Operational` suffix where needed) -- **HIGH**
- [ ] Separate template files for each channel when collecting from multiple channels -- **MEDIUM**

### Event filtering

- [ ] Event ID filter present for high-volume channels (Security, Sysmon) -- **HIGH**
- [ ] Event ID filter is configurable via template variable -- **MEDIUM**
- [ ] Provider filter used when channel aggregates multiple sources -- **LOW**
- [ ] Level filter set when only high-severity events are needed -- **LOW**

### Performance

- [ ] `ignore_older` configured for high-volume channels -- **MEDIUM**
- [ ] `batch_read_size` appropriate for expected event volume -- **LOW**
- [ ] API type documented if using experimental -- **LOW**

### Forwarded events

- [ ] `forwarded: true` set when reading `ForwardedEvents` channel -- **HIGH**
- [ ] Language handling configured for multi-locale environments -- **MEDIUM**

### XML rendering

- [ ] `include_xml` enabled only when raw XML is needed downstream -- **LOW**
- [ ] Event size impact considered when `include_xml: true` -- **LOW**

### Common patterns

- [ ] `preserve_original_event` is conditional (`{{#if}}`) -- **MEDIUM**
- [ ] `forwarded` tag and `publisher_pipeline.disable_host` are coupled -- **MEDIUM**
- [ ] Custom processors passthrough at top level -- **LOW**
