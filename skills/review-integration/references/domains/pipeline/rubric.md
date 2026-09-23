# Severity rubric — pipeline

Canonical review guidance for standalone and hosted reviewers. Apply the
[shared definitions and calibration](../severity-core.md) and
[shared conflict resolutions](../conflicts-core.md).
Also read the [relevant conflict resolutions](conflict-resolutions.md).

## Universal rules (same severity regardless of package age)

| Domain | Finding | Severity |
|--------|---------|----------|
| Pipeline | event.ingested set in pipeline | HIGH |
| Pipeline | Trailing remove of event.original PRESENT (deprecated pattern; never ask for one to be added) | HIGH |
| Pipeline | Double-brace Mustache instead of triple | MEDIUM |
| Pipeline | Unanchored grok pattern | MEDIUM |

## Rules with new-vs-existing severity adjustment

| Domain | Finding | New package | Existing package |
|--------|---------|------------|-----------------|
| Pipeline | Missing pipeline-level on_failure | HIGH | Missing entirely: HIGH. Wrong structure/order: LOW |
| Pipeline | `preserve_duplicate_custom_fields` (manifest var, template tag, pipeline conditional, or test-config tag) | HIGH -- applies to new packages AND to a new data stream added to an existing package | Not a finding when the use pre-exists in an unchanged data stream (was officially recommended before deprecation). MEDIUM when the PR touches the processors that implement the pattern; HIGH when the PR refactors that pipeline |
| Pipeline | Missing processor tag | MEDIUM | LOW (only enforced from format_version 3.6.0) |
| Pipeline | CEL-only opening processors (`remove_agentless_tags` + terminate) missing on a NEW CEL stream in an agentless-enabled package (`deployment_modes.agentless.enabled: true`), or where sibling pipelines already carry the block | MEDIUM | LOW at most (Agentless-era additions; pre-Agentless integrations don't have them — absence there is not a finding) |
| Pipeline | JSE00001 pattern differs from current standard | HIGH | MEDIUM (if event.original is preserved by alternate means) |
| Pipeline | Geo enrichment without ASN companion | HIGH | MEDIUM (newer standard) |

## ECS field declarations

Judge the fields a pipeline sets against the "ECS field declarations"
section in `../fields/rubric.md`.

## Pattern details

- Pipeline-level `on_failure` uses the required three-step structure. For a new
  package, missing or wrong structure is HIGH. For existing packages, missing
  handling is HIGH and wrong structure/order is LOW. Full structure enforcement
  starts at `format_version >= 3.6.0`.
- `preserve_duplicate_custom_fields` is a deprecated pattern that keeps
  spreading by copy-paste from older packages. Decide by the age of the **data
  stream**, not the package: a data stream whose directory is added in the diff
  is new even when `changelog.yml` has many entries, and gets HIGH. Look for the
  manifest `vars` entry and the `tags` entry in the stream template first -- a
  new stream can declare the variable without its own pipeline containing the
  `remove ... if !ctx.tags.contains(...)` conditional, and the manifest entry
  alone is the finding. Pre-existing use in an unchanged stream is technical
  debt, not a finding; it becomes MEDIUM when the PR edits the processors that
  implement the pattern and HIGH when the PR refactors that pipeline. See
  `conflict-resolutions.md` for the reroute exception.
- For JSE00001, verify that `event.original` is preserved. An existing alternate
  implementation that achieves this is MEDIUM, not HIGH.

## Additional review exceptions

- A missing `@custom` pipeline call (`{{ IngestPipeline "@custom" }}`, or the
  `type@custom` / `global@custom` hooks) — Fleet injects these at install time, so
  package source pipelines must NOT declare them. Do not flag their absence as a
  missing extension point or upgrade-safety gap.
- A pipeline that does NOT remove `event.original` at the end. The trailing
  remove-unless-`preserve_original_event` processor is a DEPRECATED pattern:
  storage-optimization removal happens in a final pipeline outside the
  integration, which honors the `preserve_original_event` tag — so the
  package's toggle is NOT a no-op without an in-pipeline remove. Never ask
  for the processor to be added — its *presence* is the finding.
- A missing CEL-opening Agentless block (the `remove` of `organization`/
  `division`/`team` tagged `remove_agentless_tags`, plus the collector-error
  `terminate`) on an EXISTING pipeline. These are Agentless-era additions;
  pre-Agentless pipelines don't have them and retrofitting is a modernization
  choice, not a defect. Flag the absence only on a NEW CEL data stream in a
  package whose manifest enables agentless deployment, or where sibling
  pipelines in the same package already carry the block (a consistency gap).
