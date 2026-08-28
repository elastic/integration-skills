# ECS entity field catalog

Single source of truth for ECS `entity.*` field mapping in Elastic integrations.

Aligned with: ECS v9.5.0 — entity fieldset (beta), entity_reference fieldset.

**Entity fields apply only to entity data streams** (those with `event.kind: asset`). Never
flag or apply entity field requirements to event logs, metric streams, APM, or CDR findings
streams. See `entity-datastream-classification.md` to classify a data stream before using
this catalog.

---

## ECS availability matrix

The `entity.attributes.*`, `entity.lifecycle.*`, and `entity.relationships.*` leaf fields do
**not** exist at ECS `v9.3.0` (the repo default pin). They first appear at `v9.4.0`.

| Field group | ECS v9.3.0 | ECS v9.4.0+ | Maturity | `external: ecs` usable |
|---|---|---|---|---|
| `entity.id`, `entity.name`, `entity.source` | ✅ (core) | ✅ | core | ✅ at `v9.3.0+` |
| `entity.type`, `entity.last_seen_timestamp`, `entity.display_name` | ✅ (extended, beta) | ✅ | beta | ✅ at `v9.3.0+` |
| `entity.attributes.*` (all 6 leaves) | ❌ (bare `object`) | ✅ | beta | ✅ at `v9.4.0+` only |
| `entity.lifecycle.last_activity` | ❌ | ✅ | beta | ✅ at `v9.4.0+` only |
| `entity.relationships.*` | ❌ (`entity_reference` missing) | ✅ | beta | ✅ at `v9.4.0+` only |

**ECS pin rule:** packages with entity data streams must set `git@v9.4.0` or higher in
`_dev/build/build.yml` and a matching `ecs.version` in the pipeline (the two must match).
Using `external: ecs` on `entity.attributes.*`, `entity.lifecycle.*`, or
`entity.relationships.*` at `git@v9.3.0` causes `field is undefined` build failures.
**Recommended pin for new packages: `git@v9.5.0`.**

To verify field availability at a given tag:
```bash
curl -s https://raw.githubusercontent.com/elastic/ecs/<tag>/generated/csv/fields.csv \
  | awk -F, '$3=="entity"' | cut -d, -f4,5 | sort -u
```

---

## Reusable nesting

The `entity` fieldset is reusable. Valid parents at ECS v9.5.0:

| Prefix | Example | Use when |
|---|---|---|
| `user.entity.*` | `user.entity.attributes.mfa_enabled` | User identity entities |
| `host.entity.*` | `host.entity.attributes.managed` | Host/device entities |
| `service.entity.*` | `service.entity.attributes.storage_class` | Service/app entities |
| `cloud.entity.*` | `cloud.entity.relationships.owns` | Cloud resource entities |
| `orchestrator.entity.*` | `orchestrator.entity.type` | Container/orchestrator entities |
| `entity.*` (root) | `entity.id` | When no dedicated parent fieldset applies |
| `entity.target.*` | `entity.target.type` | The *targeted* entity in an event (distinct from the primary entity) |

Do not invent `device.entity.*` — `device` is not a valid parent in ECS.

Cross-reference `ecs-field-mappings` skill → *Reusable fieldset nesting rules* for the
general nesting pattern. Use the parent that matches the entity type being described: a user
membership record uses `user.entity.*`, not root `entity.*`.

---

## entity.type allowed values

`entity.type` is a keyword array (`normalize: [array]`). When `entity` is nested under a
dedicated fieldset (e.g. `user.entity.*`), include the matching type value in the array.

| Value | When to use |
|---|---|
| `user` | User account, identity, service account, or any human/bot subject |
| `host` | Physical server, VM, cloud instance, endpoint device |
| `service` | Web service, microservice, background service |
| `application` | Software application (web app, mobile app, desktop) |
| `container` | Docker container, Kubernetes pod |
| `cloud` | Cloud provider account or multi-cloud scope |
| `orchestrator` | Kubernetes, Docker Swarm, or other orchestration system |
| `function` | Serverless function (Lambda, Cloud Functions) |
| `queue` | Message queue / broker (SQS, Kafka, RabbitMQ) |
| `database` | Database system or instance |
| `bucket` | Object storage container (S3 bucket, GCS bucket, Azure Blob container) |
| `session` | User or connection session |

---

## Categorization for entity data streams

| Entity type | `event.kind` | `event.category` | `event.type` | `event.outcome` |
|---|---|---|---|---|
| User snapshot (org member, identity) | `asset` | `["iam"]` | `["user", "info"]` | not set |
| Host / device snapshot | `asset` | `["host"]` | `["info"]` | not set |
| Service / app snapshot | `asset` | `["configuration"]` | `["info"]` | not set |
| Generic entity snapshot (no category match) | `asset` | `[]` (omit) | `["info"]` | not set |

