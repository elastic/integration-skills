# Authentication patterns

Header, query-parameter, and signed-query authentication in CEL programs. Credentials live in the `state:` block and are passed into requests as shown below.

## Header auth

Most APIs authenticate via HTTP headers. Pass credentials in the `Header` map of the request:

```cel
request("GET", state.url).with({
  "Header": {
    "Authorization": ["Bearer " + state.api_token],
  }
}).do_request()
```

For optional headers (credentials may or may not be configured), use the optional syntax:

```cel
request("GET", state.url).with({
  "Header": {
    ?"Authorization": has(state.api_token) ?
      optional.of(["Bearer " + state.api_token]) : optional.none(),
  }
}).do_request()
```

## Query parameter auth

Some APIs authenticate via query parameters in the URL rather than headers. Build the full URL using `.format_query()` with credentials as query parameters:

```cel
(state.url + "/current?" + {
    "access_key": [state.api_key],
    "query": [state.location],
}.format_query()).as(target_url,
  request("GET", target_url).do_request().as(resp, ...)
)
```

Multiple query params with different credential keys:

```cel
request(
  "GET",
  state.url.trim_right("/") + "/feed/nod/?" + {
    "api_username": [state.api_username],
    "api_key": [state.api_key],
    "sessionID": [state.session_id],
  }.format_query()
).with({
  "Header": {"Accept": ["application/x-ndjson"]}
}).do_request()
```

When using query param auth, `redact.fields` in the template must still list the secret state keys (e.g., `api_key`) to prevent them from appearing in debug logs.

## Signed query parameter auth

Some APIs require HMAC-signed parameters in the URL. Compute the signature in CEL and include it as a query parameter:

```cel
state.url.trim_right("/") + "/ingestion/rules/save_result_set/?" + {
  "AccessID": [state.access_id],
  "Expires": [string(state.expires)],
  "Signature": [(
    [state.access_id, string(state.expires)].join("\n")
    .hmac("sha1", bytes(state.secret_key))
    .base64()
  )],
}.format_query()
```

## Choosing auth strategy


| Auth location   | When to use                                                  | Template notes                                                       |
| --------------- | ------------------------------------------------------------ | -------------------------------------------------------------------- |
| Header          | API expects `Authorization`, `X-API-Key`, or similar headers | Credentials in `state:` block, passed via `Header` map               |
| Query parameter | API expects credentials in URL (e.g., `?access_key=...`)     | Credentials in `state:` block, appended to URL via `.format_query()` |
| Signed query    | API requires HMAC/signature in URL params                    | Compute signature in CEL using `.hmac()` and `.base64()`             |


## Auth scope at config level

Auth mechanisms at the config level differ in scope — this is critical for choosing request style:

- `**auth.digest**`, `**auth.oauth2**`, `**auth.file**`, `**auth.aws**` — applied to **all requests** including `.do_request()`. No CEL-side auth logic needed.
- `**auth.basic`**, `**auth.token**` — applied only to **direct calls** (`get()`, `post()`, `head()`), **not** `.do_request()`. Prefer direct calls with these. If `.do_request()` is needed (e.g. for custom headers beyond auth), use `basic_authentication(user, pass)` on the request map instead of manual header construction.

**Prefer input-level auth** over in-program token fetching. Use in-program auth only when the API requires non-standard authentication (session cookies, HMAC signing, custom token endpoints not supported by `auth.oauth2`).