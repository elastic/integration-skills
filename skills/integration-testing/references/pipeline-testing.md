# pipeline testing

Everything needed to create, generate, and debug `elastic-package test pipeline` fixtures for ingest pipeline validation.

## Test directory layout

Pipeline tests live at:

`data_stream/<stream>/_dev/test/pipeline/`

Canonical file patterns:
- input logs: `test-<package>-<datastream>-<type>-sample.log`
- input JSON events: `test-<package>-<datastream>-<type>-sample.json`
- optional config: `test-common-config.yml` or `test-<package>-<datastream>-<type>-sample.<ext>-config.yml`
- expected output: `test-<package>-<datastream>-<type>-sample.<ext>-expected.json`

Where:
- `<package>`: the package name (e.g. `acme_firewall`)
- `<datastream>`: the data stream name (e.g. `event`, `traffic`)
- `<type>`: the event type or log variant being tested (e.g. `alert`, `auth`, `dns`)

Example: `test-acme_firewall-event-alert-sample.log`

Always follow this convention. Do not use free-form names like `test1.log`.

Good scenario names describe behavior:
- `test-acme_firewall-event-successful-login-sample.log`
- `test-acme_firewall-event-malformed-record-sample.log`
- `test-acme_firewall-traffic-dns-sample.log`

## Input types

### Raw log fixtures (`.log`)

Use for line-oriented logs and multiline traces. Each event is normally one line unless multiline settings are configured.

```text
67.43.156.13 - - [25/Oct/2016:14:49:33 +0200] "GET / HTTP/1.1" 200 612 "-" "Mozilla/5.0 ..."
67.43.156.13 - - [25/Oct/2016:14:49:34 +0200] "GET /favicon.ico HTTP/1.1" 404 571 "-" "Mozilla/5.0 ..."
```

### JSON event fixtures (`.json`)

Use for structured input and explicit field control. JSON test fixtures use this shape:

```json
{
  "events": [
    {
      "@timestamp": "2024-01-15T10:30:00.000Z",
      "message": "{\"cpu_usage\":85.2}"
    }
  ]
}
```

## Config file options

Supported `*-config.yml` sections:

- `fields`: static fields injected before pipeline execution
- `dynamic_fields`: field-to-regex map for non-deterministic values (e.g. `event.ingested`)
- `numeric_keyword_fields`: list of field paths whose values arrive as numbers in the source but are declared as `keyword` in `fields.yml`. Do not artificially stringify these values in the fixture — declare them here instead. Common candidates: `network.iana_number`, port numbers, error codes, protocol or class codes.
- `multiline`: controls multiline record grouping for `.log` inputs

### `fields`

Injects static values into each input event before the ingest pipeline runs. Common uses: stable `@timestamp` for deterministic tests, tags, and stream-specific config.

```yaml
fields:
  "@timestamp": "2020-04-28T11:07:58.223Z"
  tags:
    - preserve_original_event
  event:
    timezone: "+0000"
```

### `dynamic_fields`

Compares selected fields using regex instead of exact value. Use for non-deterministic fields — any field whose value changes between test runs (e.g., fields derived from `_ingest.timestamp`).

**Note:** Integration pipelines must NOT set `event.ingested` — it is managed by Elasticsearch outside the integration. If you encounter a legacy integration that sets `event.ingested` in its pipeline, include it in `dynamic_fields`; for new integrations following current standards, this entry is not needed.

If the pipeline sets `@timestamp` from `_ingest.timestamp` as a fallback (non-deterministic), add it:

```yaml
dynamic_fields:
  "@timestamp": "^[0-9]{4}(-[0-9]{2}){2}T[0-9]{2}(:[0-9]{2}){2}\\.[0-9]{3}"
```

### `numeric_keyword_fields`

Lists fields that may look numeric in test data but are mapped as `keyword`. Do not stringify the value in the fixture or add a `convert` processor — Elasticsearch coerces silently at index time. Declare them here:

```yaml
numeric_keyword_fields:
  - zoom.meeting.id
  - ocsf.src_endpoint.type_id
  - network.iana_number
```

### `multiline`

Groups multiple log lines into one event before pipeline simulation. Most common option is `first_line_pattern`:

```yaml
multiline:
  first_line_pattern: "^\\d{4}\\/\\d{2}\\/\\d{2} "
```

```yaml
multiline:
  first_line_pattern: '^(?:\{|\d{4}-\d{2}-\d{2})'
  negate: true
  match: after
```

### Config placement strategy

- Always create a single `test-common-config.yml` that applies to all fixtures in the directory.
- The `test-common-config.yml` must always include `fields.tags: [preserve_original_event]`:
  ```yaml
  fields:
    tags:
      - preserve_original_event
  ```
- Only add a per-test config file (`test-<package>-<datastream>-<type>-sample.<ext>-config.yml`) when a specific sample requires configuration that differs from the common config.
- Do not create per-test config files by default.

### `source.geo` fields and `dynamic_fields`

Do **not** add `source.geo.*` (or other geo enrichment fields like `destination.geo.*`) to `dynamic_fields`. These fields are deterministic — they are produced by the `geoip` processor based on static IP-to-location databases and should produce consistent values in pipeline tests.

If `source.geo` fields cause pipeline test failures (mismatches, missing fields), the root cause is almost certainly an incorrect `format_version` or `conditions.kibana.version` in the root `manifest.yml`. The correct values are:

```yaml
format_version: "3.4.2"
conditions:
  kibana:
    version: "^8.19.0 || ^9.1.0"
```

Fix the root manifest first. If failures persist after correcting the manifest, ignore the specific lint/validate complaints for those geo fields rather than adding them to `dynamic_fields`.

## Expected output format

Expected files (`*-expected.json`) are JSON objects with an `expected` array. Each entry corresponds to one input event. Use `null` for events intentionally dropped by the pipeline.

**Minimal example:**

```json
{
  "expected": [
    {
      "ecs": { "version": "9.1.0" },
      "event": { "kind": "event", "category": ["web"], "type": ["info"] }
    }
  ]
}
```

**Typical log pipeline example:**

```json
{
  "expected": [
    {
      "@timestamp": "2016-10-25T12:49:33.000Z",
      "ecs": { "version": "8.11.0" },
      "event": {
        "category": ["web"],
        "kind": "event",
        "type": ["access"],
        "outcome": "success",
        "original": "67.43.156.13 - - [25/Oct/2016:14:49:33 +0200] \"GET / HTTP/1.1\" 200 612 \"-\" \"Mozilla/5.0 ...\""
      },
      "http": { "request": { "method": "GET" }, "response": { "status_code": 200 } },
      "source": { "address": "67.43.156.13" },
      "url": { "original": "/" }
    }
  ]
}
```

**Drop-path example:**

```json
{
  "expected": [null]
}
```

**Expected output files must never be created or edited manually.** Always generate them:

```bash
elastic-package test pipeline --data-streams <stream> --generate
```

Then review the generated diff to confirm the output is correct. If a field value is wrong, fix the ingest pipeline and regenerate — do not hand-edit the expected JSON.

### Reviewing generated output

After running `--generate`, check:
- Parser extracted intended fields
- ECS categorization fields are correct (`event.kind`, `event.category`, `event.type` are arrays)
- Field types match expectations (string/number/object/array)
- Dotted field names from source data are correctly expanded into nested objects (e.g., `"host.name": "x"` in source becomes `{"host": {"name": "x"}}` in expected output)
- `geo_point` fields appear under the correct parent entity (`source.geo.location`, `destination.geo.location`) not at root
- `event.original` is present when `preserve_original_event` is set in config
- No accidental new fields from temporary pipeline state (e.g., `_tmp`)
- `null` entries only where drop behavior is intentional
- No accidental field drops

