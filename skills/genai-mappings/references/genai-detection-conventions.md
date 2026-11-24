# GenAI detection conventions

How GenAI integrations populate `gen_ai.*` and the fields around them, so that one detection
rule or ML job runs unchanged on every source. `genai-field-catalog.md` says which fields exist
and what values they take. This file says which records get them and how, and how to change a
published field without breaking its consumers.

Sources:

- elastic/integrations#22224: canonical `gen_ai.provider.name` and `gen_ai.operation.name`
  values
- elastic/integrations#22225: tool-call conventions (multi-call records, call and result,
  identity, tool definitions, message shape, categorization)
- elastic/integrations#20738 and the `aws_bedrock` 2.4.0 pipeline
  (`packages/aws_bedrock/data_stream/invocation/elasticsearch/ingest_pipeline/genai.yml`), the
  first package that follows these conventions

**Before applying a section, read the issue again.** #22225 section 2 (call and result) had an
open question on 2026-11-20. If a later comment answers it, the answer wins over this file.
When statements conflict, the later maintainer decision wins, and #22224 / #22225 win over an
earlier comment on a package issue (for example, an early #20738 comment placed tool results
under `user`; #22225 section 5 puts them under `tool`).

---

## 1. Only fields in the pinned ECS

A root `gen_ai.*` field is valid only if the ECS release the package pins defines it. This is
the catalog's rule 3, checked mechanically:

```bash
# Tag from _dev/build/build.yml (dependencies.ecs.reference: git@v9.5.0 -> v9.5.0)
ECS=~/.elastic-package/cache/fields/ecs/v9.5.0/ecs_nested.yml
grep -E '^    gen_ai\.[a-z0-9_.]+:$' "$ECS" | tr -d ' :' | sort -u    # 32 fields at v9.5.0
# The cache exists once elastic-package has built a package at that pin. Without it:
# curl -s https://raw.githubusercontent.com/elastic/ecs/v9.5.0/generated/ecs/ecs_nested.yml
```

Every `gen_ai.*` name in the package's `fields/*.yml` and pipelines, and every `gen_ai.*`
name a report proposes, must be in that list. Anything else goes to
`<integration>.<data_stream>.<field>`. In a gap report, a name outside the list is ⚠️ if the
package already writes it, and never a recommendation.

### Fields to wait for

`gen_ai.tool.source.*`, `gen_ai.usage.cache_read.input_tokens` and
`gen_ai.usage.cache_write.input_tokens` (RFC 0060) and `gen_ai.conversation.id` (ECS `main`)
are accepted for ECS but not in a release. Their values stay in a vendor field under the
source's name, for example the gateway target in `aws.bedrock_agentcore.gateway.target` or
`aws_bedrock.invocation.usage.cache_read_input_tokens`. The catalog's *Source values with no
ECS field* section has the list and what to do when an ECS release ships them.

Never a field, in ECS or elsewhere:

| Name | Use instead |
|---|---|
| `gen_ai.tool.call.count` | `MV_COUNT(gen_ai.tool.call.id)` (#22225 section 1; call ids are unique, so deduplicated doc values still count every call) |
| a tool definition fingerprint | a documented derived value (#22225 section 4), computed at query time |

---

## 2. `gen_ai.provider.name` per integration

The OTel well-known value of the platform that served the request (#22224). Platforms built on
a provider use the provider's value and keep their own name in their namespace. Aggregators
translate the upstream provider.

| Package | `gen_ai.provider.name` | Notes |
|---|---|---|
| `aws_bedrock` | `aws.bedrock` | Whatever the model vendor |
| `aws_bedrock_agentcore` | `aws.bedrock` | The platform name stays in `aws.bedrock_agentcore.*.provider_name`. A rule on `aws.bedrock` then matches Bedrock and AgentCore records. |
| `azure_openai` | `azure.ai.openai` | Not `az.ai.openai` |
| `azure_ai_foundry` | `azure.ai.inference` | |
| `gcp_vertexai` | `gcp.vertex_ai` | Not `vertex_ai` |
| `anthropic`, `anthropic_metrics` | `anthropic` | |
| `claude_code`, `claude_cowork` | the backend that served the call | `anthropic` for the Anthropic API. These products can also call Bedrock or Vertex AI: follow the catalog's multi-backend rule. |
| `openai`, `openai_chatgpt_enterprise` | `openai` | |
| `lite_llm` | the upstream provider, translated (`bedrock` → `aws.bedrock`) | The native provider stays in the vendor namespace |

**`gen_ai.system` → `gen_ai.provider.name`.** A package that writes `gen_ai.system` adds
`gen_ai.provider.name` in a minor release and keeps `gen_ai.system` for that release, marked
deprecated (section 9). The changelog names both fields. The next major removes it.

---

## 3. `gen_ai.operation.name` per source

OTel value in `gen_ai.operation.name`, the native verb in `event.action` (or the vendor
namespace, where noted). A record that is not a GenAI operation gets no operation.

| Source and record | `gen_ai.operation.name` | Native verb kept in |
|---|---|---|
| Bedrock `Converse`, `ConverseStream` | `chat` | `event.action` |
| Bedrock `InvokeModel`, `InvokeModelWithResponseStream` | by what the body is: `chat` (a `messages` list), `text_completion` (a single `prompt` or `inputText` string and no messages), `embeddings` (embedding model or body). Unset for image, video and rerank models, which have no OTel value. | `event.action` |
| Bedrock `ApplyGuardrail` | unset: no generation | `event.action` |
| AgentCore runtime `InvokeAgentRuntime` | `invoke_agent` | `event.action` |
| AgentCore gateway tool invocation | `execute_tool` | `event.action: invoke_gateway`, the value #22224 gives (the package's existing gateway operation name), on the records of a tool invocation. The tool name goes to `gen_ai.tool.name` (section 4, prefixed names), not `event.action`. Gateway records that are not a tool call (`tools/list`, errors without a tool) get no operation and keep their current `event.action`. `gen_ai.provider.name` is on every record of the stream (a stream-wide constant). |
| Bedrock `CreateResponse` (OpenAI Responses API), other invocation operations with a chat body | `chat` | `event.action` |
| Bedrock S3 body-offload objects (no envelope) | unset: the envelope record carries the operation | — |
| AgentCore memory operations | the OTel memory value that matches (`search_memory`, `create_memory`, …), else unset | `event.action` |
| Azure OpenAI `ChatCompletions_Create` | `chat` | `event.action` |
| Azure AI Foundry `ChatCompletions` | `chat` | `event.action` |
| Vertex AI `GenerateContent`, `StreamGenerateContent` | `generate_content` | `event.action` |
| Anthropic `/v1/messages` | `chat` | `event.action` |
| Claude Code / Cowork `api_request` | `chat` | `query_source` stays in the vendor namespace. It names an internal thread, not an operation. |
| Claude Code / Cowork `tool_result` | `execute_tool` | `event.action` (`tool_result`) |
| ChatGPT Enterprise connector, tool and MCP calls | `execute_tool` (not `invoke_tool`) | `event.action` |
| ChatGPT Enterprise conversation messages, agent runs | `chat` | `event.action` |
| LiteLLM `acompletion` / `embedding` | `chat` / `embeddings` | vendor namespace (`call_type`) |
| Usage and cost aggregates, token counting, admin and audit events | unset | — |

Rules:

- `execute_tool` only where the record shows that the tool ran (section 4). A call that a model
  requested in a provider log keeps the operation of the invocation (`chat`).
- Changing a value the package already writes (a vendor verb today) is **Breaking**. Copy the
  current value to `event.action` or the vendor namespace in a minor first, then change
  `gen_ai.operation.name` in the next major (section 9).

---

## 4. Tool calls

### One record per call (option A): execution-side sources

Sources that log the tool run already write one record per call: Claude Code / Cowork
`tool_result`, AgentCore gateway logs, ChatGPT Enterprise connector calls, LiteLLM MCP calls,
OTel `execute_tool` spans. Each record carries:

| Field | Value |
|---|---|
| `gen_ai.operation.name` | `execute_tool` when the record shows the call ran; unset on a decision record (approved or rejected, not run) |
| `gen_ai.tool.name` | the real tool name (resolve MCP placeholders) |
| `gen_ai.tool.call.id` | the call id, when the source has one |
| `gen_ai.tool.type` | from the source (section 8): MCP tools are `extension`, AgentCore gateway target tools `function` |
| `gen_ai.tool.call.arguments` | the tool's input, when logged |
| `gen_ai.tool.call.result` | the tool's output, when logged |
| `event.outcome`, `error.type` | the outcome of the tool call: this record **is** the call |

When one call writes several records (a start line, a routing line, a completion line), each
record that names the tool or the `tools/call` method gets `gen_ai.tool.name` (when named) and
`execute_tool`: on an execution-side source, a logged call is a call the platform ran. Records
are not joined, so a record that names neither leaves them unset. The arguments go on the
record that carries them, the result on the record that carries it. `event.outcome` is set
from the record that carries the call's status; an outcome the package already writes on the
other records of the call stays as it is (No change).

`gen_ai.tool.call.id` is the id the model gave the call. A protocol request id (the MCP
JSON-RPC `id`, which OTel's MCP conventions record as `jsonrpc.request.id`) is not a call id:
keep it in the vendor namespace.

**Platform-prefixed tool names.** Gateways that expose tools as `<target>___<tool>` (AgentCore
gateway) split the prefix off: `gen_ai.tool.name` is `<tool>`, and the target is the tool
source (RFC 0060, elastic/ecs#2711). When the record also names the target by id (the AgentCore
routing line's `from target <id>`), that id is the future `gen_ai.tool.source.name`, as in
RFC 0060's AgentCore example, with `gen_ai.tool.source.type: gateway_target`. A record with
only the prefix leaves the future source unset; the prefix stays in the vendor tool name. Until
`gen_ai.tool.source.*` is released, the target stays in the vendor namespace, and the full
prefixed name stays in the vendor tool-name field: it is the name the model saw, which joins
the call to the model's `tool_call` part.

### One record per invocation (option B): provider logs

Provider invocation logs (Bedrock, Azure OpenAI, Vertex AI, OpenAI, Anthropic) hold every
tool call of a response in one record, and ingest pipelines cannot split a document. Use
order-aligned arrays:

- `gen_ai.tool.name`, `gen_ai.tool.type` and `gen_ai.tool.call.id` list the calls **in the
  response**, in the order the model generated them. Index `i` of each array is the same call.
  Never sort, deduplicate or reorder them, and never infer execution order from the next
  request.
- Only the response's calls. Calls in the request's history (earlier turns, or results being
  returned) are not added. Server-side tool calls the provider ran in the response (web
  search, code execution) are included, with their type (`extension`).
- If any call in the response has no id, leave `gen_ai.tool.call.id` unset for the record:
  a shorter id array would pair names with the wrong ids.
- No `gen_ai.tool.call.count`. `MV_COUNT(gen_ai.tool.call.id)` gives it.
- `gen_ai.tool.call.arguments` and `gen_ai.tool.call.result` stay unset: they hold one call. The
  arguments are in each `tool_call` part of `gen_ai.output.messages`.
- `gen_ai.response.id` joins a response to its calls when there is no trace id. Set it only
  from a real completion id. When the API returns none (Bedrock Converse), leave it unset.
- `gen_ai.operation.name` keeps the invocation's value (`chat`). `event.action` keeps the native
  verb. #22225's `event.action: tool_call_requested` applies only to calls split into their own
  documents before ingest, which no ingest-pipeline integration does.

The README of a package using option B says that the arrays keep generation order in
`_source`, that keyword doc values (aggregations, ES|QL, ML datafeeds) are sorted and
deduplicated so the name-to-id pairing exists only in `_source`, and that
`MV_COUNT(gen_ai.tool.call.id)` counts the calls.

---

## 5. Linking a call to its result

#22225 section 2 asks that `gen_ai.tool.call.result` go on the record where the result is first
seen, with the originating `gen_ai.tool.call.id`, and that failed calls set
`event.outcome: failure` and `error.type`.

- **Execution-side records (option A)** apply this as written: the record is the call, so the
  result, the call id and the outcome all describe it.
- **Provider logs (option B)** have a conflict, raised on #22225 on 2026-11-20 and not answered
  on that date. One invocation record holds results of earlier calls in its request and new
  calls in its response. Adding result ids to `gen_ai.tool.call.id` mixes answered calls with
  new ones, and a failed tool would mark a successful invocation as failed. Until #22225
  answers:
  - results stay in `gen_ai.input.messages` as `tool_call_response` parts (`id`, `response`)
    under `role: tool`;
  - `gen_ai.tool.call.id` and the other tool arrays hold only the response's calls;
  - `gen_ai.tool.call.result` stays unset;
  - `event.outcome` and `error.*` describe the invocation, not the tools; a native tool status
    (Bedrock `toolResult.status`) stays inside the part.

  A gap report lists `gen_ai.tool.call.result` on provider-log streams as an open question
  citing #22225, not as a gap.
- Sources that log only a result size (Claude Code / Cowork `tool_result_size_bytes`) leave
  `gen_ai.tool.call.result` unset.

---

## 6. Event categorization

| Record | `event.category` / `event.type` |
|---|---|
| A tool call derived from a provider log (the model only requested it) | unset. Select on `gen_ai.operation.name` and `event.action`. |
| An execution-side tool record | by what the tool did, when known: file tools → `file`, shell tools → `process`, fetch tools → `web` or `network`, permission decisions → `iam` (as `claude_code` does since #19967) |
| Nothing in the ECS vocabulary fits | unset |

Don't change the categorization a package already gives its inference records unless the
report shows it is wrong.

---

## 7. Identity

### Callers: `user.name` is the stable principal

A per-identity baseline needs one value per caller across sessions (#22225 section 3).
`user.name` holds the principal that stays the same; `user.id` may keep the raw value. Each
package documents in its README how it derives `user.name`.

AWS ARNs (Bedrock, AgentCore), parsed the way `aws.cloudtrail` does:

| ARN form | `user.id` | `user.name` | Also |
|---|---|---|---|
| `arn:aws:sts::<account>:assumed-role/<role>/<session>` | full ARN | `<role>` | `<session>` to `related.user`; to `user.email` when it is an email address, with its local part also in `related.user` |
| `arn:aws:iam::<account>:user/[<path>/]<name>` | full ARN | `<name>` (last segment) | |
| `arn:aws:sts::<account>:federated-user/<name>` | full ARN | `<name>` | |
| `arn:aws:iam::<account>:root` and other principals | full ARN | unset | |

The session segment of an assumed role changes per session or invocation. It is never
`user.name`. Sources whose `user.id` is already stable (an account email, a user id) need no
change, but their README still says which field is the principal.

The grok processor is in `genai-pipeline-patterns.md` (*Identity*).

### Agents: `gen_ai.agent.*`

Set `gen_ai.agent.id` / `gen_ai.agent.name` only where a hosted agent exists: AgentCore
runtime (agent runtime ARN and name), OTel `invoke_agent` spans, ChatGPT Enterprise custom
agents, Bedrock Agents. The agent is a baseline key separate from the caller: never put it in
`user.*`, and never fill `gen_ai.agent.*` from the caller.

---

## 8. Tool definitions

Each `gen_ai.tool.definitions` entry carries at least `type`, `name` and `description`, and
`parameters` when the source has a schema (#22225 section 4).

- `description` is populated on security streams although OTel makes it opt-in: poisoning and
  look-alike detections key on it. The README states the deviation.
- `type` is an OTel `gen_ai.tool.type` value, never the native type:

| `type` | Native tools |
|---|---|
| `function` | Tools the caller runs: custom and function tools, Converse `toolSpec`, Gemini `functionDeclarations`, Anthropic client tools (`bash_*`, `text_editor_*`, `computer_*`, `memory_*`), OpenAI `function`, `custom`, `computer_use_preview`, `local_shell`, `shell`, `apply_patch`. Also AgentCore gateway target tools, whatever the target kind (#20889; the RFC 0060 example) |
| `datastore` | Retrieval: OpenAI `file_search`, knowledge base retrieval, Gemini `retrieval` |
| `extension` | Server-side, built-in and MCP tools: web search, code execution, Converse `systemTool`, `mcp`, ChatGPT Enterprise MCP connectors (#22225) |

Where a source isn't in the table, use the package's sub-issue if it gives a type, else the
OTel definitions (catalog, `gen_ai.tool.type`), and say which in the Basis.

- A built-in tool with no name takes its native type as `name` (for example
  `web_search_20250305`).
- On option B records, `gen_ai.tool.type[i]` is the type of the definition with the same name
  as `gen_ai.tool.name[i]`, or `function` when the request has no such definition.
- The native type stays visible in the raw body; it is not copied to another field.

---

## 9. Changing a published field

### Change classes

Every row of a gap report states what the change does to published data:

| Change | Meaning |
|---|---|
| **New** | The package does not set the field on this record type today, even if it sets it on other record types. Setting it changes nothing. |
| **Additive** | The field is set on this record type today, and the change only adds to it: a new key or part type inside a `flattened` field, a mapping parameter that stops rejections. A release whose rows are all New or Additive is an additive release. |
| **Breaking** | An existing field changes value, type or shape, or is renamed or removed. This includes the removal of a deprecated field. Adding `ignore_above` or a depth cap to a published field is not Breaking: it only stops rejections (Additive). |
| **No change** | Already correct. |

Not a change class: the `ecs.version` value the pipeline sets, and a pin bump. They are
required housekeeping, not a change to the data (*No change*).

Change is measured against the **last released version** of the package: that is the data
users have and consumers read. When the checkout holds unreleased work (an open PR branch), a
field the branch already adds is still *New*, with Basis `PR #N`, and its status says what the
branch does. A field the branch changes is *Breaking* only if the released version publishes
it differently. Values new in the unreleased branch can still change without a breaking
release.

And where the expected value comes from:

| Basis | Meaning |
|---|---|
| `main` | Read in the package source or its sample events, at a named commit |
| `issue #N` | Stated in a public issue (#22224, #22225, the package's sub-issue) and not re-checked |
| `PR #N` | Implemented in an open pull request, at a named head commit |
| `RFC` | Defined in an accepted ECS RFC that no release includes yet |
| `proposal` | This skill's own convention or recommendation, not confirmed by an issue or PR |

### Consumers first

Before any Breaking change, find what reads the field:

1. **Detection rules**: elastic/detection-rules, every rule whose query or
   `related_integrations` names the package. Code search misses dotted field names, so read
   the rules: `git clone --depth 1 https://github.com/elastic/detection-rules` and
   `grep -rl '<package>' rules*/ | xargs grep -n '<field>'`.
2. **ML jobs**: anomaly-detection job and datafeed configurations that read the package's
   data: in the package's `kibana/` assets, in other integration packages that ship ML modules
   (`grep -rl '<field>' packages/*/kibana/ml_module`, for example `security_ai`), and in
   elastic/kibana's ML module definitions.
3. **The package's own assets**: dashboards, saved searches, transforms (`grep -r '<field>'
   packages/<pkg>/kibana packages/<pkg>/elasticsearch`).
4. **Kibana solution code** that names the package or the field (elastic/kibana, for example
   Security and Cloud Security integration-specific code).
5. **The tracking issue**: owners of rules and jobs often list what they read.

The report lists, per Breaking row, how many consumers were found and where. It names public
files only.

### Release sequence for Breaking rows

1. **Minor release: add.** Write the new field (or copy the current value to `event.action` or
   the vendor namespace) next to the old one. Mark the old field deprecated in its field
   `description` (`Deprecated: use <new field>. Removed in the next major version.`). The
   changelog entry names old and new field.
2. **Consumers move.** Rules, ML jobs and dashboards switch to the new field. Their version
   gating is the consumer owners' decision.
3. **Next major: remove.** Remove the old field, with a `breaking-change` changelog entry and a
   migration table in the README. Release it only after the consumer updates are released.

Never add and remove in the same release. When a rule matches over the whole request or
response body (system prompt and tool definitions included), the normalized fields don't cover
it: keep a full-body `text` field in the vendor namespace (for `aws_bedrock`,
`aws_bedrock.invocation.input.body_text` and `output.body_text`), added in the minor like any
other replacement, so the rules can move before the major.

**When the package issue agreed something else.** If the package's tracking issue records a
different sequence agreed with the consumers' owners (for example a replacement that ships only
in the major), follow the agreement and list the deviation from this sequence in the report's
*Open questions*, with what the consumers lose (no release to move in).

**When the new field collides with a published one.** If the ECS field's path holds a published
object (`gen_ai.request.model.id` makes `gen_ai.request.model` an object, which the ECS keyword
can't replace in place), the two can't coexist. The minor puts the value in a vendor field
(`aws_bedrock.invocation.model_id`) for consumers to move to; the major replaces the object
with the ECS field. The row is ⚠️ and Breaking.

---

## 10. Content: capture, shape and truncation

- **Capture** is on by default for security data streams where the integration controls it,
  and documented where the user controls it (`genai-source-discovery.md`).
- **Build from the structured body** before it is removed. Never re-parse a serialized string
  copy of the body: a copy built without proper escaping is not valid JSON. When the source's
  only body is a non-JSON serialization (for example Java `Map.toString()` text), parsing it
  is allowed; the report says the extraction is lossy and which values can be lost.
- **Shape**: the OTel message schema, with tool results under `role: tool` and a normalized
  `finish_reason` on each output message (catalog, *Message shapes*).
- **Truncation marker**: when the pipeline removes or cuts content (a body over a size limit, a
  text field cut to a maximum length), it appends a value to `tags` that names the field, for
  example `gen_ai_prompt_removed` or `completion_text_truncated`. Replacing a value by its hash
  counts as removing it. Not a new field. A rule that needs the full content can then tell "no
  match" from "content removed".
- **`flattened` caveat**: flattened fields don't keep object boundaries, so a query can't match
  `type: tool_call` and `name: X` on the same part. Per-call detections use `gen_ai.tool.name`
  and `gen_ai.tool.call.id` (section 4), not the message fields.
