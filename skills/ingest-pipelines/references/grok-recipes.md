# Grok Pattern Recipes

## Pattern library reference

The authoritative built-in pattern library for Elasticsearch's grok processor lives in the Elasticsearch source tree:

- **Browsable directory (all pattern files):** https://github.com/elastic/elasticsearch/tree/master/libs/grok/src/main/resources/patterns/ecs-v1
- **Core `grok-patterns` file (IP, hostname, timestamps, numbers, paths, syslog, HTTP):** https://github.com/elastic/elasticsearch/blob/master/libs/grok/src/main/resources/patterns/ecs-v1/grok-patterns

Always check those sources for the actual regex behind a pattern before assuming it matches a specific input shape.

---

## Core grok syntax

### Three expression forms

| Form | Syntax | Effect |
|------|--------|--------|
| Match only | `%{SYNTAX}` | Matches the pattern; no field created |
| Named capture | `%{SYNTAX:field.name}` | Matches and stores result in `field.name` |
| Typed capture | `%{SYNTAX:field.name:TYPE}` | Matches, stores, and coerces to `TYPE` |

```
# Match only — skip a token
%{IP} - %{USER:user.name}

# Named capture
%{IP:source.ip} %{WORD:http.request.method} %{URIPATH:url.path}

# Typed capture
%{NUMBER:http.response.status_code:int} %{NUMBER:http.response.body.bytes:long}
```

### Inline regex captures

When no built-in pattern fits, embed a raw regex directly:

```
(?<log.level>DEBUG|INFO|WARN|ERROR|FATAL)
(?<event.action>[a-zA-Z0-9_\-]+)
```

Inline regex and `%{SYNTAX}` references can be freely mixed in the same expression.

---

## Type coercion

By default every capture is a string. Append a type suffix to coerce:

| Suffix | Result type | Common use |
|--------|-------------|------------|
| `int` | 32-bit integer | Response codes, small counts |
| `long` | 64-bit integer | Bytes, large counters |
| `double` | 64-bit float | Durations, rates |
| `float` | 32-bit float | Rarely preferred over `double` |
| `boolean` | Boolean | `true`/`false` (case-insensitive) |

```
%{NUMBER:http.response.status_code:int}
%{NUMBER:http.response.body.bytes:long}
%{NUMBER:event.duration:double}
```

---

## Custom patterns with `pattern_definitions`

Define reusable inline patterns directly in the grok processor (no separate pattern file needed for Elasticsearch pipelines):

```yaml
- grok:
    field: event.original
    pattern_definitions:
      THREAD_ID: "[A-Za-z0-9#]+"
      JAVA_CLASS: "[a-zA-Z$_][a-zA-Z$_0-9]*(?:\\.[a-zA-Z$_][a-zA-Z$_0-9]*)*"
    patterns:
      - '^%{TIMESTAMP_ISO8601:timestamp} \[%{THREAD_ID:thread}\] %{WORD:log.level} %{JAVA_CLASS:logger} - %{GREEDYDATA:message}$'
    tag: parse_java_log
```

Naming convention: `SCREAMING_SNAKE_CASE`; prefix with a namespace to avoid collisions: `MYAPP_REQUEST_ID` instead of `REQUEST_ID`.

---

## Syslog header recipes

Syslog integrations receive a full syslog line and need to split the header from the payload. Parse the header in `default.yml` or a shared sub-pipeline, then route the extracted message to a format-specific sub-pipeline.

**Rule:** never overwrite `event.original`. Store extracted sub-fields in `_temp.*` when you need to pass them to sub-pipelines.

### RFC 3164 — traditional syslog header

```
Sample:
Jan 15 10:30:00 web-01 sshd[1234]: Accepted publickey for alice from 192.168.1.10 port 55234

Pattern:
^%{SYSLOGTIMESTAMP:timestamp} %{IPORHOST:host.hostname} %{NOTSPACE:process.name}(?:\[%{POSINT:process.pid:int}\])?: %{GREEDYDATA:message}$

Fields: timestamp, host.hostname, process.name, process.pid
Payload: message
```

### RFC 5424 — structured syslog header (no SD-ELEMENT)

