# Polymorphic patterns

Many capabilities in CEL input programs can be implemented at multiple abstraction levels: raw CEL expressions, mito library functions, or YAML config options. This reference maps each capability to its available implementations and the minimum version required, so builders can choose the right approach for their target version.

## Authentication

| Capability | Pure CEL | mito/lib function | Config option | Minimum version | Preferred approach |
|---|---|---|---|---|---|
| Basic auth | Manual `"Authorization": ["Basic " + bytes(...).base64()]` header | `basic_authentication(user, pass)` returns encoded header value | `auth.basic` (username/password in config) | CEL/lib: all versions; config: v8.6.0 | Config for static credentials; lib function if credentials are dynamic |
| Bearer / Token auth | Manual `"Authorization": ["Bearer " + state.token]` header | None | `auth.custom` (custom header/value pair) | CEL: all versions; config: v8.19.0 / v9.1.0 | Config for static tokens on new integrations; manual header remains common |
| OAuth2 client credentials | Manual `post()` to token endpoint, parse response, attach token | None | `auth.oauth2` (client_id, client_secret, token_url, scopes) | CEL: all versions; config: v8.6.0 | Config unless the integration needs flow control (e.g. custom token caching logic) |
| HMAC-based signing | Vendor-specific CEL: Duo (SHA1), ThreatConnect (SHA256), Akamai (EG1-HMAC-SHA256) | None | None | CEL: all versions | CEL-only. Vendor schemes are too varied for a config shortcut |
| AWS SigV4 | Manual signing via `aws/config` integration pattern | `sign_aws_from_env()` / `sign_aws_from_static()` | `auth.aws` (region, service, access_key_id, secret_access_key) | CEL: all versions; lib functions: v8.19.0 / v9.1.0; config: v9.3.0 | New integrations should use config or lib functions. Manual signing only for pre-v8.19 targets |
| Digest auth | None | None | `auth.digest` (username, password) | Config: v8.12.0 | Config only |
| Okta JWT auth | None | None | `auth.oauth2` with `provider: okta`; `jwk_pem` from v8.13.0; `dpop_key_pem` from v9.3.0 | Config: v8.11.0 | Config only |
| File-based token | None | None | `auth.file` (reads token from file at each evaluation) | Config: v9.3.0 | Config only |

## HTTP headers

Static headers can be declared in config via `resource.headers` (available from v8.18.1). Dynamic or conditional headers must still be set in CEL using `.with({"Header": ...})`.

| Situation | Approach |
|---|---|
| Header value is constant across all requests | `resource.headers` config |
| Header value depends on state, cursor, or response data | CEL `.with({"Header": ...})` |
| Integration must run on versions before v8.18.1 | CEL `.with({"Header": ...})` |

Most existing integrations predate `resource.headers` and set everything in CEL. New integrations targeting v8.18.1+ should put static headers in config.

## Rate limiting

| Mechanism | How it works | Minimum version | Notes |
|---|---|---|---|
| Static token bucket | `resource.rate_limit.limit` + `resource.rate_limit.burst` in YAML | v8.6.0 | Fixed rate; no CEL needed |
| Response-header rate limiting (return-to-Go) | `rate_limit()` via `Limit()` overload. Return map placed in `state.rate_limit` | v8.6.0 | Rate limit changes take effect on the **next** evaluation cycle only |
| Response-header rate limiting (immediate apply) | `rate_limit()` via `LimitWithApply()` overload. Apply callback fires during evaluation | v9.3.0 | Changes take effect between requests **within the same evaluation**. Not back-ported to 8.19 |
| 429 retry | `resource.retry` handles HTTP 429 automatically | v8.6.0 | Some integrations also log 429 via `debug()` |

Named policies for `rate_limit()`: `"okta"` (Okta rate limit headers) and `"draft"` (IETF rate limit draft headers).

## Request construction

