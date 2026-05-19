# Painless Script Patterns

Reference for Painless usage inside `script` ingest processors. For foundational rules (no `?.` in script bodies, `equalsIgnoreCase` guidance, tag/description requirement, prefer built-in processors), see `SKILL.md` -- Painless script best practices. This document covers deeper patterns and examples.

## ctx read patterns

All document fields are accessed through `ctx`. Use the null-safe `?.` operator for nested paths to avoid `NullPointerException`. Note: `ctx` itself is always non-null in ingest pipelines, so `ctx?.field` is unnecessary -- use `ctx.field` directly. The `?.` operator is useful on nested paths where a parent may be absent.

```yaml
- script:
    tag: extract_user_info
    description: Extract user info with safe nested access
    lang: painless
    source: |
      if (ctx.user?.identity != null) {
        def name = ctx.user.identity.name;
        if (name != null && !name.isEmpty()) {
          ctx.user.full_name = name;
        }
      }
```

Both `ctx.user?.identity != null` and the explicit chained form `ctx.user != null && ctx.user.identity != null` are valid. The null-safe `?.` form is preferred for conciseness. The verbose form may be clearer in complex conditions with side effects.

Bracket notation is useful when field names contain dots or special characters:

```yaml
- script:
    tag: read_dotted_field
    description: Read a field name that contains a literal dot
    lang: painless
    source: |
      if (ctx.containsKey('host.name')) {
        ctx.host_name = ctx['host.name'];
      }
```

`containsKey` checks for field presence without risk of a null pointer:

```painless
if (ctx.containsKey('source') && ctx.source.containsKey('ip')) {
  // safe to use ctx.source.ip
}
```

## ctx write patterns

Direct assignment creates or overwrites a field. `remove` deletes it.

```painless
ctx.event.outcome = 'success';
ctx.put('event.outcome', 'success');   // equivalent map-style put
ctx.remove('_temp');                   // delete a field
ctx.list_field.add(item);             // append to an existing list
```

## params usage

`params` holds immutable constants declared in the processor config. Values in `params` are set once and shared across all documents processed by that script. Elasticsearch compiles the script once and caches it; changing only `params` values does not trigger recompilation.

Use `params` for:
- Lookup/mapping tables
- Regex patterns
- Threshold values and configuration constants

```yaml
- script:
    tag: map_severity
    description: Map severity label string to numeric value using params lookup
    lang: painless
    params:
      severity_map:
        low: 1
        medium: 2
        high: 3
        critical: 4
    source: |
      def label = ctx.event?.severity_label;
      if (label != null && params.severity_map.containsKey(label)) {
        ctx.event = ctx.event ?: [:];
        ctx.event.severity = params.severity_map.get(label);
      }
```

For 1-2 constant values, inline comparisons in `source` are fine. For 3+ values or lookup tables, move them into `params` for readability and maintainability:

```yaml
# Avoid for many values -- harder to read and maintain
- script:
    source: |
      if (ctx.raw_status == "ACTIVE") { ctx.status = "active"; }
      else if (ctx.raw_status == "INACTIVE") { ctx.status = "inactive"; }
      else if (ctx.raw_status == "DISABLED") { ctx.status = "disabled"; }

# Preferred -- params keep source generic and readable
- script:
    tag: map_status
    description: Normalize raw status using params lookup table
    lang: painless
    params:
      status_map:
        ACTIVE: active
        INACTIVE: inactive
        DISABLED: disabled
    source: |
      if (ctx.raw_status != null) {
        ctx.status = params.status_map.getOrDefault(ctx.raw_status, ctx.raw_status);
      }
```

## Map initialization for nested writes

Before writing to a nested path, ensure every parent map exists. A write to `ctx.event.outcome` fails if `ctx.event` is `null`. Use the `?:` (Elvis) operator with `[:]` (empty map literal) for concise null-coalescing initialization.

