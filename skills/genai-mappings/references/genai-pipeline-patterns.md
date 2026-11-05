# GenAI pipeline patterns

How to populate `gen_ai.*` fields in an ingest pipeline. Field meanings, types, allowed values
and the review checklist live in `genai-field-catalog.md`. This file covers the processors
only. General processor rules (tags, `on_failure`, error message format, `rename` vs `set`)
come from `ingest-pipelines` and still apply.

Aligned with: ECS v9.5.0 `gen_ai`, OTel GenAI semantic conventions JSON schemas.

Every snippet here was run through `_ingest/pipeline/_simulate` on Elasticsearch 9.5, and the
output was indexed into an index mapped per the catalog's field definition rules.

---

## Layout

- Put the GenAI processors in a dedicated sub-pipeline, for example
  `elasticsearch/ingest_pipeline/genai.yml`, called from `default.yml` after the vendor
  payload is parsed:
  ```yaml
  - pipeline:
      tag: pipeline_genai
      name: '{{ IngestPipeline "genai" }}'
      if: ctx.vendor?.request_body != null || ctx.vendor?.response_body != null
  ```
- Decode serialized bodies into a temporary field (`_temp.*`), build `gen_ai.*` from it, and
  `remove` the temporary field at the end.
- Give every `script` a `description` that says which vendor format it handles.
- OTel-native streams (`input: otelcol`): write to `attributes.gen_ai.*` instead of top-level
  `gen_ai.*`. The snippets below use top-level paths; change the prefix. Only write ECS field
  names there too.
- Never write a `gen_ai.*` field that is not in the pinned ECS release (catalog rule 3).
  Values without an ECS field stay in the vendor namespace.

---

## Constants and lookups

### Provider

When the stream has a single provider, prefer the `constant_keyword` definition (catalog rule 4)
and set nothing. Otherwise:

```yaml
- set:
    tag: set_gen_ai_provider_name
    field: gen_ai.provider.name
    value: aws.bedrock
```

Per-record provider (gateways, multi-backend products): map the vendor value through a lookup.
Unknown values are lowercased, never invented. The keys below are LiteLLM provider names as an
example. Take the real list from the vendor's documentation.

```yaml
- script:
    tag: script_set_gen_ai_provider_name
    description: Map the LiteLLM provider to the OTel gen_ai.provider.name value.
    lang: painless
    if: ctx.vendor?.provider instanceof String && ctx.vendor.provider != ''
    params:
      providers:
        openai: openai
        anthropic: anthropic
        bedrock: aws.bedrock
        azure: azure.ai.openai
        azure_ai: azure.ai.inference
        vertex_ai: gcp.vertex_ai
        gemini: gcp.gemini
        mistral: mistral
        cohere: cohere
        groq: groq
        deepseek: deepseek
        xai: x_ai
    source: |
      def p = ctx.vendor.provider.toLowerCase();
      ctx.gen_ai = ctx.gen_ai ?: new HashMap();
      ctx.gen_ai.provider = ['name': params.providers.getOrDefault(p, p)];
```

### Operation

Map vendor operation names to OTel values. Leave unmapped values unset. The raw value goes to
`event.action`.

```yaml
- script:
    tag: script_set_gen_ai_operation_name
    description: Map the vendor operation to an OTel gen_ai.operation.name value. Unknown operations leave the field unset.
    lang: painless
    if: ctx.vendor?.operation instanceof String
    params:
      operations:
        ChatCompletions_Create: chat
        Completions_Create: text_completion
        Embeddings_Create: embeddings
    source: |
      def op = params.operations.get(ctx.vendor.operation);
      if (op != null) {
        ctx.gen_ai = ctx.gen_ai ?: new HashMap();
        ctx.gen_ai.operation = ['name': op];
      }
```

---

## Decoding serialized bodies

