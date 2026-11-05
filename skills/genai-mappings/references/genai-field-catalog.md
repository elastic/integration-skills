# ECS gen_ai field catalog

Single source of truth for `gen_ai.*` field mapping in Elastic integrations.

Aligned with: ECS v9.5.0 `gen_ai` field set (all fields `level: extended`, beta). Values and
message shapes come from the OpenTelemetry GenAI semantic conventions
([open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai)).
OTel is **not** a source of field names: only fields in a released ECS version are used.
ECS states that every `gen_ai` field except `gen_ai.token.type` is an exact match of the OTel
attribute with the same name.

Classify the data stream first (`genai-datastream-classification.md`). Then use this file to
decide which fields apply, how to define them, and what values they take.

---

## ECS availability matrix

| Field group | v9.1.0 – v9.4.0 | v9.5.0 | ECS `main` |
|---|---|---|---|
| `gen_ai.system` | ✅ | ❌ removed | ❌ |
| `gen_ai.provider.name` | ❌ | ✅ | ✅ |
| `request.*`, `response.*`, `operation.name`, `output.type`, `agent.*`, `tool.name`, `tool.type`, `tool.call.id`, `token.type`, `usage.*` | ✅ (counts typed `integer`) | ✅ (counts typed `long`) | ✅ |
| `input.messages`, `output.messages`, `system_instructions`, `tool.definitions`, `tool.call.arguments`, `tool.call.result` (`flattened`) | ❌ | ✅ | ✅ |
| `gen_ai.conversation.id` | ❌ | ❌ | ✅ (unreleased, do not use yet) |

**Pin rule:** `_dev/build/build.yml` → `dependencies.ecs.reference: "git@v9.5.0"` and pipeline
`ecs.version: "9.5.0"`. The two must match. At a lower pin, `external: ecs` on any field
added in v9.5.0 fails the build with `field definition not found in schema`, and `gen_ai.request.max_tokens`,
`gen_ai.request.seed`, `gen_ai.request.choice.count` and `gen_ai.usage.*` resolve to
`integer`, not `long`.

Verify at any tag:
```bash
curl -s https://raw.githubusercontent.com/elastic/ecs/<tag>/generated/csv/fields.csv \
  | awk -F, '$3=="gen_ai"' | cut -d, -f4,5 | sort
```

---

## Field reference

Types are as published in ECS v9.5.0. The **Define as** column is what to put in the
package's field files (see *Field definition rules* below for why some differ from ECS).

### Identity of the operation

| Field | ECS type | Define as | Meaning | Example | Notes and restrictions |
|---|---|---|---|---|---|
| `gen_ai.provider.name` | keyword | `external: ecs` (or `constant_keyword` override when one value per stream) | The GenAI provider as identified by the client or server instrumentation. | `openai` | Use the OTel well-known value (table below). It names the **API/platform that served the request**, not the model author: Claude served through Bedrock is `aws.bedrock`. |
| `gen_ai.operation.name` | keyword | `external: ecs` | The name of the operation being performed. | `chat` | Use the OTel well-known value (table below). Never copy a vendor API method name here. |
| `gen_ai.request.model` | keyword | `external: ecs` | The name of the GenAI model a request is being made to. | `gpt-4` | The exact name requested, as sent. For a fine-tuned or deployment-aliased model, use the most specific name available. Keyword scalar, never an object (`gen_ai.request.model.id` is wrong). |
| `gen_ai.response.model` | keyword | `external: ecs` | The name of the model that generated the response. | `gpt-4-0613` | Only from the response, or from a source field documented as the serving model. Do not copy `request.model` into it unless the source documents that its single model field is both. |
| `gen_ai.response.id` | keyword | `external: ecs` | The unique identifier for the completion. | `chatcmpl-123` | The provider's completion/message id (`chatcmpl-…`, `msg_…`, `resp_…`). A provider request id (`req_…`) is acceptable only when no completion id exists; say so in the pipeline `description`. |
| `gen_ai.conversation.id` | keyword | **Not usable yet**: only on ECS `main` (rule 3) | The unique identifier for a conversation (session, thread), used to store and correlate messages within this conversation. | `conv_5j66UpCpwteGg4YSxUnt7lPY` | Until an ECS release includes it, keep the source id in the vendor namespace. Once released: only from a real session/thread/conversation id in the source; a generated UUID, trace id or content hash **must not** be used as a fallback. |
| `gen_ai.output.type` | keyword | `external: ecs` | The content type **requested by the client**. | `text` | Values: `text`, `json`, `image`, `speech`. Set it from the request (for example `response_format`), not from what came back. |

