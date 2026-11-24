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
and set nothing, or `set` the constant.

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

Map vendor operation names to OTel values with the same kind of lookup. The difference is the
fallback: an unmapped value leaves the field unset (`params.operations.get(...)`, and set the
field only when the result is not null). The raw value goes to `event.action`. The native-to-OTel
values per source are in `genai-detection-conventions.md`, section 3.

---

## Decoding serialized bodies

Decode with a `json` processor into `_temp.*`, guarded by
`ctx.vendor?.request_body instanceof String && ctx.vendor.request_body.startsWith('{')`, with
the `on_failure` handler that `ingest-pipelines` defines. When the source sometimes sends an
object and sometimes a string, also add a `set` with `copy_from` guarded by `instanceof Map`.

---

## Scalars and numbers

- Scalars: `set` with `copy_from` and `ignore_empty_value: true`.
- Numbers: `convert` from the decoded body into the `gen_ai.*` field. Counts and `seed` →
  `type: long`. `temperature`, `top_p`, `top_k`, penalties → `type: double`.
- Arrays of strings (`stop_sequences`, `encoding_formats`): the source may send a string or an
  array. Wrap a string into a one-element list in a `script`, and don't write an empty list.

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
`gen_ai.tool.definitions` in one `script` per vendor format. The message fields are for chat,
text completion and content generation; embeddings, rerank and image records leave them
unset. The target shape is in the
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
      List defs = new ArrayList();
      for (def t : ctx._temp?.request?.tools ?: []) {
        if (!(t instanceof Map)) { continue; }
        Map fn = t.function instanceof Map ? t.function : t;
        if (fn.name == null) { continue; }
        Map d = ['type': 'function', 'name': fn.name];
        if (fn.description != null) { d.description = fn.description; }
        if (fn.parameters != null) { d.parameters = fn.parameters; }
        defs.add(d);
      }
      if (!defs.isEmpty()) { g.tool = ['definitions': defs]; }
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
        // Option B: the response's calls, in generation order. Chat Completions tools are all
        // client-side functions, so every type is function.
        g.tool = g.tool instanceof Map ? g.tool : new HashMap();
        g.tool.name = toolNames;
        List toolTypes = new ArrayList();
        for (def n : toolNames) { toolTypes.add('function'); }
        g.tool.type = toolTypes;
        // An id array shorter than the name array would pair names with the wrong ids.
        if (toolIds.size() == toolNames.size()) { g.tool.call = ['id': toolIds]; }
      }
      if (!g.isEmpty()) { ctx.gen_ai = g; }
