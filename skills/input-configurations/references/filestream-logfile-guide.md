# Filestream and logfile input guide

Complete reference for building and reviewing `filestream.yml.hbs` and `log.yml.hbs` templates in Elastic integrations.

Filestream is the current file-based input. The logfile input (`type: log`) is deprecated -- new integrations must use filestream. This guide covers both so reviewers can evaluate legacy templates and assess migration readiness.

## File location

```
packages/<package>/data_stream/<data_stream>/agent/stream/filestream.yml.hbs
packages/<package>/data_stream/<data_stream>/agent/stream/log.yml.hbs          # legacy
```

## Required structure

### Filestream

```yaml
paths:
{{#each paths as |path|}}
  - {{path}}
{{/each}}

{{#if exclude_files}}
prospector.scanner.exclude_files:
{{#each exclude_files as |pattern|}}
  - {{pattern}}
{{/each}}
{{/if}}

{{#if multiline_pattern}}
parsers:
  - multiline:
      pattern: '{{multiline_pattern}}'
      negate: {{multiline_negate}}
      match: {{multiline_match}}
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

### Logfile (legacy)

```yaml
paths:
{{#each paths as |path|}}
  - {{path}}
{{/each}}

allow_deprecated_use: true

exclude_files: ['\.gz$']

{{#if multiline_pattern}}
multiline:
  pattern: '{{multiline_pattern}}'
  negate: {{multiline_negate}}
  match: {{multiline_match}}
  max_lines: 5000
  timeout: 10s
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

## Syntax differences between filestream and logfile

| Aspect | Filestream | Logfile (deprecated) |
|---|---|---|
| File exclusions | `prospector.scanner.exclude_files:` (YAML list) | `exclude_files: ['\.gz$']` (inline array) |
| Multiline | `parsers:` block with nested `- multiline:` | `multiline:` or `multiline.*` flat keys |
| Deprecation flag | Not needed | `allow_deprecated_use: true` required |
| State tracking | Improved file identity with fingerprinting | Registry-based |
| Status | Recommended for all new integrations | Deprecated |

## Validation rules

### 1. Paths must use Handlebars variables

Paths must iterate over a template variable. Hardcoded paths prevent users from customizing the file locations through the integration UI.

```yaml
# correct
paths:
{{#each paths as |path|}}
  - {{path}}
{{/each}}

# wrong -- hardcoded
paths:
  - /var/log/app/*.log
```

### 2. Exclude compressed and rotated files

Log directories commonly contain `.gz` or `.zip` archives from log rotation. These must be excluded to avoid re-ingesting old data or attempting to read compressed content.

```yaml
# filestream
prospector.scanner.exclude_files:
  - '\.gz$'
  - '\.zip$'

# logfile
exclude_files: ['\.gz$']
```

Omitting this exclusion is an error for any data stream where log rotation may produce compressed files.

### 3. Filestream uses parsers, not multiline keys

Filestream replaced the top-level `multiline.*` keys with a `parsers:` pipeline. Using the old syntax in a filestream template is invalid.

```yaml
# correct -- filestream
parsers:
  - multiline:
      pattern: '^{'
      negate: true
      match: after

# wrong -- old syntax in a filestream template
multiline.pattern: '^{'
multiline.negate: true
multiline.match: after
```

### 4. Filestream uses prospector.scanner for exclusions

The logfile `exclude_files` key does not work in filestream templates. Use `prospector.scanner.exclude_files` instead.

```yaml
# correct -- filestream
prospector.scanner.exclude_files:
{{#each exclude_files as |pattern|}}
  - {{pattern}}
{{/each}}

# wrong -- logfile syntax in a filestream template
exclude_files:
  - '\.gz$'
```

### 5. Logfile must include allow_deprecated_use

Every `log.yml.hbs` template must contain `allow_deprecated_use: true`. Without this flag the agent emits deprecation warnings or refuses to start (depending on version).

### 6. New integrations must use filestream

If the PR introduces a new integration or a new data stream and uses `log.yml.hbs`, flag it. The logfile input should only appear in existing integrations that have not yet migrated. New work must use `filestream.yml.hbs`.

### 7. Multiline must include max_lines and timeout

Any multiline configuration should set `max_lines` and `timeout` to prevent unbounded memory growth when a multiline pattern fails to match a terminating line.

```yaml
# filestream
parsers:
  - multiline:
      pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
      negate: true
      match: after
      max_lines: 500
      timeout: 5s

# logfile
multiline:
  pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
  negate: true
  match: after
  max_lines: 5000
  timeout: 10s
```

## Multiline patterns

### JSON logs (pretty-printed)

When JSON objects span multiple lines, match the opening brace and group subsequent lines.

```yaml
parsers:
  - multiline:
      pattern: '^{'
      negate: true
      match: after
      max_lines: 5000
      timeout: 10s
```

### Timestamp-based logs

Lines that begin with a timestamp start a new event. Lines without a leading timestamp are continuations.

```yaml
# ISO timestamp
parsers:
  - multiline:
      pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
      negate: true
      match: after

# Syslog timestamp
parsers:
  - multiline:
      pattern: '^[A-Z][a-z]{2} [0-9]{1,2} [0-9]{2}:'
      negate: true
      match: after
```

### Stack traces (Java / Python)

Stack trace continuation lines are appended to the preceding event.

```yaml
# Java stack traces
parsers:
  - multiline:
      pattern: '^\s+(at |\.\.\.)'
      negate: false
      match: after

# Python tracebacks
parsers:
  - multiline:
      pattern: '^Traceback|^\s+File'
      negate: false
      match: after
```

### Whitespace continuation

Lines starting with whitespace are treated as continuations of the previous line.

```yaml
parsers:
  - multiline:
      pattern: '^\s'
      negate: false
      match: after
```

## Parsers pipeline (filestream only)

Filestream supports a pipeline of parsers that process log lines before they become events. Parsers execute in order.

| Parser | Description |
|---|---|
| `multiline` | Combine multiline messages into a single event |
| `ndjson` | Parse newline-delimited JSON |
| `container` | Parse Docker/Kubernetes container log format |
| `syslog` | Parse RFC 3164 / RFC 5424 syslog lines |

Example combining container parsing with multiline:

```yaml
parsers:
  - container: {}
  - multiline:
      pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
      negate: true
      match: after
```

## Include and exclude filters

### prospector.scanner.exclude_files (filestream)

Regex patterns matched against the full file path. Matching files are skipped entirely.

```yaml
prospector.scanner.exclude_files:
  - '\.gz$'
  - '\.zip$'
  - '\.old$'
```

### prospector.scanner.include_files (filestream)

When set, only files matching at least one pattern are collected. All others are ignored.

```yaml
prospector.scanner.include_files:
  - '\.log$'
  - '\.json$'
```

### exclude_files (logfile)

Same purpose, different syntax. Takes an inline YAML array.

```yaml
exclude_files: ['\.gz$']
```

## Close and clean options

These settings control when file handles are released and when state entries are cleaned up. Correct values depend on the log rotation strategy of the monitored application.

### Filestream

```yaml
{{#if close_inactive}}
close.on_state_change.inactive: {{close_inactive}}
{{/if}}
{{#if close_removed}}
close.on_state_change.removed: {{close_removed}}
{{/if}}
{{#if clean_removed}}
clean_removed: {{clean_removed}}
{{/if}}
```

| Setting | Description | Typical value |
|---|---|---|
| `close.on_state_change.inactive` | Close the file handle after no new data for this duration | `5m` |
| `close.on_state_change.removed` | Close when the file is removed from disk | `5s` |
| `clean_removed` | Remove state entry for files that have been deleted | `true` |

### Logfile

```yaml
{{#if close_inactive}}
close_inactive: {{close_inactive}}
{{/if}}
{{#if ignore_older}}
ignore_older: {{ignore_older}}
{{/if}}
{{#if scan_frequency}}
scan_frequency: {{scan_frequency}}
{{/if}}
```

| Setting | Description | Typical value |
|---|---|---|
| `close_inactive` | Close file handle after inactivity | `5m` |
| `ignore_older` | Skip files not modified within this duration | `72h` |
| `scan_frequency` | How often to check for new files | `10s` |

## Rotation handling

Filestream handles log rotation through file identity tracking. It recognizes that a rotated file (e.g., `app.log` renamed to `app.log.1`) is the same file and continues reading from where it left off, then picks up the new `app.log`.

Key settings that affect rotation behavior:

```yaml
prospector.scanner.check_interval: 10s
prospector.scanner.fingerprint.enabled: true
prospector.scanner.symlinks: true
```

| Setting | Purpose |
|---|---|
| `check_interval` | How frequently the scanner looks for new or changed files |
| `fingerprint.enabled` | Use content fingerprinting instead of inode/device for file identity |
| `symlinks` | Follow symbolic links (disabled by default) |

For logfile input, symlink handling requires an explicit flag:

```yaml
{{#if symlinks}}
symlinks: {{symlinks}}
{{/if}}
```

## Harvester configuration

### Encoding

When log files use a non-UTF-8 encoding, specify it explicitly. Mismatched encoding produces garbled text.

```yaml
{{#if encoding}}
encoding: {{encoding}}
{{/if}}
```

Common values: `utf-8` (default), `latin1`, `utf-16-be`, `utf-16-le`, `big5`, `shift-jis`.

### Line terminator

Most files use the default (auto-detected), but some formats require explicit configuration:

```yaml
{{#if line_terminator}}
line_terminator: {{line_terminator}}
{{/if}}
```

Values: `auto`, `line_feed`, `vertical_tab`, `form_feed`, `carriage_return_line_feed`, `next_line`, `line_separator`, `paragraph_separator`, `null_terminator`.

### Recursive glob

Enable `**` expansion in path patterns to match files in subdirectories:

```yaml
prospector.scanner.recursive_glob: true
```

## Parameters reference

### Filestream

| Parameter | Type | Description |
|---|---|---|
| `paths` | array | File paths, supports glob patterns |
| `prospector.scanner.exclude_files` | array | Regex patterns to exclude |
| `prospector.scanner.include_files` | array | Regex patterns to include |
| `prospector.scanner.symlinks` | bool | Follow symlinks |
| `prospector.scanner.recursive_glob` | bool | Enable `**` in paths |
| `prospector.scanner.check_interval` | duration | File scan interval |
| `prospector.scanner.fingerprint.enabled` | bool | Use content fingerprinting for file identity |
| `ignore_older` | duration | Ignore files not modified within this duration |
| `ignore_inactive` | string | Ignore inactive files (`since_first_start`, `since_last_start`) |
| `encoding` | string | File encoding |
| `line_terminator` | string | Line terminator override |
| `close.on_state_change.inactive` | duration | Close file handle after inactivity |
| `close.on_state_change.removed` | duration | Close after file removal |
| `clean_removed` | bool | Remove state for deleted files |
| `parsers` | array | Parser pipeline |

### Logfile

| Parameter | Type | Description |
|---|---|---|
| `paths` | array | File paths, supports glob patterns |
| `allow_deprecated_use` | bool | Required, must be `true` |
| `exclude_files` | array | Regex patterns to exclude (inline format) |
| `multiline.pattern` | string | Multiline start pattern |
| `multiline.negate` | bool | Negate the pattern match |
| `multiline.match` | string | `after` or `before` |
| `multiline.max_lines` | int | Maximum lines per event |
| `multiline.timeout` | duration | Multiline timeout |
| `close_inactive` | duration | Close file handle after inactivity |
| `ignore_older` | duration | Skip old files |
| `scan_frequency` | duration | File discovery interval |
| `symlinks` | bool | Follow symlinks |
| `encoding` | string | File encoding |

## Migration from logfile to filestream

When evaluating whether a `log.yml.hbs` can be migrated, apply these translations:

| Logfile | Filestream |
|---|---|
| `exclude_files: ['\.gz$']` | `prospector.scanner.exclude_files:` followed by YAML list items |
| `multiline:` block or `multiline.*` keys | `parsers:` block with `- multiline:` |
| `allow_deprecated_use: true` | Remove entirely |
| `close_inactive: 5m` | `close.on_state_change.inactive: 5m` |
| `scan_frequency: 10s` | `prospector.scanner.check_interval: 10s` |
| `symlinks: true` | `prospector.scanner.symlinks: true` |

### Before (log.yml.hbs)

```yaml
paths:
{{#each paths as |path|}}
  - {{path}}
{{/each}}
exclude_files: ['\.gz$']
allow_deprecated_use: true
multiline:
  pattern: '^{'
  negate: true
  match: after
  max_lines: 5000
  timeout: 10s
```

### After (filestream.yml.hbs)

```yaml
paths:
{{#each paths as |path|}}
  - {{path}}
{{/each}}
prospector.scanner.exclude_files:
  - '\.gz$'
parsers:
  - multiline:
      pattern: '^{'
      negate: true
      match: after
      max_lines: 5000
      timeout: 10s
```

## Common configuration patterns

### Basic log file (filestream)

```yaml
paths:
{{#each paths as |path|}}
  - {{path}}
{{/each}}

prospector.scanner.exclude_files:
  - '\.gz$'
```

### JSON log files (filestream)

```yaml
paths:
{{#each paths as |path|}}
  - {{path}}
{{/each}}

prospector.scanner.exclude_files:
  - '\.gz$'

{{#if multiline_json}}
parsers:
  - multiline:
      pattern: '^{'
      negate: true
      match: after
      max_lines: 5000
      timeout: 10s
{{/if}}

{{#if custom}}
{{custom}}
{{/if}}
```

### Application logs with stack traces (filestream)

```yaml
paths:
{{#each paths as |path|}}
  - {{path}}
{{/each}}

prospector.scanner.exclude_files:
  - '\.gz$'
  - '\.old$'

parsers:
  - multiline:
      pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
      negate: true
      match: after
      max_lines: 500
      timeout: 5s

processors:
- add_locale: ~
{{#if processors}}
{{processors}}
{{/if}}
```

### Syslog files (logfile, legacy)

```yaml
paths:
{{#each paths as |path|}}
  - {{path}}
{{/each}}
exclude_files: ['\.gz$']
allow_deprecated_use: true
multiline:
  pattern: '^\s'
  negate: false
  match: after

processors:
- add_locale: ~
```

## Error handling considerations

- **Paths that may not exist yet**: The agent tolerates missing paths on startup. If the directory appears later, files are picked up on the next scan cycle.
- **Permission issues**: The agent process must have read access to log files and their parent directories. Journal or container log paths may require elevated permissions.
- **Disk space for state**: The filestream registry and logfile state file grow with the number of tracked files. In high-churn environments (many short-lived log files), ensure `clean_removed` is enabled to prevent unbounded state growth.

## Review checklist

### Path configuration

- [ ] Paths use `{{#each paths}}` iteration -- **HIGH**
- [ ] No hardcoded paths -- **HIGH**
- [ ] Glob patterns are appropriate for the target application -- **MEDIUM**

### File exclusions

- [ ] Compressed files excluded (`.gz$`, `.zip$`) -- **HIGH**
- [ ] Old/rotated file patterns excluded if applicable -- **MEDIUM**
- [ ] Correct syntax for input type (`prospector.scanner.exclude_files` for filestream, `exclude_files` for logfile) -- **HIGH**

### Multiline

- [ ] Uses `parsers:` in filestream, `multiline:` in logfile -- **HIGH**
- [ ] Pattern appropriate for the log format -- **HIGH**
- [ ] `max_lines` set -- **MEDIUM**
- [ ] `timeout` set -- **MEDIUM**
- [ ] `negate` and `match` values correct for the pattern strategy -- **HIGH**

### Input type selection

- [ ] New integrations use filestream, not logfile -- **HIGH**
- [ ] Logfile templates include `allow_deprecated_use: true` -- **HIGH**
- [ ] Migration to filestream assessed for existing logfile data streams -- **LOW**

### Harvester and performance

- [ ] Close timeouts appropriate for log volume and rotation strategy -- **MEDIUM**
- [ ] Encoding specified if non-UTF-8 logs -- **MEDIUM**
- [ ] Rotation handling considered (fingerprinting, symlinks) -- **LOW**
- [ ] `clean_removed` enabled for high-churn environments -- **LOW**

### Common patterns

- [ ] `preserve_original_event` is conditional (`{{#if}}`) -- **MEDIUM**
- [ ] `forwarded` tag and `publisher_pipeline.disable_host` are coupled -- **MEDIUM**
- [ ] Custom processors passthrough at top level -- **LOW**