`asset` vs `state` disambiguation:
- **`asset`**: the document *is* the entity — one record per entity per collection cycle, representing its current state. Suitable for entity store ingestion.
- **`state`**: a finding or posture result *about* a resource at a point in time (CDR misconfiguration, vulnerability). Do not use `asset` for CDR findings.

---

## Core identity fields (Must Have)

Missing these causes entity store lookup failures or broken entity analytics.

| Field | Type | ECS | Purpose |
|---|---|---|---|
| `@timestamp` | date | yes | Collection cycle timestamp (when the snapshot was collected, not when the entity was created) |
| `event.kind` | keyword | yes | **Must be `asset`** |
| `entity.id` | keyword | yes | Stable identifier for the entity, persisting across cycles. Must mirror the dedicated fieldset id field (e.g., `user.entity.id = user.id`) |
| `entity.name` | keyword | yes | Human-readable display name. Mirror `user.name`, `host.name`, etc. |
| `entity.type` | keyword | yes | From the allowed values table above. Use the parent-matching value (e.g., `["user"]` under `user.entity.*`) |
| `entity.source` | keyword | yes | Name of the source system (e.g., `"github"`, `"okta"`) |
| `entity.last_seen_timestamp` | date | yes | When the entity was last observed in the source data. Often equals `@timestamp` for full-cycle polling |
| `user.id` | keyword | yes | (User entities) Primary user identifier from the source system |
| `user.name` | keyword | yes | (User entities) User login or short name |
| `user.email` | keyword | yes | (User entities) User email address when available |
| `host.name` | keyword | yes | (Host entities) Host display name |
| `host.id` | keyword | yes | (Host entities) Stable host identifier |

ECS schema guidance (from `schemas/entity.yml`): *"For entities with dedicated field sets
(for example, host, user), this value should match the corresponding \*.id field."*

---

## Attributes (Should Have)

Leaf fields in `entity.attributes.*` are new in ECS v9.4.0 — require the `git@v9.5.0` pin.

**Only map source fields to `entity.attributes.*` sub-fields that are defined in ECS at the pinned version.** Verify a field exists before using it — do not assume a plausible name is real. If a source field has no ECS equivalent in this section, map it to the integration's own namespace instead: `<integration_name>.<datastream_name>.<field_name>` (e.g., `github.members.is_employee` for a field `isEmployee` in a GitHub members stream). An invented ECS path does not fail at ingest — it silently creates an unmapped field that may conflict with a future ECS definition under the same name.

| Field | Type | Applies to | ECS v9.4.0+ | Purpose |
|---|---|---|---|---|
| `entity.attributes.mfa_enabled` | boolean | User | yes | Whether MFA is enabled for this user |
| `entity.attributes.managed` | boolean | Host, Service | yes | Whether the entity is managed by an external administration system |
| `entity.attributes.permissions` | keyword (array) | User, Host, Service | yes | Individual action-level permissions explicitly granted (`Read`, `Write`, `Delete`, `Execute`). Not roles or groups. |
| `entity.attributes.known_redirects` | keyword (array) | Service | yes | Known redirect URIs for OAuth apps or services |
| `entity.attributes.storage_class` | keyword | Service (storage) | yes | Storage tier/class (e.g., `STANDARD`, `GLACIER`, `COLDLINE`) |
| `entity.attributes.oauth_consent_restriction` | keyword | Service | yes | OAuth consent restriction (`admin_only`, `verified_only`, `unrestricted`) |

### Fields with no ECS equivalent → custom namespace

Never invent an `entity.attributes.*` path. Two cases apply:

- **Source-specific fields** — entity-relevant vendor data with no ECS equivalent: map to the integration's own namespace (`<integration_name>.<datastream_name>.<field_name>`).
- **Known non-existent fields** — `entity.attributes.asset` does not exist in ECS at any version (verified v9.3.0–v9.5.0 and main). The concept "this record is an asset" is expressed by setting `event.kind: asset` on the data stream, not by any per-record field.

| Example source field | Wrong mapping | Correct mapping |
|---|---|---|
| `isEmployee` | `entity.attributes.is_employee` ❌ | `github.members.is_employee` ✅ |
| `siteAdmin` | `entity.attributes.site_admin` ❌ | `github.members.site_admin` ✅ (also consider `user.roles`) |
| `organizationRole` | `entity.attributes.organization_role` ❌ | `github.members.organization_role` ✅ (also consider `user.roles`) |
| "is asset" / tracked concept | `entity.attributes.asset` ❌ | set `event.kind: asset` on the data stream ✅ |

---

## Lifecycle (Should Have)

