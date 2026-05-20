# API Test Script Specification

This reference defines the structure, behaviour, and requirements for the `test-api.py` script generated during the research phase. The script exercises the exact API flow proposed for the CEL integration so a human can validate connectivity, authentication, pagination, and response structure before any Elastic Agent work begins.

**Applicability:** Generate this script only when the recommended collection method is API-based (CEL input type). It does not apply to syslog, file-based, or cloud-ingest collection methods.

## File location

```
research_results/<product_slug>/test-api.py
```

Same directory as `research-brief.md` — the root of the research output folder.

## General rules

- **Standard library only.** The script must use only Python 3 standard library modules (`urllib.request`, `json`, `logging`, `argparse`, `ssl`, `os`, `tarfile`, etc.). No `requests`, `httpx`, or other third-party packages. This ensures the script runs on any system with Python 3 installed.
- **Mirror the proposed CEL flow.** The script's request sequence, pagination logic, cursor handling, and termination conditions must match what was proposed in the research brief for the CEL program. Annotate key sections with comments referencing the corresponding CEL logic (e.g., "Same branching as the CEL program's first-request vs continuation-request logic").
- **TLS verification disabled.** Always disable TLS certificate verification (`ssl._create_unverified_context()` or equivalent). This is a testing tool, not a production client — it may be pointed at mock servers, proxies, or dev environments with self-signed certificates.
- **Redact secrets in all output.** Credentials must never appear in the log file, trace file, stdout, or archive. Implement redaction helpers that scrub Authorization headers, API keys, tokens, and any other sensitive values before writing them anywhere.

## Script header (module docstring)

The script must begin with a comprehensive docstring that serves as standalone documentation:

```
#!/usr/bin/env python3
"""
<Product Name> — API Connectivity & Flow Test
==============================================

<1-2 sentence description of what this script tests and which API it targets.>

Vendor-side setup
-----------------
<Step-by-step instructions for everything a user needs to do on the vendor
side before running this script. This is vendor-specific and must cover:>

1. How to create the credentials (API key, OAuth app, service account, etc.)
2. Which admin console / portal / page to visit
3. What permissions or scopes to grant
4. Any prerequisites (license tier, feature flags, admin role)
5. Any values to note down (org ID, tenant URL, client ID, etc.)

<This section should be detailed enough that someone unfamiliar with the
vendor can follow it end-to-end. It mirrors the "Vendor-side setup" section
of the research brief.>

Usage
-----
    python3 test-api.py <required args> [optional args]

    Environment variables:
        <VAR_NAME>    <description> (alternative to --flag)
        ...

Optional flags:
    --url              Base API URL including scheme (default: <vendor default>)
    --max-pages        Stop after N pages (default: 5)
    --mock             Skip archiving; print output directory path instead
    ...

Output
------
On success the script creates an output directory containing:
    test-api.log             — verbose step-by-step log
    trace.json               — detailed request/response trace (auth redacted)

The directory is then archived as <output-dir>.tar.gz.
Please send this archive to the integration maintainers for review.
"""
```

## CLI arguments and environment variables

Every credential and connection parameter must be accepted both as a CLI argument and as an environment variable. The CLI argument takes precedence when both are provided.

### Required parameters (vendor-specific)

These vary per vendor. Common examples:

| CLI flag | Env var | Description |
|----------|---------|-------------|
| `--api-key` | `<VENDOR>_API_KEY` | API key or bearer token |
| `--client-id` | `<VENDOR>_CLIENT_ID` | OAuth2 client ID |
| `--client-secret` | `<VENDOR>_CLIENT_SECRET` | OAuth2 client secret |
| `--org-id` / `--tenant-id` | `<VENDOR>_ORG_ID` | Organization or tenant identifier |

Use `argparse` with `default=os.environ.get("VAR_NAME")` so either source works.

### Standard parameters (always present)

These flags must appear in every test-api.py, regardless of vendor:

| CLI flag | Env var | Default | Description |
|----------|---------|---------|-------------|
| `--url` | `<VENDOR>_URL` | Vendor's default base URL (full `https://...`) | Base API URL including scheme. Always configurable even if the vendor has a single static URL — this lets users point at mock servers or regional endpoints. |
| `--max-pages` | — | `5` | Maximum number of pages to fetch. Prevents infinite pagination loops during testing. The CEL program may not have this safeguard, but the test script always must. |
| `--timeout` | — | `60` | HTTP request timeout in seconds. |
| `--proxy` | `HTTPS_PROXY` | None | HTTP/HTTPS proxy URL. |
| `--output-dir` | — | `test-api-output` | Name of the output directory. |
| `--mock` | — | `false` | Mock mode — skip archiving the output directory as `.tar.gz`. Instead, print the full absolute path to the output directory and a message that all request/response results are logged there (`test-api.log` and `trace.json`). Used by the CEL builder agent to run the script against a local mock server and inspect the output files directly. |

