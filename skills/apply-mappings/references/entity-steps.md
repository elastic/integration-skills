# Entity steps

Steps that apply to an `entity-mappings` report. The pipeline builder reads this file together
with `entity-mappings/references/entity-field-catalog.md` and
`entity-mappings/references/entity-pipeline-patterns.md`. Those two are the authority on fields,
categorization and processors. This file only says how to apply a report with them.

## Reading the entity report

The statuses do **not** mean "already done" in an entity report.

- **✅ Direct mapping**: a source field the integration already has maps to the ECS field. It
  is an instruction. Check the pipeline and implement it when missing.
- **🔄 Derived mapping**: the value is computed from existing fields, with the derivation in
  plain English. Same: check, then implement.
- **🔍 Gap analysis**: each gap has one recommendation (*Extract from existing call*, *Add API
  parameter*, *New API call*, *New data stream*, *Cannot be collected*) and implementation notes
  with endpoint, scope and data shape. The action table in `SKILL.md` maps them.
- **⛔ Not applicable**: nothing to do.
- *ECS Availability Impact* says whether the v9.5.0 pin is needed. *Required New Scopes /
  Permissions* lists scopes the integration does not request today (D11).
- *Entity Type Classification* gives the `entity.type` per stream.

## Order of work inside a stream

1. **Pin**: done in Phase 4 (at least `git@v9.4.0`, bumped to `git@v9.5.0`).
2. **Categorization**: `event.kind: asset` with `set`; `event.category` and `event.type` as
   arrays with `append`; no `event.outcome`.
3. **Identity**: `entity.type` from the report, lowercase; `entity.id` mirroring the dedicated
   fieldset id (`user.id`, `host.id`); `entity.name`, `entity.source`,
   `entity.last_seen_timestamp`. The key must be stable across collection cycles (D10 when the
   report offers several).
4. **Attributes, lifecycle, relationships**: only the ECS leaves the report lists. Coerce
   booleans, write array-valued attributes as arrays, build relationship objects with the nine
   allowed keys.
5. **No-ECS values** (`isEmployee`, `siteAdmin`, …): `<integration>.<data_stream>.<field>`.
   Never under `entity.attributes.*`.
6. **`@timestamp`** stays the collection time. A source "updated at" goes to
   `entity.lifecycle.last_activity` when that is what it means.
7. **Fixtures**: extend the handwritten inputs with the source fields the mappings need, one
   record per shape (for example a user with and without MFA). Anonymize.
8. **Self-check** against the entity pipeline review checklist before returning.

## Rules specific to applying on an existing package

- **Stream names and shapes**: user and host streams are separate groups, even in one package.
  Two user streams with the same source shape can be grouped.
- **`event.kind` on a stream that publishes `event`** and is really an inventory snapshot: this
  changes published output. Treat it like D4.
- **New scopes or permissions** the report lists: D11. Document them in the README with how to
  grant them. Requiring them is a breaking change for existing policies.
- **`entity.attributes.asset`** or any other invented entity field found in the package: remove
  it after D2, and express "this record is an asset" with `event.kind: asset`.
- **Do not apply entity fields** to event log or CDR findings streams, even if the report
  lists them: report the contradiction.
- **Packages on the `entity-analytics` input** are not covered (see `SKILL.md`).

## README

Document every new variable, every new scope or permission, and which entity attributes need
them. Entity data streams carry no content-capture settings.
