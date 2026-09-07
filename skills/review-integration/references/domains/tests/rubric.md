# Severity rubric — tests

Canonical review guidance for standalone and hosted reviewers. Apply the
[shared definitions and calibration](../severity-core.md) and
[shared conflict resolutions](../conflicts-core.md).

## Universal rules (same severity regardless of package age)

| Domain | Finding | Severity |
|--------|---------|----------|
| Tests | No handwritten pipeline test/input fixtures | HIGH |
| Tests | Missing test-common-config.yml | HIGH |

## Rules with new-vs-existing severity adjustment

| Domain | Finding | New package | Existing package |
|--------|---------|------------|-----------------|
| Tests | source.geo in dynamic_fields | MEDIUM | LOW (acceptable workaround if version bump not in scope) |

## Generated outputs are excluded

Never read raw `*-expected.json` or `sample_event*.json` during a review, including
through full diffs, repository APIs, or other tools. Do not regenerate, compare,
or audit these snapshots for stale values, mismatches, formatting, or provenance.
Leave their validation to `elastic-package` in CI. Their paths/counts may appear
in the change index solely to explain the exclusion.

Review handwritten test configurations, input fixtures, and producing source.
Check which normal, boundary, and failure scenarios they exercise, including
relevant routing branches, missing/optional fields, and recovery behavior. Report
concrete scenario gaps without using generated outputs as evidence.

For a demanding scenario, an already-supplied compact test digest may help. It is
not a default read, proof of complete coverage, or permission to inspect raw
snapshots. Do not create or verify the digest by reading generated outputs.
If permitted evidence is insufficient, state that limitation rather than infer
that all scenarios passed. If only excluded outputs changed, skip the review
without issuing a clean assessment.