| Field | Type | ECS | Purpose |
|---|---|---|---|
| `entity.lifecycle.last_activity` | date | v9.4.0+ | Timestamp of the most recent *action* by or attributed to this entity. Distinct from `entity.last_seen_timestamp` — activity implies the entity *did* something, not just that it appeared in a log. |

Three timestamp fields with distinct semantics:

| Field | Meaning |
|---|---|
| `@timestamp` | When this snapshot was collected (collection cycle time) |
| `entity.last_seen_timestamp` | When the entity was last observed in the data source (passive) |
| `entity.lifecycle.last_activity` | When the entity last performed an action (active use) |

`event.ingested` must **never** be set by an integration pipeline — it is managed by
Elasticsearch's final pipeline (see `ecs-field-mappings` SKILL.md).

---

## Relationships (Should Have — alpha; cap findings at MEDIUM)

`entity.relationships.*` is part of the `entity_reference` fieldset, which first appears at
`v9.4.0`. It is currently **alpha and subject to change**. For this reason, review findings
about missing or wrong relationship fields should be capped at **MEDIUM** severity.

| Field | Type | Applied to | Purpose |
|---|---|---|---|
| `entity.relationships.owns` | object | User, Host, Service | Identifiers of assets or identities this entity owns |
| `entity.relationships.depends_on` | object | User, Host, Service | Identifiers of entities this entity requires to operate |
| `entity.relationships.supervises` | object | User | Identifiers of entities this entity supervises (org hierarchy, people management) |
| `entity.relationships.administers` | object | User, Host, Service | Identifiers of entities this entity administers (technical admin, not people management) |

### Allowed keys on relationship objects

**Only** these keys may appear on `entity.relationships.*` objects. All values are `normalize: [array]`.
Do not use ad-hoc or integration-specific property names.

| Key | ECS type | Semantics |
|---|---|---|
| `entity.id` | keyword | Referenced entity identifiers |
| `host.id` | keyword | Referenced host identifiers |
| `host.name` | keyword | Referenced host names |
| `user.id` | keyword | Referenced user identifiers |
| `user.name` | keyword | Referenced user names |
| `user.email` | keyword | Referenced user email addresses |
| `user.domain` | keyword | Referenced user directory / AD domain |
| `service.id` | keyword | Referenced service identifiers |
| `service.name` | keyword | Referenced service names |

**Pipeline note:** ECS relationship field names are dotted leaves (`entity.relationships.owns.user.id`).
When an ingest pipeline sets a value at that dotted path, Elasticsearch expands it into a
nested object `{owns: {user: {id: […]}}}`. Always write the dotted path in `set`/`append`
processors — not a nested map literal. See `entity-pipeline-patterns.md` for processor
patterns.

Example (the object stored in Elasticsearch after a pipeline writes the dotted leaves):
```json
{
  "user.entity": {
    "relationships": {
      "supervises": {
        "user.id": ["00u123", "00u456"],
        "user.email": ["alice@example.com", "bob@example.com"]
      }
    }
  }
}
```

---

## Adjacent non-entity fields (Should Have)

These are standard ECS fields, not `entity.*`, but are required on entity data streams
for correct entity store routing and correlation.

| Field | Type | Purpose |
|---|---|---|
| `user.name` | keyword | User entities: login name. Required for entity correlation. |
| `user.id` | keyword | User entities: stable user identifier. Mirror to `user.entity.id`. |
| `user.email` | keyword | User entities: email address when available. |
| `user.roles` | keyword (array) | Roles assigned to the user (`admin`, `member`, etc.). Not groups. |
| `user.group.name` | keyword | Name of the primary group. `user.group` is a reused fieldset, not a keyword field — use `user.group.name`, `user.group.id`, `user.group.domain` individually. |
| `host.name` | keyword | Host entities: display name. Required for entity correlation. |
| `host.id` | keyword | Host entities: stable identifier. Mirror to `host.entity.id`. |
| `host.os.version` | keyword | Host entities: OS version string when available. |
| `related.user` | keyword (array) | All user-related values from the record (names, emails, IDs) for cross-entity search. |
| `related.hosts` | keyword (array) | All host-related values (hostnames, IPs) for cross-entity search. |

**`user.group` disambiguation:** `user.group` in ECS is a reused `group` fieldset, not a
keyword array. Correct usage: `user.group.name` (string), `user.group.id` (string),
`user.group.domain` (string). The field `user.group` alone is not a leaf field and must not
appear in `fields.yml` without a nested subfield.

---

## Field disambiguation

