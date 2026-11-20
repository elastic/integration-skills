# Decision points

Every design decision that this skill asks the user about, with the question and the options.
Ask them in Phase 3, before editing, with the platform's question tool (Claude Code:
`AskUserQuestion`, up to four per call). The
recommended option goes first. Each question names the fields and streams concerned and says
what the choice costs. If a builder meets a decision that is not listed here, it returns
`DECISION NEEDED` and you ask it the same way.

## Standing decisions (already made, do not ask again)

| Id | Decision |
|---|---|
| S1 | The skill implements what the integration controls (its own request, call or input configuration). What the user's environment or the vendor account controls (a logging setting, an environment variable in the user's application) is documented in the README only. The field is still mapped, so that it works once the setting is on. |
| S2 | A new variable that makes the integration collect prompts, responses, tool details or other content is **off by default**. |
| S3 | One stream at a time, except streams with the same shape, source and work items (Phase 2). |
| S4 | A report item that needs a new data stream is deferred to `create-integration`. |
| S5 | GenAI: no `gen_ai.*` name outside the pinned ECS release, even when a report, issue or reference table proposes it (`gen_ai.tool.call.count`, RFC 0060 fields). The value goes to the vendor namespace. |
| S6 | GenAI tool calls: one record per call (option A) where the source logs the tool run; order-aligned arrays (option B) for provider logs. Pipelines don't split documents (#22225). |
| S7 | GenAI: `gen_ai.response.finish_reasons` stays verbatim; the normalized value goes only into each output message's `finish_reason` (#20738). |

## Decisions

### D1: ECS pin bump

- **Comes up when:** the package pin is below the floor (GenAI `git@v9.5.0`, entity
  `git@v9.4.0`, bump to `git@v9.5.0`).
- **Question:** bump `_dev/build/build.yml` and `ecs.version` in the pipelines of all N data
  streams (list them)?
- **Options:** Bump (recommended) / Do not bump, and skip the mappings that need it.
- **Cost:** every stream's expected test output changes, and fields other streams use are
  resolved at the new pin.

### D2: A published field is wrong or not ECS

- **Comes up when:** a ⚠️ item names a field that is already published under a wrong name (for
  example `gen_ai.system`, an OpenTelemetry attribute under `gen_ai.*`, a wrong provider value).
- **Options:** Add the correct field now, deprecate the old one, and remove it in the next
  major after its consumers move (recommended; D16) / Fix in place, as a breaking change (only
  when the consumer check found nothing and the user accepts a major now) / Leave it.