```yaml
- json:
    tag: json_request_body
    field: vendor.request_body
    target_field: _temp.request
    if: ctx.vendor?.request_body instanceof String && ctx.vendor.request_body.startsWith('{')
    on_failure:
      - append:
          field: error.message
          value: 'Processor {{{_ingest.on_failure_processor_type}}} with tag {{{_ingest.on_failure_processor_tag}}} in pipeline {{{_ingest.on_failure_pipeline}}} failed with message: {{{_ingest.on_failure_message}}}'
```

Handle both encodings when the source sometimes sends an object and sometimes a string: guard
the `json` processor with `instanceof String`, and add a `set` with `copy_from` guarded by
`instanceof Map`.

---

## Scalars and numbers

```yaml
- set:
    tag: set_gen_ai_request_model
    field: gen_ai.request.model
    copy_from: _temp.request.model
    ignore_empty_value: true
- convert:
    tag: convert_gen_ai_request_temperature
    field: _temp.request.temperature
    target_field: gen_ai.request.temperature
    type: double
    ignore_missing: true
    on_failure:
      - append:
          field: error.message
          value: 'Processor {{{_ingest.on_failure_processor_type}}} with tag {{{_ingest.on_failure_processor_tag}}} in pipeline {{{_ingest.on_failure_pipeline}}} failed with message: {{{_ingest.on_failure_message}}}'
```

Counts and `seed` → `type: long`. `temperature`, `top_p`, `top_k`, penalties → `type: double`.

### Arrays of strings (`stop_sequences`, `encoding_formats`)

The source may send a string or an array:

```yaml
- script:
    tag: script_set_gen_ai_request_stop_sequences
    lang: painless
    if: ctx._temp?.request?.stop != null
    source: |
      def s = ctx._temp.request.stop;
      List out = s instanceof List ? new ArrayList(s) : [s.toString()];
      if (!out.isEmpty()) {
        ctx.gen_ai = ctx.gen_ai ?: new HashMap();
        ctx.gen_ai.request = ctx.gen_ai.request ?: new HashMap();
        ctx.gen_ai.request.stop_sequences = out;
      }
```

---

## Token totals

`gen_ai.usage.input_tokens` must include cached tokens, and `output_tokens` must include
reasoning tokens. Copy the provider's total when it already includes them (OpenAI
`prompt_tokens`/`completion_tokens`, Gemini `promptTokenCount`). Sum when it does not:

```yaml
- script:
    tag: script_set_gen_ai_usage_input_tokens
    description: Anthropic input_tokens excludes cached tokens; OTel requires the total.
    lang: painless
    if: ctx._temp?.response?.usage?.input_tokens instanceof Number
    source: |
      def u = ctx._temp.response.usage;
      long total = ((Number) u.input_tokens).longValue();
      if (u.cache_read_input_tokens instanceof Number) { total += ((Number) u.cache_read_input_tokens).longValue(); }
      if (u.cache_creation_input_tokens instanceof Number) { total += ((Number) u.cache_creation_input_tokens).longValue(); }
      ctx.gen_ai = ctx.gen_ai ?: new HashMap();
      ctx.gen_ai.usage = ctx.gen_ai.usage ?: new HashMap();
      ctx.gen_ai.usage.input_tokens = total;
```

Gemini: `output_tokens = candidatesTokenCount + thoughtsTokenCount`. Usage reports split by
token kind: sum all input kinds for `input_tokens`.

ECS has no field for the separate cache and reasoning counts. Keep them in the vendor
namespace under their source names (`<integration>.<data_stream>.cache_read_input_tokens`), and
make sure they are copied there before `_temp` is removed.

---

## Messages

Build `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.system_instructions` and
`gen_ai.tool.definitions` in one `script` per vendor format. The target shape is in the
catalog's *Message shapes* section. Rules the scripts follow:

- Every message is `{role, parts: [...]}`. Every part has a `type`.
- Content that is a string becomes one `text` part. Unknown block types are kept as
  `{type: <vendor type>}` so that their presence is still visible. Do not drop them silently,
  and do not copy large binary data (images, base64) into the part.
