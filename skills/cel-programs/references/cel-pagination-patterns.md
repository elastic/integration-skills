# CEL program structure patterns

Full working patterns for common API collection styles. Use the matching pattern for your API; see the main `cel-programs` skill for state rules and error handling.

## Cursor placement: what survives a restart

The CEL input writes `state.cursor` to the registry after each evaluation that publishes events. Nothing else on `state` is written. Any key that encodes *where the program is in a walk* must therefore live under `cursor`:

| Belongs under `cursor` | Can stay on `state` |
|---|---|
| next-page token, offset, page number, next URL | auth tokens and their expiry |
| worklist of IDs still to visit | derived config (`batch_size`, URLs) |
| "fetch more after this page" flags | `rate_limit` output |
| high-water timestamp | |

```cel
// WRONG — page token and worklist are on state; a restart drops them and the walk restarts
{
  "worklist": body,
  "next_page": {"token": body.?pagination.nextCursor},
  "want_more": body.?pagination.nextCursor.orValue(null) != null,
}

// CORRECT — mid-walk position is under cursor
{
  "cursor": {
    "worklist": body,
    "next_page": {"token": body.?pagination.nextCursor},
    "fetch_more": body.?pagination.nextCursor.orValue(null) != null,
  },
  "want_more": body.?pagination.nextCursor.orValue(null) != null,
}
```

Read positions back with optional access (`state.?cursor.next_page.token`) so a fresh install works. When a walk completes, clear the transient sub-object (`"cursor": {"last_timestamp": ...}` with no `next_page`) rather than leaving stale tokens; `with()` is a shallow merge, so omitting the sub-object removes it.

### Expiring tokens

Many continuation tokens are only valid for minutes to hours (Graph `@odata.nextLink`/`$skiptoken`, Okta `after`, Google `nextPageToken`, scroll IDs, SentinelOne `cursor`). Persisting one under `cursor` is still right: most restarts (agent upgrade, policy change, reboot) take seconds, and resuming beats re-walking. But a token restored after a long outage will be rejected, so the token must not be the only thing the program can resume from.

1. **Keep a non-expiring anchor beside the token.** The high-water timestamp, the last ID seen, or the worklist of IDs still to visit. The token is a shortcut into the walk; the anchor is where the walk restarts if the shortcut is gone.
2. **Treat an invalid-token response as a signal, not an error.** Branch on the status or body the API uses for it (`400`/`410`, `InvalidPageToken`, `Scroll context missing`, ...), clear the token, and re-list from the anchor. Returning the single-object error shape here is wrong: it drops the whole cursor, anchor included, and the next run starts from the initial interval.
3. **Expect some overlap.** Re-listing from the anchor re-fetches anything between the anchor and where the token pointed. `fingerprint → _id` in the pipeline absorbs it.

```cel
// Invalid-token branch: drop the token, keep the anchor, let the next evaluation re-list.
resp.StatusCode == 400 && string(resp.Body).contains("invalid cursor") ?
  {
    "events": [{"message": "retry"}],   // placeholder so the cursor change is persisted
    "cursor": {"last_timestamp": state.cursor.last_timestamp},
    "want_more": true,
  }
:
  ...
```

Worklists are not opaque, so they do not expire, but entries can go stale (the item was deleted). The usual 404-on-item handling covers that; drop the item and continue.

On agentless deployments the input state is kept in an Elasticsearch-backed store shared per component, so a token one instance stored may be replayed by another after a longer gap than a local restart would produce. The anchor-plus-clear pattern is what keeps that safe.

Reference fix: elastic/integrations#20022 (sentinel_one `threat_event` and `application_risk`).

## Full re-list streams (no server-side "updated since")

Some APIs expose no incremental filter: every call returns the whole collection. Inventories, posture assessments, and many threat intelligence feeds work this way. Each interval then appends a full copy of the collection.

Rules for these streams:

