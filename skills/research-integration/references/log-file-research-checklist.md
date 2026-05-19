# Log and File Research Checklist

Use this checklist when the product writes local log files or sends syslog messages over the network. This covers `filestream`, `tcp`, and `udp` input types.

## Discovery phase

- [ ] Find the official logging documentation for the product
- [ ] Identify all distinct log types/sources the product generates
- [ ] Determine whether the product supports remote syslog forwarding, local files, or both
- [ ] Check for log configuration guides (enabling verbose logging, choosing formats, configuring destinations)
- [ ] Look for log message catalogs or reference documents that list all event IDs/types
- [ ] Check if the vendor publishes **log format definitions, parser code, or message catalogs** in a public git repository. If found, clone into `temp/` for analysis. Parser code from vendor SDKs or SIEM connectors can reveal field structures more completely than documentation

## Log file details (filestream input)

### Paths and locations

- [ ] **Default log file paths per OS:**
  - Linux: `<path>`
  - Windows: `<path>`
  - macOS: `<path>` (if applicable)
- [ ] **Glob patterns needed:** do paths include variable components (dates, hostnames, instance names)?
- [ ] **Multiple log files:** does the product write to different files for different log types?
- [ ] **Log rotation:**
  - Rotation trigger (size, time, both)
  - Rotated file naming pattern (`.1`, `.log.1`, date suffix)
  - Compression of rotated files (gzip?)
  - Retention policy (number of files, days)
- [ ] **File permissions:** does the agent need special permissions to read the log files?
- [ ] **Character encoding:** UTF-8, ASCII, other?

### File format

- [ ] **Format identified:** syslog / JSON / NDJSON / CSV / key-value / CEF / LEEF / W3C extended / custom delimited / multiline free text
- [ ] **One event per line?** Or does a single event span multiple lines?
- [ ] **If multiline:**
  - Start pattern (regex that identifies the first line of an event)
  - End pattern (if applicable)
  - Example of a complete multiline event
- [ ] **Header lines:** does the file start with header/metadata lines that should be skipped?

## Syslog details (tcp/udp input)

### Transport

- [ ] **Protocol:** UDP only / TCP only / both supported
- [ ] **Default port:** vendor's recommended port (or standard 514)
- [ ] **TLS support:** does the product support syslog over TLS (TCP)?
- [ ] **Syslog RFC:**
  - RFC 3164 (BSD format): `<PRI>TIMESTAMP HOSTNAME APP-NAME: MSG`
  - RFC 5424 (IETF format): `<PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA MSG`
- [ ] **Facility and severity usage:** which syslog facility does the product use? Does severity map to event severity?

### Message format inside syslog

- [ ] **Message format identified:** CEF / LEEF / key-value pairs / JSON / free text / mixed
- [ ] **If CEF:**
  - CEF version
  - Device vendor / device product / device version fields
  - Event class ID patterns
  - Extension key names and types
  - Example CEF messages for each event type
- [ ] **If LEEF:**
  - LEEF version
  - Delimiter character
  - Key names and types
- [ ] **If key-value:**
  - Delimiter between pairs (space, comma, pipe, etc.)
  - Separator between key and value (=, :, etc.)
  - Quoting rules for values with spaces
  - Escape characters
- [ ] **If JSON:**
  - Is it a complete JSON object per message?
  - Or is JSON embedded within a syslog prefix?

## Message structure and parsing

### Delimiters and structure

- [ ] **Field delimiter:** character(s) that separate fields
- [ ] **Message structure pattern:** regex or grok pattern sketch for the common message format
- [ ] **Variable-length fields:** fields that can contain the delimiter character (need special parsing)
- [ ] **Optional fields:** fields that may be absent in some messages

### Timestamp handling

- [ ] **Timestamp field:** where in the message is the timestamp?
- [ ] **Timestamp format:** `MMM dd HH:mm:ss` / ISO 8601 / Unix epoch / custom
- [ ] **Timezone:**
  - Always UTC?
  - Includes timezone offset?
  - Local timezone with no offset (requires `tz_offset` config)?
  - Multiple timestamps in one event (which is authoritative)?
- [ ] **Timestamp precision:** seconds / milliseconds / microseconds

## Event types and content

### Event type identification

- [ ] **Event type indicator:** which field or pattern distinguishes event types?
  - Syslog facility/severity
  - Message ID or event ID field
  - Application name in syslog header
  - Keyword or prefix in the message body
  - Combination of fields
- [ ] **Complete event type list:**

| Event type / ID | Category | Description | Example trigger |
|----------------|----------|-------------|-----------------|
| <type> | <category> | <description> | <what causes this event> |

### Field inventory per event type

For each event type (or for common fields shared across types):

- [ ] **Field list captured:**

| Field name | Type | Description | Example value | Present in all events? |
|-----------|------|-------------|---------------|----------------------|
| <field> | <type> | <desc> | <example> | <yes/no> |

- [ ] **Enumeration values:** for status, action, severity, direction, protocol fields -- list all known values
- [ ] **IP address fields:** identify all fields containing IP addresses (needed for ECS mapping and GeoIP)
- [ ] **User identity fields:** identify fields with usernames, email addresses, user IDs
- [ ] **Hostname fields:** identify fields with hostnames, FQDNs

### Sample data

- [ ] **At least 3-5 sample messages per event type** (from vendor docs, not fabricated)
- [ ] **Edge cases captured:**
  - Minimal message (fewest optional fields)
  - Maximal message (all fields populated)
  - Error/failure events
  - Events with special characters (Unicode, quotes in values)
- [ ] **All samples saved** to `references/sample-events/` with descriptive filenames

## Platform-specific considerations

- [ ] **Version differences:** do log formats change between product versions?
- [ ] **Configuration-dependent output:** do log fields change based on product configuration or license level?
- [ ] **Encoding issues:** are there known encoding problems (e.g., Windows event logs with mixed encoding)?
- [ ] **Volume estimates:** approximate events per second/minute in a typical deployment

## Pipeline implications

After gathering the above, note:

- [ ] **Parsing approach:** grok / dissect / JSON parse / KV parse / CSV parse / combination
- [ ] **Multiline handling needed:** yes/no, with proposed pattern
- [ ] **Branching needed:** are there multiple event formats that require different parsing branches?
- [ ] **Timezone injection:** will `tz_offset` config be needed for timestamp parsing?
- [ ] **Common parsing challenges:** embedded JSON, URL-encoded values, nested key-value, variable field order
