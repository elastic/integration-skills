# Entity steps

How to apply an `entity-mappings` report. The pipeline builder reads this file and then, under
`entity-mappings/references/`, `entity-field-catalog.md` and `entity-pipeline-patterns.md`.
Those two are the authority on fields, categorization and processors, and they win when a
report row disagrees with them. This file only adds what applying a report to a published
stream needs.

## Reading the entity report

The statuses do **not** say what the package already does. ✅ *Direct mapping* and 🔄 *Derived
mapping* are instructions: this source field, or this derivation in plain English, feeds that
ECS field. Check the pipeline and implement what is missing. Your work items already carry
the action for each 🔍 gap, and its implementation notes give endpoint, scope and data shape.

*Entity Type Classification* gives the `entity.type` per stream. *ECS Availability Impact*
names the fields that need the pin, which Phase 4 has already set. *Required New Scopes /
Permissions* lists the scopes the integration does not request today (D5).

## Order of work inside a stream

Follow the patterns file section by section: event categorization, `entity.id` and the
dedicated fieldsets, boolean coercion, array-valued attributes, relationship objects,
`@timestamp` on snapshots. On top of it:

1. **Only the ECS leaves the report lists.** A value with no ECS field (`isEmployee`,
   `siteAdmin`, …) goes to `<integration>.<data_stream>.<field>`, never under
   `entity.attributes.*`.
2. **`entity.id` must be stable** across collection cycles. When the report offers several
   keys, that is D8.
3. **Fixtures**: extend the handwritten inputs with the source fields the mappings need, one
   record per shape (for example a user with and without MFA). Anonymize.
4. **Self-check** against the patterns' *Entity pipeline review checklist* before returning.

## Rules specific to a published stream

- **A D3 work item**: do what its Action says for this release, and nothing more. This covers
  `event.kind` on a stream that publishes `event` and is really an inventory snapshot, and
  `entity.attributes.asset` or any other invented entity field found in the package. "This
  record is an asset" is expressed with `event.kind: asset`.
- **New scopes or permissions** the report lists: D5. Requiring them is a breaking change for
  existing policies.
- **Do not apply entity fields** to event log or CDR findings streams, even if the report
  lists them: report the contradiction.

## What the orchestrator needs back for the README

Besides the return the task prompt asks for: which entity attributes need a new variable,
scope or permission. Entity data streams carry no content-capture settings.
