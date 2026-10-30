# GenAI source discovery

How to find **every** source field that can feed a `gen_ai.*` field. This is the research
half of the skill. `research-integration` may load it: it describes data, not pipelines.

The goal is that no field is marked unavailable while the source can provide it. Tracking
issues and earlier analyses are a starting point, not evidence. Example: elastic/integrations#20741
lists `gen_ai.request.max_tokens`, `gen_ai.system_instructions` and `gen_ai.tool.definitions` as
"not emitted" by Claude Code, but all three are in the raw API request bodies that Claude Code
sends when `OTEL_LOG_RAW_API_BODIES=1` is set.

---

## The three layers

Check each `gen_ai.*` field against all three layers, in order. A field is **unavailable**
only when all three come back empty, and the report must say what was checked in each.

| Layer | Question | Where to look |
|---|---|---|
| **1. Mapped** | Does the integration already populate it, and correctly? | `fields/*.yml`, ingest pipeline, generated expected output |
| **2. Received, not parsed** | Does the integration already receive the data but keep it as a string, a vendor field, or drop it? | Handwritten fixtures (`_dev/test/pipeline/test-*.log/json`), mock API responses (`_dev/deploy/**`), system test samples, vendor fields of type `keyword`/`text`/`flattened` holding JSON, `remove`/`drop` processors |
| **3. Available at source** | Can the source send it with a different setting, endpoint, transport or record type? | Vendor API reference, logging configuration docs, OTel instrumentation docs of the product, changelogs of the vendor API |

For layer 3, fetch the **current** vendor documentation. Do not rely on memory or on the
integration README: GenAI APIs change every few months.

---

## Where GenAI data hides

### Serialized bodies

The most common gap. The source sends a full request or response, and the integration stores
it as an unparsed string or only extracts one or two values from it.

Signs: fields named `*_body`, `*Body*`, `*_json`, `payload`, `request`, `response`,
`messages`, `content`, `parameters`, `tool_input`, `tool_parameters`, `metadata`, typed
`keyword`, `text` or `flattened`, or values in fixtures that start with `{` or `[`.

When you find one, **decode a sample** and map its contents with the per-API tables below.

### Content-capture opt-ins

Prompt and response content, tool arguments and results, and reasoning are usually off by
default. Record each opt-in, who controls it (the customer's admin, the API caller, or the
integration), and any size limit. The README of the package must explain how to enable it.

| Source | Setting | Effect (verify in current vendor docs) |
|---|---|---|
| Amazon Bedrock | Model invocation logging (CloudWatch Logs and/or S3), per data type (text, image, embedding) | Request/response bodies in `input.inputBodyJson` / `output.outputBodyJson`. Large bodies are written only to S3 and referenced by `input.inputBodyS3Path` / `output.outputBodyS3Path`. |
| Azure OpenAI | API Management in front of the deployment, diagnostic setting `ApiManagementGatewayLogs` (and the LLM gateway log category where available) | Request and response bodies only through APIM. The native Azure OpenAI `RequestResponse` category has no bodies. |
| Vertex AI | Request-response logging to BigQuery, configured per model or endpoint, with a sampling rate | Full request/response for the sampled share of calls |
| Claude Code (OTel); check which gates Claude Cowork supports | `OTEL_LOG_USER_PROMPTS` | Prompt text on `user_prompt` events |
| | `OTEL_LOG_ASSISTANT_RESPONSES` (falls back to `OTEL_LOG_USER_PROMPTS` when unset) | Response text on `assistant_response` events (text blocks only) |
| | `OTEL_LOG_TOOL_DETAILS` | Tool parameters and tool input on tool events and spans |
| | `OTEL_LOG_TOOL_CONTENT` | Tool result content, **only** in the `tool.output` span event. Requires tracing. Log events carry only `tool_result_size_bytes`. |
| | `OTEL_LOG_RAW_API_BODIES=1` | Raw request/response bodies on `api_request_body` / `api_response_body` events, **truncated** at the content limit (60 KB default) |
| | `OTEL_LOG_RAW_API_BODIES=file:<dir>` | Untruncated bodies written to local disk. Events carry only a `body_ref` path, so nothing reaches Elastic over OTLP. |
| | `CLAUDE_CODE_OTEL_CONTENT_MAX_LENGTH` | Changes the content limit for all content-bearing attributes |
| | `ENABLE_BETA_TRACING_DETAILED=1` + `BETA_TRACING_ENDPOINT` | Extra span attributes (`new_context`, `user_system_prompt`, `tool_input`, `response.model_output`). Changes where logs and traces are sent. |
| | — | Extended-thinking content is **always** redacted from bodies, whatever the settings. Reasoning parts are ⛔ for this source. |
| LiteLLM | `general_settings.store_prompts_in_spend_logs`; S3/GCS logging callbacks | `/spend/logs/v2` omits the heavy `messages`/`response` columns. The bucket transport carries the full standard logging payload. |
| OpenAI Responses API | `store: true` on the request (default); not available for Zero Data Retention orgs | Stored response objects can be listed and fetched |
| Anthropic | Compliance API (Enterprise) | Request bodies of API calls. No response bodies. |
| Any provider | Reasoning must be requested by the **caller** (Anthropic/Bedrock `thinking`, Gemini `thinkingConfig.includeThoughts`, OpenAI `reasoning.summary`) | Without it, only reasoning token counts exist |