```

`tools[].function` becomes `gen_ai.tool.definitions` entries `{type: function, name,
description, parameters}`. The name, type and id arrays list only the response's calls: the
`tool_calls` of earlier assistant turns in `messages[]` are history and stay in
`gen_ai.input.messages` (`genai-detection-conventions.md`, section 4).

### Anthropic Messages format

Covers the Anthropic API, Bedrock `InvokeModel` for Claude models, and Anthropic Compliance API
request bodies. `system` goes to `system_instructions`. `thinking` becomes `reasoning`.
Anthropic sends tool results inside a `user` turn. OTel puts them in a `role: tool` message, so
the script splits that turn and keeps the order of its blocks (#22225 section 5).

```yaml
- script:
    tag: script_normalize_anthropic_messages
    description: >-
      Normalize Anthropic Messages request and response bodies into the OTel GenAI message
      shape. Tool results move from the user turn to a role tool message. Tool definition types
      become OTel values: client tools are function, server tools are extension. The tool name,
      type and id arrays list the response's tool calls in generation order.
    lang: painless
    if: ctx._temp?.request instanceof Map || ctx._temp?.response instanceof Map
    params:
      function_tool_prefixes:
        - bash_
        - text_editor_
        - computer_
        - memory_
      finish_reasons:
        end_turn: stop
        stop_sequence: stop
        max_tokens: length
        model_context_window_exceeded: length
        tool_use: tool_call
        refusal: content_filter
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
      String toolType(def nativeType, Map p) {
        if (!(nativeType instanceof String) || nativeType == 'custom') { return 'function'; }
        for (def x : p.function_tool_prefixes) {
          if (nativeType.startsWith(x)) { return 'function'; }
        }
        return 'extension';
      }
      Map rb = ctx._temp?.request;
      Map resp = ctx._temp?.response;
      Map g = ctx.gen_ai instanceof Map ? ctx.gen_ai : new HashMap();
      Map defTypes = new HashMap();
      if (rb != null) {
        List sys = toParts(rb.system);
        if (!sys.isEmpty()) { g.system_instructions = sys; }
        List input = new ArrayList();
        for (def m : rb.messages ?: []) {
          if (!(m instanceof Map) || m.role == null) { continue; }
          List cur = new ArrayList();
          String curRole = m.role;
          for (def p : toParts(m.content)) {
            String r = p.type == 'tool_call_response' ? 'tool' : m.role;
            if (r != curRole && !cur.isEmpty()) {
              input.add(['role': curRole, 'parts': cur]);
              cur = new ArrayList();
            }
            curRole = r;
            cur.add(p);
          }
          input.add(['role': curRole, 'parts': cur]);
        }
        if (!input.isEmpty()) { g.input = ['messages': input]; }
        if (rb.tools instanceof List && !rb.tools.isEmpty()) {
          List defs = new ArrayList();
          for (def t : rb.tools) {
            if (!(t instanceof Map)) { continue; }
            // A built-in tool without a name takes its native type as name.
            Map d = ['type': toolType(t.type, params), 'name': t.name ?: t.type];
            if (t.description != null) { d.description = t.description; }
            if (t.input_schema != null) { d.parameters = t.input_schema; }
            defs.add(d);
            if (d.name != null) { defTypes.putIfAbsent(d.name, d.type); }
          }
          g.tool = ['definitions': defs];
        }
      }
      if (resp != null) {
        Map om = ['role': resp.role ?: 'assistant', 'parts': toParts(resp.content)];
        if (resp.stop_reason != null) {
          om.finish_reason = params.finish_reasons.getOrDefault(resp.stop_reason, resp.stop_reason);
          g.response = g.response ?: new HashMap();
          g.response.finish_reasons = [resp.stop_reason];
        }
        g.output = ['messages': [om]];
        List names = new ArrayList();
        List types = new ArrayList();
        List ids = new ArrayList();
        for (def p : om.parts) {
          if (p.type == 'tool_call' && p.name != null) {
            names.add(p.name);
            types.add(defTypes.getOrDefault(p.name, 'function'));
            if (p.id != null) { ids.add(p.id); }
          }
        }
        if (!names.isEmpty()) {
          g.tool = g.tool instanceof Map ? g.tool : new HashMap();
          g.tool.name = names;
          g.tool.type = types;
          if (ids.size() == names.size()) { g.tool.call = ['id': ids]; }
        }
      }
      if (!g.isEmpty()) { ctx.gen_ai = g; }
```

The `redacted_thinking` block falls into the generic branch and keeps only its type: its data
is encrypted. Server tools (`web_search_*`, `code_execution_*`) are `extension`; add the
retrieval tools of the API version you map to a `datastore` list if it has any.

### Other formats

Adapt one of the two scripts. The table lists the differences:

| Format | Messages | System | Tool call / result | Reasoning | Finish reason → OTel |
|---|---|---|---|---|---|
| Bedrock Converse | `messages[].content[]` blocks keyed by name (`{text}`, `{toolUse}`, `{toolResult}`) | `system[].text` | `toolUse{toolUseId,name,input}` → `tool_call`; `toolResult{toolUseId,content,status}` → `tool_call_response` in a **`role: tool`** message (Bedrock sends it in a `user` turn; split it as the Anthropic script does) | `reasoningContent.reasoningText.text` | see the table below |
| Gemini / Vertex | `contents[]` with `role` `user`/`model` (→`assistant`), `parts[]` | `systemInstruction.parts[].text` | `functionCall{name,args,id?}` / `functionResponse{name,response,id?}` | parts with `thought: true` | `STOP`→`stop`; `MAX_TOKENS`→`length`; `SAFETY`,`RECITATION`,`BLOCKLIST`,`PROHIBITED_CONTENT`,`SPII`→`content_filter`; `MALFORMED_FUNCTION_CALL`→`error` |
| OpenAI Responses | `input` (string or items) | `instructions` | `output[type=function_call]{call_id,name,arguments}`; results are `function_call_output` items in a later `input` (→ `role: tool`) | `output[type=reasoning].summary[].text` | from `status`/`incomplete_details.reason`: `completed`→`stop`; `max_output_tokens`→`length`; `content_filter`→`content_filter`; `failed`/`cancelled`→`error` |

**Worked example: Bedrock `stopReason` → output message `finish_reason`.** The per-message value
uses the OTel enumeration; `gen_ai.response.finish_reasons` keeps the Bedrock value. Values from
the Bedrock Converse API reference; the OTel value is the closest match where none is exact.

| Bedrock `stopReason` | `finish_reason` |
|---|---|
| `end_turn`, `stop_sequence` | `stop` |
| `tool_use` | `tool_call` |
| `max_tokens`, `model_context_window_exceeded` | `length` |
| `guardrail_intervened`, `content_filtered` | `content_filter` |
| `malformed_model_output`, `malformed_tool_use` | `error` |
| anything else | the Bedrock value, unchanged |

---

## Tool execution records

Records that describe **one** tool call (agent gateway logs, tool result events, connector
calls) set the scalar tool fields directly (option A; `genai-detection-conventions.md`,
sections 4 to 8, say which records get `execute_tool`, a tool type, an outcome and a category).
Arguments and results need a script:

```yaml
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