### Request parameters

All of these come from the **request**. Set them only when the request carries them. Never
fill a provider default.

| Field | ECS type | Define as | Meaning | Example | Notes |
|---|---|---|---|---|---|
| `gen_ai.request.max_tokens` | long | `external: ecs` | Max tokens the model generates for a request. | `100` | OpenAI `max_tokens`/`max_completion_tokens`/`max_output_tokens`, Gemini `maxOutputTokens`, Bedrock Converse `inferenceConfig.maxTokens`. |
| `gen_ai.request.temperature` | double | `external: ecs` | Temperature setting. | `0.0` | |
| `gen_ai.request.top_p` | double | `external: ecs` | top_p sampling setting. | `1.0` | |
| `gen_ai.request.top_k` | double | `external: ecs` | top_k sampling setting. | `1.0` | ECS types it `double` though the value is an integer. Convert to a number, not a string. |
| `gen_ai.request.frequency_penalty` | double | `external: ecs` | Frequency penalty. | `0.1` | |
| `gen_ai.request.presence_penalty` | double | `external: ecs` | Presence penalty. | `0.1` | |
| `gen_ai.request.seed` | long | `external: ecs` | Seed for reproducible sampling. | `100` | |
| `gen_ai.request.choice.count` | long | `external: ecs` | Target number of candidate completions. | `3` | OpenAI `n`, Gemini `candidateCount`. |
| `gen_ai.request.stop_sequences` | nested ⚠ | **local `type: keyword`** | Sequences that stop generation. | `["forest", "lived"]` | Array of strings. See rule 1 below. |
| `gen_ai.request.encoding_formats` | nested ⚠ | **local `type: keyword`** | Encoding formats requested in an embeddings operation. | `["float", "binary"]` | Array of strings. See rule 1 below. |

### Response and usage

| Field | ECS type | Define as | Meaning | Example | Notes |
|---|---|---|---|---|---|
| `gen_ai.response.finish_reasons` | nested ⚠ | **local `type: keyword`** | Reasons the model stopped, one per generation received. | `["stop", "length"]` | Array of strings, same order as choices/candidates. Keep the **provider's values verbatim** (`end_turn`, `tool_calls`, `STOP`). Normalized values belong in each output message's `finish_reason`. |
| `gen_ai.usage.input_tokens` | long | `external: ecs` | Tokens used in the input (prompt). | `100` | OTel: **must include cached tokens**. Where the provider reports them separately (Anthropic), sum them. See the pipeline patterns. |
| `gen_ai.usage.output_tokens` | long | `external: ecs` | Tokens used in the response (completion). | `180` | OTel: reasoning tokens SHOULD be included. Where the provider reports them separately from the output count, sum them (check each API in `genai-source-discovery.md`). |
| `gen_ai.token.type` | keyword | `external: ecs` | The type of token being counted. | `input` | Only on records that count **one** token type (metric/cost rows broken down by type). Values `input`, `output`. Keep the vendor's finer value (`cache_read_input_tokens`) in the vendor namespace. ECS-only, not in the OTel attribute registry. |

### Content fields (`flattened`)

All six are `flattened`. They accept a JSON object or an array of objects. **They reject a
bare string.** Their internal shape is defined by the OTel JSON schemas (see *Message shapes*).