- Tool arguments and tool results that arrive as JSON strings are decoded. If decoding fails,
  or the value is a scalar, wrap it as `[{type: text, content: <string>}]`. (OTel requires an
  object and defines no wrapper; this is the skill's convention, chosen to match the part
  shape.)
- `finish_reason` in each output message uses the OTel value where one exists.
  `gen_ai.response.finish_reasons` keeps the provider's values.
- Reasoning blocks become `reasoning` parts. Redacted or encrypted reasoning is not content.
- Never assign a string to a `flattened` field. Only assign `Map` or `List` values.

### OpenAI Chat Completions format

Covers Azure OpenAI / Azure AI Foundry gateway bodies, LiteLLM OpenAI-format payloads and any
OpenAI-compatible API. System/developer messages stay in `input.messages` (OTel: they are part
of the chat history).

```yaml
- script:
    tag: script_normalize_openai_chat_messages
    description: Normalize OpenAI Chat Completions messages and choices into the OTel GenAI message shape.
    lang: painless
    if: ctx._temp?.request?.messages instanceof List || ctx._temp?.response?.choices instanceof List
    source: |
      Object decode(def v) {
        if (v instanceof String) {
          try { return Json.load(v); } catch (Exception e) { return [['type': 'text', 'content': v]]; }
        }
        return v;
      }
      List textParts(def content) {
        List out = new ArrayList();
        if (content instanceof String) {
          if (!content.isEmpty()) { out.add(['type': 'text', 'content': content]); }
        } else if (content instanceof List) {
          for (def c : content) {
            if (!(c instanceof Map)) { continue; }
            if (c.type == 'text' && c.text != null) {
              out.add(['type': 'text', 'content': c.text]);
            } else if (c.type != null) {
              out.add(['type': c.type]);
            }
          }
        }
        return out;
      }
      Map toolCall(def tc) {
        Map p = ['type': 'tool_call', 'id': tc.id, 'name': tc.function?.name];
        def a = decode(tc.function?.arguments);
        if (a != null) { p.arguments = a; }
        return p;
      }
      Map g = ctx.gen_ai ?: new HashMap();
      List input = new ArrayList();
      for (def m : ctx._temp?.request?.messages ?: []) {
        if (!(m instanceof Map) || m.role == null) { continue; }
        List parts;
        if (m.role == 'tool') {
          parts = [['type': 'tool_call_response', 'id': m.tool_call_id, 'response': decode(m.content)]];
        } else {
          parts = textParts(m.content);
          for (def tc : m.tool_calls ?: []) { parts.add(toolCall(tc)); }
        }
        input.add(['role': m.role, 'parts': parts]);
      }
      if (!input.isEmpty()) { g.input = ['messages': input]; }
      List output = new ArrayList();
      List reasons = new ArrayList();
      List toolNames = new ArrayList();
      List toolIds = new ArrayList();
      Map normalized = ['tool_calls': 'tool_call', 'function_call': 'tool_call'];
      for (def ch : ctx._temp?.response?.choices ?: []) {
        if (!(ch instanceof Map)) { continue; }
        Map msg = ch.message instanceof Map ? ch.message : new HashMap();
        List parts = textParts(msg.content);
        for (def tc : msg.tool_calls ?: []) {
          parts.add(toolCall(tc));
          if (tc.function?.name != null) { toolNames.add(tc.function.name); }
          if (tc.id != null) { toolIds.add(tc.id); }
        }
        Map om = ['role': msg.role ?: 'assistant', 'parts': parts];
        if (ch.finish_reason != null) {
          om.finish_reason = normalized.getOrDefault(ch.finish_reason, ch.finish_reason);
          reasons.add(ch.finish_reason);
        }
        output.add(om);
      }
      if (!output.isEmpty()) { g.output = ['messages': output]; }
      if (!reasons.isEmpty()) {
        g.response = g.response ?: new HashMap();
        g.response.finish_reasons = reasons;
      }
      if (!toolNames.isEmpty()) {
        g.tool = ['name': toolNames];
        if (!toolIds.isEmpty()) { g.tool.call = ['id': toolIds]; }
      }
      if (!g.isEmpty()) { ctx.gen_ai = g; }
```

