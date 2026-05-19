# Manifest Rules Reference

Comprehensive rules for `manifest.yml` validation in Elastic integration packages. Covers format_version selection, variable scoping, Handlebars template declarations, routing rules, and YAML structure.

---

## Variable shadowing

### The rule

Fleet variables can be declared at four levels:

1. **Package level** -- `manifest.yml` top-level `vars:`
2. **Policy template level** -- `manifest.yml` under `policy_templates[].vars:`
3. **Input level** -- `manifest.yml` under `policy_templates[].inputs[].vars:`
4. **Data stream level** -- `data_stream/*/manifest.yml` under `streams[].vars:`

A variable declared in an inner scope MUST NOT reuse the name of a variable in an outer scope. This is **variable shadowing** and is rejected by `elastic-package` validation.

### Why it is rejected

When a variable name appears at multiple levels, Fleet cannot determine which value the user intended. The inner declaration shadows the outer one, leading to:
- confusing UI where the same variable appears twice
- ambiguous Handlebars template resolution
- validation failures in `elastic-package check`

### Correct vs incorrect

```yaml
# WRONG -- "api_key" declared at package level AND input level
# manifest.yml
vars:
  - name: api_key          # Package-level
    type: password
    title: API Key
    required: true

policy_templates:
  - name: events
    inputs:
      - type: cel
        vars:
          - name: api_key  # Shadows package-level "api_key"
            type: password
            title: API Key
```

```yaml
# CORRECT -- unique names at each scope
# manifest.yml
vars:
  - name: api_key
    type: password
    title: API Key
    required: true

policy_templates:
  - name: events
    inputs:
      - type: cel
        vars:
          - name: initial_interval  # Different name, no shadow
            type: text
            title: Initial Interval
```

### Common shadowing patterns

| Outer scope | Inner scope | Typical variable |
|-------------|------------|-----------------|
| Package | Input | `api_key`, `url` |
| Package | Data stream | `proxy_url`, `ssl` |
| Policy template | Input | `interval`, `tags` |

### How to detect and fix

1. List all variable names at each scope level across the root `manifest.yml` and all `data_stream/*/manifest.yml` files.
2. Check that no name appears in both an outer and inner scope.
3. If shadowing is found, rename the inner variable to be more specific (e.g., `events_api_key` instead of `api_key`).

---

## Handlebars variable declarations

### The rule

Every Handlebars variable referenced in agent input templates (`*.yml.hbs` files) MUST be declared as a variable in the corresponding manifest. Undeclared variables silently resolve to empty strings, causing broken configs at runtime.

Variables can be declared at any manifest scope:
- Package-level: `manifest.yml` -> `vars:`
- Policy template: `manifest.yml` -> `policy_templates[].vars:`
- Input-level: `manifest.yml` -> `policy_templates[].inputs[].vars:`
- Data stream: `data_stream/*/manifest.yml` -> `streams[].vars:`

### How to check

1. Scan the `.yml.hbs` file for all `{{variable_name}}` references (excluding Handlebars helpers and built-in variables).
2. For each variable, verify it exists in one of the manifest scopes above.
3. Flag any variable that is not declared anywhere.

### Correct vs incorrect

```yaml
# CORRECT -- all template variables are declared
# data_stream/events/agent/stream/cel.yml.hbs
interval: {{interval}}
resource.url: {{url}}/api/v1/events
{{#if proxy_url}}
resource.proxy_url: {{proxy_url}}
{{/if}}
{{#if ssl}}
resource.ssl: {{ssl}}
{{/if}}

# data_stream/events/manifest.yml -- variables declared
streams:
  - input: cel
    vars:
      - name: interval
        type: text
        title: Polling Interval
        default: 5m
      - name: url
        type: text
        title: API URL
        required: true
      - name: proxy_url
        type: text
        title: Proxy URL
      - name: ssl
        type: yaml
        title: SSL Configuration
```

```yaml
# WRONG -- "api_version" used in template but not declared
# data_stream/events/agent/stream/cel.yml.hbs
resource.url: {{url}}/api/{{api_version}}/events
#                         ^^^^^^^^^^^^^^^^ NOT in any manifest!
```

### Built-in variables

Some variables are provided by Fleet automatically and do NOT need declaration in manifests:

- `{{data_stream.type}}` -- logs, metrics, etc.
- `{{data_stream.dataset}}` -- the data stream dataset name
- `{{data_stream.namespace}}` -- the namespace
- `{{output}}` -- output configuration

### Handlebars helpers (not variables)

These are control-flow helpers, not variable references. Do not flag them:

- `{{#if var}}...{{/if}}`
- `{{#unless var}}...{{/unless}}`
- `{{#each items as |item|}}...{{/each}}`
- `{{#contains "value" array}}...{{/contains}}`

### Common mistakes

1. **Copy-paste from another integration** -- template references a variable from the source integration that was never added to this package's manifest.
2. **Renamed variable** -- manifest variable was renamed but the template still uses the old name.
3. **Wrong scope** -- variable declared at package level but template expects it at data stream level. This works at runtime, but may confuse users when reviewing the code.

---

## Routing rules configuration

### The rule

When a data stream uses `routing_rules.yml` to route documents to different backing indices based on field values, the data stream manifest **must** declare both:

```yaml
elasticsearch:
  dynamic_dataset: true
  dynamic_namespace: true
```

Without these flags, Elastic Agent does not have write permissions to the dynamically-named data streams that routing rules create. Documents are rejected with permission errors at index time.

### Why both flags are required

- `dynamic_dataset: true` -- allows the data stream name's dataset component to vary based on routing rules (e.g., `logs-mypackage.alerts` vs `logs-mypackage.events`).
- `dynamic_namespace: true` -- allows the namespace component to vary (e.g., routing to a different namespace per tenant).

Even if only one dimension varies, both flags are typically needed because Fleet's permission model grants write access based on the full `{type}-{dataset}-{namespace}` triple.

### Correct vs incorrect

```yaml
# WRONG -- routing_rules.yml exists but manifest lacks dynamic flags
# data_stream/events/manifest.yml
title: Events
type: logs
streams:
  - input: cel
    title: Events

# data_stream/events/routing_rules.yml exists
```

```yaml
# CORRECT -- dynamic flags declared alongside routing_rules
# data_stream/events/manifest.yml
title: Events
type: logs
elasticsearch:
  dynamic_dataset: true
  dynamic_namespace: true
streams:
  - input: cel
    title: Events

# data_stream/events/routing_rules.yml
- source_dataset: events
  rules:
    - target_dataset: alerts
      if: ctx.severity == "critical"
  default_dataset: events
```

### Routing rules file structure

```yaml
# data_stream/*/routing_rules.yml
- source_dataset: <original_dataset>
  rules:
    - target_dataset: <new_dataset>
      if: <painless condition>
      namespace: <optional namespace override>
  default_dataset: <fallback_dataset>
```

### Checklist

1. Does the data stream have a `routing_rules.yml` file?
2. If yes, does the data stream manifest declare `dynamic_dataset: true`?
3. Does it also declare `dynamic_namespace: true`?
4. Are both flags under a properly nested `elasticsearch:` key (not dot-notation)?
5. Are the routing rule conditions valid Painless expressions?
6. Is there a `default_dataset` fallback for unmatched documents?

---

## YAML structure

### The rule

YAML keys must use proper dictionary nesting, not dot-separated flat keys. While some YAML parsers treat `elasticsearch.dynamic_dataset` as a literal key name, Fleet and `elastic-package` expect nested structure.

Dot-notation keys create a single key whose name contains a literal dot, rather than a nested object. This can cause validation failures or silent misinterpretation.

### Correct vs incorrect

```yaml
# WRONG -- dot in key name, creates a single key "elasticsearch.dynamic_dataset"
elasticsearch.dynamic_dataset: true
elasticsearch.dynamic_namespace: true
```

```yaml
# CORRECT -- proper YAML nesting
elasticsearch:
  dynamic_dataset: true
  dynamic_namespace: true
```

```yaml
# WRONG
elasticsearch.source_mode: synthetic
elasticsearch.index_mode: time_series
```

```yaml
# CORRECT
elasticsearch:
  source_mode: synthetic
  index_mode: time_series
```

### Where this applies

This rule applies to all manifest files in the package:
- `manifest.yml` (top-level package manifest)
- `data_stream/*/manifest.yml` (data stream manifests)
- any YAML file validated by `elastic-package`

The most common occurrence is the `elasticsearch` section in data stream manifests, where `dynamic_dataset`, `dynamic_namespace`, `source_mode`, and `index_mode` must be nested under an `elasticsearch:` parent key.

---

## format_version selection

### The rule

The `format_version` field in `manifest.yml` declares which package spec version the package conforms to. Always use the **minimum version that supports the features the package actually uses**, not the latest available spec version.

The current standard is `"3.4.2"`.

### Why minimum matters

Using the latest spec version without needing its features:
- forces users to run a newer Kibana than necessary
- breaks backward compatibility for no reason
- makes it harder to determine which features the package actually depends on

### Feature-to-version mapping

Only bump when the package uses a feature introduced in a newer spec version:

| Feature | Minimum format_version |
|---------|----------------------|
| Basic package structure | 1.0.0 |
| Input-level variables | 2.0.0 |
| `elasticsearch.privileges` | 2.3.0 |
| `routing_rules.yml` support | 2.9.0 |
| `lifecycle` field | 3.0.0 |
| Secret variables (`secret: true`) | 3.0.0 |
| `elasticsearch.source_mode` | 3.0.3 |

### When bumping is justified

A `format_version` bump is justified only when the PR also introduces a feature that requires the higher version. Review questions:

1. What `format_version` is declared?
2. Does the package use any feature that requires this version?
3. Could a lower version work?
4. If the PR bumps `format_version`, does it also introduce a feature that requires the bump?

---

## Review checklist

- [ ] format_version matches package needs -- **HIGH** if wrong
- [ ] No variable shadowing across scopes -- **HIGH**
- [ ] Every `{{var}}` in templates declared in manifest -- **HIGH**
- [ ] Routing rules have dynamic_dataset + dynamic_namespace -- **HIGH** if routing_rules.yml present but flags missing
- [ ] YAML uses nested structure, not dotted keys -- **MEDIUM**
- [ ] All variables have title, description, type, required -- **MEDIUM**
- [ ] Defaults present for optional variables -- **LOW**