| Field | Define as | Meaning | Value shape |
|---|---|---|---|
| `gen_ai.input.messages` | `external: ecs` + `ignore_above: 8191` | Chat history provided to the model as input, in the order sent. | `[{role, parts[], name?}]` |
| `gen_ai.output.messages` | `external: ecs` + `ignore_above: 8191` | Messages returned by the model. One message per choice/candidate. | `[{role, parts[], finish_reason}]` |
| `gen_ai.system_instructions` | `external: ecs` + `ignore_above: 8191` | System message or instructions provided **separately from** the chat history. | `[{type: "text", content}]` |
| `gen_ai.tool.definitions` | `external: ecs` + `ignore_above: 8191` | Tool definitions available to the model or agent. | `[{type, name, description?, parameters?}]` |
| `gen_ai.tool.call.arguments` | `external: ecs` + `ignore_above: 8191` | Parameters passed to the tool call: the tool's **input** as generated by the model. Product metadata about the call (server names, permission context, summaries) is not arguments. | object (decode a JSON string first) |
| `gen_ai.tool.call.result` | `external: ecs` + `ignore_above: 8191` | Result returned by the tool call, if any and if it succeeded. | object (decode a JSON string first; wrap a plain string, see the pipeline patterns) |

`gen_ai.system_instructions` vs `gen_ai.input.messages`: OTel says instructions that are
**part of the chat history** (OpenAI Chat Completions `role: system`/`developer` messages) stay
in `gen_ai.input.messages`. Only a separate field (Anthropic `system`, Gemini
`systemInstruction`, OpenAI Responses `instructions`, Bedrock Converse `system`) goes to
`gen_ai.system_instructions`.

### Agents and tools

| Field | ECS type | Define as | Meaning | Example | Notes |
|---|---|---|---|---|---|
| `gen_ai.agent.id` | keyword | `external: ecs` | Unique identifier of the GenAI agent. | `asst_5j66UpCpwteGg4YSxUnt7lPY` | OTel: the provider-assigned stable id of a hosted agent (Bedrock agent ARN, assistant id). Not a transient in-memory id. |
| `gen_ai.agent.name` | keyword | `external: ecs` | Human-readable agent name. | `Math Tutor` | |
| `gen_ai.agent.description` | keyword | `external: ecs` | Free-form agent description. | `Helps with math problems` | ECS sets `index: false`: stored, not searchable. |
| `gen_ai.tool.name` | keyword | `external: ecs` | Name of the tool used by the agent. | `Flights` | Resolve the real tool name. If the source uses a placeholder such as `mcp_tool`, take the name from the tool parameters. |
| `gen_ai.tool.type` | keyword | `external: ecs` | Type of the tool. | `function` | Values: `function` (client-side, model generates arguments, client runs it), `extension` (agent-side, calls external APIs), `datastore` (retrieval/knowledge). Infer only when the source's semantics make it unambiguous, and say why in the pipeline `description`. |
| `gen_ai.tool.call.id` | keyword | `external: ecs` | The tool call identifier. | `call_mszuSIzqtI65i1wAUOE8w5H4` | |

**Requested vs executed.** A permission or decision record (a tool call that was approved or
rejected) describes a tool call but not its execution. Set `gen_ai.tool.*` on it, but set
`gen_ai.operation.name: execute_tool` only on records showing that the tool actually ran.

**One tool call vs many.** `gen_ai.tool.*` describes **a** tool call. Set all of them on
records that represent a single tool call (`execute_tool` operations, tool decision and
result events, gateway tool logs). On an inference record whose response holds several tool
calls, keep each call as a `tool_call` part in `gen_ai.output.messages`, and set only
`gen_ai.tool.name` and `gen_ai.tool.call.id` as order-aligned arrays so detections can match
on them. Do **not** put several calls' arguments or results into the single
`gen_ai.tool.call.arguments` / `gen_ai.tool.call.result` field.

---

## Well-known values

### `gen_ai.provider.name`

From the OTel registry. Use these exact strings. The values proposed in some tracking
issues (`az.ai.openai`, `vertex_ai`, `aws_bedrock`) are **wrong**.

| Value | Use for |
|---|---|
| `openai` | OpenAI API (`api.openai.com`), including ChatGPT Enterprise / Codex telemetry about OpenAI-served models |
| `anthropic` | Anthropic API (`api.anthropic.com`) |
| `aws.bedrock` | Amazon Bedrock, **whatever the model vendor** (OTel: MUST be `aws.bedrock`) |
| `azure.ai.openai` | Azure OpenAI |
| `azure.ai.inference` | Azure AI Inference / Azure AI Foundry model inference endpoint |
| `gcp.vertex_ai` | Vertex AI (`aiplatform.googleapis.com`) |
| `gcp.gemini` | Gemini API / AI Studio (`generativelanguage.googleapis.com`) |
| `gcp.gen_ai` | Any Google GenAI endpoint when the backend is unknown |
| `cohere`, `mistral`, `groq`, `deepseek`, `perplexity`, `x_ai`, `ibm.watsonx.ai`, `moonshot_ai` | those providers |

