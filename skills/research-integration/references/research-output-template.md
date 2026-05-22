# Research Output Template

Use this template as the structure for the `research-brief.md` file written to `research_results/<product_slug>/`.

Every section below should be populated. If a section does not apply, include it with a note explaining why (e.g., "N/A -- this product uses API collection, not log files."). This makes gaps explicit and prevents downstream consumers from wondering if information was simply missed.

---

## Template starts here

````markdown
# Research Brief: <Product/Vendor Name>

> **Generated:** <date>
> **Researcher:** AI-assisted research via /research-integration skill
> **Status:** DRAFT | READY FOR REVIEW
> **Confidence:** HIGH | MEDIUM | LOW (overall confidence in completeness)

## 1. Product Overview

### 1.1 What is it?

<2-5 sentences describing the product, what it does, and what kind of organization uses it.>

### 1.2 Vendor

- **Vendor name:** <vendor>
- **Product name:** <product>
- **Product category:** <e.g., endpoint security, network firewall, identity provider, cloud CSPM>
- **Vendor documentation portal:** <URL>

### 1.3 Data generated

<What kinds of data does this product generate? Security events, audit logs, metrics, configuration state, alerts, etc. List the major categories.>

### 1.4 Existing Elastic coverage

<Does an Elastic integration already exist for this product (check `integrations/packages/` and `packages/`)? If yes, what does it cover and what gaps exist? If no, note that this is a new integration.>

### 1.5 Competitive SIEM coverage

<1-2 sentence summary of the overall competitive landscape: which competitors have integrations for this product, and how comprehensive is their coverage.>

| Vendor | Integration name | Supported data sources | Collection method | Link |
|--------|-----------------|----------------------|-------------------|------|
| IBM QRadar | <name or "No integration found"> | <data sources covered, or N/A> | <API / syslog / agent / N/A> | <URL or N/A> |
| Splunk | <name or "No integration found"> | <data sources covered, or N/A> | <API / syslog / agent / N/A> | <URL or N/A> |
| Sumo Logic | <name or "No integration found"> | <data sources covered, or N/A> | <API / syslog / agent / N/A> | <URL or N/A> |

See `references/competitive-siem-coverage.md` for full per-vendor analysis including support tier, version, gaps, and comparison notes.

## 2. Data Collection Method

### 2.1 Recommended method

- **Input type:** <e.g., `cel`, `tcp`/`udp`, `aws-s3`, `filestream`, `azure-eventhub`>
- **Rationale:** <why this method is recommended>

### 2.2 Alternative methods

<List other viable methods with brief pros/cons. If only one method exists, state that.>

| Method | Input type | Pros | Cons |
|--------|-----------|------|------|
| <method 1> | <type> | <pros> | <cons> |
| <method 2> | <type> | <pros> | <cons> |

### 2.3 Vendor-side setup required

<What does the user need to configure on the vendor side to enable data export? API key creation, syslog forwarding rules, S3 bucket policies, etc.>

## 3. Data Source Details

### 3.1 Connection and authentication

<Detailed connection information for the recommended collection method.>

**For API-based:**
- Base URL: `<url>`
- API version: <version>
- Authentication: <see below>
- Rate limits: <requests per minute/hour, burst limits>
- Documentation: <link to auth docs>

**Authentication detail (choose the applicable block):**

*If API key or static Bearer token:*
- Method: <API key header / API key query param / Bearer token>
- Header format: `<e.g., Authorization: Bearer <token>, X-API-Key: <key>>`
- Credential creation steps: <how to obtain the key>
- Required scopes/permissions: <list>
- Token lifetime: <expiry, or "does not expire">

*If OAuth2 (authorization_code or client_credentials):*
- Method: OAuth2
- Grant type: <`authorization_code` / `client_credentials` / both>
- Authorization URL: `<url>` (authorization_code only)
- Token URL: `<url>`
- Refresh URL: `<url>` (often same as token URL)
- Scopes required: <list of scopes needed for data collection>
- All available scopes: <full list if documented>
- Client registration: <how to create a client_id / client_secret — app registration steps, admin console, etc.>
- Token lifetime: <access token expiry, e.g., "30 days", "1 hour">
- Refresh token lifetime: <if documented>
- Token response format: `access_token`, `refresh_token`, `expires_in`, `token_type`
- Additional notes: <PKCE required? Specific redirect URI requirements? VPC/tenant-specific URLs?>

*If interactive-only token generation (manual PAT, browser token page):*
- Method: Manual token generation (interactive only)
- Note: <1-2 sentences describing the manual process. State this is not a standard OAuth2 flow and is not suitable as the primary auth method for an automated integration. If a proper OAuth2 flow also exists, reference it above as the primary method.>

