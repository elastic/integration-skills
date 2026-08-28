# Entity vs event data stream classification

Use this guide to decide whether a proposed or existing data stream is an **entity stream**
(inventory/snapshot, `event.kind: asset`) or an **event stream** (timeline log, `event.kind: event`).

This is the only file from `entity-mappings` that `research-integration` is allowed to load,
because research is a data-gathering phase that must not prescribe pipeline or field details.

---

## Research-time rule (before any code exists)

Four signals, evaluated against what Research Track B already produced:

| Signal | Description | Strength |
|--------|-------------|---------|
| **No event timestamp** | The only timestamps are properties of the subject (`created_at`, `updated_at`, `last_login_at`), not "when this happened". | Necessary |
| **Idempotent re-read** | Re-calling with no time filter returns the same records with refreshed values — a snapshot, not new rows. No incremental time filter exists; no advancing event cursor. Check research-brief section 3.4: if "Time-based filtering" is *"none available"*, suspect entity. | Strongest |
| **Stable primary key** | A key (login, user ID, ARN, device ID) persists across collection cycles and uniquely identifies the subject. | Supporting |
| **Vendor vocabulary** | Endpoint or collection name includes words like: *list users, members, membership, directory, roster, inventory, devices, assets, resources, accounts, identities*. Event-style vocabulary: *events, audit log, activity, alerts, findings*. | Supporting |

**Decision rule:** entity stream if and only if signals 1 **and** 2 both hold.

When classified as entity:
- Set `event.kind: asset`
- Name the stream after the population: `entities`, `identities`, `members`, `users`, `devices`, `groups`, `apps`
- Record the `entity.type` from the allowed values: `bucket`, `database`, `container`, `function`, `queue`, `host`, `user`, `application`, `service`, `session`, `cloud`, `orchestrator`

---

## Review-time rule (existing package, files only — first hit wins)

1. **Definitive:** the pipeline sets `event.kind: asset` anywhere.
2. **Definitive:** `input: entity-analytics` appears in a data stream or policy-template input in any `manifest.yml`.
3. **Strong:** any `fields/*.yml` file declares a field matching `*entity.attributes.*`, `*entity.lifecycle.*`, `*entity.relationships.*`, `entity.type`, or `entity.id`.
4. **Heuristic:** stream name is one of: `users`, `user`, `members`, `membership`, `groups`, `devices`, `hosts`, `assets`, `inventory`, `accounts`, `identities`, `entities`, `apps`, `applications`, `service_accounts`, `roles`, `resources` — **and** the pipeline sets no `event.action` or `event.outcome` — **and** pipeline test fixtures carry no per-record event timestamp distinct from collection time.
5. **Negative gate (overrides 3 and 4):** root `manifest.yml` categories include `cloudsecurity_cdr` **and** the stream sets `result.evaluation` or `vulnerability.*` — this is a CDR *findings* stream, `event.kind: state`. Load the CDR references (`ecs-field-mappings/references/cdr-field-requirements.md` and `ingest-pipelines/references/cdr-pipeline-requirements.md`), **not** entity references.

**Severity rule:** if classification rests on heuristic 4 alone, report entity findings one severity level lower than listed and state the classification basis. This keeps the "cite concrete evidence" discipline honest.

---

## Worked examples

| Integration | Stream | Classification | Deciding signals |
|---|---|---|---|
| GitHub | `members` | **entity** | No event timestamp; re-reading returns same member roster; stable `login` key; endpoint is `organization.membersWithRole` |
| GitHub | `audit` | event | Every record is a timestamped audit action |
| Okta | `users` | **entity** | No event timestamp; idempotent re-read of full user directory; stable `id` |
| Wiz | `vulnerabilities` | **not entity** (CDR state) | Sets `result.evaluation`, `cloudsecurity_cdr` in manifest categories — negative gate fires |
| AWS | `cloud_asset_inventory` | **entity** | Inventory snapshot of cloud resources; no event time; stable ARN |
| CrowdStrike | `alerts` | event | Detection events with per-alert timestamps |
