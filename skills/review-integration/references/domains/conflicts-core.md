# Conflict resolutions -- shared core

> **Not for single-pass reviews.** This file exists for reviewers that own
> a single domain within a larger, domain-split review. If you are running
> the `review-integration` skill end to end, read `../conflict-resolutions.md` instead --
> it is the authoritative copy.

Conflict resolutions that apply to every domain, plus the cross-domain
entries no single domain owns alone. A domain-scoped reviewer reads this
file plus the `conflict-resolutions.md` for its own domain, where one
exists; a single-pass review reads `references/conflict-resolutions.md`
instead, which carries the same content whole.

> **Maintenance:** these entries mirror `../conflict-resolutions.md`. A PR
> that changes an entry must change both files in the same PR.

Build skills (loaded in Step 3) are prescriptive — they teach the current recommended way to build integrations. The review skill must accept a broader range of valid patterns, including older approaches that predate current standards. This file documents where the review interpretation diverges from the build prescription and why.

## ECS field declarations vs dynamic mapping

Cross-domain: the fields reviewer judges the declarations, the pipeline
reviewer judges the fields its pipelines set.

**Conflict**: The `ecs-field-mappings` skill says pipeline fields must be declared in `fields/ecs.yml`. But standard ECS keyword/date fields work via dynamic mapping and don't require explicit `external: ecs` declarations.

**Resolution**: On packages whose `conditions.kibana.version` floor is >= 8.13.0, only flag when the field type genuinely requires explicit declaration (`geo_point` on non-standard parent prefixes, `geo_shape`, `nested`, `flattened`) or when `elastic-package` would fail validation — standard keyword/date and standard-prefix geo ECS fields are not findings. If the constraint admits stacks below 8.13 (which never apply `ecs@mappings`, regardless of package-spec version), pipeline-set ECS fields still need declarations.

## Build-skill authoring process vs product correctness

Applies to every domain.

**Conflict**: Build skills include both runtime requirements and authoring-process guidance. Runtime requirements (e.g., mito compatibility — mito is the library Elastic CEL programs execute on, not generic CEL) are product correctness concerns. Authoring-process rules (e.g., "write no more than 10-15 lines before testing," reference loading order, incremental development methodology) guide how to produce code, not what correct code looks like.

**Resolution**: Runtime requirements from build skills are valid review concerns — a CEL program that doesn't work on mito is defective. Authoring methodology and workflow sequencing are not review findings. Review evaluates the product artifact, not how it was produced.

## First-version leniency

Applies to every domain; the changelog and logo specifics matter most to
the structure reviewer.

**Conflict**: Strict changelog-link and asset rules would flag every first-version package for placeholders that are expected during initial development.

**Resolution**: For first-version packages (`0.0.1`/`1.0.0` with a single changelog entry), placeholder changelog links and placeholder logos/icons are informational notes only, not findings. Do not judge a link by matching a known placeholder value: `elastic-package lint` only checks that a github.com link ends in a positive integer, so `pull/99999`, `pull/12345`, and every other invented number pass it equally. The property that matters is whether the link points at the PR or issue that introduces the change, and `.buildkite/scripts/check_changelog_entries.sh` already enforces exactly that on every link a PR ADDS (`/issues/<n>` links are exempt; the skip label is `changelog-link-check:skip`). Do not duplicate a deterministic CI check — flag a link only where that check cannot see it, such as an entry the PR did not touch or a review with no PR context. `elastic-package lint` REJECTS `pull/0`, so never grant leniency to that value. CI keeps flagging the link until it is replaced with the real PR link before merge; that is expected pre-merge behavior, not noise.
