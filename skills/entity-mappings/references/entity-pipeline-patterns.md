# Entity pipeline patterns

Pipeline-side requirements and processor patterns for entity/inventory data streams.

**Field definitions live in `entity-mappings/references/entity-field-catalog.md`.** Do not
restate field types, ECS availability, or review checklists here — they are the catalog's
responsibility. This file covers only *how to implement* those fields in an ingest pipeline.

Aligned with: ECS v9.5.0 — entity fieldset (beta), entity_reference fieldset.

**Applies only to entity data streams** (`event.kind: asset`). Do not apply these patterns
to event logs, metric streams, or CDR findings streams. See
`entity-datastream-classification.md` to classify a data stream first.

---

## Event categorization

Every entity data stream must set `event.kind: asset` and the appropriate `event.category`
and `event.type` arrays. These processors follow ECS categorization patterns A/B/C from
`ingest-pipelines/references/processor-cookbook.md`; defer to that reference for the full
pattern library.

```yaml
# event.kind is a scalar — use set
- set:
    field: event.kind
    value: asset
    tag: set-event-kind

# event.category and event.type are arrays — use append (never set)
# User entity example:
- append:
    field: event.category
    value: iam
    tag: append-event-category
- append:
    field: event.type
    value: [user, info]
    allow_duplicates: false
    tag: append-event-type

# Host entity example:
# - append: { field: event.category, value: host, ... }
# - append: { field: event.type, value: [info], ... }
```

Do NOT set `event.outcome` on entity snapshot records — no success/failure applies to an
inventory cycle.

---

## Building entity.id and mirroring dedicated fieldsets

`entity.id` must equal the dedicated fieldset's primary identifier so the entity store can
correlate across sources.

```yaml
# User entity: mirror user.id to user.entity.id (and root entity.id for store)
- set:
    field: user.entity.id
    copy_from: user.id
    ignore_empty_value: true
    ignore_missing: true
    tag: mirror_user_id_to_entity
- set:
    field: entity.id
    copy_from: user.id
    ignore_empty_value: true
    ignore_missing: true
    tag: set_entity_id
- set:
    field: entity.name
    copy_from: user.name
    ignore_empty_value: true
    ignore_missing: true
    tag: set_entity_name
- set:
    field: entity.source
    value: "<integration_name>"
    tag: set_entity_source
- set:
    field: entity.type
    value: [user]
    tag: set_entity_type
- set:
    field: entity.last_seen_timestamp
    copy_from: "@timestamp"
    ignore_empty_value: true
    ignore_missing: true
    tag: set_entity_last_seen
```

For host entities, substitute `host.id` / `host.name` and `entity.type: [host]`.

---

## Boolean coercion for attributes

Vendor APIs often return booleans as strings (`"true"`, `"TRUE"`, `"1"`, `"yes"`) or
integers. Always coerce to a true boolean before setting ECS boolean attributes.

```yaml
# Coerce hasTwoFactorEnabled (string or bool) → user.entity.attributes.mfa_enabled
- set:
    field: user.entity.attributes.mfa_enabled
    value: true
    if: >-
      ctx._ingest?.body?.hasTwoFactorEnabled == true ||
      ctx._ingest?.body?.hasTwoFactorEnabled == "true" ||
      ctx._ingest?.body?.hasTwoFactorEnabled == "TRUE" ||
      ctx._ingest?.body?.hasTwoFactorEnabled == "1"
    tag: set-mfa-enabled-true
- set:
    field: user.entity.attributes.mfa_enabled
    value: false
    if: >-
      ctx._ingest?.body?.hasTwoFactorEnabled != null &&
      ctx.user?.entity?.attributes?.mfa_enabled == null
    tag: set-mfa-enabled-false
```

Alternatively, use the `convert` processor when the source type is already boolean-ish:

```yaml
- convert:
    field: _ingest.body.isManaged
    target_field: host.entity.attributes.managed
    type: boolean
    ignore_missing: true
    ignore_failure: true
    tag: convert-managed-to-boolean
```

---

## Array-valued attributes

`entity.attributes.permissions` and `entity.attributes.known_redirects` must be keyword
arrays. The most common mistake is joining the values into a comma-separated string.

```yaml
# Correct: append each permission individually
- foreach:
    field: _ingest.body.permissions
    processor:
      append:
        field: user.entity.attributes.permissions
        value: "{{_ingest._value}}"
        allow_duplicates: false
    ignore_missing: true
    tag: append-permissions

# Anti-pattern (wrong — creates a comma-joined string):
# - set:
#     field: user.entity.attributes.permissions
#     value: "{{_ingest.body.permissions}}"
```

---

## Building entity.relationships.* objects

ECS relationship field names are **dotted leaf paths** such as
`user.entity.relationships.supervises.user.id`. When an ingest pipeline writes to a dotted
path, Elasticsearch expands it into nested objects at index time. Always write the dotted
path in processor `field` or `target_field` — do not construct nested map literals.

```yaml
# Append a supervised user's ID to the supervises relationship
- append:
    field: user.entity.relationships.supervises.user.id
    value: "{{_ingest.body.managedUserId}}"
    allow_duplicates: false
    ignore_missing: true
    tag: append-supervises-user-id

# Append a supervised user's email (separate leaf, same relationship)
- append:
    field: user.entity.relationships.supervises.user.email
    value: "{{_ingest.body.managedUserEmail}}"
    allow_duplicates: false
    ignore_missing: true
    tag: append-supervises-user-email
```