Add `tools[].function` → `gen_ai.tool.definitions` (`{type: 'function', name, description,
parameters}`) in the same script when the request carries tools.

### Anthropic Messages format

Covers the Anthropic API, Bedrock `InvokeModel` for Claude models, and Anthropic Compliance API
request bodies. `system` goes to `system_instructions`. `thinking` becomes `reasoning`. Tool
results stay in the `user` turn where Anthropic puts them.

```yaml
- script:
    tag: script_normalize_anthropic_messages
    description: Normalize Anthropic Messages request and response bodies into the OTel GenAI message shape.
    lang: painless
    if: ctx._temp?.request instanceof Map || ctx._temp?.response instanceof Map
    source: |
      List toParts(def content) {
        List out = new ArrayList();
        if (content instanceof String) {
          if (!content.isEmpty()) { out.add(['type': 'text', 'content': content]); }
          return out;
        }
        if (!(content instanceof List)) { return out; }
        for (def b : content) {
          if (!(b instanceof Map)) { continue; }
          if (b.type == 'text' && b.text != null) {
            out.add(['type': 'text', 'content': b.text]);
          } else if (b.type == 'thinking' && b.thinking != null) {
            out.add(['type': 'reasoning', 'content': b.thinking]);
          } else if (b.type == 'tool_use') {
            Map p = ['type': 'tool_call', 'id': b.id, 'name': b.name];
            if (b.input instanceof Map) { p.arguments = b.input; }
            out.add(p);
          } else if (b.type == 'tool_result') {
            out.add(['type': 'tool_call_response', 'id': b.tool_use_id, 'response': b.content]);
          } else if (b.type != null) {
            out.add(['type': b.type]);
          }
        }
        return out;
      }
      Map rb = ctx._temp?.request;
      Map resp = ctx._temp?.response;
      Map g = ctx.gen_ai instanceof Map ? ctx.gen_ai : new HashMap();
      if (rb != null) {
        List sys = toParts(rb.system);
        if (!sys.isEmpty()) { g.system_instructions = sys; }
        List input = new ArrayList();
        for (def m : rb.messages ?: []) {
          if (m instanceof Map && m.role != null) { input.add(['role': m.role, 'parts': toParts(m.content)]); }
        }
        if (!input.isEmpty()) { g.input = ['messages': input]; }
        if (rb.tools instanceof List && !rb.tools.isEmpty()) {
          List defs = new ArrayList();
          for (def t : rb.tools) {
            if (!(t instanceof Map)) { continue; }
            Map d = ['type': t.type ?: 'function', 'name': t.name];
            if (t.description != null) { d.description = t.description; }
            if (t.input_schema != null) { d.parameters = t.input_schema; }
            defs.add(d);
          }
          g.tool = ['definitions': defs];
        }
      }
      if (resp != null) {
        Map fr = ['end_turn': 'stop', 'stop_sequence': 'stop', 'max_tokens': 'length', 'tool_use': 'tool_call', 'refusal': 'content_filter'];
        Map om = ['role': resp.role ?: 'assistant', 'parts': toParts(resp.content)];
        if (resp.stop_reason != null) {
          om.finish_reason = fr.getOrDefault(resp.stop_reason, resp.stop_reason);
          g.response = g.response ?: new HashMap();
          g.response.finish_reasons = [resp.stop_reason];
        }
        g.output = ['messages': [om]];
      }
      if (!g.isEmpty()) { ctx.gen_ai = g; }
```

The `redacted_thinking` block falls into the generic branch and keeps only its type: its data
is encrypted.

### Other formats

Adapt one of the two scripts. The table lists the differences:

| Format | Messages | System | Tool call / result | Reasoning | Finish reason → OTel |
|---|---|---|---|---|---|
| Bedrock Converse | `messages[].content[]` blocks keyed by name (`{text}`, `{toolUse}`, `{toolResult}`) | `system[].text` | `toolUse{toolUseId,name,input}` / `toolResult{toolUseId,content}` | `reasoningContent.reasoningText.text` | `end_turn`,`stop_sequence`→`stop`; `max_tokens`→`length`; `tool_use`→`tool_call`; `guardrail_intervened`,`content_filtered`→`content_filter` |
| Gemini / Vertex | `contents[]` with `role` `user`/`model` (→`assistant`), `parts[]` | `systemInstruction.parts[].text` | `functionCall{name,args,id?}` / `functionResponse{name,response,id?}` | parts with `thought: true` | `STOP`→`stop`; `MAX_TOKENS`→`length`; `SAFETY`,`RECITATION`,`BLOCKLIST`,`PROHIBITED_CONTENT`,`SPII`→`content_filter`; `MALFORMED_FUNCTION_CALL`→`error` |
| OpenAI Responses | `input` (string or items) | `instructions` | `output[type=function_call]{call_id,name,arguments}`; results are `function_call_output` items in a later `input` | `output[type=reasoning].summary[].text` | from `status`/`incomplete_details.reason`: `completed`→`stop`; `max_output_tokens`→`length`; `content_filter`→`content_filter`; `failed`/`cancelled`→`error` |

---

## Tool execution records

Records that describe **one** tool call (agent gateway logs, tool result events, connector
calls) set the scalar tool fields directly:

```yaml
- set:
    tag: set_gen_ai_operation_name_execute_tool
    field: gen_ai.operation.name
    value: execute_tool
- set:
    tag: set_gen_ai_tool_name
    field: gen_ai.tool.name
    copy_from: vendor.tool_name
    ignore_empty_value: true
- script:
    tag: script_set_gen_ai_tool_call_result
    description: Decode the tool result and make sure a scalar never reaches the flattened field.
    lang: painless
    if: ctx.vendor?.tool_result != null
    source: |
      def v = ctx.vendor.tool_result;
      if (v instanceof String) {
        try { v = Json.load(v); } catch (Exception e) { }
      }
      if (!(v instanceof Map) && !(v instanceof List)) {
        v = [['type': 'text', 'content': v.toString()]];
      }
      ctx.gen_ai = ctx.gen_ai ?: new HashMap();
      ctx.gen_ai.tool = ctx.gen_ai.tool ?: new HashMap();
      ctx.gen_ai.tool.call = ctx.gen_ai.tool.call ?: new HashMap();
      ctx.gen_ai.tool.call.result = v;
```

`Json.load("42")` returns a number, so the scalar check runs after decoding, not instead of it.
Use the same script for `gen_ai.tool.call.arguments`.

When a product hides the real tool name behind a placeholder (for example `mcp_tool`), resolve
the real name from the tool parameters before setting `gen_ai.tool.name`, and keep the
placeholder in the vendor namespace.

Extract `file.path`, `url.full`/`url.domain`, `destination.address` and
`process.command_line` from the decoded arguments of file, fetch and shell tools.

---

## Finishing

```yaml
- remove:
    tag: remove_temp
    field: _temp
    ignore_missing: true
```

---

## Test fixtures

Pipeline test inputs must cover, per vendor format:

- Content capture **off** (no bodies): only identity, model and usage fields appear
- String content and block/array content
- A system prompt as a string and as blocks (where the format allows both)
- A response with tool calls, including more than one call
- A tool result as JSON, as plain text and as a number
- Reasoning/thinking content, and redacted reasoning
- Several choices/candidates (where the API allows `n` / `candidateCount`)
- A body that is not valid JSON (expect `error.message`, no partial `gen_ai` content)
- Cached and reasoning token counts (check the totals)

Pipeline tests validate fields against their definitions but do **not** index into the real
mapping, so they cannot catch `flattened` or `nested` rejections. System tests do. Add at least
one system test document whose message content is longer than 32766 bytes.