| These fields | Are distinct because |
|---|---|
| `user.group.name` vs `entity.attributes.permissions` | `group` = membership (who you belong to); `permissions` = discrete actions you can perform (`Read`, `Write`, `Delete`). A user can be in a group that *confers* permissions, but the group itself is not the permission. |
| `entity.relationships.administers` vs `entity.relationships.supervises` | `supervises` = org hierarchy / people management ("whose manager are you?"); `administers` = technical administration ("which systems do you manage?"). |
| `entity.last_seen_timestamp` vs `entity.lifecycle.last_activity` | `last_seen_timestamp` = entity appeared in a log (passive observation); `last_activity` = entity performed an action (active use). |
| `entity.relationships.owns` vs `entity.relationships.supervises` | `owns` = asset ownership (hosts, devices, resources); `supervises` = people management (direct reports, org hierarchy). |
| `entity.attributes.permissions` vs `user.roles` | `permissions` = individual action-level rights (`Read`, `Write`); `roles` = named roles (`admin`, `editor`). Both may be populated when distinct. |

---

## Field definition examples

### For packages pinned to `git@v9.5.0` (recommended for entity data streams)

Use `external: ecs` for all entity fields that exist at `v9.4.0+` (see availability matrix).

`ecs.yml` excerpt:
```yaml
# Core entity fields (available since v9.3.0)
- name: entity.id
  external: ecs
- name: entity.name
  external: ecs
- name: entity.type
  external: ecs
- name: entity.source
  external: ecs
- name: entity.last_seen_timestamp
  external: ecs
# Attributes (available since v9.4.0)
- name: user.entity.attributes.mfa_enabled
  external: ecs
- name: user.entity.attributes.permissions
  external: ecs
# Lifecycle (available since v9.4.0)
- name: user.entity.lifecycle.last_activity
  external: ecs
# Relationships (available since v9.4.0)
- name: user.entity.relationships.owns.user.id
  external: ecs
- name: user.entity.relationships.supervises.user.id
  external: ecs
```

`_dev/build/build.yml`:
```yaml
dependencies:
  ecs:
    reference: "git@v9.5.0"
```

Pipeline `set` processor (`ecs.version`):
```yaml
- set:
    field: ecs.version
    value: "9.5.0"
    tag: set-ecs-version
```

---

## Entity field review checklist

### What to flag

- [ ] `event.kind` not set to `asset` on entity/inventory data stream -- **HIGH**
- [ ] `entity.id` missing or not mirroring the dedicated fieldset id (`user.id`, `host.id`) -- **HIGH**
- [ ] `entity.type` missing or using a value not in the allowed values table -- **HIGH**
- [ ] `entity.source` missing -- **MEDIUM**
- [ ] `entity.last_seen_timestamp` missing -- **MEDIUM**
- [ ] `user.name` / `user.id` / `user.email` missing on user entity stream -- **MEDIUM**
- [ ] `host.name` / `host.id` missing on host entity stream -- **MEDIUM**
- [ ] Entity leaf fields using `external: ecs` at `git@v9.3.0` pin (undefined at that version) -- **HIGH** if build fails
- [ ] **New** entity data streams in a package NOT pinned to `git@v9.4.0` or higher in `build.yml` -- **HIGH** (entity leaf fields undefined at v9.3.0); for a **pre-existing** entity data stream with a matched pin below `git@v9.4.0`, flag as **LOW** (upgrade suggestion, not an immediate build breakage if leaf fields are not yet in use)
- [ ] `entity.attributes.asset` emitted as a field (not in ECS) -- **HIGH**
- [ ] Any `entity.*` sub-field emitted that does not exist in ECS at the pinned version (invented field) -- **HIGH**; move to `<integration>.<datastream>.<field>` custom namespace
- [ ] `user.group` declared as a keyword array instead of using `user.group.name` / `user.group.id` -- **MEDIUM**
- [ ] Relationship keys outside the 9 allowed keys -- **MEDIUM** (alpha, cap at MEDIUM)
- [ ] Entity fields applied to an event log or CDR findings stream -- **HIGH** (wrong `event.kind`)

### When entity fields are NOT required

Do NOT flag missing entity fields for:
- Event log or metric data streams (those with `event.kind: event`, `metric`, or `state`)
- CDR findings streams (`cloudsecurity_cdr` category, `event.kind: state`)
- APM data streams
- Any stream where the CDR negative gate fires (see `entity-datastream-classification.md`)

---

## How to refresh this file

Re-derive the complete entity field list from the ECS repo to verify catalog accuracy:

```bash
# List all entity leaf fields at a given tag
curl -s https://raw.githubusercontent.com/elastic/ecs/<tag>/generated/csv/fields.csv \
  | awk -F, '$3=="entity"' | cut -d, -f4,5 | sort -u

# Check entity_reference fieldset exists at a tag (200 = present, 404 = missing)
curl -s -o /dev/null -w '%{http_code}' \
  https://raw.githubusercontent.com/elastic/ecs/<tag>/schemas/entity_reference.yml
```

Update the `Aligned with:` line at the top of this file and the availability matrix whenever
you bump the catalog to a new ECS version.