### Transports and endpoints of the same source

The same vendor often has several ways out, with different content: API vs bucket export,
summary endpoint vs detail endpoint, list endpoint vs get-by-id endpoint, audit log vs usage
report. List them all and note which `gen_ai.*` fields each one carries. A field that only one
transport carries is still in scope. Record it as needing that transport.

### Record types inside one stream

Event-type fields (`event.name`, `type`, `activity_type`, `operation`, `methodName`) split one
stream into record types with different payloads. Inventory every type from the vendor docs,
not only the ones in the current fixtures.

### Multi-format bodies

One envelope can carry bodies in several formats:

- Bedrock `InvokeModel` bodies follow the **model family's** native format (Anthropic Messages,
  Amazon Nova/Titan, Meta Llama, Mistral, Cohere, …). `Converse` bodies follow one unified
  format.
- LiteLLM and other gateways pass through the upstream provider's format.
- Strings vs arrays: OpenAI `stop` is a string or an array; Anthropic `system` is a string or
  an array of blocks; OpenAI message `content` is a string or an array of parts.

Name the formats you saw and the formats the docs say can occur.

### Truncation and sampling

Record size limits (body size caps, Event Hub message limits, S3-only bodies above a
threshold) and sampling (Vertex AI request-response logging). Sampling affects completeness
only. Truncation of a **serialized JSON body** is worse: a body cut in the middle does not
parse, so every field that comes from it is lost for that record. Say how often that happens
(the limit compared with typical body sizes) and whether the source has an untruncated
alternative.

### Where each signal lands

A source can send one signal in several ways: log events, spans, span events, metrics. Check
which data stream receives each one. Span events and logs emitted alongside traces can be
routed to datasets that the package does not define (for example `logs-<dataset>.otel-*`).
Data that never lands in a stream the package defines needs a new stream (🔍, recommendation
*New data stream*).

---

## Per-API source maps

Starting points for the common API families. **Verify each against current vendor docs**
before relying on it. A missing row means that you need to look it up, not that the source lacks it.

### OpenAI Chat Completions (also Azure OpenAI bodies, LiteLLM OpenAI-format payloads)

| gen_ai field | Request | Response |
|---|---|---|
| `request.model` | `model` (Azure: deployment name; the model is in the response) | |
| `response.model` | | `model` |
| `response.id` | | `id` (`chatcmpl-…`) |
| `request.max_tokens` | `max_completion_tokens`, else `max_tokens` | |
| `request.temperature` / `top_p` / `seed` / `frequency_penalty` / `presence_penalty` | same names | |
| `request.choice.count` | `n` | |
| `request.stop_sequences` | `stop` (string → one-element array) | |
| `output.type` | `response_format.type` (`json_object`/`json_schema` → `json`, `text` → `text`) | |
| `input.messages` | `messages[]` (system/developer messages stay here) | |
| `tool.definitions` | `tools[].function` (`type: function`) | |
| `output.messages` | | `choices[].message` (+ `finish_reason`) |
| `response.finish_reasons` | | `choices[].finish_reason` (`stop`, `length`, `tool_calls`, `content_filter`) |
| `tool.name` / `tool.call.id` | | `choices[].message.tool_calls[].function.name` / `.id` |
| `usage.input_tokens` | | `usage.prompt_tokens` (already includes cached) |
| `usage.output_tokens` | | `usage.completion_tokens` (already includes reasoning) |
| vendor namespace (cached count) | | `usage.prompt_tokens_details.cached_tokens` |
| vendor namespace (reasoning count) | | `usage.completion_tokens_details.reasoning_tokens` |

Tool results are `role: tool` messages with `tool_call_id` in the **next** request.

### OpenAI Responses API

