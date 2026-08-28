# Entity field gap analysis report template

Use this template when producing an entity field gap analysis report. Follow the structure
exactly. Fill each section; use `N/A` where genuinely not applicable, with a one-sentence
justification.

---

```markdown
# ECS Entity Field Mapping: {{INTEGRATION_NAME}}

## Integration Summary

[2–4 sentences: what the integration collects, which entity types it represents, which API/source it uses]

## Data Stream Classification

| Data stream | Classification | Deciding signal |
|---|---|---|
| `<stream_name>` | entity / event / not applicable | [first matching signal from the classification rule] |

## Entity Type Classification

[Which `entity.type` value(s) apply to each entity stream, with justification. E.g.: "The `members` stream represents `user` entities — GitHub organization members map directly to the ECS `user` type."]

## ECS Availability Impact

List which recommended fields require the `git@v9.5.0` ECS pin in `_dev/build/build.yml` (all
`entity.attributes.*`, `entity.lifecycle.*`, and `entity.relationships.*` leaf fields). If
any are mapped, state that the package must upgrade its pin.

| Requires v9.5.0 pin | Fields affected |
|---|---|
| Yes / No | [field list, or "none"] |

## Required New Scopes / Permissions

[Any new API scopes, IAM permissions, or admin tokens required to collect fields marked 🔍 or
to support new API calls. Be specific about what enables what.]

| Scope / Permission | Provider call | Enables |
|---|---|---|
| `<scope>` | `<endpoint or call>` | `<field(s) it unlocks>` |

---

## Field Mapping Results

### ✅ Direct Mappings

| ECS Field | Source Field | Notes |
|---|---|---|
| `user.entity.attributes.mfa_enabled` | `hasTwoFactorEnabled` | boolean — coerce with `convert` or conditional `set` |
| ... | ... | ... |

### 🔄 Derived Mappings

For each field:

**`entity.field.name`**
- Source fields used: `raw.field.a`, `raw.field.b`
- Derivation logic: [plain English — do not write pipeline YAML]

### ⛔ Not Applicable

| ECS Field | Reason |
|---|---|
| `host.entity.attributes.managed` | This integration represents only `user` entities — there are no host records in the collected data. |
| ... | ... |

### 🔍 Gap Analysis

For each unmapped field:

#### `entity.field.name`
- **Why it's a gap:** [brief explanation]
- **Investigation findings — package:** [what you found in package files, commented fields, config vars]
- **Investigation findings — API:** [endpoint checked, what it returns or does not return]
- **Recommendation:** [one of: Extract from existing call / Add API parameter / New API call / New data stream / Cannot be collected]
- **Implementation notes:** [endpoint URL, required scope, data shape — describe the data, not the pipeline. Do not write processor YAML here.]

---

## Summary Table

| ECS Field | Status | Notes |
|---|---|---|
| `event.kind` | ✅ / 🔄 / 🔍 / ⛔ | |
| `entity.id` | | |
| `entity.name` | | |
| `entity.type` | | |
| `entity.source` | | |
| `entity.last_seen_timestamp` | | |
| `user.entity.attributes.mfa_enabled` | | |
| `user.entity.attributes.managed` | | |
| `user.entity.attributes.permissions` | | |
| `user.entity.attributes.known_redirects` | | |
| `user.entity.attributes.storage_class` | | |
| `user.entity.attributes.oauth_consent_restriction` | | |
| `user.entity.lifecycle.last_activity` | | |
| `user.entity.relationships.owns` | | |
| `user.entity.relationships.depends_on` | | |
| `user.entity.relationships.supervises` | | |
| `user.entity.relationships.administers` | | |
| `user.name` / `user.id` / `user.email` | | |
| `host.os.version` | | |
| `user.group.name` | | |
| `user.roles` | | |

## Open Questions

[Any ambiguities, decisions needed from the team, or fields where the right approach is
unclear. Include questions about new scopes, required admin access, or API rate limits that
may affect collection feasibility.]
```
