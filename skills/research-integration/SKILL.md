---
name: research-integration
description: "Research a vendor, product, or feature to collect all information needed before building an Elastic integration. Investigates data collection methods, API or log documentation, sample data formats, field schemas, ECS mapping candidates, and configuration requirements. Outputs a structured research brief to research_results/<product>/. Invoke manually with /research-integration."
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
disable-model-invocation: true
---

# Research Integration

You are the **research orchestrator**. Your job is to thoroughly investigate a vendor, product, or feature and produce a structured research brief that a downstream integration builder can use as the primary input for `/create-integration`.

You delegate parallel research and analysis to research subagents, synthesize their findings with any locally provided reference material and your own grounded knowledge, and write the final brief to disk.

Each research subagent is dispatched via the platform's **generic / general-purpose subagent** (Cursor: `generalPurpose` Task agent; Claude Code: `general-purpose` Task agent; or the equivalent on other platforms), and supplied with the research-specific operating manual inline. That manual lives in `references/research-subagent-guidance.md` (see "Before you start" below).

Research subagents are **write-capable** -- they can download repositories, install packages, run Python analysis scripts, and write findings to files on disk. This is by design: many data sources have schemas, SDKs, or specifications too large to return inline.

## What you provide

Include any combination of the following when you invoke this command.
Use `@`-mentions for files/folders and paste links inline.

| Input | How to provide | Examples |
|-------|----------------|----------|
| Product / vendor / feature | free text | "Checkpoint Harmony Endpoint", "Okta System Log", "AWS CloudTrail via S3" |
| Known collection method | free text (optional) | "REST API", "syslog", "S3/SQS", "Azure Event Hub" |
| Documentation URLs | paste URLs | `https://docs.vendor.com/api/v2`, `https://docs.vendor.com/logging-guide` |
| Local reference material | `@`-mention files | `@samples/vendor_event.json`, `@notes/vendor-api-notes.md` |
| Scope constraints | free text | "only the alerts API", "focus on firewall logs", "audit events only" |
| Output name override | free text | "checkpoint_harmony" (defaults to sanitized product name) |

Anything typed after `/research-integration` is your research goal.

### Invocation examples

```
/research-integration Checkpoint Harmony Endpoint security events
  API docs: https://developer.checkpoint.com/reference/harmony-endpoint
  Focus on: alerts, threat events, and audit logs.
  Known method: REST API with pagination.
```

```
/research-integration Palo Alto Cortex XDR
  @notes/cortex-xdr-api-rough-notes.md
  Need to investigate both the Incidents API and Alerts API.
```

```
/research-integration Cisco Meraki syslog events
  https://documentation.meraki.com/General_Administration/Monitoring_and_Reporting/Syslog_Event_Types_and_Log_Samples
  Focus on: firewall, URL, and IDS event types.
  Known method: syslog over UDP/TCP.
```

```
/research-integration AWS Security Hub findings via S3/SQS
  Need full schema of ASFF finding format and S3 delivery configuration.
```

## Before you start -- load references

Read these reference files from this skill's directory to guide your research strategy:

1. `references/data-collection-methods.md` -- understand input types and what to investigate for each
2. `references/research-output-template.md` -- the structure your final brief must follow
3. Based on the identified collection method, read the applicable checklist:
   - `references/api-research-checklist.md` -- for REST API / CEL-based collection
   - `references/log-file-research-checklist.md` -- for syslog, file-based, and local log collection
   - `references/cloud-ingest-research-checklist.md` -- for S3/SQS, Event Hub, Pub/Sub, and similar cloud delivery
4. If the collection method is (or turns out to be) API-based, also read:
   - `references/test-api-script-spec.md` -- specification for the API test script generated in Phase 7

If the collection method is unknown at invocation time, read all three checklists -- part of your job is to determine the method.

Also load:

5. `ecs-field-mappings` skill -- for ECS field mapping guidance during the analysis phase
6. `references/competitive-siem-coverage-checklist.md` -- **always load**; guides Research Track E and its full content must be embedded in the Track E subagent prompt
7. `references/research-subagent-guidance.md` -- **always load**; the operating manual every research subagent needs. Its full content must be embedded verbatim in **every** research subagent task prompt so the subagent has its methodology, temp/ usage rules, result delivery contract, quality standards, and anonymization conventions without needing to load any skill or reference file itself

Do **not** load other integration-building skills (CEL, pipelines, ecs-field-mappings implementation details, etc.). Those are for implementation, not research.

## Output location

Write all research output to:

```
research_results/<product_slug>/
```