1. **Bound growth in the pipeline.** Add a `fingerprint` processor over the record's own identifier plus a change marker (`id` + `updatedAt`, or `id` + `status`), `target_field: _id`. Repeated copies of an unchanged record are rejected within a backing index instead of accumulating.
2. **Bound growth in storage, on both deployment types.** Ship an ILM policy (`elasticsearch/ilm/default_policy.json`, attached with `ilm_policy:` in the data stream manifest) for stateful stacks **and** a `lifecycle.yml` for Serverless. Fleet applies `lifecycle.yml` only where ILM is unavailable, so one without the other leaves a deployment type unbounded. Repo conventions: 30d for inventories, 5d for feeds; make the ILM delete age and `data_retention` agree. Fingerprinting only dedups within one backing index; rollover starts a new one.
3. **Document it.** The README must state the retention, the reason, which mechanism applies on stateful versus Serverless, and how to override each.
4. **Still use `cursor` for position.** A full re-list that pages through 50k records is still a walk; its page token belongs under `cursor` so a restart resumes instead of starting over.
5. **Add a watermark if the API has one.** If the API accepts a sort and a lower bound on a change timestamp, store the high-water mark in `cursor.last_timestamp`, seed it from an `initial_interval` variable on first run, and drop the polling interval. A long interval is not a substitute: with no watermark, a 24h interval still re-ingests everything daily.

Reference fix: elastic/integrations#20211 (sentinel_one `threat_event` 2.11.1: `updatedAt__gte` watermark, interval 24h → 5m, fingerprint dedup).

## Simple single request

No pagination. Fetch all data in one request.

```cel
state.with(
  request("GET", state.url).with({
    "Header": {"Content-Type": ["application/json"]}
  }).do_request().as(resp,
    resp.StatusCode == 200 ?
      resp.Body.decode_json().as(body, {
        "events": body.items.map(e, {"message": e.encode_json()}),
      })
    :
      { "events": {"error": {...}}, "want_more": false }
  )
)
```

## Offset pagination

Uses `search_from` / `search_to` with a total count.

Key logic:
```cel
int(state.?search_from.orValue(0)).as(offset,
  // POST with offset in body
  // want_more: offset + size(results) < total_count
  // cursor: { search_from: offset + size(results) }
)
```

## Timestamp cursor pagination

Queries for records since a timestamp, advancing the cursor forward.

Key logic:
```cel
(state.?cursor.last_timestamp.orValue(
  string(now - duration(state.initial_interval))
)).as(since,
  // Request with time range: "since to now"
  // cursor: { last_timestamp: max(event timestamps) + 1s }
  // want_more: size(results) > 0
)
```

## Link header pagination

Extracts next-page URL from `Link` response header using regex.

Requires `regexp` config in the template:
```yaml
regexp:
  next_link: '<([^,]*)>;rel="next"'
```

Key logic:
```cel
get_request(
  state.?cursor.next_page.orValue(state.url + "?" + params.format_query())
).do_request().as(resp,
  // Extract next URL: resp headers matched against regexp
  // cursor: { next_page: extracted_url }
  // want_more: next_page found && results non-empty
)
```

## Next-URL pagination

API returns a relative or absolute URL for the next page in the response body.

Key logic:
```cel
get_request(
  has(state.next_url) && state.next_url != "" ?
    state.next_url
  :
    state.url + "?" + params.format_query()
).do_request().as(resp,
  resp.Body.decode_json().as(body, {
    // next_url: build from body.next if present
    // want_more: has(body.next)
  })
)
```

## GraphQL cursor pagination

Uses `hasNextPage` and `endCursor` from GraphQL `pageInfo`.

Key logic:
```cel
post_request(state.url + "/graphql", "application/json",
  {"query": state.query, "variables": {
    "first": state.batch_size,
    "after": state.?cursor.end_cursor.orValue(null),
  }}.encode_json()
).do_request().as(resp,
  // cursor: { end_cursor: body.data.items.pageInfo.endCursor }
  // want_more: body.data.items.pageInfo.hasNextPage
)
```

## Pagination continuation guardrail

