# CEL config options by beats version

Lookup table for determining when each CEL input config option was introduced. Use this during review to verify that the integration's declared `conditions.kibana.version` is compatible with all config options it uses.

## Top-level config options

| Option | First beats version | Description |
|--------|-------------------|-------------|
| `interval` | v8.6.0 | Polling interval |
| `program` | v8.6.0 | CEL program text |
| `state` | v8.6.0 | Initial state map |
| `regexp` | v8.6.0 | Named regexp patterns for Regexp extension |
| `auth` | v8.6.0 | Authentication configuration |
| `resource` | v8.6.0 | Resource (HTTP client) configuration |
| `redact` | v8.6.0 | Field redaction configuration |
| `max_executions` | v8.9.0 | Maximum evaluation cycles per interval |
| `limits` | v8.16.0 | Rate limit policies |
| `secret_state` | v8.19.14 / v9.2.8 / v9.3.3 / v9.4.0 | Encrypted credential state, map form (beats#49207; preferred over plain `state` keys + redact for new packages whose stack floor meets these versions) |
| `secret_state` fed by Fleet `secret: true` vars | v8.19.16 / v9.3.5 / v9.4.2 — never on 9.2.x | Fleet passes `secret: true` var values as strings; templating them into `secret_state` requires the string-unpack fix (beats#50508) |

## Resource sub-config options

| Option | First beats version | Description |
|--------|-------------------|-------------|
| `resource.url` | v8.6.0 | Target URL |
| `resource.ssl` | v8.6.0 | TLS/SSL settings |
| `resource.timeout` | v8.6.0 | HTTP request timeout |
| `resource.keep_alive` | v8.6.0 | HTTP keep-alive settings |
| `resource.retry` | v8.6.0 | Retry configuration (`.max_attempts`, `.wait_min`, `.wait_max` — the sanctioned retry mechanism per `cel-programs`) |
| `resource.redirect` | v8.6.0 | Redirect policy |
| `resource.rate_limit` | v8.6.0 | Per-resource rate limit (`.limit`, `.burst` — the sanctioned rate-limit mechanism per `cel-programs`) |
| `resource.tracer` | v8.9.0 | Request/response debug tracing (the block itself) |
| `resource.tracer.enabled` | v8.15.0 | The `enabled` field inside the tracer block (older stacks must use the `{{#if enable_request_tracer}}` conditional form instead) |
| `resource.transport_security` | v8.16.0 | Transport security mode |
| `resource.headers` | v8.18.1 (GA) | Static request headers |

## Auth sub-config options

| Option | First beats version | Description |
|--------|-------------------|-------------|
| `auth.basic` | v8.6.0 | Basic auth (username/password) |
| `auth.oauth2` | v8.6.0 | OAuth2 client credentials / token |
| `auth.digest` | v8.16.0 | HTTP digest auth |
| `auth.custom` | v8.16.0 | Custom auth headers via template |

## Cumulative config set

All options above are available as of v9.4.2 (the latest floor is the Fleet `secret: true` unpack for `secret_state`). The minimum version floor for each config combination is determined by the latest "First beats version" among all options used:

- Uses only v8.6.0 options: minimum is v8.6.0
- Uses `max_executions`: minimum is v8.9.0
- Uses `resource.tracer` (the block): minimum is v8.9.0
- Uses `resource.tracer.enabled` (the field): minimum is v8.15.0
- Uses `limits`, `auth.digest`, `auth.custom`, or `resource.transport_security`: minimum is v8.16.0
- Uses `resource.headers`: minimum is v8.18.1
- Uses `secret_state` (map form): minimum is v8.19.14 / v9.2.8 / v9.3.3 / v9.4.0 per release branch
- Templates Fleet `secret: true` vars into `secret_state`: minimum is v8.19.16 / v9.3.5 / v9.4.2 — no 9.2.x release supports this

## How to use

1. List every config option the integration uses (top-level, resource, auth).
2. Look up the "First beats version" for each option in the tables above.
3. Take the maximum (latest) version across all options used.
4. Verify that `conditions.kibana.version` in the root `manifest.yml` allows that beats version or later.
5. If the manifest declares a lower version than required, flag it.

Example: An integration using `auth.digest` and `resource.tracer` requires v8.16.0 (digest is the binding constraint). If the manifest says `^8.9.0`, that is incorrect -- must be `^8.16.0` or later.

Note: options that shipped in patch releases across multiple branches (`secret_state` and its Fleet-secret unpack) have a separate floor per branch. Check the floor within every branch the constraint admits, not just the overall minimum -- and remember no 9.2.x release ever received the `secret: true` unpack fix.