Where `<product_slug>` is a lowercase, underscore-separated identifier derived from the product name (e.g., `checkpoint_harmony_endpoint`, `palo_alto_cortex_xdr`, `cisco_meraki`). The user may override this with the "Output name override" input.

Create this directory structure:

```
research_results/<product_slug>/
  research-brief.md           # the main structured research brief
  test-api.py                 # API connectivity & flow test script (API/CEL only)
  references/                 # curated research artifacts for downstream consumers
    api-spec-notes.md         # API endpoint details, request/response examples (if API)
    log-format-notes.md       # log format details, sample lines (if log-based)
    field-schema-analysis.md  # detailed field inventories written by subagents
    competitive-siem-coverage.md  # detailed competitive SIEM analysis (always created)
    sample-events/            # representative sample data files
      <event_type>.json       # one file per event type or data format variant
      <event_type>.log
  temp/                       # downloaded raw artifacts (repos, SDKs, schemas, scripts)
    <descriptive-subfolder>/  # e.g., vendor-sdk/, schema-files/, openapi-spec/
  ecs-mapping-analysis.md     # initial ECS field mapping analysis
  configuration-plan.md       # planned integration configuration variables
```

Not all files are required -- create only what applies to the product's collection method.

**Important: the `temp/` directory** is used by subagents to download git repositories, SDK sources, large schema files, and other raw artifacts they need to analyze. Do not delete `temp/` after research completes -- it serves as a reference for the human and may be useful for follow-up work.

## Workflow

### Phase 1: Parse and plan

1. Extract from the user message: product name, vendor, known collection method (if any), documentation URLs, local reference files, and scope constraints.
2. Read any `@`-mentioned local files.
3. Fetch any documentation URLs provided inline to get initial context.
4. Determine the output slug and create the output directory.
5. Identify which research tracks to pursue based on what is known and unknown.

### Phase 2: Parallel research

Launch multiple research subagents in parallel using the platform's generic / general-purpose subagent (see the dispatch description at the top of this skill). Each subagent focuses on a specific research track. **You should launch as many parallel subagents as makes sense for the product -- typically 2-4 subagents, plus the always-on Track E.**

**IMPORTANT -- subagent context and capabilities:**

- Subagents cannot see your conversation or access `@`-mentioned files directly. Include any relevant content from local reference files and fetched URLs in the task prompt.
- Subagents are **write-capable**. Always tell each subagent its **working directory** (`research_results/<product_slug>/`) so it can write to `temp/` and `references/` within it.
- Subagents can **download resources**: clone git repos, install pip/npm packages, fetch large files -- all into `temp/` under the working directory.
- Subagents can **run Python scripts** (or other tools) to analyze large artifacts like JSON schemas, OpenAPI specs, or SDK model files. Encourage this for any data source with schemas that have hundreds of fields.
- Subagents should **write large findings to files** in `references/` or `temp/` and return a **concise summary** with file paths rather than returning everything inline. This keeps context manageable.

**Required structure for every research subagent task prompt:**

1. **Embed the full content of `references/research-subagent-guidance.md` verbatim** at the top of the prompt. This is the subagent's operating manual — methodology, `temp/` usage, Python analysis idiom, result delivery contract, quality standards, and anonymization conventions. Do not summarize or paraphrase it; embed it as-is. This is the same pattern Track E uses for the competitive-SIEM checklist.
2. **State the working directory explicitly** so the subagent knows where to write:
   ```
   Working directory: research_results/<product_slug>/
   - Download raw artifacts to: research_results/<product_slug>/temp/
   - Write curated findings to: research_results/<product_slug>/references/
   ```
3. **Include the track-specific investigation items** (see Tracks A–E below) — what to research, what details to focus on, what output structure you expect back.
4. **Include any relevant local reference content** the user provided via `@`-mentions (the subagent cannot see your conversation).
5. **Include any documentation URLs** the user provided inline.

#### Research Track A: Product overview and data collection methods

Instruct the subagent to investigate:
- What the product/feature is and what kind of data it generates
- All available methods for collecting/exporting data (API, syslog, file export, cloud streaming, SIEM forwarding, etc.)
- Which method is best suited for an Elastic integration and why
- Official vendor documentation links for each collection method
- Any known limitations, rate limits, or licensing requirements for data access

Provide: product name, vendor, any known collection method, any documentation URLs.

#### Research Track B: Data source deep dive

Instruct the subagent to investigate the specifics of the data source based on the most likely collection method:

**For APIs:**
- Base URL and endpoint paths
- Authentication method (API key, OAuth2, Bearer token, Basic auth, custom headers)
- **OAuth2 deep dive (critical):** If the API uses OAuth2, identify ALL supported grant types (client_credentials, authorization_code, etc.) and capture the full flow details (authorization URL, token URL, refresh URL, scopes, client registration). Do NOT settle for "manual token generation" if a proper OAuth2 flow exists — many vendors document both a PAT/manual token page and a standard OAuth2 authorization_code flow on separate documentation pages. See `api-research-checklist.md` for the detailed OAuth2 investigation checklist.
- Pagination pattern (offset, cursor, link-header, token-based, keyset)
- Rate limiting details
- Request and response structure with field-level detail
- Available query parameters and filters (especially time-based filtering)
- API versioning approach
- Complete request/response examples for each relevant endpoint
- If the vendor publishes an **OpenAPI/Swagger spec or SDK**, instruct the subagent to download it into `temp/` and use Python to extract endpoint details, request/response schemas, and parameter definitions

**For logs/syslog:**
- Log format (syslog RFC 3164/5424, CEF, LEEF, key-value, JSON, CSV, multiline)
- Default log file paths per OS
- Syslog facility and severity usage
- Message structure and delimiters
- Sample log lines for each event type

**For cloud ingest (S3/SQS, Event Hub, Pub/Sub, etc.):**
- Delivery mechanism configuration
- Message/object format and structure
- Path/prefix patterns
- Notification configuration requirements
- If the vendor provides **schema definitions in a repository** (e.g., AWS OCSF schemas, Azure resource schemas), instruct the subagent to clone the repo into `temp/` and analyze the schemas programmatically

Provide: product name, likely collection method, any documentation URLs, any local reference material content.

#### Research Track C: Event types and field schema

Instruct the subagent to investigate:
- All distinct event types, categories, or log sources the product generates
- Field names, types, and descriptions for each event type
- Common fields across event types vs. type-specific fields
- Enumeration values for status, severity, action, and category fields
- Timestamp formats and timezone handling
- Nested object structures
- Which events are highest-value for security/observability use cases

**For data sources with large schemas:** Instruct the subagent to download the schema source (git repo, SDK package, JSON schema file) into `temp/` and use Python to programmatically extract field inventories, type information, and enum values. The subagent should write the complete field analysis to `references/field-schema-analysis.md` (or multiple files if per-event-type breakdowns are needed) and return a summary.

Provide: product name, any documentation URLs, any sample data content from local files.

#### Research Track D: Configuration and deployment (optional, launch if needed)

Instruct the subagent to investigate:
- What configuration the end user needs to provide (credentials, URLs, paths, filters)
- How to enable/configure data export on the vendor side
- Network requirements (ports, protocols, firewall rules)
- Common deployment architectures
- Prerequisites and permissions needed

Provide: product name, collection method, any documentation URLs.

#### Research Track E: Competitive SIEM coverage (always launch)

**Always launch this track** in parallel with the other tracks. It is not conditional on collection method.

Instruct the subagent to check whether IBM QRadar, Splunk, and Sumo Logic have an existing integration or app for the product being researched, and to document what each covers and how it collects data.

The subagent must follow the full `references/competitive-siem-coverage-checklist.md` loaded in "Before you start" — embed the **complete checklist content** verbatim in this subagent's prompt so it has full guidance without needing to read local files. (This is in addition to the always-embedded `references/research-subagent-guidance.md` from Phase 2.)

Competitor catalog starting points to include in the prompt:
- IBM QRadar: `https://www.ibm.com/products/qradar-siem/integrations`
- Splunk: `https://splunkbase.splunk.com/apps`
- Sumo Logic: `https://www.sumologic.com/help/docs/integrations/`

For each competitor, the subagent must determine:
- Whether a matching integration/app exists (exact, partial, or no match)
- Integration/app name, publisher, direct catalog link, version, and last-updated date
- Which data sources and event types it covers (be specific, not generic)
- Collection method used (API pull, syslog push, agent/forwarder, cloud delivery, etc.)
- Protocol and wire format details (CEF, LEEF, JSON, key-value, etc.) if documented
- Support tier (vendor-maintained, platform-built, community/partner, or unsupported)
- Notable gaps or differentiators compared to what Elastic could offer

Output: write all findings to `references/competitive-siem-coverage.md` using the structure defined in the checklist (summary table → per-competitor H2 sections → comparison notes). Return a concise inline summary with which competitors have integrations, the dominant collection method found, and the path to the written file.

Provide: product name, vendor name, common aliases or abbreviations for the product, and the full content of `references/competitive-siem-coverage-checklist.md`.

### Phase 3: Synthesize and supplement

After all subagents return:

1. **Read subagent-written files.** Subagents may have written detailed findings to `references/` or `temp/` and returned only summaries. Read the files they reference to get the full picture. The subagent summaries will tell you which files to read and when.
2. **Merge findings** from all research tracks into a unified understanding.
3. **Cross-reference** subagent findings with any local reference material the user provided.
4. **Fill gaps** using your own grounded knowledge of the vendor/product. Only include information you are confident is accurate and can be attributed to known documentation, specifications, or widely established facts. Flag any details that could not be verified with a `[UNVERIFIED]` marker.
5. **Resolve conflicts** between subagent findings. When sources disagree, prefer official vendor documentation over third-party sources.
6. **Collect sample data** -- extract or compile representative sample events from documentation, API response examples, or log format guides. Save each as a separate file in the `sample-events/` subdirectory.
7. **Review temp/ artifacts** if needed. Subagents may have downloaded repos, SDKs, or schemas into `temp/`. You can inspect these directly if you need more detail than what the subagent summaries and reference files provide.
8. **Read `references/competitive-siem-coverage.md`** (written by Track E). Extract the summary table and overall comparison notes — these are used directly in section 1.5 of the research brief.

### Phase 4: ECS mapping analysis

Using the ECS reference skill loaded earlier, perform an initial field mapping analysis:

1. For each identified field from the product's data, determine:
   - Whether it maps to an existing ECS field (and which one)
   - Whether it should be a custom field under the integration namespace
   - The appropriate Elasticsearch field type
2. Identify which `event.kind`, `event.category`, `event.type`, and `event.outcome` values apply to each event type.
3. Note any fields that are strong candidates for `related.ip`, `related.user`, `related.hosts`, or `related.hash` enrichment.
4. Write the analysis to `ecs-mapping-analysis.md`.

### Phase 5: Configuration planning

Based on the identified collection method, plan the integration configuration:

1. Determine required vs. optional configuration variables.
2. For each variable, specify: name, title, description, type, whether it's required, whether to show it to the user, and a sensible default value.
3. Map variables to the appropriate input type's configuration surface. See `references/data-collection-methods.md` for the standard variables per input type.
4. Write the plan to `configuration-plan.md`.

### Phase 6: Write research brief

Compile the full research brief following the template in `references/research-output-template.md`. Write it to `research_results/<product_slug>/research-brief.md`.

The brief must be self-contained -- a reader should be able to use it as the sole input to `/create-integration` and have everything they need.

When populating **section 1.5 (Competitive SIEM Coverage)**, use the summary table extracted from `references/competitive-siem-coverage.md` in Phase 3 step 8. Include the one-line summary paragraph and the three-row competitor table inline, then add a reference pointer: `See references/competitive-siem-coverage.md for full per-vendor analysis.`

### Phase 7: API test script (API/CEL collection only)

**Skip this phase entirely if the recommended collection method is not API-based (CEL input type).** This phase only applies when the research has identified a REST API as the collection method.

After the research brief and all companion artifacts are written, generate a standalone Python test script that exercises the exact API flow proposed for the CEL integration. This lets a human validate connectivity, authentication, pagination, and response structure against a real (or mock) API before any Elastic Agent work begins.

1. **Read the specification:** Load `references/test-api-script-spec.md` from this skill's directory. It defines every requirement for the script in detail — file structure, CLI arguments, output files, error handling, and the relationship to the proposed CEL program.

2. **Gather inputs from earlier phases.** The script is synthesized from research already completed:
   - **Authentication method and credential creation steps** → from section 3.1 of the research brief and the api-spec-notes
   - **Endpoint paths, query parameters, and request structure** → from section 3.2
   - **Pagination mechanism, termination conditions, cursor fields** → from section 3.3
   - **Time-based filtering parameters and formats** → from section 3.4
   - **Configuration variables** → from `configuration-plan.md`

3. **Write the script** to `research_results/<product_slug>/test-api.py`. Key requirements (see spec for full detail):
   - **Standard library only** — `urllib.request`, `json`, `logging`, `argparse`, `ssl`, etc. No third-party dependencies.
   - **Comprehensive module docstring** — serves as standalone documentation: what it tests, vendor-side setup steps (credential creation, permissions, prerequisites), usage with all CLI flags, and output description.
   - **Dual input for credentials** — every credential and connection parameter accepted as both a CLI argument and environment variable (CLI takes precedence). Use `argparse` with `default=os.environ.get(...)`.
   - **Base URL always configurable** — full URL including scheme (`https://...`), even if the vendor has a single static URL. This enables pointing at mock servers.
   - **`--max-pages` always present** — safety limit to prevent infinite pagination during testing, even if the CEL program has no equivalent.
   - **TLS verification disabled** — this tests API flow, not certificate health.
   - **Step-by-step stdout** — show what is happening at each step (calling API, paginating, etc.) without printing raw request/response bodies or any sensitive data.
   - **Output directory** with two files:
     - `test-api.log` — verbose log (superset of stdout, written via Python `logging`)
     - `trace.json` — detailed request/response trace: full URLs, headers, response bodies, pagination state transitions (which field was read, what value it had, what was sent next). Auth values redacted.
   - **Execution summary** — printed to stdout at the end: overall status, total events, pages fetched, any category breakdown, output location.
   - **Archive** — compress the output directory as `.tar.gz` and print the path with instructions to share it with integration maintainers.
   - **Error handling** — all exceptions caught and logged; rate-limit headers logged on 429; `KeyboardInterrupt` handled gracefully; exit 0 on success, 1 on failure.

