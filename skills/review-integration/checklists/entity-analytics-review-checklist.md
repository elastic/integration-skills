# Entity-analytics package review checklist

Severity-tagged checklist for packages built on the filebeat `entity-analytics`
input (`entityanalytics_entra_id`, `entityanalytics_okta`, `entityanalytics_ad`,
and any new provider package). Load together with
`references/entity-analytics-provider-matrix.md` — several items below depend
on provider- and path-specific behavior documented there. New-vs-existing
severity calibration applies.

### Manifest / policy

- [ ] One policy template with a single `entity-analytics` input; categories include `security` and `advanced_analytics_ueba` -- **MEDIUM**
- [ ] Agentless block complete per current conventions (`release`, `organization`/`division`/`team` — see `references/repo-conventions.md`) and README has an "Elastic Managed deployment" section stating connectivity requirements -- **MEDIUM**
- [ ] Filesystem-dependent vars (`enable_request_tracer`, `jwk_file`, anything path-like) carry `hide_in_deployment_modes: [agentless]` -- **HIGH**
- [ ] `use_minimal_state` var present with `default: true`, hidden in BOTH deployment modes, with the standard "platform-managed implementation detail" comment; the hbs gates it with `{{#if use_minimal_state}}` -- **MEDIUM**
- [ ] Secrets use `type: password` + `secret: true`; credentials that may contain special characters pass through `{{escape_string}}` in the hbs -- **HIGH**
- [ ] Intervals: defaults `sync_interval: 24h` / `update_interval: 15m`; descriptions state sync > update; okta README addresses vendor rate limits -- **LOW**
- [ ] Every exposed var exists for the chosen provider (no `dataset` for jamf; `enrich_with` vocabulary per provider; `limit_window`/`limit_fixed`/`batch_size` okta-only — see the provider matrix) -- **HIGH**

### Routing and data streams

- [ ] Input data stream sets `elasticsearch.dynamic_dataset: true` AND `dynamic_namespace: true` (without both, reroute silently fails) -- **HIGH**
- [ ] `routing_rules.yml`: one rule per entity type on `ctx.<type>?.id != null`, namespace `["{{data_stream.namespace}}", "default"]`; conditions IDENTICAL to the `pipeline` dispatch conditions in `default.yml` (drift routes docs to the wrong stream) -- **HIGH**
- [ ] Device/host routing rules ordered before user rules where a doc could match both -- **MEDIUM**
- [ ] Every routing target has a `data_stream/<type>/` directory (manifest = title/dataset/type only) with mirrored `fields.yml`/`ecs.yml` updated in the SAME PR — the copies are hand-trimmed and drift silently -- **MEDIUM**

### Pipelines

- [ ] Marker handling explicit: `event.action` removed unless `started`/`completed`; markers stay in the `entity` stream (they carry no `user.id`/`device.id`) and are never routed into a typed stream nor have `asset.type` overwritten by a fallback branch (post-rename guard, cf. entityanalytics_ad #19226) -- **HIGH**
- [ ] `event.kind: asset` set exactly once in `default.yml`; per-type pipelines set `asset.category: entity` and `asset.type: <provider>_<type>`; `event.category`/`event.type` use ONE consistent style (`append` or `set`) within the package -- **MEDIUM**
- [ ] Entity keys derived from stable vendor IDs, not display names: `asset.id`, `user.id`/`user.name`, `host.id`/`host.name` (devices); `related.user`/`related.hosts` populated -- **HIGH**
- [ ] Painless tag checks are null-safe: `ctx.tags?.contains(...)`, never `ctx.tags.contains(...)` -- **MEDIUM**
- [ ] `preserve_original_event`/`preserve_duplicate_custom_fields` honored: tag-gated `event.original`, and a COMPLETE remove list including `foreach` over nested lists (registered users/owners, groups) -- **MEDIUM**
- [ ] Standard tail present in the processor list AND `on_failure`: `event.kind: pipeline_error` + append `preserve_original_event` tag; recursive null/empty pruner runs last before the tail -- **MEDIUM**
- [ ] `ecs.version` consistent with the package's `_dev/build/build.yml` ECS pin and with sibling entityanalytics packages -- **LOW**
- [ ] Dataset-filter `drop` processors key on a tag the hbs actually emits dynamically (`{{dataset}}-entities`), not a hardcoded one -- **MEDIUM**

### Template and tests

- [ ] Policy tests (`_dev/test/policy/`) cover every toggle/conditional block in the hbs (default + each enrichment toggle; entityanalytics_entra_id is the model) -- **MEDIUM**
- [ ] Enrichment toggles never emit an empty `enrich_with:`/`expand.*:` list; mutually exclusive options (e.g. `intune_managed_devices` vs custom `select.devices`) documented as conflicting -- **MEDIUM**
- [ ] `{{#contains "forwarded" tags}}` -> `publisher_pipeline.disable_host: true` present -- **LOW**
- [ ] Pipeline tests per entity type with `test-common-config.yml` injecting the `preserve_*` tags (both removal branches exercised); system tests per enrichment toggle pinned `use_minimal_state: false` when the legacy path is exercised; a `routed_data_streams`-style script test asserting per-type doc counts AND the residual entity-stream count; a minimal-state script test (EXCEPT okta — blocked on elastic/beats#52061, expect the citation instead) -- **MEDIUM** (HIGH for new packages)
- [ ] New enrichment toggle => mock service covers the new endpoints, and the toggle is implementable by the current agent version (the sign-in-activity add/remove/re-add lesson) -- **MEDIUM**

### Docs and changelog

- [ ] Permission/scope table updated for any new API surface, including which fields stay null without it and licensing notes (Graph: `GroupMember.Read.All`, `User.Read.All`, `Device.Read.All`, +`AuditLog.Read.All` for MFA/sign-in-activity, +`DeviceManagementManagedDevices.Read.All` + Intune license for Intune fields; Okta: `okta.users.read`/`okta.devices.read`, `okta.roles.read` for perms) -- **HIGH**
- [ ] The "asset inventory, not an audit trail" paragraph present, pointing at the sibling audit-log integration -- **MEDIUM**
- [ ] On-upgrade behavior changes spelled out in the changelog entry (e.g. "existing policies switch to the minimal-state sync implementation on upgrade") -- **MEDIUM**

### Anti-flags (never report these)

- Do NOT demand fingerprint/`_id` processors or entity-store transforms — append-only by design; the package's contract is the `user.entity.*`/`host.entity.*` + `asset.*` FIELDS.
- Do NOT demand marker-dependent logic (or flag its absence) on a minimal-state-default package — that path emits no markers.
- Do NOT flag missing enrichment fields as pipeline bugs — provider enrichment is best-effort (warn + skip).
- Do NOT flag duplicate-looking replays after restarts/failures — cursors roll back but published events are not retracted.
- Do NOT flag sibling-package divergences (stream `enabled:` default, `dataset` default, tracer gating style, proxy placement, `custom_options` presence) retroactively — treat sibling consistency as the bar only for the streams a PR touches.