**For syslog-based:**
- Protocol: <TCP/UDP/TLS>
- Default port: <port>
- Syslog format: <RFC 3164/5424>
- Message format inside envelope: <CEF/LEEF/KV/JSON/free text>

**For cloud ingest:**
- Service: <S3/SQS, Event Hub, Pub/Sub, etc.>
- Authentication: <IAM role, connection string, service account, etc.>
- Required permissions: <list>

### 3.2 Endpoints / data paths

<For APIs: list all relevant endpoints with path, HTTP method, and purpose.>
<For logs: list file paths per OS.>
<For cloud: list bucket/topic/hub names and path patterns.>

| Endpoint / Path | Method | Purpose | Event types |
|----------------|--------|---------|-------------|
| <path> | <GET/POST> | <description> | <event types returned> |

### 3.3 Pagination (API only)

- **Mechanism:** <offset, cursor, link-header, keyset, page-number, none>
- **Page size parameter:** `<param_name>` (default: <n>, max: <n>)
- **Next page indicator:** `<field_name>` in response body / `Link` header / etc.
- **Termination condition:** <empty results array, null cursor, count < page_size, etc.>
- **Documentation:** <link>

### 3.4 Time-based filtering (API only)

- **Start time parameter:** `<param_name>`
- **End time parameter:** `<param_name>` (if applicable)
- **Time format:** <ISO 8601, Unix epoch seconds/milliseconds, custom>
- **Timezone:** <UTC, configurable, local>
- **Sort order:** <ascending/descending by default, configurable?>
- **Incremental collection strategy:** <use last event timestamp as next start, cursor includes time state, etc.>

### 3.5 Reference documentation

<Comprehensive list of documentation links used in this research.>

| Title | URL | Relevance |
|-------|-----|-----------|
| <doc title> | <url> | <what it covers> |

## 4. Data Format and Structure

### 4.1 Format overview

- **Wire format:** <JSON, NDJSON, syslog+CEF, syslog+KV, CSV, XML, multiline text>
- **Encoding:** <UTF-8, ASCII, etc.>
- **Compression:** <gzip, none, etc.>
- **Envelope structure:** <e.g., `{"data": [...], "meta": {...}}` or flat array>

### 4.2 Event types

<List all distinct event types/categories the product generates.>

| Event type | Description | Relative volume | Priority |
|-----------|-------------|-----------------|----------|
| <type> | <description> | <high/medium/low> | <high/medium/low for integration> |

### 4.3 Field inventory

<For each event type (or shared across types), list the fields.>

#### Common fields (present in all/most event types)

| Field path | Type | Description | Example value | Always present? |
|-----------|------|-------------|---------------|-----------------|
| <field> | <string/int/float/bool/object/array> | <description> | <example> | <yes/no> |

#### <Event Type 1> specific fields

| Field path | Type | Description | Example value |
|-----------|------|-------------|---------------|
| <field> | <type> | <description> | <example> |

<Repeat for each event type.>

### 4.4 Sample data

<Include or reference representative sample events. If inline, use fenced code blocks. If separate files, reference them.>

See `references/sample-events/` for complete sample data files:
- `<event_type_1>.json` -- <description>
- `<event_type_2>.json` -- <description>
- `<event_type>.log` -- <description>

<If field inventories or schema analyses were too large to include inline, reference the files:>
See `references/field-schema-analysis.md` for the complete field inventory extracted from <source>.
See `temp/<subfolder>/` for the raw source artifacts (cloned repos, downloaded schemas, etc.).

#### Inline sample (most common event type)
```json
<paste one representative event here>
```

### 4.5 Timestamp handling

- **Primary timestamp field:** `<field_name>`
- **Format:** <ISO 8601, Unix epoch seconds, Unix epoch milliseconds, custom format string>
- **Timezone:** <always UTC, local timezone, timezone offset included, configurable>
- **Additional timestamp fields:** <list any secondary timestamps and their meaning>

### 4.6 Special parsing considerations

<Note anything that makes parsing non-trivial: multiline patterns, embedded JSON in string fields, variable schemas, field name inconsistencies across API versions, etc.>

## 5. ECS Mapping Analysis

### 5.1 Categorization per event type

| Event type | event.kind | event.category | event.type | event.outcome |
|-----------|------------|----------------|------------|---------------|
| <type> | <value> | <[values]> | <[values]> | <value or N/A> |

### 5.2 Field mappings

