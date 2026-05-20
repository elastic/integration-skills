# CEL program taxonomy

Classification system for CEL program patterns. Used by the expression
builder to select the least complex pattern class, and by the reviewer
to select complexity baselines.

## Principle

**Classify at the least complex class that satisfies the API's
requirements.** If cursor_token suffices, do not use state_machine. If
offset works, do not use worklist_expansion. The classification
constrains the generator and gives the reviewer its baseline.

## Classification dimensions

### Pagination

Classes are ordered by increasing complexity. Choose the first class
that fully describes the API's pagination mechanism.

| Class | Description | Python indicators |
|-------|-------------|-------------------|
| `none` | Single request, no pagination | No loop; single GET/POST |
| `cursor_token` | Opaque token in response body drives next request | `next_token = resp["meta"]["next"]`; `while next_token:` |
| `offset` | Numeric offset incremented by page size | `offset += limit`; `while offset < total:` |
| `page_number` | Page index incremented by 1 | `page += 1`; `while page <= max_pages:` |
| `next_url_in_body` | Full URL in response body used as next request URL | `next_url = resp["next_link"]`; `requests.get(next_url)` |
| `link_header` | RFC 5988 `Link` header with `rel="next"` | `resp.headers["Link"]`; parse for `rel="next"` |
| `graphql_relay` | GraphQL `pageInfo.hasNextPage` + `after: endCursor` | `variables["after"] = pageInfo["endCursor"]`; `while hasNextPage:` |
| `worklist_expansion` | List parent → fetch per-item detail | Outer loop lists IDs, inner loop fetches each |
| `async_job_polling` | Submit job → poll status → fetch results | POST to start, GET to poll, GET to download |
| `export_blob` | Request export → download file | POST export, poll until ready, GET blob |
| `multi_entity_orchestration` | Multiple resource types, subscription management, work queues | Multiple endpoint loops with shared state |

### State management

| Class | Description | Python indicators |
|-------|-------------|-------------------|
| `stateless` | No state persisted between polls | No cursor, no bookmark |
| `timestamp_cursor` | High-water mark timestamp advanced each poll | `bookmark = max(timestamps)`; next poll uses `since=bookmark` |
| `time_window` | Bounded from/to window, recomputed each poll | `from = now - interval`; `to = now`; no advancing bookmark |
| `state_machine` | Multiple phases with transitions | `if state == "subscribe": ... elif state == "fetch":` |
| `job_cursor` | Job ID or session token persisted across polls | `job_id = resp["job_id"]`; next poll resumes job |

## Mapping to skill vocabulary

The `cel-programs` skill and the celir taxonomy use different category
names. This table maps between them. The skill's vocabulary is
authoritative for code generation.

| Skill term | Taxonomy class(es) |
|------------|-------------------|
| Offset pagination | `offset`, `page_number` |
| Next-URL pagination | `next_url_in_body`, `link_header` |
| Timestamp cursor | `cursor_token` (when the token is a timestamp), `timestamp_cursor` |
| GraphQL cursor | `graphql_relay` |
| Multi-step state machine | `worklist_expansion`, `async_job_polling`, `export_blob`, `multi_entity_orchestration`, `state_machine` |

## Composite patterns

Real APIs sometimes combine strategies. When this happens, use the
**primary pagination mechanism** for the pagination class and note the
secondary in the classification output. Examples:

- `cursor_token` + `timestamp_cursor`: token drives pagination within
  a poll, timestamp bookmark drives the starting point across polls.
  Pagination class: `cursor_token`. State class: `timestamp_cursor`.
- `link_header` + `timestamp_cursor`: same split. Pagination class:
  `link_header`. State class: `timestamp_cursor`.

The two dimensions (pagination + state management) are independent.
A program can be `graphql_relay` + `time_window` or `offset` +
`timestamp_cursor`.

## How to classify from test-api.py

Read the collection function (`run_collection()` or `collect()`):

1. **Pagination class**: What drives the `while` loop? What value from
   the response determines whether to fetch another page?
   - Opaque string token → `cursor_token`
   - Numeric offset/skip → `offset`
   - Page number → `page_number`
   - Full URL → `next_url_in_body`
   - Link header → `link_header`
   - GraphQL pageInfo → `graphql_relay`
   - No loop → `none`

2. **State management class**: How does the script resume on the next
   run? What does `main()` pass to the collection function?
   - Nothing / fixed lookback → `time_window` or `stateless`
   - Advancing timestamp bookmark → `timestamp_cursor`
   - Job ID from previous run → `job_cursor`
   - Phase/state variable → `state_machine`

3. **Verify least complexity**: Could a simpler class work? If the API
   returns an opaque cursor but you classified as `state_machine`,
   reconsider — `cursor_token` may suffice.

## Classification output format

Return the classification as two fields alongside the `.cel` file:

```
Pagination: cursor_token
State management: timestamp_cursor
```

If the pattern is composite, note the secondary:

```
Pagination: cursor_token (primary) + timestamp_cursor (bookmark across polls)
State management: timestamp_cursor
```