```
Sample:
<34>1 2024-01-15T10:30:00.000Z mymachine.example.com sshd 1234 ID47 - Accepted publickey for alice

Pattern:
^<%{NONNEGINT:syslog.priority:int}>%{POSINT:syslog.version:int} %{TIMESTAMP_ISO8601:timestamp} %{IPORHOST:host.hostname} %{NOTSPACE:process.name} %{NOTSPACE:process.pid} %{NOTSPACE:syslog.msgid} - %{GREEDYDATA:message}$
```

### RFC 5424 — structured syslog header (with SD-ELEMENT block)

```
Sample:
<34>1 2024-01-15T10:30:00.000Z mymachine.example.com su - ID47 [exampleSDID@32473 iut="3"] BOM su root failed

Pattern:
^<%{NONNEGINT:syslog.priority:int}>%{POSINT:syslog.version:int} %{TIMESTAMP_ISO8601:timestamp} %{IPORHOST:host.hostname} %{NOTSPACE:process.name} %{NOTSPACE:process.pid} %{NOTSPACE:syslog.msgid} (?:\[%{DATA:syslog.structured_data}\]|-) %{GREEDYDATA:message}$
```

Capture the SD-ELEMENT block into `syslog.structured_data`, then pass it to a `kv` processor. See the **Syslog structured data strategies** section below for the full KV, SYSLOG5424SD, and Painless approaches.

### Split header from payload for sub-pipeline routing

When `default.yml` is a thin router, extract the envelope but do not clobber `event.original`:

```yaml
- grok:
    field: event.original
    patterns:
      - '^%{SYSLOGTIMESTAMP:_temp.timestamp} %{IPORHOST:host.hostname} %{NOTSPACE:process.name}(?:\[%{POSINT:process.pid:int}\])?: %{GREEDYDATA:_temp.message}$'
    tag: parse_syslog_header
```

Sub-pipelines then parse `_temp.message` for their specific event format. `_temp` fields are removed at the end of the pipeline.

---

## Syslog structured data strategies

Firewall and network integrations frequently receive syslog with RFC 5424 structured data elements — the `[sdId key1="value1" key2="value2"]` format, or vendor-specific `key=value key2="quoted value"` payloads embedded in syslog messages.

### Strategy 1: Grok + KV with `trim_value` (simplest)

When values use consistent quoting and keys contain no special characters, the built-in `kv` processor handles this well. Use a lookahead-based `field_split` to handle spaces inside quoted values.

This pattern is used by integrations like juniper_srx, sophos, and sonicwall_firewall in the upstream `elastic/integrations` repository.

```yaml
- kv:
    field: _temp.kv_data
    field_split: ' (?=[a-zA-Z0-9_-]+=)'
    value_split: "="
    prefix: "vendor.product."
    trim_value: '"'
    ignore_missing: true
    tag: kv_structured_data
```

Key settings:
- `field_split: ' (?=[a-zA-Z0-9_-]+=)'` — splits on spaces only when followed by a key= pattern, preserving spaces in quoted values
- `trim_value: '"'` — strips surrounding quotes from values
- `prefix` — namespaces all extracted keys under a vendor prefix

### Strategy 2: Grok with `SYSLOG5424SD` + KV with regex splits

When the syslog header follows RFC 5424 strictly, use the built-in `SYSLOG5424SD` grok pattern to capture the structured data block, then parse it with `kv`. Some vendors use `:` or `::` as the value separator instead of `=`.

This pattern is based on the `system/auth` integration in the upstream `elastic/integrations` repository.

```yaml
- grok:
    field: event.original
    patterns:
      - '^<%{NONNEGINT:log.syslog.priority:int}>%{NONNEGINT} %{TIMESTAMP} %{IPORHOST:host.hostname} %{DATA:process.name} %{POSINT:process.pid:long} %{DATA:event.code} (?:-|%{SYSLOG5424SD:syslog5424_sd}) %{GREEDYDATA:message}$'
    tag: parse_rfc5424

- kv:
    if: ctx.syslog5424_sd != null && ctx.syslog5424_sd != ''
    field: syslog5424_sd
    field_split: '(?<=") '
    value_split: '(?i)(?<=[a-z])=(?=")'
    trim_key: " "
    trim_value: " "
    prefix: parsed.
    strip_brackets: true
    tag: kv_sd_element
```

