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

## Resource sub-config options

| Option | First beats version | Description |
|--------|-------------------|-------------|
| `resource.url` | v8.6.0 | Target URL |
| `resource.ssl` | v8.6.0 | TLS/SSL settings |
| `resource.timeout` | v8.6.0 | HTTP request timeout |
| `resource.keep_alive` | v8.6.0 | HTTP keep-alive settings |
| `resource.retry` | v8.6.0 | Retry configuration |
| `resource.redirect` | v8.6.0 | Redirect policy |
| `resource.rate_limit` | v8.6.0 | Per-resource rate limit |
| `resource.tracer` | v8.9.0 | Request/response debug tracing |
| `resource.transport_security` | v8.16.0 | Transport security mode |

## Auth sub-config options

| Option | First beats version | Description |
|--------|-------------------|-------------|
| `auth.basic` | v8.6.0 | Basic auth (username/password) |
| `auth.oauth2` | v8.6.0 | OAuth2 client credentials / token |
| `auth.digest` | v8.16.0 | HTTP digest auth |
| `auth.custom` | v8.16.0 | Custom auth headers via template |

## Cumulative config set as of v9.3.0

All options above are available as of v9.3.0. The minimum version floor for each config combination is determined by the latest "First beats version" among all options used:

- Uses only v8.6.0 options: minimum is v8.6.0
- Uses `max_executions`: minimum is v8.9.0
- Uses `resource.tracer`: minimum is v8.9.0
- Uses `limits`, `auth.digest`, `auth.custom`, or `resource.transport_security`: minimum is v8.16.0

## How to use

1. List every config option the integration uses (top-level, resource, auth).
2. Look up the "First beats version" for each option in the tables above.
3. Take the maximum (latest) version across all options used.
4. Verify that `conditions.kibana.version` in the root `manifest.yml` allows that beats version or later.
5. If the manifest declares a lower version than required, flag it.

Example: An integration using `auth.digest` and `resource.tracer` requires v8.16.0 (digest is the binding constraint). If the manifest says `^8.9.0`, that is incorrect -- must be `^8.16.0` or later.
