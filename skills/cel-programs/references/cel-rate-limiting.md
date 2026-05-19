# Rate limiting

## Default: do not implement rate limiting

Most APIs do not require explicit rate limit handling in the CEL program. **By default, do NOT add any `rate_limit()` calls, `rate_limit` state propagation, or 429-handling branches to the CEL program.** These add significant complexity (extra nesting, infinity sanitization, propagation on every branch) for marginal benefit — the input framework already retries on transient failures.

## Config-only rate limiting (use when needed)

When an API has a known fixed rate limit that must be respected, use the **YAML configuration options only** — no CEL program changes required:

```yaml
resource.rate_limit.limit: 10   # max requests per second (sustained rate)
resource.rate_limit.burst: 5    # max burst above the sustained rate
```

These go in `cel.yml.hbs` alongside other `resource.*` settings. The input framework enforces the limit transparently — the CEL program does not need to know about it.

## Config-only retry (use when needed)

When the API requires custom retry behavior beyond the defaults, use the **YAML configuration options only**:

```yaml
resource.retry.max_attempts: 5    # max retries (default: 5)
resource.retry.wait_min: 1s       # min backoff (default: 1s)
resource.retry.wait_max: 60s      # max backoff (default: 60s)
```

These go in `cel.yml.hbs`. The input framework handles retry logic transparently. **Do NOT implement retry logic in the CEL program itself.**

## What NOT to do

- **Do NOT** use the `rate_limit()` CEL function in new integrations. It adds 10+ lines of nesting per HTTP call (infinity sanitization, propagation on every branch, `resp.with()` merging) and is fragile.
- **Do NOT** add `"rate_limit": resp.rate_limit` propagation to every output branch.
- **Do NOT** add special 429 handling branches (`resp.StatusCode == 429`). The standard error event pattern covers all non-200 status codes. The input framework's built-in retry handles 429 responses.
- **Do NOT** implement retry logic in the CEL program. Use `resource.retry.*` configuration.

## When to add config-only rate/retry settings

| Situation | Action |
|-----------|--------|
| API has a documented rate limit (e.g., "10 req/s") | Add `resource.rate_limit.limit` and `resource.rate_limit.burst` to `cel.yml.hbs` |
| API needs custom retry timing | Add `resource.retry.*` settings to `cel.yml.hbs` |
| No documented rate limit | Do not add any rate limit config |
| API returns rate limit headers | Rely on config-only `resource.rate_limit.*`; do NOT parse headers in CEL |