Not listed: OTel instrumentations use a lowercase provider name. Proxies and gateways (LiteLLM,
API management gateways) are not providers: report the **upstream** provider that served the
request, translated to the values above.

**Products that can route to several backends** (Claude Code can call the Anthropic API,
Amazon Bedrock, Google Cloud or Microsoft Foundry; LiteLLM routes to any provider; Azure AI
Foundry serves Azure OpenAI and other models). A `constant_keyword` is only correct when every
record of the stream is served by the same provider. Otherwise derive the value per record and
document the derivation.

When **no per-record field** says which backend served the request:

1. Look for a resource attribute or session-level setting the source does send (an endpoint
   URL, a "use Bedrock" flag, a region field that only exists for one backend).
2. If there is none, add a package variable for the backend, with the vendor's own API as the
   default. Set `gen_ai.provider.name` from it and say in the README that users on other
   backends must change it.
3. Never hard-code the vendor's own API as the value of a `constant_keyword` field for a
   multi-backend product.

Backends with no OTel well-known value (for example Claude served through Microsoft Foundry)
are an open question for the report. Do not invent a value. Product renames don't change the
OTel value: Vertex AI is still `gcp.vertex_ai` after Google renamed it Agent Platform.

### `gen_ai.operation.name`

| Value | Use for |
|---|---|
| `chat` | Chat completion: OpenAI Chat Completions / Responses, Anthropic Messages, Bedrock Converse / InvokeModel for chat models, Azure `ChatCompletions_Create` |
| `generate_content` | Multimodal content generation: Gemini / Vertex `generateContent`, `streamGenerateContent` |
| `text_completion` | Legacy text completion (OpenAI Completions, Azure `Completions_Create`) |
| `embeddings` | Embeddings |
| `retrieval` | Retrieval, such as a vector store search |
| `fetch_response` | Fetching a stored response by id without inference (OTel: do not report token usage for it) |
| `create_agent`, `invoke_agent`, `invoke_workflow`, `plan` | Agent lifecycle and orchestration |
| `execute_tool` | Executing a tool |
| `search_memory`, `create_memory`, `update_memory`, `upsert_memory`, `delete_memory`, `create_memory_store`, `delete_memory_store` | Agent memory operations |

Map vendor operation names through a lookup (see the pipeline patterns). Keep the raw value in
`event.action`. When no mapping applies, leave the field unset.

### Other enumerations

| Field / property | Values |
|---|---|
| `gen_ai.output.type` | `text`, `json`, `image`, `speech` |
| `gen_ai.tool.type` | `function`, `extension`, `datastore` |
| `gen_ai.token.type` | `input`, `output` |
| message `role` | `system`, `user`, `assistant`, `tool` (other strings allowed, such as `developer`) |
| output message `finish_reason` | `stop`, `length`, `content_filter`, `tool_call`, `compaction`, `error` (other strings allowed) |
| blob/file/uri part `modality` | `image`, `video`, `audio`, `document` |

---

## Message shapes

The OTel JSON schemas (`model/gen-ai/gen-ai-*.json` in the semconv repo) define the content of
the `flattened` fields. Instrumentations MUST follow them.

```text
gen_ai.input.messages   = [ ChatMessage ]
gen_ai.output.messages  = [ OutputMessage ]      // one per choice/candidate
gen_ai.system_instructions = [ TextPart | {type, ...} ]
gen_ai.tool.definitions = [ {type: "function", name, description?, parameters?} | {type, name} ]

ChatMessage   = { role, parts: [Part], name? }
OutputMessage = { role, parts: [Part], name?, finish_reason }

Part (by "type"):
  text                      { type, content }
  reasoning                 { type, content }                         // thinking / reasoning summaries
  tool_call                 { type, id?, name, arguments? }           // model asks for a tool
  tool_call_response        { type, id?, response }                   // result sent back to the model
  server_tool_call          { type, id?, name, server_tool_call }     // provider-executed tool
  server_tool_call_response { type, id?, server_tool_call_response }
  blob                      { type, modality, mime_type?, content }   // inline base64
  file                      { type, modality, mime_type?, file_id }
  uri                       { type, modality, mime_type?, uri }
  compaction                { type, id?, content? }
  <other>                   { type, ... }                             // anything else, keep its type
```