When a gateway prefixes the tool name with its target (`<target>___<tool>`), split it:
`gen_ai.tool.name` gets `<tool>`, and the target stays in the vendor namespace until
`gen_ai.tool.source.*` is released. When a product hides the real tool name behind a
placeholder (for example `mcp_tool`), resolve the real name from the tool parameters before
setting `gen_ai.tool.name`, and keep the placeholder in the vendor namespace.

Extract `file.path`, `url.full`/`url.domain`, `destination.address` and
`process.command_line` from the decoded arguments of file, fetch and shell tools.

---

## Identity

`user.name` holds the stable principal (`genai-detection-conventions.md`, section 7). For AWS
caller ARNs, the same rules as `aws.cloudtrail` (from `aws_bedrock` 2.4.0):

```yaml
- grok:
    tag: grok_user_name_from_identity_arn
    description: >-
      user.name is the IAM user name (without its path), the federated user name, or the role
      name of an assumed role. The session name of an assumed role changes per session, so it
      goes to related.user only. Root and other principals leave user.name unset.
    field: user.id
    patterns:
      - '^arn:[^:]+:iam::[^:]*:user/(?:[^/]+/)*%{NOT_SLASH:user.name}$'
      - '^arn:[^:]+:sts::[^:]*:assumed-role/%{NOT_SLASH:user.name}/%{NOT_SLASH:_temp.user.session_name}$'
      - '^arn:[^:]+:sts::[^:]*:federated-user/%{NOT_SLASH:user.name}$'
    pattern_definitions:
      NOT_SLASH: '[^/]+'
    if: >-
      ctx.user?.id instanceof String && ctx.user.id.startsWith('arn:') &&
      (ctx.user.id.contains(':user/') || ctx.user.id.contains(':assumed-role/') || ctx.user.id.contains(':federated-user/'))
    ignore_failure: true
```

Then append `user.name` and `_temp.user.session_name` to `related.user` (`allow_duplicates:
false`). When the session name is an email address, `aws_bedrock` also copies it to
`user.email`. The README states the derivation.

---

## Flattened safety

Three processors, in this order, at the end of the pipeline (catalog rules 2 and 2b).

### Serialize with `Json.dump`

Any value that must become a JSON string (a subtree over the depth limit, a raw body kept as
text) is made with `Json.dump`. Never concatenate strings or use `toString()`: a `Map`'s
`toString()` is not JSON, and hand-built JSON breaks on quotes and backslashes in the content.

### Empty-value cleanup skips tool schemas

A recursive "drop null and empty values" script changes tool definitions (and, the same way,
`gen_ai.tool.call.arguments` and `.result`, which are what the model and the tool sent: skip
them too where the package sets them): it turns
`enum: ['', null, 'ok']` into `['ok']` and removes empty property schemas, which are part of
the tool interface. Take the subtree out first and put it back after:

```yaml
- script:
    tag: script_drop_empty_values_keep_tool_definitions
    description: >-
      Drop null and empty values recursively. gen_ai.tool.definitions is left out, because
      empty and null values in a tool's parameter schema are part of the tool interface.
    lang: painless
    source: |
      boolean drop(Object o) {
        if (o == null || o == '') {
          return true;
        } else if (o instanceof Map) {
          ((Map) o).values().removeIf(v -> drop(v));
          return ((Map) o).size() == 0;
        } else if (o instanceof List) {
          ((List) o).removeIf(v -> drop(v));
          return ((List) o).size() == 0;
        }
        return false;
      }
      def defs = null;
      if (ctx.gen_ai?.tool instanceof Map && ctx.gen_ai.tool.definitions != null) {
        defs = ctx.gen_ai.tool.remove('definitions');
      }
      drop(ctx);
      if (defs != null) {
        if (!(ctx.gen_ai instanceof Map)) { ctx.gen_ai = new HashMap(); }
        if (!(ctx.gen_ai.tool instanceof Map)) { ctx.gen_ai.tool = new HashMap(); }
        ctx.gen_ai.tool.definitions = defs;
      }
```