**Only the 9 allowed keys** may appear under a relationship field (`entity.id`, `host.id`,
`host.name`, `service.id`, `service.name`, `user.domain`, `user.email`, `user.id`,
`user.name`). Do not invent keys like `user_handle` or `account_id`. See
`entity-field-catalog.md` → *Relationships* for the full table.

**Note on ECS field name expansion:** the full generated field name at the index level is
e.g. `user.entity.relationships.supervises.user.id`. Cross-reference
`ecs-field-mappings/SKILL.md` → *Dotted field names vs nested groups* for how Elasticsearch
expands these during ingestion.

---

## @timestamp semantics on snapshots

For entity data streams, `@timestamp` is the **collection cycle time** — when the agent
polled the API and produced this snapshot — not when the entity was created or modified.

```yaml
# @timestamp is already set by the CEL input to the fetch time — do not override it.
# If the source provides an "updated_at" that is semantically "when was last active",
# map it to entity.lifecycle.last_activity instead.
- date:
    field: _ingest.body.updatedAt
    target_field: user.entity.lifecycle.last_activity
    formats:
      - ISO8601
    ignore_missing: true
    ignore_failure: true
    tag: parse-last-activity
```

---

## Value transformations

| Transformation | Rule | Processor |
|---|---|---|
| Lowercase `entity.type` values | Always lowercase (`user`, `host`, not `User`, `HOST`) | `lowercase` or `set` with lowercase literal |
| Normalize permission strings | Strip whitespace; common capitalization variants accepted (`Read`, `READ`, `read` all valid; use as-is from source to preserve vendor semantics) | No normalization required; preserve vendor capitalization |
| Boolean vendor fields | Coerce to boolean before setting `entity.attributes.*` booleans | `convert` or conditional `set` (see Boolean coercion above) |

---

## Anti-patterns

- **Unbounded `entity.raw` dump** — `entity.raw` is an `object` type; writing a large
  vendor document to it causes mapping explosions. Write individual leaf fields only.
  `entity.behavior`, `entity.metrics` are similarly unstructured — avoid unless necessary.
- **`event.kind: asset` on an event log stream** — if the stream contains per-event
  timestamped records of things that happened, use `event.kind: event`, not `asset`.
- **Relationship keys outside the 9 allowed** — any key not in the allowed-key table will
  fail ECS compliance review.
- **Entity fields on a CDR findings stream** — findings are `event.kind: state`; they
  describe posture at a point in time about a resource, not the resource itself.
- **`user.group` as a keyword** — `user.group` is a reused fieldset, not a leaf; use
  `user.group.name`, `user.group.id`, `user.group.domain`.
- **`entity.attributes.asset` field** — this field does not exist in ECS. Do not emit it.
- **Invented `entity.*` fields** — only write `entity.*` fields that are defined in ECS at the pinned version. Do not assume a plausible name is real. Source fields with no ECS equivalent must go to the integration's custom namespace: `<integration_name>.<datastream_name>.<field_name>` (e.g., `github.members.is_employee` for a field `isEmployee`). Writing an invented path does not fail at ingest — it silently creates an unmapped field that may conflict with a future ECS field under the same name.
- **Setting `event.ingested`** — managed by Elasticsearch; never set in a pipeline.

---

## Entity pipeline review checklist

### What to flag

- [ ] `event.kind` set to `event` or `state` instead of `asset` on entity data stream -- **HIGH**
- [ ] `event.category` / `event.type` set with `set` instead of `append` (they are arrays) -- **HIGH**
- [ ] `event.outcome` set on entity snapshot (no outcome applies to an inventory cycle) -- **MEDIUM**
- [ ] `entity.id` not mirroring the dedicated fieldset id (`user.id`, `host.id`) -- **HIGH**
- [ ] Boolean coercion missing — vendor string `"true"` written directly to a boolean ECS attribute -- **MEDIUM**
- [ ] `entity.attributes.permissions` or `entity.attributes.known_redirects` written as comma-joined string instead of array -- **MEDIUM**
- [ ] Relationship keys used outside the 9 allowed — **MEDIUM** (alpha field; cap at MEDIUM)
- [ ] `entity.raw` / `entity.behavior` / `entity.metrics` used for a large vendor blob (mapping explosion risk) -- **MEDIUM**
- [ ] `entity.attributes.asset` field written (not in ECS) -- **HIGH**
- [ ] Any `entity.*` sub-field written that does not exist in ECS at the pinned version (invented field) -- **HIGH**; should be `<integration>.<datastream>.<field>` instead
- [ ] `event.ingested` set by pipeline -- **HIGH**
- [ ] `entity.*` leaf fields declared with `external: ecs` but `build.yml` still pins `git@v9.3.0` -- **HIGH** (build failure)

### What NOT to flag

Entity pipeline requirements are NOT applicable to:
- Event log, metric, or APM data streams
- CDR findings streams (`cloudsecurity_cdr` category, `event.kind: state`)
- Any stream where the entity classification negative gate fires (CDR check)
