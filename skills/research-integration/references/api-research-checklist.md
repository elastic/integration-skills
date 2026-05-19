# API Research Checklist

Use this checklist when the product exposes a REST/HTTP API for data collection. This is the most detail-intensive research track because CEL programs need precise knowledge of API behavior.

## Discovery phase

- [ ] Find the official API reference documentation portal
- [ ] Identify the API version (latest stable) and versioning strategy (URL path, header, query param)
- [ ] Locate any OpenAPI/Swagger spec if published (often at `/api-docs`, `/swagger.json`, or developer portal)
- [ ] Check for a developer/partner portal separate from end-user docs
- [ ] Look for API changelogs or deprecation notices
- [ ] Check if the vendor publishes an **SDK, client library, or schema repo** on GitHub/GitLab. If found, clone it into `temp/` -- SDK model definitions and type stubs often document the API more completely than the reference docs
- [ ] If an OpenAPI/Swagger spec is available, download it into `temp/` and use Python to extract endpoints, schemas, and parameter definitions programmatically

## Authentication

- [ ] **Method identified:** Bearer token / API key header / API key query param / OAuth2 client credentials / OAuth2 authorization code / Basic auth / HMAC signature / custom
- [ ] **Credential creation:** step-by-step instructions or link to guide
- [ ] **Required permissions/scopes:** minimum set needed for the data we want to collect
- [ ] **Token lifetime:** does the token expire? How to refresh?
- [ ] **Header format:** exact header name and value format (e.g., `Authorization: Bearer <token>`, `X-API-Key: <key>`)
- [ ] **Multi-tenant:** does the API URL or auth vary per tenant/region?

### OAuth2 investigation (critical — read carefully)

If the API uses OAuth2 in any form, **you must investigate all available grant types thoroughly**. Many APIs document multiple OAuth2 flows; it is critical to identify the correct one for a non-interactive integration.

**Elastic integration OAuth2 support:** The CEL input natively supports OAuth2 via the `auth.oauth2` configuration block, including `authorization_code` with PKCE, `client_credentials`, and token refresh. Elastic integrations can handle the full `authorization_code` flow (redirecting users to the authorization URL during setup, exchanging codes for tokens, and automatically refreshing tokens). This is the standard flow for integrations — do NOT assume it requires manual token management.

**Investigation checklist:**

- [ ] **Identify ALL OAuth2 grant types the API supports.** Look for:
  - `client_credentials` — machine-to-machine, no user interaction needed. Preferred when available.
  - `authorization_code` — standard OAuth2 flow with authorization URL, token URL, scopes, client_id/client_secret. Fully supported by Elastic integrations.
  - `refresh_token` — renewing tokens without re-authorization. Usually paired with authorization_code.
  - Interactive-only / manual token generation — e.g., "generate a personal access token in the admin console" or "visit this URL to get a token." These are NOT OAuth2 flows even if the resulting token is used as a Bearer token.

- [ ] **For `authorization_code` flow, capture ALL of these:**
  - Authorization URL (where the user is redirected to grant access)
  - Token URL (where the authorization code is exchanged for access/refresh tokens)
  - Refresh URL (often the same as token URL)
  - Available scopes and which are required for our use case
  - Whether a client_id and client_secret are required (and how to create them)
  - Token lifetime and refresh token lifetime
  - Token response format (`access_token`, `refresh_token`, `expires_in`, `token_type`)

- [ ] **For `client_credentials` flow, capture:**
  - Token URL
  - Required scopes
  - How to create client_id / client_secret (app registration, API console, etc.)
  - Token lifetime

- [ ] **Classification — determine which flow category applies:**

  | Flow type | What it means | How to handle in research output |
  |-----------|---------------|----------------------------------|
  | `client_credentials` | Machine-to-machine. Best for integrations. | Document fully as primary auth method. |
  | `authorization_code` (standard, with token/refresh URLs) | User authorizes once during setup, then tokens auto-refresh. Supported by Elastic. | Document fully as primary auth method. Include all URLs, scopes, client registration steps. |
  | `authorization_code` + `refresh_token` | Same as above, with explicit refresh. | Document fully. Note refresh URL and token lifetime. |
  | Interactive-only (manual PAT generation, browser-only token page) | Requires human in the loop every time the token expires. NOT a standard OAuth2 flow. | Note briefly — 1-2 sentences max. State that this is interactive-only and not suitable as the primary auth method for an integration. If this is the ONLY auth method, flag it as a gap in Open Questions. |

- [ ] **Common pitfall — do NOT conflate these:**
  - A vendor page where you "click to generate a token" is NOT an OAuth2 authorization_code flow. That is manual token generation.
  - An OAuth2 `authorization_code` flow with proper authorization URL, token URL, and refresh mechanism IS supported by Elastic integrations, even though the initial authorization involves a browser redirect.
  - If the docs mention both (e.g., "generate a personal access token" AND "use OAuth2 authorization code flow"), document the authorization_code flow as the primary method and mention the PAT as an alternative for testing/development.

- [ ] **If only interactive/manual token generation is found:** Investigate further. Check the API's security scheme definitions (OpenAPI `securitySchemes`), look for separate OAuth2 documentation pages, check developer portal app registration flows, and search for client_credentials or authorization_code references. Many vendors document OAuth2 flows on separate pages from their main API reference.

## Endpoints

For each relevant endpoint, capture:

- [ ] **Full path:** e.g., `/api/v2/events`
- [ ] **HTTP method:** GET / POST
- [ ] **Purpose:** what data does it return
- [ ] **Required parameters:** names, types, constraints
- [ ] **Optional parameters:** filtering, sorting, field selection
- [ ] **Time range parameters:**
  - Parameter names for start/end time
  - Accepted time format (ISO 8601, Unix seconds, Unix ms, custom)
  - Whether the range is inclusive or exclusive on each end
  - Maximum time range per request (if limited)
  - Default sort order (ascending/descending by time)
- [ ] **Response structure:**
  - Content-Type (application/json, application/x-ndjson, etc.)
  - Top-level envelope: `{ "data": [...], "pagination": {...} }` vs flat array vs other
  - Event/record array field path
  - Metadata fields in response (total count, request ID, etc.)
- [ ] **Sample request** (curl or equivalent)
- [ ] **Sample response** (full JSON with all fields visible)
- [ ] **Error responses:** status codes and body format for common errors (400, 401, 403, 404, 429, 500)

## Pagination

- [ ] **Mechanism identified:** offset + limit / cursor token / link header / page number / keyset (sort field + last value) / none
- [ ] **Request parameters:**
  - Page size parameter name and max value
  - Offset/cursor/page parameter name
  - How to request the first page (no parameter, 0, 1, empty cursor?)
- [ ] **Response indicators:**
  - Next page token/cursor field path in response body
  - Total count field (if available)
  - Has-more-pages indicator field
  - Link header format (if used)
- [ ] **Termination condition:** how to detect the last page
  - Empty data array
  - Null/missing next cursor
  - Data array length < page size
  - Offset >= total_count
  - No Link: rel="next" header
- [ ] **Ordering guarantees:** does pagination guarantee no duplicates or missed records when data is changing?
- [ ] **Sample paginated request sequence** (first request, second request with cursor/offset)

## Rate limiting

- [ ] **Documented limits:** requests per minute/hour/day, concurrent connections
- [ ] **Rate limit headers:** which response headers indicate remaining quota
  - `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`, or vendor-specific
- [ ] **429 response body format:** does it include retry-after information in the body?
- [ ] **Burst vs sustained limits:** different limits for different time windows?
- [ ] **Per-endpoint limits:** do different endpoints have different limits?
- [ ] **Recommended polling interval** based on limits and data freshness requirements

## Data content

- [ ] **Event types returned:** list of all event kinds/categories/types and how to distinguish them
- [ ] **Field inventory:** complete list of fields with names, types, descriptions, and example values
- [ ] **Nested objects:** identify deeply nested structures (e.g., `alert.details.indicators[].network.source.ip`)
- [ ] **Dynamic fields:** any fields whose names change based on content (key-value maps, custom attributes)
- [ ] **Enumeration values:** for status, severity, category, action, type fields -- document all possible values
- [ ] **Null handling:** does the API omit null fields or include them explicitly?
- [ ] **Timestamp format:** ISO 8601 with timezone, Unix epoch (seconds or ms), or custom
- [ ] **Large response considerations:** maximum response size, truncation behavior
- [ ] **Large schema handling:** if the response schema has hundreds of fields (common with security products), download the schema source (OpenAPI spec, SDK models, JSON schema) into `temp/` and use Python to extract the field inventory. Write results to `references/field-schema-analysis.md`

## Incremental collection strategy

- [ ] **Time-based filtering:** can we query events since a specific timestamp?
- [ ] **Cursor/bookmark:** does the API provide a cursor that tracks position across polls?
- [ ] **Created vs modified:** does time filtering use event creation time or last-modified time?
- [ ] **Overlap strategy:** how to handle events that arrive between polls (use last event timestamp minus small buffer?)
- [ ] **Deduplication:** does the API provide unique event IDs we can use for deduplication?
- [ ] **Backfill:** can we query historical data, and how far back?

## Error handling

- [ ] **Retry-safe methods:** are all collection endpoints idempotent?
- [ ] **Transient errors:** which HTTP status codes are retryable (429, 500, 502, 503, 504)?
- [ ] **Permanent errors:** which require user intervention (401 expired creds, 403 insufficient permissions)?
- [ ] **Error response format:** JSON body structure for errors (field names for error code, message, details)
- [ ] **Maintenance windows:** does the vendor have scheduled downtime that affects the API?

## Integration-relevant summary

After gathering the above, summarize the API behavior as a factual spec for the integration builder. **Do NOT prescribe how to implement the CEL program** — the CEL builder agent has its own skills and patterns for that. Focus on documenting the API contract:

- [ ] **Pagination summary:** what mechanism the API uses (cursor, offset, keyset, etc.), what response field indicates more pages, and what the termination condition is
- [ ] **State between polls:** what value(s) must be persisted between polling cycles (latest cursor, timestamp bookmark, offset) to avoid re-collecting data
- [ ] **Authentication classification:** which auth approach the API requires:
  - API key / static Bearer token → note header format
  - OAuth2 client_credentials → note token URL, scopes, client registration steps
  - OAuth2 authorization_code → note authorization URL, token URL, scopes, refresh mechanism
  - Interactive-only token generation → flag as a gap; note this is not suitable for automated collection
- [ ] **Estimated request volume:** approximate requests per poll cycle based on data volume and page size
- [ ] **Rate limits:** documented limits (requests/min, requests/hour) and any rate limit response headers the API returns. Note these as factual API constraints only — do NOT recommend specific rate limit implementation patterns for the CEL program.