**Never gate `want_more` on the size of the event list.** Drive `want_more` from the API's pagination signal (next-page cursor, `hasNextPage`, etc.), not from whether events were returned on the current page. Some pages may legitimately return zero events (e.g., sparse data, time windows with no activity). Tying `want_more` to event count stalls pagination silently.

A common mistake:
```cel
// WRONG — stalls pagination when a page returns no events
items.as(events, {
  "events": events.map(e, {"message": e.encode_json()}),
  "want_more": size(events) > 0,   // false when page has no events
  "cursor": {"next": next_val},
})
```

The correct pattern: drive `want_more` from the cursor/token.
```cel
// CORRECT — pagination continues as long as the API signals more pages
items.as(events, {
  "events": events.map(e, {"message": e.encode_json()}),
  "want_more": next_val != "",     // true as long as a next page exists
  "cursor": {"next": next_val},
})
```

**Rules:**
- If the API returned a next-page cursor/token, more pages exist — set `want_more: true` unconditionally.
- An empty `events` array is safe; the input will re-evaluate immediately and fetch the next page.
- Only set `want_more: false` when the API signals the last page (no next cursor, `hasNextPage == false`, etc.).
- This applies to all cursor-based patterns: next-token, next-URL, Link header, GraphQL cursor, and offset when results may be sparse.

## Page-number pagination with time-window constraints

Some APIs combine page-number pagination (incrementing `page` query parameter) with a mandatory time-window constraint — each request must include both `startTime` and `endTime`, and the allowed window is capped (commonly 30 days). The CEL program fetches all pages within the current window, then advances to the next window on the following evaluation cycle.

**Recognized pattern:** page-number pagination + bounded time window.

```cel
// Compute window bounds and current page before state.with() to keep HTTP handling at 2 levels.
state.?cursor.poll_start.orValue(
  string(now - duration(state.initial_interval))
).as(windowStart,
  (timestamp(windowStart) + duration("720h")).as(cap,
    // Cap the window at max_window_size (e.g. 30 days) relative to windowStart
    cap < now ? cap : now
  ).as(windowEnd,
    int(state.?cursor.page.orValue(1)).as(page,
      state.with(
        request("GET", state.url.trim_right("/") + "?" + {
          "startTime": [string(windowStart)],
          "endTime":   [string(windowEnd)],
          "page":      [string(page)],
          "per_page":  [string(int(state.batch_size))],
        }.format_query()).with({
          "Header": {
            "Authorization": ["Bearer " + state.api_key],
          }
        }).do_request().as(resp,
          resp.StatusCode == 200 ?
            resp.Body.decode_json().as(body,
              body.pagination.hasNextPage ?
                // More pages in this window — advance page, keep window
                {
                  "events":    body.items.map(e, {"message": e.encode_json()}),
                  "cursor":    {"poll_start": string(windowStart), "page": page + 1},
                  "want_more": true,
                }
              :
                // Last page — advance window start, reset page
                {
                  "events":    body.items.map(e, {"message": e.encode_json()}),
                  "cursor":    {"poll_start": string(windowEnd), "page": 1},
                  "want_more": false,
                }
            )
          :
            {
              "events":    {"error": {"code": string(resp.StatusCode), "id": string(resp.Status), "message": "GET: " + string(resp.Body)}},
              "want_more": false,
            }
        )
      )
    )
  )
)
```

### Key decisions for this pattern

| Decision | Rationale |
|----------|-----------|
| `initial_interval` ≤ 30 days (`720h`) | Prevents the first window from exceeding the API's maximum allowed range. Set the manifest default to `720h` or less. |
| `windowEndCandidate < now ? ... : now` | Clamps the window end to the current time so the final window does not overshoot. |
| Cursor stores `poll_start` + `page` | Allows resuming mid-window across evaluation cycles. |
| `want_more: true` when `hasNextPage` | Drives pagination from the API signal, not from event count (see Pagination continuation guardrail). |
| `want_more: false` at window end | CEL input re-schedules the next evaluation after `interval`, which advances to the next window. |