Packages without such a script don't need one.

### Depth cap

```yaml
- script:
    tag: script_cap_flattened_depth
    description: >-
      A flattened field rejects the whole document when an object is nested more than 20
      levels deep, which a deep tool schema, tool input or tool result can reach. Store any
      object below max_depth levels as a JSON string. Values within the limit are unchanged.
    lang: painless
    params:
      max_depth: 20
      fields:
        - [gen_ai, input, messages]
        - [gen_ai, output, messages]
        - [gen_ai, system_instructions]
        - [gen_ai, tool, definitions]
        - [gen_ai, tool, call, arguments]
        - [gen_ai, tool, call, result]
    source: |
      int depth(def v) {
        int d = 0;
        if (v instanceof Map) {
          for (def x : v.values()) { d = (int) Math.max(d, depth(x)); }
          return d + 1;
        }
        if (v instanceof List) {
          for (def x : v) { d = (int) Math.max(d, depth(x)); }
        }
        return d;
      }
      def cap(def v, int level, int maxDepth) {
        if (v instanceof Map) {
          if (level > maxDepth) { return Json.dump(v); }
          Map out = new HashMap();
          for (def e : v.entrySet()) { out.put(e.getKey(), cap(e.getValue(), level + 1, maxDepth)); }
          return out;
        }
        if (v instanceof List) {
          List out = new ArrayList();
          for (def x : v) { out.add(cap(x, level, maxDepth)); }
          return out;
        }
        return v;
      }
      for (def path : params.fields) {
        def parent = ctx;
        for (int i = 0; i < path.size() - 1 && parent instanceof Map; i++) {
          parent = parent.get(path.get(i));
        }
        if (!(parent instanceof Map)) { continue; }
        String leaf = path.get(path.size() - 1);
        def v = parent.get(leaf);
        if (v != null && depth(v) > params.max_depth) {
          parent.put(leaf, cap(v, 1, params.max_depth));
        }
      }
```

Add to `fields` every vendor field mapped as `flattened`, including raw body copies that
`preserve_duplicate_custom_fields` keeps. Run the cap after the cleanup, so that the strings it
creates are not touched.

---

## Truncation marker

When the pipeline removes content or cuts it to a maximum length, append a tag that names the
field. Not a new field (#22225 section 5):

```yaml
- script:
    tag: script_remove_oversized_request_body
    description: >-
      A keyword copy of the request body longer than 32766 characters would reject the
      document. Remove it and mark the removal in tags.
    lang: painless
    if: ctx.vendor?.request_body instanceof String && ctx.vendor.request_body.length() > 32766
    source: |
      ctx.vendor.remove('request_body');
      if (!(ctx.tags instanceof List)) { ctx.tags = new ArrayList(); }
      if (!ctx.tags.contains('vendor_request_body_removed')) { ctx.tags.add('vendor_request_body_removed'); }
```

Name the tag `<field>_removed` or `<field>_truncated` and list the tags in the README.

---

## Test fixtures

Pipeline test inputs must cover, per vendor format:

- Content capture **off** (no bodies): only identity, model and usage fields appear
- String content and block/array content
- A system prompt as a string and as blocks (where the format allows both)
- A response with tool calls, including more than one call and two calls to the same tool
  (the arrays keep both, in order)
- A request with tool results in a user turn next to text (the results come out under
  `role: tool`)
- A tool result as JSON, as plain text and as a number
- Tool definitions of each native kind (client, server/built-in, MCP, retrieval) and a schema
  with `''`, `null` and empty values
- A tool input or result nested more than 20 levels deep
- Content above each removal or truncation threshold (the tag appears)
- Each identity form the source sends (for AWS: assumed role, IAM user with a path, federated
  user, root), with account ids anonymized
- Reasoning/thinking content, and redacted reasoning
- Several choices/candidates (where the API allows `n` / `candidateCount`)
- A body that is not valid JSON (expect `error.message`, no partial `gen_ai` content)
- Cached and reasoning token counts (check the totals)

Pipeline tests validate fields against their definitions but do **not** index into the real
mapping, so they cannot catch `flattened` or `nested` rejections. System tests do. Add at least
one system test document whose message content is longer than 32766 bytes, and one with a
tool schema deeper than 20 levels. Two things hide the rejection:

- **LogsDB** index mode sets a default `ignore_above` of 8191, so a stack that runs logs data
  streams in LogsDB never shows the length rejection. Also index the long document into an
  index in standard mode with the package's mappings.
- **The failure store** catches rejected documents, so a system test that only counts the
  documents it finds can pass. Check `<data stream>::failures` after the test.