| Pattern | When to use |
|---|---|
| `request("GET", url).with({...}).do_request()` | Need custom headers, body, or other request options. Dominates in practice |
| `get(url)` / `get_request(url)` | Simple GET with no custom headers |
| `post(url, content_type, body)` | Simple POST with fixed content type |
| `post_request(url, content_type, body).with({...})` | POST that also needs custom headers |
| `head(url)` | Pre-flight checks (e.g. checking `Content-Length` before download) |

### URL construction

| Approach | Pros | Cons |
|---|---|---|
| String concatenation (`state.url + "?key=" + state.val`) | Simple, readable for trivial cases | Breaks on values that need URL encoding |
| `parse_url()` + `format_url()` / `parse_query()` + `format_query()` | Correct encoding guaranteed | More verbose |

Prefer `parse_query()` / `format_query()` when query parameter values may contain special characters.

## Data encoding

| Function | Purpose | Minimum version |
|---|---|---|
| `.base64()` | Encode bytes/string to base64 | All versions |
| `.base64_decode()` | Decode base64 (with padding) to bytes | All versions |
| `.base64_raw_decode()` | Decode base64 without padding to bytes | All versions |
| `encode_json(value)` | Serialize a CEL value to a JSON string | All versions |
| `decode_json(string)` | Parse a JSON string into a CEL value | All versions |
| `decode_json_stream(bytes)` | Parse newline-delimited JSON | All versions |
| `decode_xml(bytes)` | Parse XML; optional XSD hints via `xsd:` config | XML: all versions; `xsd:` config: v8.9.0 |
| `sprintf(format, [args])` | Printf-style string formatting | v8.18.0 / v9.0.0 (mito v1.16.0) |

When an API returns base64 without padding, use `.trim_right("=").base64_raw_decode()` instead of `.base64_decode()`.

The `decode_json_string_numbers` config option (v8.19.0 / v9.1.0, mito v1.22.0) preserves numeric precision by decoding JSON numbers as strings rather than floats.

Prefer `sprintf` over string concatenation for readability when targeting v8.18.0+.

## Environment and secrets

| Feature | Description | Minimum version |
|---|---|---|
| `allowed_environment` | Whitelists environment variable names accessible via the `env` global in CEL | v8.16.0 |
| `secret_state` | Unconditional redaction of named state keys in logs and diagnostics | v9.4.0 (unreleased) |

Before `secret_state`, secrets stored in `state` require explicit `redact` config entries for log redaction.

## Debugging aids

| Feature | Description | Minimum version |
|---|---|---|
| `debug(tag, value)` | Logs `tag: value` to the debug log and returns `value` unchanged. Can be inserted anywhere in an expression chain | v8.11.0 (mito v1.6.0) |
| `resource.tracer` | Enables HTTP request/response tracing in config | v8.6.0 |
| `tracer.enabled` | Toggle to control whether the tracer is active | v8.15.0 |
| `failure_dump` | Dumps full program state on failure for post-mortem analysis | v8.18.0 / v9.0.0 |
| `record_coverage` | Records which branches of the CEL program were evaluated | v8.18.0 / v9.0.0 |

## Patterns worth noting

1. **Auth header duplication.** Some integrations set the same static header in both `resource.headers` and CEL `.with()`. This is harmless but redundant. New code should pick one.

2. **HMAC signing cannot move to config.** Vendor-specific HMAC schemes (Duo SHA1, ThreatConnect SHA256, Akamai EG1) are too varied. These remain pure CEL.

3. **AWS SigV4 has three abstraction levels.** Manual signing, library functions (`sign_aws_from_env()` / `sign_aws_from_static()`), and config (`auth.aws`). New code should use the highest abstraction available for the target version.

4. **`request().with().do_request()` dominates.** Convenience functions like `get()` and `post()` exist but most integrations need custom headers, making the full request builder the standard pattern.

5. **`sprintf` adoption is slow.** Available since v8.18.0 / v9.0.0 but many integrations still use string concatenation. Prefer `sprintf` in new code for readability.