### Accepted limitation — chunking across very long lookback

When `initial_interval` covers a range longer than one window (e.g. `8760h` / 1 year), the program advances one window per evaluation cycle. Each cycle covers at most `max_window_size` worth of history. This is an accepted limitation of the page-number + time-window pattern — time-window chunking within a single evaluation cycle is a future enhancement. For now, keep `initial_interval` ≤ `max_window_size` in the manifest default to avoid multi-cycle catch-up on first run.

## Multi-step / subscription flow

APIs that require initialization before polling (cursor creation, subscription registration, token exchange) use a multi-step pattern. The key design principle is **do not duplicate the fetch logic** — if both the init and steady-state branches need the same request/response handling, consolidate it using Technique 6 from `cel-code-style.md` (either variant).

### Init-then-steady-state (preferred for simple init)

When the init request returns a cursor or token that the steady-state path already uses, split the work across evaluations:

```cel
state.?cursor.realtime.as(persisted,
  persisted.hasValue() ?
    // Steady state: fetch events using the persisted cursor.
    state.with(
      request("GET", state.url.trim_right("/") + "/events?" + {
        "cursor": [persisted.orValue("")],
      }.format_query()).with({
        "Header": {"Accept": ["application/json"]},
      }).do_request().as(resp,
        resp.StatusCode == 200 ?
          resp.Body.decode_json().as(body,
            body.?events.orValue([]).map(e, {"message": e.encode_json()}).as(events, {
              "events": (size(events) > 0) ? events : [{"retry": true}],
              "cursor": {
                ?"realtime": body.?next_cursor.optMap(v, string(v)),
              },
              "want_more": body.?more_to_read.orValue(false),
            })
          )
        :
          {
            "events": {
              "error": {
                "code": string(resp.StatusCode),
                "id": string(resp.Status),
                "message": "GET /events: " + (
                  size(resp.Body) != 0 ? string(resp.Body) : string(resp.Status)
                ),
              },
            },
            "want_more": false,
          }
      )
    )
  :
    // Init: create a cursor, persist it, re-evaluate immediately into steady state.
    state.with(
      request("GET", state.url.trim_right("/") + "/cursor/create?" + {
        "company_id": [state.company_id],
      }.format_query()).with({
        "Header": {"Accept": ["application/json"]},
      }).do_request().as(resp,
        resp.StatusCode == 200 ?
          (string(resp.Body.decode_json().?next_cursor.orValue("")) != "") ?
            {
              "events": [{"retry": true}],
              "cursor": {
                ?"realtime": resp.Body.decode_json().?next_cursor.optMap(v, string(v)),
              },
              "want_more": true,
            }
          :
            {
              "events": {
                "error": {
                  "code": "cursor_create",
                  "id": "empty_cursor",
                  "message": "GET /cursor/create: empty next_cursor in response",
                },
              },
              "want_more": false,
            }
        :
          {
            "events": {
              "error": {
                "code": string(resp.StatusCode),
                "id": string(resp.Status),
                "message": "GET /cursor/create: " + (
                  size(resp.Body) != 0 ? string(resp.Body) : string(resp.Status)
                ),
              },
            },
            "want_more": false,
          }
      )
    )
)
```

Key points:
- The init branch makes **one** request, stores the cursor via a placeholder event (`[{"retry": true}]`), and sets `want_more: true`.
- The placeholder must be an **array** event (not a single-object error) so the cursor is persisted.
- The immediate re-evaluation enters the steady-state branch — fetch logic exists in one place only.
- See Technique 6 in `cel-code-style.md` for the structural rationale and Variant B (intermediate result map) as an alternative.

### Complex state machine (subscribe → list → fetch)

When the flow has more than two phases (e.g. subscribe, then list content IDs, then fetch each item), use multiple ternary branches based on cursor flags:

Pattern:
- Multiple ternary branches based on state flags (`subscribed`, `todo_content`, `todo_links`, `todo_types`)
- Each branch makes a different API call and updates its portion of state
- `want_more: true` while work remains in any queue