The ECS documentation example shows `"result"` on a `tool_call_response` part. The OTel JSON
schema, which is normative, uses **`response`**. Use `response`.

Reasoning content (Anthropic `thinking` blocks, Gemini parts with `thought: true`, OpenAI
Responses `reasoning` items with `summary[]`) becomes a `reasoning` part in the output message,
before the text part, in source order. Encrypted or redacted reasoning (Anthropic
`redacted_thinking`, signatures, `encrypted_content`) is not reasoning content. Drop it or keep
it as `{type: "<vendor type>"}` with no content.

---

## Source values with no ECS field

**Never define a field under `gen_ai.*`, or under any other ECS field set, that is not in a
released ECS version at or below the package's pin.** This holds even when the OpenTelemetry
GenAI registry defines the attribute, and even when the name is on ECS `main`. When ECS adopts
an attribute it may change its name or type, and a package that guessed would then conflict
with ECS.

Keep these values in the vendor namespace, under the source's own name:
`<integration>.<data_stream>.<source_field>` (for example
`anthropic.messages.usage.cache_read_input_tokens`). Don't rename them to look like the OTel
key. When ECS adds the field, copy the vendor value to it with `external: ecs`.

Research still records these values: they are data the integration should keep, and they show
what will be mappable once ECS catches up. OTel attributes that sources often provide:

| OTel attribute (reference only) | Typical source |
|---|---|
| `gen_ai.usage.cache_read.input_tokens` | OpenAI `prompt_tokens_details.cached_tokens`, Anthropic `cache_read_input_tokens`, Gemini `cachedContentTokenCount` |
| `gen_ai.usage.cache_write.input_tokens` | Anthropic `cache_creation_input_tokens` |
| `gen_ai.usage.reasoning.output_tokens` | OpenAI `reasoning_tokens`, Anthropic `thinking_tokens`, Gemini `thoughtsTokenCount` |
| `gen_ai.request.stream` | `stream` request flag |
| `gen_ai.request.reasoning.level` | OpenAI `reasoning.effort`, Anthropic `output_config.effort` |
| `gen_ai.request.previous_response.id` | OpenAI `previous_response_id` |
| `gen_ai.response.status` | OpenAI Responses `status` |
| `gen_ai.response.time_to_first_chunk` | time-to-first-token metrics |
| `gen_ai.agent.version` | agent version |
| `gen_ai.tool.description` | tool description |
| `gen_ai.data_source.id` | knowledge base id |
| `gen_ai.conversation.id` (ECS `main`) | session, thread or conversation id |

---

## Field definition rules

### Rule 1 — `nested` ECS fields: declare locally as `keyword`