| gen_ai field | Source |
|---|---|
| `request.model` / `response.model` | `model` (the response object echoes the request) |
| `response.id` | `id` (`resp_…`) |
| `system_instructions` | `instructions` |
| `input.messages` | `input` (string, or items with `role` and `content[]`) |
| `output.messages` | `output[]` items: `message` → text parts; `function_call` → `tool_call`; `reasoning.summary[]` → `reasoning`; built-in tool items (`web_search_call`, `file_search_call`, `mcp_call`, …) → `server_tool_call` |
| `request.max_tokens` / `temperature` / `top_p` | `max_output_tokens` / `temperature` / `top_p` |
| `tool.definitions` | `tools[]` |
| `tool.name` / `tool.call.id` / `tool.call.arguments` | `output[type=function_call]` `name` / `call_id` / `arguments` (JSON string) |
| `response.finish_reasons` | derived from `status` + `incomplete_details.reason` |
| `usage.*` | `usage.input_tokens` (includes cached), `usage.output_tokens` (includes reasoning), `usage.input_tokens_details.cached_tokens`, `usage.output_tokens_details.reasoning_tokens` |
| vendor namespace (previous response) | `previous_response_id` |
| vendor namespace (conversation; `gen_ai.conversation.id` once ECS releases it) | `conversation.id` when the response belongs to a conversation |

### Anthropic Messages (also Bedrock InvokeModel for Claude, Anthropic Compliance API bodies)

| gen_ai field | Request | Response |
|---|---|---|
| `request.model` / `response.model` | `model` | `model` |
| `response.id` | | `id` (`msg_…`) |
| `request.max_tokens` / `stop_sequences` | same names | |
| `request.temperature` / `top_p` / `top_k` | same names, **only with API version `2023-06-01`**. API version `2026-10-21` rejects them with a 400. | |
| `output.type` | `output_config.format` | |
| vendor namespace (effort) | `output_config.effort` | |
| vendor namespace (streaming) | `stream` | |
| `system_instructions` | `system` (string or text blocks) | |
| `input.messages` | `messages[]`: blocks `text`, `image`, `document`, `tool_use`, `tool_result`, `thinking` | |
| `tool.definitions` | `tools[]` (`name`, `description`, `input_schema`; server tools have a versioned `type`) | |
| `output.messages` | | `content[]`: `text`, `thinking` → `reasoning`, `redacted_thinking`, `tool_use` → `tool_call`, `server_tool_use` / `*_tool_result` → `server_tool_call*` |
| `response.finish_reasons` | | `stop_reason` (`end_turn`, `max_tokens`, `stop_sequence`, `tool_use`, `pause_turn`, `refusal`) |
| `tool.name` / `tool.call.id` / `tool.call.arguments` | | `content[type=tool_use]` `name` / `id` / `input` |
| `usage.input_tokens` | | **`input_tokens + cache_read_input_tokens + cache_creation_input_tokens`** |
| `usage.output_tokens` | | `output_tokens` (already includes thinking tokens) |
| vendor namespace (cache counts) | | `cache_read_input_tokens`, `cache_creation_input_tokens` |
| vendor namespace (thinking count) | | `usage.output_tokens_details.thinking_tokens` |

The API version is sent in the `anthropic-version` header, which usually isn't in the logged
body. The parameters that can appear depend on it.

### Amazon Bedrock model invocation log envelope

| gen_ai field | Envelope field |
|---|---|
| `provider.name` | `aws.bedrock` (always) |
| `operation.name` | from `operation`: `Converse`, `ConverseStream`, `InvokeModel`, `InvokeModelWithResponseStream` → `chat` for chat/text models; embedding models → `embeddings`. The model family decides. |
| `request.model` | `modelId` (model id, inference profile id or ARN, as requested) |
| `usage.input_tokens` / `output_tokens` | `input.inputTokenCount` / `output.outputTokenCount`, unless the body has a fuller breakdown (cache tokens) |
| Everything else | Decode `input.inputBodyJson` / `output.outputBodyJson` with the model family's table, or the Converse table |
| Adjacent | `identity.arn` → `user.*`/`cloud.*`; `requestId` → keep in vendor namespace (it is not a completion id); `accountId`, `region` → `cloud.*` |

**Bedrock Converse body**

