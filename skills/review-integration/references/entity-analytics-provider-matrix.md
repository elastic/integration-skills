# Entity-analytics input: provider semantics for reviewers

Facts verified 2026-08-12 against elastic/beats main
(`x-pack/filebeat/input/entityanalytics`). The input is **Experimental**.
Consumed by `entityanalytics_entra_id` (provider `azure-ad`),
`entityanalytics_okta` (`okta`), and `entityanalytics_ad` (`activedirectory`);
a `jamf` provider exists but has no dedicated package.

The input has TWO code paths selected by `use_minimal_state` (bool, default
false): legacy per-provider kvstore inputs, and minimal-state `entcollect`
providers. Packages now default `use_minimal_state: true` via a hidden var.
**The observable event stream differs between the paths** — most
entity-analytics review false positives come from assuming the wrong path.

## Path-level differences (highest false-positive risk)

| Behavior | Legacy path | Minimal-state path |
|---|---|---|
| Full-sync bracket markers (`event.action: started`/`completed` + `event.start`/`event.end`, `labels.identity_source`) | Emitted around full syncs only — and conditionally: azure-ad and jamf skip both markers when state is empty; okta emits `started` BEFORE fetching, so a mid-sync failure leaves an unclosed bracket | **Never emitted** |
| `event.kind: asset` | **Never set by the input** (pipelines set it) | Always set by the input |
| Restart behavior | Resumes schedule from persisted `last_sync` — a restart does NOT force a full sync | **Full sync on every process start** |
| State | Full entity state + cursors in bbolt `kvstore/<input-id>.db` | Cursors/idsets only; agentless deployments use an ES-backed store |
| Deletion detection (okta) | **Never emits deletions** — deprovisioned users appear as `user-modified` with `okta.status: DEPROVISIONED` | Detects deletions via idset |

Consequences to apply during review:
- Transform/query/pipeline logic keyed on markers or on input-set
  `event.kind: asset` is path-dependent. Flag logic that assumes markers exist
  when the package defaults `use_minimal_state: true`; flag mappings that
  REQUIRE input-set `event.kind` under legacy.
- Full sync republishes ALL known entities with `event.action: *-modified`
  (not `*-discovered`). Pipelines must be idempotent on `user.id`/`device.id`.
- Never demand fingerprint/`_id` processors — these packages are deliberately
  append-only; dedup/latest-doc collapsing is a downstream (entity store)
  concern, and the packages ship `user.entity.*`/`host.entity.*` + `asset.*`
  FIELDS only, never entity-store transforms. Both demands are anti-flags.

## Per-provider matrix

| | azure-ad | okta | activedirectory | jamf |
|---|---|---|---|---|
| Entity types | users + devices (`dataset: all/users/devices`) | users + devices | users + devices + **groups** (`group.id` docs need `include_empty_groups`, 9.4+ preview) | **devices only — no `dataset` option** |
| Incremental mechanism | Graph delta links | `lastUpdated ge` cursor (second-resolution, `ge` not `gt`) | LDAP `whenChanged>=` filter (NOT USN-based) | **none — full page walk every cycle** (docs claiming server-side filtering are stale) |
| Deletion signal | Graph `@removed` tombstones (delta-payload fields only, attributes not re-fetched) | never (legacy) / idset (minimal) | absence, detected during FULL sync only; `whenChanged` set to detection time | `IsManaged` flag; legacy has a known inversion bug — fixed only on the minimal path |
| Interval validation | rejects `update > sync`; **allows equal** | rejects `update >= sync` | rejects `>=` | rejects `>=` |
| `enrich_with` vocabulary | `mfa`, `sign_in_activity`, `none` (validated) | `groups` (default), `roles`, `factors`, `perms`, `devices`, `supervises`, `none` (**NOT validated — typos are silently ignored**, producing empty enrichment with no error) | n/a | n/a |
| Rate limiting | none (non-200 is fatal for the cycle) | per-endpoint from `X-Rate-Limit-*` headers; `limit_window`, `limit_fixed`, `batch_size` are okta-only options | none | none |
| Vendor namespace | `azure_ad.*` | `okta.*` (+ root-level `groups`/`roles`/`factors`/`devices`/`supervises`) | `activedirectory.*` (renamed to the package namespace in-pipeline) | `jamf.*` |

Defaults across providers: `sync_interval` 24h, `update_interval` 15m.

## Operational facts reviewers need

- **Enrichment is best-effort.** azure-ad MFA/sign-in-activity and okta
  per-user enrichment failures warn and skip — absent enriched fields are not
  a pipeline bug.
- **State is keyed by input `id`.** Changing the id orphans kvstore state
  (next run re-discovers everything). Changing `select.*`/`enrich_with` does
  NOT invalidate persisted state: azure-ad merges old+new attribute sets, so
  removed attributes persist across incrementals until the next full sync.
- **Partial-failure semantics:** a fetch error aborts the cycle and rolls back
  cursors, but already-published events are not retracted — duplicates and
  unclosed okta `started` brackets are normal, not package bugs.
- **`labels.identity_source`** is set to the input's id on every doc (both
  paths) — packages expose an `id`-style var for it; a declared
  `labels.identity_source` field with no var to feed it is an orphan worth
  noting (and vice versa).

## Upstream doc/code drift — do NOT propagate into findings or package docs

- Okta `collect_device_details` is documented in beats but does not exist in
  code — packages must use `dataset: devices|all` instead.
- Jamf incremental sync is documented as server-filtered; the code full-walks
  every cycle — rate/quota estimates based on the doc are wrong.
- Okta minimal-state script tests are blocked upstream (elastic/beats#52061:
  the provider hardcodes https without custom-TLS support, so it cannot run
  against a self-signed mock). Do NOT flag a missing okta minimal-state test
  as a package gap; expect the blocking issue cited in a comment instead
  (the packages already do this).