ECS types `gen_ai.response.finish_reasons`, `gen_ai.request.stop_sequences` and
`gen_ai.request.encoding_formats` as `nested` with no properties
([elastic/ecs#2560](https://github.com/elastic/ecs/issues/2560)). `external: ecs` produces a
`nested` mapping, and indexing `["stop"]` fails with *"object mapping for
[gen_ai.response.finish_reasons] tried to parse field [null] as object, but found a concrete
value"*. A local `keyword` definition passes `elastic-package check`:

```yaml
# fields/fields.yml
- name: gen_ai.response.finish_reasons
  type: keyword
  description: >-
    Array of reasons the model stopped generating tokens, corresponding to each generation
    received. Defined locally as keyword because ECS types it as nested without properties
    (elastic/ecs#2560).
- name: gen_ai.request.stop_sequences
  type: keyword
  description: >-
    List of sequences that the model will use to stop generating further tokens. Defined
    locally as keyword because ECS types it as nested without properties (elastic/ecs#2560).
```

Do not apply the `ecs-field-mappings` guidance on "nested (array-of-objects) ECS fields" to
these three. They hold strings, not objects.

### Rule 2 — `flattened` ECS fields: add `ignore_above: 8191`

Leaves of a `flattened` field are indexed as keywords. A leaf longer than 32766 bytes (a long
prompt, response or tool result) makes Elasticsearch **reject the whole document**. Fleet does
not add a default `ignore_above` to `flattened` fields. 8191 characters is the largest value
that is safe for any UTF-8 content (4 bytes per character). Longer values stay in `_source` and
are not indexed. The other keys remain searchable.

```yaml
# fields/ecs.yml
- name: gen_ai.input.messages
  external: ecs
  ignore_above: 8191
- name: gen_ai.output.messages
  external: ecs
  ignore_above: 8191
- name: gen_ai.system_instructions
  external: ecs
  ignore_above: 8191
- name: gen_ai.tool.definitions
  external: ecs
  ignore_above: 8191
- name: gen_ai.tool.call.arguments
  external: ecs
  ignore_above: 8191
- name: gen_ai.tool.call.result
  external: ecs
  ignore_above: 8191
```

### Rule 3 — no field that isn't in a released ECS version

Do not define `gen_ai.conversation.id`, OTel-only attributes, or any other name that is not in
the pinned ECS release, not even locally with `type: keyword`. Rules 1 and 2 are different: they
change how an **ECS-defined** field is mapped, not which fields exist. Keep the source value in
the vendor namespace (*Source values with no ECS field*).

### Rule 4 — constant provider

When every record of a stream is served by one provider, the ECS field with a
`constant_keyword` override is fine:

```yaml
- name: gen_ai.provider.name
  external: ecs
  type: constant_keyword
  value: anthropic
```

The pipeline then does not need to set it. Test fixtures still show it.

### Rule 5 — everything else: `external: ecs`

```yaml
- name: gen_ai.request.model
  external: ecs
- name: gen_ai.usage.input_tokens
  external: ecs
```

### Vendor fields that were copied to `gen_ai.*`

Follow `ingest-pipelines`: prefer `rename` from the vendor field to the ECS field so that the
data is not stored twice. In an **existing** package, removing a published vendor field is a
breaking change. Copy with `set` and `copy_from`, and keep the removal for a major version. The
normalized message fields are not duplicates of the raw body: they have a different shape. On
an existing package, keep the raw body unless the change is released as breaking.

---

## Anti-patterns seen in the repository

| Seen | Problem | Correct |
|---|---|---|
| `gen_ai.system` | Removed in ECS v9.5.0 | `gen_ai.provider.name` |
| `gen_ai.prompt` / `gen_ai.completion` (text) | Not ECS. `gen_ai.prompt` also collides with the OTel `gen_ai.prompt.name` object. | `gen_ai.input.messages` / `gen_ai.output.messages` |
| `gen_ai.usage.prompt_tokens` / `completion_tokens` | Old OTel names, not ECS | `gen_ai.usage.input_tokens` / `output_tokens` |
| `gen_ai.request.model.id`, `.version`, `.instructions` | `gen_ai.request.model` is a keyword, not an object | `gen_ai.request.model`, `gen_ai.system_instructions` |
| `gen_ai.response.finish_reasons` as `external: ecs` | Maps as `nested`, rejects string arrays | local `keyword` (rule 1) |
| `flattened` field with no `ignore_above` | Long content rejects documents | rule 2 |
| Raw vendor body copied into `gen_ai.output.messages` | Not the OTel message shape. Detections cannot rely on `role`/`parts`. | Normalize (pipeline patterns) |
| Vendor op name in `gen_ai.operation.name` (`acompletion`, `InvokeModel`, `repl_main_thread`) | Not an OTel value | Map through a lookup, raw value in `event.action` |
| `provider.name: aws_bedrock` / `az.ai.openai` / `vertex_ai` | Not OTel values | `aws.bedrock` / `azure.ai.openai` / `gcp.vertex_ai` |
| Invented `gen_ai.*` (`gen_ai.threat.*`, `gen_ai.policy.*`, `gen_ai.user.id`, `gen_ai.guardrail_id`) | Not ECS | Vendor namespace, or the proper ECS field set (`user.*`, `rule.*`) |
| OTel attributes under `gen_ai.*` (`gen_ai.usage.cache_read.input_tokens` in `lite_llm`) | Not ECS. ECS may adopt it under another name or type. | Vendor namespace, under the source's name |
| `gen_ai.conversation.id` defined locally | Only on ECS `main`, not released | Vendor namespace until released |
| Anthropic `input_tokens` copied as-is when cache fields exist | Under-counts input tokens | Sum (pipeline patterns) |
| `gen_ai.usage.cache_creation.input_tokens` | Not ECS | Vendor namespace (`<integration>.<data_stream>.cache_creation_input_tokens`) |
| Product metadata about a tool call (for example `tool_parameters`) in `gen_ai.tool.call.arguments` | Not the tool's input | The tool input field; metadata stays in the vendor namespace |
| `constant_keyword` provider on a multi-backend product | Wrong for every non-default backend | Per-record value, or a package variable (provider fallback above) |

---

## Review checklist

Severities follow `review-integration`'s rubric. Fields are beta, so cap findings that only
concern value precision at MEDIUM.

### What to flag

- [ ] GenAI stream in a package pinned below `git@v9.5.0`, or `ecs.version` not matching the pin -- **HIGH** on a new stream / **MEDIUM** on an existing stream being changed
- [ ] `gen_ai.response.finish_reasons` / `request.stop_sequences` / `request.encoding_formats` defined with `external: ecs` -- **HIGH** (documents rejected)
- [ ] `flattened` `gen_ai.*` field without `ignore_above` -- **HIGH** (documents rejected on long content)
- [ ] A scalar can reach a `flattened` field (plain-string system prompt, unparsed JSON string) -- **HIGH**
- [ ] Field under `gen_ai.*` (or any ECS field set) that is not in the pinned ECS release, including OTel registry attributes and `gen_ai.conversation.id` -- **HIGH** on new fields; **LOW** for pre-existing ones in unchanged streams
- [ ] `gen_ai.system` emitted on a stream pinned at v9.5.0+ -- **MEDIUM**
- [ ] `gen_ai.provider.name` value not an OTel well-known value when one exists -- **MEDIUM**
- [ ] `constant_keyword` provider on a stream that can be served by several providers -- **MEDIUM**
- [ ] `gen_ai.operation.name` holding a vendor operation name -- **MEDIUM**
- [ ] Message fields not in the OTel shape (`role` + `parts[]`) -- **MEDIUM**
- [ ] `gen_ai.usage.input_tokens` excluding cached tokens when the source reports them separately -- **MEDIUM**
- [ ] `gen_ai.tool.call.arguments` / `.result` holding several calls -- **MEDIUM**
- [ ] `gen_ai.tool.call.arguments` holding product metadata instead of the tool input -- **MEDIUM**
- [ ] `gen_ai.operation.name: execute_tool` on a record where the tool did not run (rejected decision) -- **LOW**
- [ ] Source field available in fixtures or vendor docs that maps to a `gen_ai.*` field but is not mapped -- **MEDIUM** (state the source field)
- [ ] Content is only collected after a vendor-side opt-in and the README does not say how to enable it -- **MEDIUM**
- [ ] `gen_ai.response.model` copied from `request.model` without a documented reason -- **LOW**
- [ ] `gen_ai.request.*` parameter filled from a provider default instead of the request -- **LOW**

### When gen_ai fields are NOT required

Do not flag missing `gen_ai.*` fields on streams classified as out of scope by
`genai-datastream-classification.md` (admin audit logs, billing without a model dimension,
infrastructure metrics).

---

## How to refresh this file

```bash
# ECS fields and types at a tag
curl -s https://raw.githubusercontent.com/elastic/ecs/<tag>/generated/csv/fields.csv \
  | awk -F, '$3=="gen_ai"' | cut -d, -f4,5 | sort
# ECS definitions, examples and OTel relation
curl -s https://raw.githubusercontent.com/elastic/ecs/<tag>/schemas/gen_ai.yml
# OTel registry (well-known values) and message JSON schemas
curl -s https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/model/gen-ai/registry.yaml
curl -s https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/model/gen-ai/gen-ai-output-messages.json
```

Update the `Aligned with:` line and the availability matrix whenever ECS ships a new `gen_ai`
change. Check whether elastic/ecs#2560 is fixed (rule 1), and whether `gen_ai.conversation.id` or
any attribute in *Source values with no ECS field* has been released. Move released ones into
the field tables.