| gen_ai field | Source |
|---|---|
| `input.messages` | `messages[]` with `content[]` blocks: `text`, `image`, `document`, `toolUse`, `toolResult`, `reasoningContent` |
| `system_instructions` | `system[]` (`{text}` blocks) |
| `request.max_tokens` / `temperature` / `top_p` / `stop_sequences` | `inferenceConfig.maxTokens` / `.temperature` / `.topP` / `.stopSequences` |
| `request.top_k` | `additionalModelRequestFields.top_k` (model-specific) |
| `tool.definitions` | `toolConfig.tools[].toolSpec` (`name`, `description`, `inputSchema.json`) |
| `output.messages` | `output.message` (`content[]`: `text`, `toolUse` → `tool_call`, `reasoningContent.reasoningText.text` → `reasoning`) |
| `response.finish_reasons` | `stopReason` (`end_turn`, `tool_use`, `max_tokens`, `stop_sequence`, `guardrail_intervened`, `content_filtered`) |
| `usage.*` | `usage.inputTokens`, `outputTokens`, `cacheReadInputTokens`, `cacheWriteInputTokens`. Check whether `inputTokens` includes the cache counts for the model; if not, sum. |

### Gemini / Vertex AI `generateContent`

The BigQuery export of Vertex AI request-response logging stores the same objects in
`full_request` / `full_response`, with snake_case keys.

| gen_ai field | Source |
|---|---|
| `provider.name` | `gcp.vertex_ai` (Vertex endpoint) or `gcp.gemini` (AI Studio endpoint) |
| `operation.name` | `generate_content` |
| `request.model` | request `model` / log `model` (full resource path, as requested) |
| `response.model` | `modelVersion` |
| `response.id` | `responseId` |
| `system_instructions` | `systemInstruction.parts[]` |
| `input.messages` | `contents[]` (`role`: `user`/`model` → `user`/`assistant`; `parts[]`: `text`, `inlineData`, `fileData`, `functionCall`, `functionResponse`) |
| `request.*` | `generationConfig.maxOutputTokens`, `temperature`, `topP`, `topK`, `seed`, `stopSequences`, `candidateCount`, `presencePenalty`, `frequencyPenalty` |
| `output.type` | `generationConfig.responseMimeType` (`application/json` → `json`); `responseModalities` |
| `tool.definitions` | `tools[].functionDeclarations[]` (also built-in tools: `googleSearch`, `codeExecution`, `retrieval`) |
| `output.messages` | `candidates[].content` (`parts[]` with `thought: true` → `reasoning`; `functionCall` → `tool_call`; `executableCode`/`codeExecutionResult` → `server_tool_call*`) |
| `response.finish_reasons` | `candidates[].finishReason` (`STOP`, `MAX_TOKENS`, `SAFETY`, `RECITATION`, `BLOCKLIST`, `PROHIBITED_CONTENT`, `SPII`, `MALFORMED_FUNCTION_CALL`, `OTHER`, …) |
| `tool.name` / `tool.call.arguments` | `functionCall.name` / `functionCall.args` (`functionCall.id` when present) |
| `usage.input_tokens` | `usageMetadata.promptTokenCount` (includes `cachedContentTokenCount`) |
| `usage.output_tokens` | `usageMetadata.candidatesTokenCount` **+ `thoughtsTokenCount`**: Gemini reports thoughts separately |
| vendor namespace (cache / reasoning counts) | `cachedContentTokenCount` / `thoughtsTokenCount` |

### OTel-native product telemetry (Claude Code, Codex, agent SDKs)

These products emit OTel log events or spans. Many attributes already use `gen_ai.*` names or
map one-to-one. For each product:

1. Get the full list of event names and attributes from the product's monitoring docs, not only
   from the fixtures.
2. List the content gates (see the opt-in table) and which attributes each gate adds.
3. Map per event type, following the stream kinds in `genai-datastream-classification.md`.
4. Check which backend the product called (`anthropic`, `aws.bedrock`, `gcp.vertex_ai`).
   Products that support several backends often expose this in a resource or event attribute.
5. Watch for attributes with misleading names: a "source" or "query source" attribute that
   names an internal thread is not `gen_ai.operation.name`; a request id is not a completion id.
6. Separate the **tool's input** (the arguments the model generated, for example
   `tool_input`) from **product metadata about the call** (for example `tool_parameters`,
   which holds things like MCP server and tool names or a command summary). Only the input
   goes to `gen_ai.tool.call.arguments`. Metadata stays in the vendor namespace or feeds
   other fields (`gen_ai.tool.name` for MCP tools).
7. Check where every signal lands (*Where each signal lands* above), especially span events.
8. If the backend can't be told apart per record, see the provider fallback in the catalog.

**OTel-native data streams** (`input: otelcol`, OTel-native schema): span and log attributes
stay under `attributes.*` and `resource.attributes.*`. The platform's OTel index templates map
them, not the package's field files, and expose them under their own names. A source attribute
that is already named `gen_ai.*` therefore shows up as `gen_ai.*` without any pipeline
processor or field definition. For these streams:

- Judge the attribute as sent: ✅ if its name and value follow the catalog, ⚠️ if not (for
  example the removed `gen_ai.system`, or a vendor value in `gen_ai.operation.name`).
- Write corrected or new values under `attributes.gen_ai.*`, not at the top level, so that
  the document doesn't hold two copies. Only ECS field names: do not add OTel attributes that
  ECS has not adopted. Attributes the source itself sends under such names are the source's
  data; report them, but don't add new ones.
- Catalog rules 1 and 2 (`nested` and `flattened` definitions) are about package field files.
  For OTel-native streams, check the mapping actually installed (`GET <index>/_mapping`)
  before deciding whether they apply.

### Usage and cost reports (Anthropic Admin API, OpenAI usage API, cloud metrics)

| gen_ai field | Typical source |
|---|---|
| `provider.name` | constant |
| `request.model` | the model grouping key of the bucket |
| `usage.input_tokens` | sum of all input token kinds in the bucket (uncached + cache read + cache write) |
| `usage.output_tokens` | output tokens of the bucket |
| `token.type` | on rows split by token kind: input kinds → `input`, output kinds → `output` |
| vendor namespace (cache counts) | the cache read / write kinds |

Rows aggregate many requests. Message-level fields, `response.id` and `request.*` parameters do
not exist here and are ⛔ with that reason.

---

## Field-by-field questions

Answer every question for every in-scope record type. Each answer cites a source field, a vendor
doc URL or a fixture.

| Field | Questions |
|---|---|
| `provider.name` | Which API served the request? Can the product route to several providers? Is there a per-record field that says which? |
| `operation.name` | Which field names the operation or endpoint? Does every value map to an OTel well-known value? Which values don't? |
| `request.model` / `response.model` | Is there a requested model **and** a serving model? Is the request value a deployment, alias, profile or ARN? |
| `response.id` | Is there a completion/message id, distinct from a request or trace id? |
| conversation id (vendor namespace until ECS releases `gen_ai.conversation.id`) | Is there a real session, thread or conversation id? Is it stable across the records of one conversation? |
| `request.*` parameters | Is the request body available (layers 2 and 3)? Which parameters does the API accept, **in which API versions**? (Any accepted parameter is available when the caller sets it.) |
| `output.type` | Does the request specify a response format or modality? |
| `input.messages` | Where is the chat history? Is it the full history or only the last turn? Which opt-in enables it? Size limits? |
| `system_instructions` | Is there a separate system field, or are system messages part of the history? |
| `output.messages` | Where is the response content? Several choices/candidates? Streaming chunks or assembled? |
| reasoning | Does the response carry thinking/reasoning content or summaries? What must the caller set? Is it encrypted or redacted? |
| `response.finish_reasons` | Per choice/candidate? What values can occur? |
| `usage.*` | Do the counts include cached and reasoning tokens? Are cache read/write and reasoning counts reported separately? |
| `token.type` | Are rows split by token kind? |
| `tool.definitions` | Are tool schemas in the request? Built-in/server tools? MCP tools? |
| `tool.name` / `tool.call.id` / `tool.call.arguments` | Where are the model's tool calls? One per record or many? Arguments as a JSON string or an object? Is the real tool name hidden behind a placeholder (MCP)? Which field is the tool's input, and which is product metadata about the call? |
| `tool.call.result` | Are tool results logged, and under which opt-in? In this record, in the next request, or in a different signal (span event)? |
| `tool.type` | Does the source say where the tool runs (client function, agent-side extension, datastore)? |
| `agent.id` / `name` / `description` | Is there a hosted agent resource with a stable id? |

### Adjacent ECS fields

Security detections on GenAI data also rely on these. Check them in the same pass:

| ECS field | Typical source |
|---|---|
| `user.*` (`user.id`, `user.email`, `user.name`) | Caller identity: IAM ARN, API key owner, account email, `metadata.user_id` |
| `source.ip`, `user_agent.*` | Caller IP and client |
| `organization.*`, `cloud.account.id`, `cloud.region` | Tenant, account, region |
| `file.path` | Tool arguments of file read/write/edit tools |
| `url.*`, `destination.address`, `destination.domain` | Tool arguments of fetch/browse/HTTP tools, MCP server URLs, gateway upstream URLs |
| `process.command_line` | Tool arguments of shell/exec tools |
| `error.*`, `event.outcome` | Failed calls, refusals, guardrail interventions |
| `event.duration` | Latency fields (convert to nanoseconds) |
| `rule.*` | Guardrail or content-filter policy that fired |
