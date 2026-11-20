# GenAI field gap analysis report template

Follow this structure. Fill every section. Where a section does not apply, write `N/A` and one
sentence saying why.

---

```markdown
# ECS GenAI Field Mapping: {{INTEGRATION_NAME}}

Package version {{VERSION}} at commit {{COMMIT}}. ECS pin {{PIN}}.

## Summary

[3–5 sentences: what the integration collects, which streams are in scope, the most important
gaps, what must change at the source (opt-ins, transports, new streams), and whether the work
needs a breaking release.]

Counts cover the core `gen_ai.*` fields only. Mixed streams get one row per record-type group.

| Stream | Record types | Kind | ✅ | ⚠️ | 🔄 | 🔍 | ⛔ |
|---|---|---|---|---|---|---|---|
| `<stream>` | `<types, or "all">` | Inference / Agent / Tool execution / Message / Usage metrics / Product telemetry | n | n | n | n | n |

Break the 🔍 count down by recommendation below the table, for example: "`<stream>`: 6 🔍 =
3 extract from existing data, 2 source-side setting, 1 new data stream."

Change counts over every row of the report: New n, Additive n, Breaking n, No change n.

## ECS pin

| Current `build.yml` pin | Pipeline `ecs.version` | Required | Action |
|---|---|---|---|
| `git@v8.11.0` | `8.11.0` | `git@v9.5.0` | Bump both |

## Data stream classification

| Stream | Record type | Kind | Deciding evidence |
|---|---|---|---|
| `<stream>` | `<event type or "all">` | ... | [endpoint, field or fixture] |

## Content capture and source configuration

What the user must enable at the source for content fields to exist, and what the README says
today.

| Setting | Controlled by | Enables | Limits | In README? |
|---|---|---|---|---|
| `OTEL_LOG_RAW_API_BODIES=1` | user's environment | `input.messages`, `output.messages` | — | yes / no |

## Field mapping: `<stream>` (repeat per in-scope stream)

Single-kind stream:

The *Recommendation* column is filled only for 🔍, with one value from the workflow's
recommendation table. *Change* and *Basis* are defined in the workflow (*Change and Basis*).

| Field | Status | Recommendation | Change | Basis | Source | Notes |
|---|---|---|---|---|---|---|
| `gen_ai.provider.name` | 🔄 | | New | issue #22224 | constant | `aws.bedrock` for every record |
| `gen_ai.operation.name` | 🔄 | | New | issue #22224 | `operation` | Only in `event.action` today; map `Converse`→`chat` |
| `gen_ai.request.model` | 🔍 | Extract from existing data | New | main | `modelId` | |
| `gen_ai.system` | ⚠️ | | Breaking | issue #22224 | | Not in ECS v9.5.0: deprecate in the next minor, remove in the next major |
| `gen_ai.request.seed` | ⛔ | | | | | Not available: the API has no seed parameter |
| ... every field from the workflow's Phase 4 list ... | | | | | | |

Mixed stream: one status column per record-type group, then *Change* and *Basis* for the
field. Each cell is `<status> <source>`, and a 🔍 cell adds the recommendation:
`🔍 <recommendation>: <source>`. A ⛔ cell for a record type that does not carry the value names
the one that does. When the Change differs per record type, write it in the cell
(`🔄 New: <source>`) and leave the Change column empty. Notes go below the table.

| Field | `api_request` | `api_request_body` | `tool_result` | Change | Basis |
|---|---|---|---|---|---|
| `gen_ai.request.max_tokens` | ⛔ on `api_request_body` | 🔍 Source-side setting: `body.max_tokens` | ⛔ | New | main |
| `gen_ai.tool.name` | ⛔ | ⛔ | ✅ `tool_name` | No change | main |

### ⚠️ Incorrect mappings

For each:
- **Field:** `gen_ai.x`
- **Now:** [what the package does]
- **Should be:** [per the catalog and the detection conventions]
- **Change:** Breaking / Additive, and why
- **Basis:** [issue, PR or proposal]

### 🔍 Gaps

For each:
#### `gen_ai.x`
- **Recommendation:** [one of: Extract from existing data / Add API parameter or request setting / New API call / Source-side setting (document only) / New data stream]
- **Layer:** 2 (received) / 3 (source)
- **Source:** [exact path in the payload, or the vendor doc URL]
- **What is needed:** [parse an existing field / the parameter or setting to add and its default / the setting the user must enable / endpoint Y / the new stream, and who controls it]
- **Notes:** [formats, size limits, string vs object. Describe the data, not processors.]

### ⛔ No action possible

| Field | Reason | Evidence |
|---|---|---|
| `gen_ai.request.seed` | Not available | Layer 1: not mapped. Layer 2: not in any fixture. Layer 3: the API has no seed parameter ([doc]) |
| `gen_ai.tool.call.id` | Not applicable | Stream kind: usage metrics, no per-call records |

## Detection conventions

One row per in-scope stream (`genai-detection-conventions.md`).

| Stream | Provider / operation (native verb in) | Tool calls | Call results | Identity (`user.name`) | Agent | Tool definition types | Messages (role `tool`, `finish_reason`) | Truncation tags | Categorization |
|---|---|---|---|---|---|---|---|---|---|
| `<stream>` | `aws.bedrock` / `chat` (`event.action`) | option B, aligned, README note: yes/no | in `input.messages`; #22225 open | role name from ARN; README: yes/no | — | OTel / native | yes / no | yes / no | unset (request-derived) |

## Fields outside the pinned ECS

Every `gen_ai.*` name the package defines or writes that is not in ECS {{PIN}}.

| Field | Written by the pipeline? | Value moves to | Plan |
|---|---|---|---|
| `gen_ai.system` | yes | `gen_ai.provider.name` | Deprecate in the next minor, remove in the next major |

## Values with no ECS field

Kept in the vendor namespace. Never mapped to a `gen_ai.*` name until a released ECS version
defines it. Status: ✅ the package already keeps it in the vendor field, 🔍 it does not yet
(with the recommendation), ⛔ the source does not send it.

| Value | Stream | Source | Vendor field | Status | ECS field once released |
|---|---|---|---|---|---|
| cache read tokens | | `usage.cache_read_input_tokens` | `<integration>.<stream>.cache_read_input_tokens` | | `gen_ai.usage.cache_read.input_tokens` (RFC 0060: wait for an ECS release) |
| tool source | | gateway target | `<integration>.<stream>.target` | | `gen_ai.tool.source.*` (RFC 0060: wait for an ECS release) |
| session id | | `session.id` | `<integration>.<stream>.session_id` | | `gen_ai.conversation.id` (ECS `main`) |

## Adjacent ECS fields

| Field | Stream | Source | Status | Change |
|---|---|---|---|---|
| `user.name` | | role name from `identity.arn` | | |
| `file.path` | | tool arguments `file_path` | | |

## Breaking changes and consumers

One row per Breaking row above (workflow Phase 5b).

| Field | Change | Consumers found | Next minor | Next major | Gated on |
|---|---|---|---|---|---|
| `gen_ai.system` | removed | n rules (detection-rules paths), n dashboards | add `gen_ai.provider.name`, deprecate | remove | rule updates released |

## Release plan

- **Next minor (additive):** [every New and Additive row, the deprecations]
- **Next major (breaking):** [every Breaking row]
- **Waiting for ECS:** [RFC 0060 fields and any other pending field]

## Differences from the tracking issue and reference tables

| Field / record | Source says | Finding | Reason |
|---|---|---|---|
| `gen_ai.provider.name` | `az.ai.openai` | `azure.ai.openai` | OTel registry (#22224) |

## Documentation changes

[What the README must add: opt-ins, required settings, what is collected with and without them,
the `user.name` derivation, the tool-array note for option B, the truncation tags, the
deprecations and the migration table for the major.]

## Open questions

[Decisions for the team: breaking changes, new streams or transports, ambiguous provider or
operation values, the #22225 call-result question where it applies.]
```
