# API conformance methodology

Procedure for cross-referencing input implementation against vendor API documentation.

## When to run

When the PR modifies input templates (`cel.yml.hbs`, `httpjson.yml.hbs`) AND API documentation is available (linked in PR description, commit messages, manifest variable descriptions, or data stream README).

## What to cross-reference

For each API endpoint the integration calls:

| Aspect | What to verify |
|--------|---------------|
| Endpoint URL | Path matches API docs (correct version, correct resource) |
| HTTP method | GET/POST/PATCH matches what the API expects |
| Query parameters | Required params included, names match docs |
| Request headers | Content-Type, Accept, custom headers match docs |
| Authentication | Method matches API requirements |
| Pagination style | cursor/offset/page/link matches API's documented pagination |
| Response schema | split target matches documented response body structure |
| Rate limit headers | Header names match vendor's rate limit implementation |

## Conformance table output

For each endpoint, produce:

| Endpoint | Aspect | Expected (from docs) | Found (in implementation) | Status |
|----------|--------|---------------------|--------------------------|--------|
| /api/v2/events | Pagination | cursor-based, `nextToken` field | cursor-based, `body.nextToken` | PASS |
| /api/v2/events | Rate limit | `X-RateLimit-Remaining` header | Not handled | FAIL |

## Limitations

- Not applicable when no API docs are available
- Do not speculate about undocumented behavior
- If the API docs are ambiguous, note the ambiguity rather than flagging a finding