| Source field | ECS field | Notes |
|-------------|-----------|-------|
| <vendor_field> | <ecs_field> | <mapping notes, type conversion needed, etc.> |
| <vendor_field> | <package_name.vendor_field> | custom field, no ECS equivalent |

### 5.3 Related field enrichment

| ECS enrichment field | Source fields |
|---------------------|--------------|
| `related.ip` | <list of fields containing IP addresses> |
| `related.user` | <list of fields containing usernames> |
| `related.hosts` | <list of fields containing hostnames> |
| `related.hash` | <list of fields containing hashes> |

### 5.4 Geo enrichment candidates

<List IP address fields that are candidates for GeoIP enrichment and the appropriate ECS parent (source.geo, destination.geo, etc.)>

## 6. Configuration Plan

> Variables listed below must come from the standard-variable tables in `references/data-collection-methods.md`, plus any documented vendor-specific variables (e.g., tenant ID for a multi-tenant API). **Never list `preserve_duplicate_custom_fields`, `event.ingested` toggles, trailing `event.original` removal flags, or any other deprecated pipeline-behavior variable here**, even if you saw them in legacy integrations under `elastic/integrations`. Pipeline behavior is the pipeline builder's concern, not configuration. The only valid `preserve_*` var is `preserve_original_event` (file/syslog inputs only, never CEL).

### 6.1 Required configuration variables

| Variable | Type | Title | Description | Default | Show user |
|----------|------|-------|-------------|---------|-----------|
| <var_name> | <text/url/password/integer/bool/yaml> | <display title> | <help text> | <default or none> | <yes/no> |

### 6.2 Optional configuration variables

| Variable | Type | Title | Description | Default | Show user |
|----------|------|-------|-------------|---------|-----------|
| <var_name> | <type> | <title> | <description> | <default> | <yes/no> |

### 6.3 Deployment notes

<Any notes about deployment architecture, network requirements, firewall rules, proxy considerations, etc.>

## 7. Recommended Integration Architecture

### 7.1 Package name

`<package_name>` (lowercase, underscores)

### 7.2 Data streams

| Data stream name | Input type | Source | Description |
|-----------------|------------|--------|-------------|
| <stream_name> | <input_type> | <endpoint/file/topic> | <what it collects> |

### 7.3 Architecture rationale

<Why this data stream breakdown? Could be: one stream per API endpoint, one stream per log type, single stream with pipeline routing, etc. Explain the reasoning.>

### 7.4 Estimated complexity

- **Pipeline complexity:** <simple (flat JSON) / moderate (nested, multiple event types) / complex (multiline, variable schemas, routing)>
- **CEL complexity:** <simple (single endpoint, basic pagination) / moderate (multiple endpoints, OAuth, cursor state) / complex (multi-step state machine, multiple auth methods, cursor expiration)>
- **Field count estimate:** <approximate number of fields per stream>

## 8. Open Questions and Gaps

<List anything that could not be determined from research and requires user input, vendor clarification, or hands-on testing.>

| # | Question | Impact | Suggested resolution |
|---|----------|--------|---------------------|
| 1 | <question> | <high/medium/low> | <how to resolve> |

## 9. Source Attribution

<List all sources used in this research with how they were accessed.>

| Source | URL | Access method | Date |
|--------|-----|---------------|------|
| <title> | <url> | <web search / user provided / local file / own knowledge> | <date> |
````

---

## Usage notes

- Sections 1-4 form the factual research foundation.
- Section 5 (ECS mapping) is an analysis layer that requires the ECS reference skill.
- Section 6 (Configuration) bridges research to implementation planning.
- Section 7 (Architecture) is the integration design recommendation.
- Section 8 (Open questions) captures what still needs human judgment.
- Section 9 (Attribution) provides traceability for all claims.

The brief should be thorough enough that someone can pass it directly to `/create-integration` as the primary input.

## Companion artifacts

The research brief is the primary output, but it is supported by additional files in the same directory:

- **`test-api.py`** -- *(API/CEL collection only)* Standalone Python script that exercises the exact API flow proposed for the CEL integration. Tests connectivity, authentication, pagination, and response structure. Run it against the real vendor API and share the resulting archive for development. See `references/test-api-script-spec.md` in the skill directory for the full specification.
- **`references/`** -- Curated research artifacts: detailed field analyses, API spec notes, sample events. These are polished enough for downstream consumers.
- **`temp/`** -- Raw downloaded artifacts: cloned repos, SDK sources, large schema files, analysis scripts. Retained as reference for the human and for reproducibility. Not cleaned up unless disk space is critical.

When the brief references detailed findings that are too large to include inline, it should point to the appropriate file in `references/` or `temp/` with a path and one-line description.