4. **Mirror the proposed CEL flow.** The script's request sequence, pagination logic, and termination conditions must match what was described in the research brief for the CEL program. This is the core value of the script — if it works, the CEL program should work too.

### Phase 8: Verify and report

1. Verify all output files are written and well-formed.
2. If `test-api.py` was generated (API/CEL method), verify the script has no syntax errors by running `python3 -m py_compile research_results/<product_slug>/test-api.py`.
3. List all files created with their paths.
4. Provide a concise summary to the user:
   - Product overview (1-2 sentences)
   - Recommended collection method and why
   - Number of distinct event types/data streams identified
   - Key findings or surprises
   - Gaps or areas that need user input
   - If `test-api.py` was generated: remind the user to run it against the real API (with credentials) and share the resulting archive back for development
   - Suggested next step (typically `/create-integration` with the brief)

## Research quality standards

- **Ground all claims in sources.** Every factual statement in the brief should be traceable to vendor documentation, official specs, or widely established technical references. When using your own knowledge, explicitly note it.
- **Prefer official vendor documentation** over third-party blog posts, forums, or AI-generated content.
- **Include direct links** to source documentation wherever possible.
- **Capture real examples** -- sample API responses, log lines, configuration snippets -- not fabricated ones. If you must construct an example to illustrate structure, mark it `[CONSTRUCTED EXAMPLE]`.
- **Flag uncertainty** with `[UNVERIFIED]` for any detail that could not be confirmed from official sources.
- **Be specific, not generic.** "The API uses pagination" is not useful. "The API uses cursor-based pagination via a `next_cursor` field in the response body; pass it as the `cursor` query parameter" is useful.
- **Cover edge cases.** Note rate limits, maximum page sizes, required permissions, deprecated endpoints, known bugs, and any gotchas.

## Guardrails

- Do not fabricate sample data that looks real. Sample data must come from documentation or be clearly marked as constructed.
- Do not start building the integration. This skill produces research only.
- Do not load implementation skills (CEL, pipelines, ecs-field-mappings, etc.) -- those are for the build phase.
- **Do not prescribe CEL implementation details.** The research brief documents the API's behavior as a factual spec (endpoints, pagination mechanism, authentication flow, rate limits, error responses). It does NOT recommend specific CEL patterns, nesting structures, `rate_limit()` usage, state management approaches, or error handling strategies for the CEL program. The CEL builder agent has its own skills with authoritative patterns. Research output that prescribes CEL implementation details will be ignored or — worse — followed incorrectly, overriding the CEL skill's patterns.
  - **Good:** "Pagination uses `next_cursor` with `more_to_read` boolean. Terminate when `more_to_read` is false."
  - **Bad:** "The CEL program should use `want_more: body.more_to_read` and store the cursor in `state.?cursor.next_cursor`."
  - **Good:** "Rate limits: 100 req/min/user. Headers: `X-Ratelimit-Limit`, `X-Ratelimit-Remaining`, `X-Ratelimit-Reset`."
  - **Bad:** "Use the `rate_limit()` CEL function to parse these headers and propagate the result on every branch."
- If a product has multiple viable collection methods, document all of them with a recommendation and rationale, but produce detailed deep-dive material for the recommended method.
- If research reveals the product does not expose data in a way that Elastic can ingest, say so clearly in the brief.

## Handoff

After this command completes, continue with:

1. **If `test-api.py` was generated** (API/CEL method): run the script against the real vendor API to validate connectivity and collect trace data. Share the resulting `.tar.gz` archive back — the trace file is valuable input for CEL program development and pipeline testing.
2. `/create-integration @research_results/<product_slug>/research-brief.md` to build the integration using the research brief as input.
3. Provide additional sample data files from `research_results/<product_slug>/references/sample-events/` via `@`-mentions.
