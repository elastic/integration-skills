# Decision points

Every design decision that this skill asks the user about, with the question and the options.
Phase 3 of the workflow says when and how to ask. The recommended option goes first. If a
builder meets a decision, it returns `DECISION NEEDED` and you ask it the same way.

**Not decisions.** Do not ask about what the rules in `SKILL.md` fix: source-side settings
are documented only, content capture is off by default, new data streams are deferred, vendor
fields are copied and kept. Do not ask either about what the mapping skills fix: field names,
values, the tool-call representation, where tool results go, finish reasons. A later answer on
a public issue that changes one of those is D7.

## D1: The report is stale

- **Comes up when:** the package changed after the report was written, the stream list
  differs, or Phase 1 marks rows `contradicted`.
- **Options:** Re-run the assessment first (recommended) / Continue with the verified rows
  only.

## D2: ECS pin bump

- **Comes up when:** the package pin is below the floor of Phase 4.
- **Question:** bump `_dev/build/build.yml` and `ecs.version` in the pipelines of all N data
  streams? List them, in scope or not.
- **Options:** Bump (recommended) / Do not bump, which stops the work for that kind.
- **Cost:** every stream's expected test output changes, and fields other streams take from
  ECS are resolved at the new pin.

## D3: Published fields that change

- **Comes up when:** a GenAI row has Change *Breaking* (a ⚠️ fix, a rename, a retype, a value
  that changes meaning, the removal of a deprecated field), or an entity item changes or
  removes something the package publishes. Not asked when the input gives the release scope.
- **Question:** which release does this run build? State, per field, the rules, ML jobs and
  dashboards that read it (Phase 1).
- **Options:** The next minor: every New and Additive row, and the minor half of each Breaking
  row (recommended) / The next major: the major half, for fields whose replacement the package
  already has. It can be built early, and it is released only after the consumers have
  moved / Leave the Breaking rows out.

| Breaking row | Minor half | Major half |
|---|---|---|
| A wrong or non-ECS name (`gen_ai.system`, an OpenTelemetry attribute under `gen_ai.*`, an invented entity field) | Add the correct field next to it. Deprecate the old one in its `description`. | Remove the old field. |
| A wrong type under the right name | Nothing: one name cannot hold two types. Document the limitation. | Retype. |
| A value that changes meaning (cache-inclusive token totals, an OTel operation name, another provider string) | Keep the current value available in `event.action` or the vendor namespace. | Change the value. |
| A new field whose path holds a published object (`gen_ai.request.model` over `gen_ai.request.model.id`) | Put the value in a vendor field. | Replace the object with the ECS field. |
| `event.kind` on an entity stream that publishes `event` | Nothing. Say in the question that the stream does not pass the entity checklist until the major. | Change it to `asset`. |

- **Cost:** a major is a `breaking-change` entry. Rules and ML jobs that read the old field or
  compare the old value stop matching.
- **Note:** the Action of each D3 work item states the half this run builds, because builders
  do not read this file. A removal also covers the package's own dashboards, transforms and
  ML assets that read the field: this skill does not edit them, so list them under *Breaking
  changes* as work the major needs. Section 9 of `genai-detection-conventions.md` is the
  rule for the rest: never a replacement and a removal in one release, the full-body `text`
  field for rules that match a whole body, and a sequence agreed otherwise on the package's
  issue.

## D4: A source-side change

- **Comes up when:** Phase 5 adds a request parameter, a request setting or a call.
- **Question:** propose the variable's name, title and scope (data stream or package), and
  its default when it does not collect content. Say what the change adds per response or per
  collection cycle.
- **Options:** Behind the proposed variable, off by default (recommended when it adds
  content, volume, cost, a request per cycle or rate-limit pressure) / Always on, because the
  data is small and comes in the same response / Skip the rows that need it.
- **Note:** a variable that collects content is off by default whatever the answer.

## D5: A new required scope or permission

- **Comes up when:** an item needs a scope, IAM policy or admin token the integration does
  not request today.
- **Options:** Make that request optional behind a variable, off by default (recommended) /
  Require it, which is a breaking change for existing policies / Skip those fields.

## D6: Provider on a multi-backend product

- **Comes up when:** a product can route to several backends (GenAI), and no field, resource
  attribute or session setting tells them apart per record. When one does, use it: that is
  not a decision.
- **Question:** propose the variable's name and its default, the vendor's own API.
- **Options:** A package variable (recommended, the catalog's rule for multi-backend
  products) / Leave the provider unset.
- **Note:** never a constant: it is wrong for every other backend.

## D7: A value the report left open

- **Comes up when:** a vendor operation, event or type has no clear OpenTelemetry (GenAI) or
  ECS (entity) value, or a comment on a public issue that is newer than the mapping skill
  changes a row (the user or a builder reports it).
- **Options:** One option per candidate value, plus Leave unmapped.

## D8: Identity

- **Comes up when:** an entity report names several candidates for `entity.id` or leaves
  `entity.type` open; or a GenAI report leaves `user.name` open, because the caller id is not
  stable across sessions and the conventions do not cover its form.
- **Options:** One option per candidate, with the stability of each (does it survive
  collection cycles, sessions, renames?), plus, for `user.name`, Leave unset and document why.
- **Note:** whatever the answer, the README states how `user.name` is derived.

## D9: Fixture without a real sample

- **Comes up when:** a `todo` row's source path is in no fixture, mock response or generator
  code of the package: only the vendor documentation shows it. Typical for a source-side
  setting that was never on.
- **Options:** The user provides an anonymized sample / Build the fixture from the vendor
  documentation, and mark it in the report as not verified against real data (recommended when
  no sample is available) / Skip the mapping.

## D10: Adjacent ECS fields

- **Comes up when:** the report lists adjacent fields beyond the ones its *Detection
  conventions* table asks for (`file.path`, `process.command_line`, `url.*`, …).
- **Options:** Leave them out (recommended) / Include them.

## D11: A problem found on the way

- **Comes up when:** the work meets something the report does not cover: a baseline test
  that fails, a record type that already fails the pipeline, real names or account ids in
  existing fixtures, a `cel` or `httpjson` input without agentless, a reviewer finding on
  something this run did not introduce, a new finding from the check in Phase 10.
- **Options:** List it as a follow-up (recommended when the work does not depend on it) / Fix
  it in this change, with its own changelog entry (recommended when it blocks the work or
  sits in the code being changed).
- **Note:** real personal data is always reported, whatever the answer. When it sits in a
  generated file that cannot be regenerated here (`sample_event.json` without a system test),
  the user decides whether the same literal replacement is applied to it by hand.