### Vendor-specific optional parameters

Add flags that mirror configuration variables from the configuration plan, for example:

- `--initial-interval` — lookback window (e.g., `24h`, `30m`)
- `--batch-size` / `--page-size` — items per page
- `--event-type` / `--log-type` — filter to a specific event category
- Any other filter or option the API supports that is useful for testing

## CLI output (stdout)

The stdout output is for the human running the script. It must be concise and step-oriented:

1. **Banner** — script name and purpose, one-line summary.
2. **Parameter summary** — show the resolved configuration (base URL, org/tenant ID, credentials masked to last 4 chars, page size, max pages, etc.).
3. **Step-by-step progress** — for each logical step (e.g., each paginated request), print a single line showing:
   - Step/page number (e.g., `[2/5]`)
   - What is happening (e.g., "Requesting page…")
   - Result (e.g., "OK (42 events, 0.31s)" or "FAILED (HTTP 401, 0.12s)")
   - Brief context on the result (e.g., time span of events, "no more pages")
4. **Execution summary** — after the collection loop, print:
   - Overall status: SUCCESS or FAILED
   - Total events collected
   - Total pages fetched
   - Any product/category breakdown if the data supports it
   - Output directory and archive location
5. **Handoff message** — tell the user to send the archive to the integration maintainers.

**What NOT to print to stdout:**
- Raw request bodies
- Raw response bodies
- Full headers
- Any sensitive credential values (even partial)

## Output directory

The script creates a directory (default: `test-api-output/`) containing exactly two files:

### 1. `test-api.log` — verbose log file

A text log file written by Python's `logging` module at DEBUG level. Contains everything printed to stdout plus additional detail:

- Full resolved configuration (credentials redacted)
- For each request: URL (redacted), timing, response status code, body length
- Rate-limit header values when present
- Pagination state transitions (cursor values, offset changes)
- Error details with full tracebacks
- Summary statistics

This is a superset of stdout — anything on stdout also appears in the log, with more detail.

### 2. `trace.json` — request/response trace

A JSON array where each element represents one HTTP exchange. This is the detailed diagnostic file for developers analyzing the API flow. Each entry contains:

```json
{
  "page": 1,
  "request": {
    "method": "GET",
    "url": "<full URL with query params, auth redacted>",
    "headers": {"<header>": "<value, auth redacted>"},
    "body": null
  },
  "response": {
    "status_code": 200,
    "headers": {"<header>": "<value>"},
    "body": {"<parsed JSON object or string if not JSON>": "..."},
    "elapsed_s": 0.312
  },
  "pagination": {
    "mechanism": "<cursor|offset|page|etc.>",
    "field_used": "<e.g., meta.next>",
    "value_from_response": "<the cursor/offset value received>",
    "value_for_next_request": "<what will be sent in the next request>",
    "want_more": true
  },
  "event_count": 42,
  "error": null
}
```

Key requirements for the trace:
- **Full response body included** — this is the detailed trace, not the summary log. Response bodies are essential for debugging field mapping and pipeline development.
- **Body fields must be parsed JSON objects, not strings** — both request and response `body` fields must be stored as parsed JSON objects (dicts/lists), not as raw JSON strings. Storing them as strings causes double-escaping in the trace file, making it hard to read. Use a `_try_parse_body` helper (see below) that attempts `json.loads` and falls back to the raw string if parsing fails. For POST request bodies where the payload dict is already available in Python, store `redact_dict(payload)` directly rather than serializing and re-parsing.
- **Pagination logic exposed** — show exactly which field was read from the response, what value it had, and how it was used to construct the next request. This validates that the proposed CEL pagination logic works correctly.
- **Auth redacted** — even in the detailed trace, replace credential values with `[REDACTED]`. For response bodies that may contain OAuth tokens (e.g. token exchange endpoints), redact `access_token`, `refresh_token`, and `id_token` keys from the parsed object before storing.
- **Errors included** — if a request fails, the entry still gets written with the error details.

#### `_try_parse_body` helper

Every script must include this helper (adapt the redaction logic for the vendor if the response body may contain credentials such as OAuth tokens):

```python
def _try_parse_body(text):
    """Return parsed JSON object if *text* is valid JSON, otherwise return the string as-is."""
    if not text:
        return text
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text
```