```yaml
- script:
    tag: init_event_outcome
    description: Set event outcome with safe parent initialization
    lang: painless
    source: |
      ctx.event = ctx.event ?: [:];
      ctx.event.outcome = 'success';
```

For deeply nested paths, each level must be initialized:

```yaml
- script:
    tag: set_deep_nested_field
    description: Set a deeply nested field with full parent chain init
    lang: painless
    source: |
      ctx.organization = ctx.organization ?: [:];
      ctx.organization.department = ctx.organization.department ?: [:];
      ctx.organization.department.name = ctx._temp_dept;
```

When building a new nested object from scratch, initialize the root as a `HashMap` and populate it:

```yaml
- script:
    tag: build_related_object
    description: Build related.ip from multiple source fields
    lang: painless
    source: |
      def ips = new HashSet();
      if (ctx.source?.ip != null) {
        ips.add(ctx.source.ip);
      }
      if (ctx.destination?.ip != null) {
        ips.add(ctx.destination.ip);
      }
      if (!ips.isEmpty()) {
        ctx.related = ctx.related ?: [:];
        ctx.related.ip = new ArrayList(ips);
      }
```

## Field API (ES 9.2+)

The Field API provides cleaner syntax for deeply nested field access. It handles null parent maps automatically, eliminating manual `HashMap` initialization chains. Available in Elasticsearch 9.2+ for conditionals.

```painless
// Field API -- set a deeply nested field without manual HashMap init
field('system.cpu.total.norm.pct').set($('cpu.usage', 0.0) / 100.0)
```

Without the Field API, the same operation requires explicit initialization of every parent:

```painless
ctx.system = ctx.system ?: [:];
ctx.system.cpu = ctx.system.cpu ?: [:];
ctx.system.cpu.total = ctx.system.cpu.total ?: [:];
ctx.system.cpu.total.norm = ctx.system.cpu.total.norm ?: [:];
ctx.system.cpu.total.norm.pct = ctx.cpu.usage / 100.0;
```

Reference: https://www.elastic.co/docs/manage-data/ingest/transform-enrich/readable-maintainable-ingest-pipelines

## foreach processor context

When a `script` runs inside a `foreach` processor, the current array element is accessed via `ctx._ingest._value`, not through the array directly.

```yaml
- foreach:
    tag: normalize_event_items
    description: Lowercase the name field on each item in event.items
    field: event.items
    processor:
      script:
        tag: lowercase_item_name
        description: Lowercase the current item name
        lang: painless
        source: |
          if (ctx._ingest._value.name != null) {
            ctx._ingest._value.name = ctx._ingest._value.name.toLowerCase();
          }
```

Key rules:
- `ctx._ingest._value` refers to the current element of the array specified in `foreach.field`.
- `ctx._ingest._value.name` with `foreach.field: event.items` resolves to `event.items[*].name`.
- Writing to `ctx._ingest._value` or its sub-fields modifies the element in place.
- The script still has access to the full document via `ctx` for reading other fields.

## Conditional field removal

Use `containsKey` to check before removing. Removing a non-existent key from `ctx` does not throw, but checking first is idiomatic when the removal is conditional on other logic:

```yaml
- script:
    tag: remove_temp_fields
    description: Remove all temporary fields after processing
    lang: painless
    source: |
      def to_remove = ['_temp', '_header', '_raw_message'];
      for (def field : to_remove) {
        if (ctx.containsKey(field)) {
          ctx.remove(field);
        }
      }
```

For nested field removal:

```yaml
- script:
    tag: clean_empty_nested
    description: Remove nested object if all its children are null
    lang: painless
    source: |
      if (ctx.source != null && ctx.source.ip == null && ctx.source.port == null) {
        ctx.remove('source');
      }
```

## Common script patterns

### Array deduplication

```yaml
- script:
    tag: dedup_tags
    description: Remove duplicate entries from tags array
    lang: painless
    source: |
      if (ctx.tags != null && ctx.tags instanceof List) {
        ctx.tags = new ArrayList(new LinkedHashSet(ctx.tags));
      }
```