`--generate` records current behavior — it does not validate whether that behavior is correct.

## Core workflow

```bash
# 1) Start local ES-only stack
elastic-package stack up -d --services=elasticsearch

# 2) Run scoped pipeline tests while iterating
elastic-package test pipeline --data-streams <stream>

# 3) Regenerate expected outputs when behavior changes intentionally
elastic-package test pipeline --data-streams <stream> --generate

# 4) Review diffs before commit
git diff data_stream/<stream>/_dev/test/pipeline/
```

## Wiring provided log samples into test fixtures

When sample data is available, use it as the basis for pipeline test input files:

1. **Sanitize first — no exceptions.** Strip all customer data before writing any fixture file. See the data anonymization section below.

2. **Determine the fixture format:**
   - Plain text / syslog lines → `.log` file, one event per line
   - NDJSON (one JSON object per line) → `.log` file, one compact JSON object per line (do **not** pretty-print — that breaks the test runner)
   - Structured JSON input events → `.json` file using the `{"events": [...]}` wrapper format

3. **Split by event type.** If the sample contains multiple distinct event types, create one fixture file per type. Do not combine unrelated event types into a single fixture.

4. **Do not reformat or modify the log content.** Write sanitized lines exactly as they appear. Only touch the values that need anonymization.

5. Generate and review expected output:
   ```bash
   elastic-package test pipeline --data-streams <stream> --generate
   ```

## Fixture scenario coverage

Use a minimal but representative set:
- Happy path records (the normal case)
- Malformed record handling (what happens with bad input)
- Empty input / drop-path behavior (events the pipeline intentionally discards)
- Multiline cases (if the stream supports them)
- Boundary values (large IDs, unicode text, optional fields)

Prefer one scenario per file for clear diffs and easier failure diagnosis.

## Reference package patterns

- `nginx` / `apache`: log fixtures with multiline and dynamic timestamp handling
- `postgresql` / `auditd`: multiline-heavy fixtures
- `amazon_security_lake`: extensive `numeric_keyword_fields` usage for OCSF IDs
- `zoom` and similar webhook streams: JSON fixtures with per-test config overrides
- `agentless_hello_world`: minimal JSON fixture shape

## Data anonymization

**Never commit customer data.** All test fixture data must be fully anonymized before committing. No real production data, customer data, or identifiable information may appear in pipeline test inputs (`test-*.log`, `test-*.json`) or generated expected outputs (`*-expected.json`).

Replace every identifying value with a synthetic example of the same format: IP addresses, hostnames, email addresses, usernames, organization names, account IDs, API keys, and any other value traceable to a real person, system, or organization. Use RFC 5737 documentation IP ranges (`198.51.100.x`, `203.0.113.x`), `example.com`/`example.org` domains, and realistic placeholder names. Replacements must preserve the structural shape that parsers depend on.

Refer to the `anonymize-logs` skill for the full anonymization policy and placeholder conventions.

## Troubleshooting

- **"field X is undefined" for ECS fields** (e.g. `field "destination.ip" is undefined`):
  - Root cause: missing or outdated `_dev/build/build.yml`
  - Fix: create or update `_dev/build/build.yml` with `dependencies.ecs.reference: "git@v9.3.0"`
  - Do **not** add ECS fields to `fields.yml` to work around this — fix `build.yml` instead
  - Custom (non-ECS) fields reported as undefined must still be defined in the appropriate field files
- Unexpected diffs on time-like fields:
  - Add or tighten `dynamic_fields` regex entries
- Multiline fixture split incorrectly:
  - Adjust `multiline.first_line_pattern` (and `negate` / `match` if needed)
- Numeric vs keyword mismatch:
  - Add the field path to `numeric_keyword_fields` in the test config
- Pipeline test cannot find expected behavior after parser change:
  - Rerun scoped test, then regenerate with `--generate`, then review diff
- Pipeline resolution or syntax issues:
  - Run `elastic-package lint` and verify ingest pipeline file paths