For APIs that return OAuth tokens in response bodies (e.g. token exchange endpoints), extend the helper to redact sensitive keys from the parsed object:

```python
def _try_parse_body(text):
    """Return parsed JSON object if *text* is valid JSON, otherwise return the string as-is.
    When the parsed result is a dict, redact known OAuth token keys in-place."""
    if not text:
        return text
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return redact(text)
    if isinstance(obj, dict):
        for key in ("access_token", "refresh_token", "id_token"):
            if key in obj and obj[key]:
                obj[key] = "[REDACTED]"
    return obj
```

### Archiving

After the collection loop and output writing, the script checks the `--mock` flag:

**When `--mock` is NOT set (default — normal mode):**

1. Creates a `.tar.gz` archive of the output directory.
2. Prints the archive path to stdout.
3. Instructs the user to share the archive with the integration maintainers.
4. If archiving fails, falls back gracefully and tells the user the unarchived directory path.

**When `--mock` IS set (mock mode):**

1. Skips `.tar.gz` archive creation entirely.
2. Prints the full absolute path to the output directory.
3. Prints a message indicating that all request and response results are logged in the output directory (`test-api.log` for the verbose log and `trace.json` for the detailed request/response trace).

Mock mode is designed for the CEL builder agent workflow. When the agent runs `test-api.py --mock` against a local system test mock server, it can immediately inspect the output files to validate that the mock API is returning the expected responses — without needing to decompress an archive first.

## Error handling

- **All exceptions caught** — the script must never crash with an unhandled exception. Wrap the main collection loop in try/except and log the full traceback to both the log file and trace file.
- **HTTP errors** — handle and log: connection errors, timeouts, non-2xx status codes, invalid JSON responses, rate limiting (429).
- **Rate limiting** — if a 429 is received, log the rate-limit headers (Retry-After, X-RateLimit-Reset, etc.) and stop. Do not implement automatic retry/backoff — the script is for testing, not production collection.
- **Keyboard interrupt** — catch `KeyboardInterrupt`, log it, and still write the output files and archive before exiting.
- **Exit code** — exit 0 on success, exit 1 on any failure.

## Script structure

The script should follow this general structure (adapt to the vendor):

```python
#!/usr/bin/env python3
"""<docstring as described above>"""

import argparse
import json
import logging
import os
import shutil
import ssl
import sys
import tarfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

# --- Helpers ---
# Redaction utilities, interval parsing, product detection, etc.

# --- HTTP transport ---
# A do_request() function using urllib with TLS verification disabled,
# proxy support, and timeout handling.

# --- Core collection loop ---
# The main pagination loop that mirrors the proposed CEL program.
# Each iteration: build URL, make request, parse response, extract
# pagination state, decide want_more, log everything.

# --- Main ---
# Argument parsing (with env var fallbacks), output directory setup,
# logger setup, run collection, write trace, print summary, archive.

if __name__ == "__main__":
    main()
```

## Relationship to CEL program design

The test script is the **ground truth** for CEL program construction. The
relationship is directional: test-api.py is the source of truth, and the
CEL program is a **translation** from it. The script has been tested
against a real API; even if the research brief has inaccuracies, the
script's behaviour can be accepted as correct.

Specifically:

- **Same endpoints** — the script calls the same API paths the CEL program will use.
- **Same authentication** — the script uses the same auth mechanism (API key header, OAuth2 token exchange, etc.).
- **Same pagination** — the script implements the same pagination pattern (cursor, offset, keyset) with the same termination conditions.
- **Same time-based filtering** — the script uses the same time parameters and formats.
- **Same request construction** — query parameters, headers, and body (if POST) match what the CEL program will send.

The CEL expression builder receives test-api.py as its primary input and
translates the collection function (`run_collection()` or equivalent)
into CEL. The research brief provides supplementary context (field
meanings, data types, edge cases not exercised by the script), but the
Python implementation is the specification.

The script also serves as the **mock specification** (the mock is derived
from the script's request/response flow) and the **mock validator** (the
script must pass against the mock before CEL translation begins). When a
`trace.json` exists from a real API run, it acts as an offline **fidelity
witness** — comparing mock responses against the trace catches cases
where the mock and script agree but both diverge from real API behaviour.

## Example reference

See the Atlassian Jira test script at `research_results/jira/test-api.py` for a complete working example. It demonstrates all of the patterns described here: stdlib-only HTTP, redaction, pagination mirroring, step-by-step stdout, verbose log file, trace file, archiving, and comprehensive error handling.