`LinkedHashSet` preserves insertion order while removing duplicates.

### IP normalization

```yaml
- script:
    tag: normalize_ipv6
    description: Expand compressed IPv6 addresses to full form
    lang: painless
    params:
      ipv4_mapped_prefix: '::ffff:'
    source: |
      if (ctx.source != null && ctx.source.ip != null) {
        def ip = ctx.source.ip;
        if (ip.startsWith(params.ipv4_mapped_prefix)) {
          ctx.source.ip = ip.substring(params.ipv4_mapped_prefix.length());
        }
      }
```

### String manipulation

```yaml
- script:
    tag: extract_domain_from_email
    description: Extract domain part from user email address
    lang: painless
    source: |
      if (ctx.user != null && ctx.user.email != null) {
        def email = ctx.user.email;
        int idx = email.indexOf('@');
        if (idx > 0) {
          ctx.user.domain = email.substring(idx + 1);
        }
      }
```

### Timestamp arithmetic

```yaml
- script:
    tag: compute_duration
    description: Compute event duration from start and end timestamps
    lang: painless
    source: |
      if (ctx.event != null && ctx.event.start != null && ctx.event.end != null) {
        def start = ZonedDateTime.parse(ctx.event.start);
        def end = ZonedDateTime.parse(ctx.event.end);
        ctx.event.duration = ChronoUnit.NANOS.between(start, end);
      }
```

## Anti-patterns

**Overuse of scripts when processors suffice.** Before writing any `script` processor, you **must** verify that no built-in processor can do the job. `script` is slower than every built-in processor except `geoip`/`user_agent` — it carries Painless compilation cost and per-document execution overhead. Common replacements:

| Script doing | Use instead |
|---|---|
| `ctx.field = ctx.other_field` | `rename` or `set` with `copy_from` |
| `ctx.field = value` (constant) | `set` |
| `ctx.list.add(value)` | `append` |
| Type conversion | `convert` |
| String splitting or extraction | `dissect` or `grok` |
| Regex replacement | `gsub` |
| Regex matching / extraction | `grok` with `pattern_definitions` |
| Case normalization | `lowercase` / `uppercase` |

**Concrete example — extracting a domain from an email address:**

```yaml
# WRONG — script for a job dissect handles natively
- script:
    tag: script_set_user_domain
    lang: painless
    description: Extract domain from email address.
    if: ctx.vendor?.owner instanceof String && ctx.vendor.owner.contains('@')
    source: |-
      String u = ctx.vendor.owner;
      int at = u.lastIndexOf('@');
      if (at > 0 && at < u.length() - 1) {
        ctx.user = ctx.user ?: [:];
        ctx.user.domain = u.substring(at + 1);
      }

# CORRECT — dissect is faster, shorter, and easier to review
- dissect:
    tag: dissect_user_domain
    field: vendor.owner
    pattern: "%{?_ignore}@%{user.domain}"
    if: ctx.vendor?.owner != null && ctx.vendor.owner.contains('@')
```

**Missing null checks.** Every field access in a script body must be guarded. A missing null check on a field that is absent in some documents causes `NullPointerException` at ingest time, which triggers `on_failure` for that document.

**Hardcoded values in script bodies.** Constants belong in `params`, not inline in the `source` string. Inline values prevent Elasticsearch from caching the compiled script across different configurations and make the mapping logic harder to review.

## Review checklist

- [ ] **Script could be replaced with a built-in processor** -- **MEDIUM** (see anti-patterns table above)
- [ ] Script has `tag` and `description` -- **MEDIUM**
- [ ] `params` used for constants instead of hardcoding in script body -- **LOW**
- [ ] Null checks present before field access -- **MEDIUM**
- [ ] No `ctx?` usage (ctx is always non-null) -- **LOW**
