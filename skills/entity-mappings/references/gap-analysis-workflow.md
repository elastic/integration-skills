# Entity field gap analysis workflow

Use this workflow to analyse an existing Elastic integration package and determine which
ECS `entity.*` fields can be supported, which need additional API calls or data streams, and
which are not applicable.

This workflow can also be triggered standalone via `/entity-mappings @packages/<package>`.

---

## Before you start — classify the data streams

**Gap-analysing an event stream is a category error.** Before mapping any fields, classify
each data stream in the package:

1. Read `entity-mappings/references/entity-datastream-classification.md` end-to-end.
2. Apply the review-time classification rule (first hit wins) to each data stream.
3. Only proceed with entity field analysis for streams classified as entity streams.
4. For event streams, note "not an entity stream — entity fields do not apply" and move on.

If the package has **no entity streams at all**, report that conclusion and stop. The
package does not need entity field support in its current form; a new data stream may be
needed (investigate in Phase 4).

---

## Phase 1 — Understand the integration

Navigate to `packages/<name>` (or use the path provided). Read, in order:

1. `README.md` or `docs/README.md` — what the integration collects, which API/source
2. `data_stream/*/fields/*.yml` — existing ECS field mappings per data stream
3. `data_stream/*/elasticsearch/ingest_pipeline/*.yml` — current pipeline processors
4. `data_stream/*/sample_event.json` or `_dev/test/pipeline/test-*.json` — real data samples
5. `data_stream/*/agent/stream/*.yml.hbs` — collection method, API endpoints called
6. Root `manifest.yml` and data stream `manifest.yml` — configuration options, vars, and API endpoints

Note:
- Which entity types this integration primarily represents (host, user, service, etc.)
- Which API endpoints or data sources are currently called
- What raw fields are available in sample data that are not yet mapped to ECS entity fields

---

## Phase 2 — Fetch vendor documentation

Identify the upstream API or data source (usually visible in Phase 1 from the agent
stream template or README).

For common vendors:
- AWS: https://docs.aws.amazon.com/
- GCP: https://cloud.google.com/docs
- Azure: https://learn.microsoft.com/en-us/azure/
- GitHub: https://docs.github.com/en/rest
- Okta: https://developer.okta.com/docs/reference/
- Other: identify the vendor docs URL from the integration README or manifest

Fetch the relevant API documentation. Note:
- API endpoints available and their schemas
- Sample data structures
- Fields that could map to entity attributes, lifecycle, or relationships

---

## Phase 3 — Map each catalog field

**Read `entity-mappings/references/entity-field-catalog.md` before mapping.**

For each stream classified as an entity stream in the pre-step, work through every field in
the catalog and assign one of four statuses:

| Status | Meaning |
|---|---|
| ✅ Direct mapping | A field maps 1:1 or near-1:1 to an integration field. Provide the source field name. |
| 🔄 Derived mapping | The value can be computed or inferred from existing fields (conditional, script, combination). Explain the derivation logic. |
| 🔍 Requires investigation | No current field maps to this, but the data source *may* provide it. Move to Phase 4. |
| ⛔ Not applicable | This field is not relevant to the entity type. Justify specifically — "not applicable" is never assumed without explanation. |

Fields to assess (always assess all; skip only with explicit justification):

- `event.kind`, `event.category`, `event.type` (categorization)
- `entity.id`, `entity.name`, `entity.type`, `entity.source`, `entity.last_seen_timestamp`
- `user.entity.attributes.mfa_enabled`, `.managed`, `.permissions`, `.known_redirects`, `.storage_class`, `.oauth_consent_restriction`
- `user.entity.lifecycle.last_activity`
- `user.entity.relationships.owns`, `.depends_on`, `.supervises`, `.administers`
- Adjacent fields: `user.name`, `user.id`, `user.email`, `user.group.name`, `user.roles`, `host.name`, `host.id`, `host.os.version`

If the integration has **multiple entity data streams**, analyse each separately where answers differ.

---

## Phase 4 — Investigate gaps

For every field marked 🔍, investigate through each angle:

### 4a. Search the package for clues

- Are there commented-out fields, TODOs, or alternative data streams in the integration
  that might surface this data?
- Are there configuration variables in `manifest.yml` that, if enabled, would expose this field?

### 4b. Check the vendor API

- Search for or fetch the relevant endpoint documentation.
- Determine whether the missing field is available via:
  - **Existing API call** — the data is already fetched but not extracted
  - **Different endpoint** on the same API — not currently called
  - **New API call** — requires additional permissions or scopes
  - **New data stream** — the data represents a separate entity type or entity population

### 4c. Recommendation

For each gap, choose one:

| Recommendation | When to use |
|---|---|
| **Extract from existing call** | The field is available in the current API response but not yet mapped |
| **Add API parameter** | Modify the existing call to request additional fields (via `fields`, `expand`, etc.) |
| **New API call** | Describe the endpoint, required permissions, and when it would be triggered |
| **New data stream** | The data represents a distinct entity population warranting its own stream |
| **Cannot be collected** | Explain why the data is not available from this source at all |

**Do not design the pipeline or field YAML.** Describe the data that is available and what
the source provides. Implementation is the pipeline builder's job.

**Note required new scopes/permissions** — these must be called out explicitly because they
require user action to enable (OAuth scopes, IAM policies, admin tokens). Example: GitHub
`read:org` for MFA status, Okta admin scope for lifecycle data.

---

## Dispatch convention for per-stream analysis subagents

When the analysis scope is large (several entity streams, or a complex API surface), dispatch
per-stream analysis subagents following the repo's dispatch convention:

1. Point each subagent at `entity-mappings/references/analysis-subagent-guidance.md` **by
   path** — do not paste its contents into the task prompt.
2. Tell each subagent: its working package path, which data stream to analyse, the entity
   type, and any documentation URLs.
3. Each subagent writes its findings to a per-stream markdown file; you read and synthesize.

---

## Output

Write the final report following `entity-mappings/references/gap-analysis-report-template.md`.
Save it as `entity-gap-analysis.md` in the package root (alongside `README.md`), or to
a path the user specifies.