### Strategy 3: Painless script for complex quoted-value KV

When values contain embedded equals signs, mixed quoting, or irregular delimiters that defeat the `kv` processor, use a Painless script. This is heavier but handles edge cases reliably.

This pattern is used by integrations like fortinet_fortigate and fortinet_fortimanager in the upstream `elastic/integrations` repository.

```yaml
- script:
    lang: painless
    if: ctx._temp?.kv_data != null
    tag: script_parse_quoted_kv
    description: Split KV pairs handling quoted values with embedded spaces/delimiters.
    source: |
      def splitUnquoted(String input, String sep) {
        def tokens = [];
        def startPosition = 0;
        def isInQuotes = false;
        char quote = (char)"\"";
        for (def i = 0; i < input.length(); i++) {
          if (input.charAt(i) == quote) {
            isInQuotes = !isInQuotes;
          } else if (input.charAt(i) == (char)sep && !isInQuotes) {
            def token = input.substring(startPosition, i).trim();
            if (!token.equals("")) { tokens.add(token); }
            startPosition = i + 1;
          }
        }
        def last = input.substring(startPosition).trim();
        if (!last.equals("")) { tokens.add(last); }
        return tokens;
      }
      def arr = splitUnquoted(ctx._temp.kv_data, " ");
      Map map = new HashMap();
      Pattern pattern = /^\"|\"$/;
      for (def i = 0; i < arr?.length; i++) {
        def kv = splitUnquoted(arr[i], "=");
        if (kv.length == 2 && kv[0].length() > 0) {
          map[kv[0]] = pattern.matcher(kv[1]).replaceAll("");
        }
      }
      ctx.vendor = new HashMap();
      ctx.vendor.product = map;
```

Prefer strategy 1 or 2 when possible; use the script approach only when KV edge cases demand it.

---

## Web server / HTTP access log

```
Sample (Nginx combined):
192.168.1.1 - alice [15/Jan/2024:10:30:00 +0000] "GET /api/v1/health HTTP/1.1" 200 512 "https://example.com" "Mozilla/5.0"

Pattern (ECS field names):
^%{IPORHOST:source.ip} - %{DATA:user.name} \[%{HTTPDATE:timestamp}\] "%{WORD:http.request.method} %{NOTSPACE:url.original}(?: HTTP/%{NUMBER:http.version})?" %{NUMBER:http.response.status_code:int} (?:%{NUMBER:http.response.body.bytes:long}|-) "(?:%{URI:http.request.referrer}|-)" "%{DATA:user_agent.original}"$
```

The built-in `%{COMMONAPACHELOG}` and `%{COMBINEDAPACHELOG}` patterns exist but use legacy (non-ECS) field names. Prefer the explicit ECS-mapped pattern above.

---

## Common mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Unanchored pattern | Partial match produces wrong field values | Prepend `^` — fail fast on non-matching lines |
| `DATA` or `GREEDYDATA` without a bounding delimiter | Catastrophic backtracking; high CPU | Use `NOTSPACE` or `WORD`, or bound with lookahead: `%{DATA:f}(?=\s)` |
| Unescaped literal special characters | Pattern silently fails or matches the wrong segment | Escape `[`, `]`, `(`, `)`, `.`, `{`, `}` with `\` |
| Multi-pattern array ordered worst-first | Every line tries the slow/uncommon pattern first | Put the most common format at index 0 |
| No fallback pattern | Non-matching lines error or fail silently | Add `%{GREEDYDATA:message}` as the last entry |
| Wrong type suffix (`integer`, `Integer`) | Field stays as string | Use `int`/`long`/`double`/`float`/`boolean` only |
| Capturing the same ECS field twice | Second capture silently overwrites the first | Use distinct names; merge fields after parsing |

---

## Debugging

- **Kibana Grok Debugger**: Stack Management → Grok Debugger — interactive pattern testing against sample input
- **Elasticsearch Simulate API**: `POST _ingest/pipeline/_simulate` with `"trace_match": true` — see which pattern index matched and inspect intermediate fields
- **regex101.com**: select Oniguruma flavor for regex-level step-by-step explanation
