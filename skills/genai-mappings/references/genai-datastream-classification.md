# GenAI data stream classification

Decides **whether** a data stream is in scope for `gen_ai.*` fields and **which field groups**
apply to it. Classify before mapping. Gap-analysing a stream that is out of scope produces
noise, and treating an in-scope stream as out of scope hides real gaps.

`research-integration` may load this file. It describes data, not pipelines.

---

## Stream kinds

| Kind | What one record is | Examples | Field groups that apply |
|---|---|---|---|
| **Inference** | One model call: request and/or response | Bedrock model invocation logs, Azure OpenAI / APIM gateway request-response logs, Vertex AI request-response logs, LiteLLM spend logs, OpenAI Responses objects, Anthropic Compliance API `/v1/messages` records | Identity, request parameters, response, usage, content, tool (as `tool_call` parts and name/id arrays) |
| **Agent / orchestration** | One agent invocation, step or run | Bedrock AgentCore runtime logs, ChatGPT Enterprise custom agent runs, agent spans | Identity (`operation.name: invoke_agent` / `create_agent`), agent, content when logged |
| **Tool execution** | One tool / connector / MCP call | AgentCore gateway logs, Claude Code `tool_result` / `tool_decision` events, ChatGPT Enterprise app and connector logs | Identity (`operation.name: execute_tool`), all `gen_ai.tool.*`; plus `file.*`, `url.*`, `destination.*` from the tool arguments |
| **Conversation / message** | One message in a conversation | ChatGPT Enterprise conversation messages, Claude Code `user_prompt` events | Identity, the message in `input.messages` (user) or `output.messages` (assistant), `response.model`/`response.id` on assistant messages |
| **Usage / cost metrics** | An aggregate per time bucket and model | Anthropic Admin usage and cost reports, OpenAI usage API, Vertex AI and Azure OpenAI platform metrics | `provider.name`, `request.model` (as a dimension), `usage.input_tokens` / `usage.output_tokens` as bucket totals, `token.type` on rows broken down by token type. Cache token counts stay in the vendor namespace. |
| **Product telemetry** (OTel-native apps) | One event or span emitted by an AI application | Claude Code / Claude Cowork OTel events, Codex logs | Map per event type: each event type is one of the kinds above (an `api_request` event is inference, a `tool_result` event is tool execution) |
| **Out of scope** | Records that only mention an AI product | Admin audit logs (user invited, key created, setting changed), billing without a model dimension, generic infrastructure metrics | None. At most `gen_ai.provider.name` when it helps correlation. Do not report missing fields. |

**Time-series (TSDB) metric streams** (`index_mode: time_series`): adding a new `dimension: true`
field changes the time-series identity of every document. When `gen_ai.request.model` copies a
field that is already a dimension (such as a CloudWatch `ModelId`), define it **without**
`dimension: true`. Token counts copied to `gen_ai.usage.*` keep the source's `metric_type`.

A stream can hold several kinds, discriminated by an event-type field (product telemetry, Admin
API audit logs that contain `compliance_api_accessed` records with request bodies). Classify
**per event type** and map each type separately.

### The audit-log trap

Some audit or compliance streams look out of scope but contain full inference requests: for
example a record type that stores an API request body as a string. Before marking a stream out
of scope, check every record type for a request or response body, prompt, model name or token
count. If one exists, the record type is **Inference**, even if its current pipeline never
parses it.

---

## Research-time rule (no code yet)

Answer these from vendor documentation and samples:

1. Does a record correspond to a model call, an agent run, a tool call, a message, or an
   aggregate of those? → in scope, kind as above.
2. Does any record type carry a request or response body, prompt text, model name or token
   count, even as an unparsed string or only after an opt-in? → in scope for that record type.
3. Otherwise → out of scope.

Write the kind for each proposed stream into the research brief, with the deciding evidence (an
endpoint name, a documented field, a sample record).

## Review-time rule (existing package; first hit wins)

1. **Definitive:** the pipeline or fields declare any `gen_ai.*` field → in scope.
2. **Definitive:** handwritten fixtures (`_dev/test/pipeline/test-*.log|json`, mock API
   responses, `_dev/deploy/` samples) contain a model identifier, token counts, a `messages` or
   `contents` array, a request/response body, a tool/function call, or an agent/session id → in
   scope.
3. **Strong:** the package is about an LLM provider, AI gateway, agent platform or AI
   assistant, and the stream is not an admin audit or billing stream without a model
   dimension → in scope.
4. Otherwise → out of scope. State the reason in one sentence.

Prefer handwritten inputs over generated `*-expected.json` and `sample_event.json`: the
question is what the **source** sends, not what the current pipeline keeps.

---

## Worked examples (from the GenAI ECS epic, elastic/integrations#20737)

| Package | Stream | Kind | Deciding evidence |
|---|---|---|---|
| `aws_bedrock` | `invocation` | Inference | Model invocation logs with `input.inputBodyJson`, `output.outputBodyJson`, token counts |
| `aws_bedrock` | `runtime`, `guardrails` | Usage metrics (TSDB) | CloudWatch metrics; `runtime` has per-model token counts with the model id as a dimension |
| `aws_bedrock_agentcore` | `runtime_application_logs` | Agent | `InvokeAgentRuntime` records with session id and prompt payload |
| `aws_bedrock_agentcore` | `gateway_application_logs` | Tool execution | Gateway tool invocations with tool name and target |
| `aws_bedrock_agentcore` | `memory_application_logs` | Agent (memory) | Check for memory operations → `operation.name` memory values |
| `azure_openai`, `azure_ai_foundry` | `logs` | Inference | Request/response logs with `backend_request_body` / `backend_response_body` |
| `azure_openai`, `azure_ai_foundry`, `gcp_vertexai` | `metrics` | Usage metrics | Token and request counts per model deployment |
| `gcp_vertexai` | `prompt_response_logs` | Inference | `full_request` / `full_response` |
| `gcp_vertexai` | `auditlogs` | Mixed: audit + Inference (no content) | `PredictionService.*` / `LlmBidiService.*` records carry the model in `protoPayload.resourceName` and the operation in `methodName`; admin methods are out of scope |
| `claude_code`, `claude_cowork` | `events` | Product telemetry | `api_request`, `api_error`, `api_request_body`/`api_response_body` → inference; `user_prompt`, `assistant_response` → message; `tool_result`/`tool_decision` → tool; hook, plugin and config events → out of scope |
| `claude_code` | `traces` (OTel-native) | Product telemetry | `llm_request` spans → inference; tool spans → tool execution; `interaction` spans → agent. Span attributes already named `gen_ai.*` arrive through the OTel passthrough (`genai-source-discovery.md`). |
| `anthropic` | `audit` | Mixed: audit + Inference | `compliance_api_accessed` records store a `/v1/messages` request body |
| `anthropic_metrics` | `usage`, `cost`, `rate_limit` | Usage metrics | Rows per model and bucket; `cost` has a token type |
| `openai` | `completions`, `embeddings`, `images`, `audio_*`, `moderations` | Usage metrics | OpenAI usage API buckets grouped by model |
| `openai` | `audit` | Out of scope | Admin actions |
| `openai_chatgpt_enterprise` | `conversation_message` | Message | One message with author role and model |
| `openai_chatgpt_enterprise` | `app_log`, `custom_agents_log`, `codex_log` | Tool execution / Agent / Product telemetry | Per event type |
| `lite_llm` | `spend_tracking` | Inference | One proxied call with model, provider, tokens, optional messages/response |