- **Cost:** in place is a `breaking-change` entry and a major version bump. Both fields means
  duplicated data until the removal. State how many dashboards, rules and ML jobs read the old
  field (the report's *Breaking changes and consumers* table).

### D3: A published field needs a new type

- **Comes up when:** a field is typed differently from what the catalog requires (for example
  `gen_ai.response.finish_reasons` as `nested` through `external: ecs`).
- **Options:** Retype in the next major, and document the limitation until then
  (recommended; D16) / Retype in place now, as a breaking change / Leave it and document the
  limitation.
- **Cost:** a type change causes mapping conflicts for existing data (package-spec's breaking
  change list). The same name cannot be kept with two types.

### D4: A published field would change meaning

- **Comes up when:** a populated field gets a different value for the same input (token totals
  that now include cached tokens, an operation name mapped through the OTel values, a different
  provider string).
- **Options:** Keep the current value elsewhere first (`event.action` or the vendor namespace)
  in a minor, and change the field in the next major (recommended; D16) / Change it in place,
  as a breaking change / Leave the value and add nothing.
- **Cost:** package-spec counts "default behavior changes that alter collected/normalized
  output" as breaking. Rules and ML jobs that compare the old value stop matching.

### D5: A vendor field would be duplicated

- **Comes up when:** an ECS field is filled from a vendor field that the package already
  publishes.
- **Options:** Copy and keep the vendor field (recommended) / Rename, which removes the vendor
  field and is a breaking change.
- **Note:** normalized message fields never replace the raw body: they have a different shape.

### D6: The new variable

- **Comes up when:** Phase 5 adds a variable.
- **Question:** name, title and scope (data stream or package). The default is fixed by S2 for
  content capture. For a variable that only changes which metadata is requested, propose the
  default and say why.
- **Options:** Proposed name and scope (recommended) / Another name or scope (user text).

### D7: A request change that alters volume, cost or rate limits

- **Comes up when:** a parameter or call adds data to every response, or adds a request per
  collection cycle.
- **Options:** Always on, because the data is small / Behind a variable, off by default
  (recommended when volume or rate limits are affected) / Skip.

### D8: Provider on a multi-backend product

- **Comes up when:** a product can route to several backends (GenAI), and the report could not
  tell them apart per record.
- **Options:** A package variable with a default (recommended) / A per-record source field, if
  one exists / A constant.
- **Note:** a constant is wrong for every non-default backend (catalog rule 4).

### D9: A value mapping the report left open

- **Comes up when:** a vendor operation, event or type has no clear OpenTelemetry (GenAI) or ECS
  (entity) value.
- **Options:** One option per candidate value, plus Leave unmapped.

### D10: Entity identity

- **Comes up when:** the report names several candidates for `entity.id`, or leaves
  `entity.type` open.
- **Options:** One option per candidate, with the stability of each key (does it survive
  collection cycles, renames?).

### D11: A new required scope or permission

- **Comes up when:** an entity item needs a scope, IAM policy or admin token the integration
  does not request today.
- **Options:** Require it, which is a breaking change for existing policies / Make that request
  optional behind a variable, off by default (recommended) / Skip those fields.

### D12: Fixture without a real sample

- **Comes up when:** a 🔍 *Source-side setting* item has no sample in the repository, because
  the setting was never on.
- **Options:** The user provides an anonymized sample / Build the fixture from the vendor
  documentation, and mark it in the report as not verified against real data (recommended when
  no sample is available) / Skip the mapping.

### D13: Adjacent ECS fields

- **Comes up when:** the report lists adjacent fields (`user.*`, `file.path`, `url.*`, …).
- **Options:** Core fields and values with no ECS field only (recommended) / Include the
  adjacent fields.

### D14: The report is stale

- **Comes up when:** Phase 0 or Phase 1 finds that the package changed since the report, or
  items contradict the package.
- **Options:** Re-run the assessment first (recommended) / Continue with the verified items
  only.

### D15: Grouping

- **Comes up when:** Phase 2 proposes a group.
- **Question:** which streams go in which group, and why they count as the same shape.
- **Options:** The proposed groups (recommended) / One stream at a time.

### D16: Release plan for Breaking rows

- **Comes up when:** the report has Breaking rows, or D2, D3 or D4 is answered with a breaking
  option.
- **Question:** which rows go in this change (the next minor: add and deprecate) and which wait
  for the next major (remove or change), and is the consumer check done?
- **Options:** This change adds and deprecates; the removals are prepared as a separate major,
  merged after the consumers' updates are released (recommended) / Only the additive part now,
  no major prepared / Everything in one major now (only when no consumer was found).
- **Note:** list the consumers found per field (rules, ML jobs, dashboards). A rule that
  matches over a whole body needs a full-body `text` field in the vendor namespace that
  survives the major. Never add and remove in the same release.

### D17: Tool results on provider-log streams

- **Comes up when:** a provider-log stream carries tool results in the request, and #22225
  section 2 has no maintainer answer yet (check the issue first).
- **Options:** Keep results in `gen_ai.input.messages` as `tool_call_response` parts under
  `role: tool`, tool arrays with the response's calls only, `event.outcome` for the
  invocation (recommended, the interim rule in `genai-detection-conventions.md`, section 5) /
  Follow a later answer on #22225 (user text).
- **Note:** don't add result ids to `gen_ai.tool.call.id`, and don't set `event.outcome:
  failure` on an invocation because a tool failed.

### D18: Identity derivation

- **Comes up when:** the source's caller id is not stable across sessions and it is not an AWS
  ARN covered by the conventions, or the report leaves `user.name` open.
- **Options:** One option per candidate field, with whether it survives sessions and
  invocations / Leave `user.name` unset and document why.
- **Note:** whatever the answer, the README states how `user.name` is derived.
