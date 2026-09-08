# Shared conflict resolutions

Canonical review exceptions shared by standalone and hosted reviewers. Load this
once and follow the relevant domain conflict reference when more detail is needed.

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

**Resolution**: For first-version packages (`0.0.1`/`1.0.0` with a single changelog entry), placeholder changelog links and placeholder logos/icons are informational notes only, not findings. At any later version they are LOW findings. The standard for a changelog `link` is one thing: the pull request URL of the PR that introduces the change, `https://github.com/elastic/integrations/pull/<n>`. Judge an added link against that in three steps. (1) Shape: a URL that is not `/pull/<n>` is a finding, including an `/issues/<n>` link -- the repository's `check_changelog_entries.sh` tolerates issue links, the review standard does not. (2) Placeholder: a pull number that is one digit repeated up to four times (`1`, `99`, `1111`, `9999`), any run of zeros, or `99999`, `12345`, `123456` is never a real target; `elastic-package lint` accepts all of them except `pull/0`, which it REJECTS, so never grant leniency to that one. (3) Match: any other pull number that is not this PR's own is a mismatch, unless the PR carries the `changelog-link-check:skip` label, which the changelog sync workflow applies to PRs that legitimately link the backport PR. A host may supply these three as `changelog_link_shape`, `changelog_placeholder`, and `changelog_link_mismatch` observations in `context/diagnostics.json`; verify each against the diff before reporting. CI fails the mismatch case on its own pre-merge, so report it once at LOW and do not escalate; an unreplaced placeholder still failing CI is expected pre-merge behavior, not extra noise.
