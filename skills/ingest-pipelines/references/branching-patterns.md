# branching patterns for ingest pipelines

Use this guide when one linear parser is not enough and you need conditional or staged routing.

## When to branch

Branch when at least one of these is true:
- the same stream receives multiple formats (for example JSON and plain text)
- different event classes need different object mapping logic
- complex parsing becomes difficult to review in one large `default.yml`
- array items require per-element pipeline processing (`foreach` + `pipeline`)

Keep single-path pipelines for simple, uniform formats.

## Branching primitives

### `pipeline` processor

```yaml
- pipeline:
    name: '{{ IngestPipeline "pipeline_branch_name" }}'
    if: ctx.some?.field != null
    ignore_missing_pipeline: true
    tag: route_branch_name
```

Use:
- `name` via `{{ IngestPipeline "..." }}` for package-aware pipeline naming
- `if` guard to route selectively
- `ignore_missing_pipeline: true` if branch presence may vary by package version
- `tag` for failure diagnostics

### `foreach` + `pipeline` for arrays

```yaml
- foreach:
    field: ocsf.resources
    ignore_missing: true
    processor:
      pipeline:
        name: '{{ IngestPipeline "pipeline_resources_data_json" }}'
```

Use this when each item in an array needs repeated parse/normalize logic.

## Naming conventions

Recommended conventions:
- `default.yml` as orchestrator/router
- `pipeline_parser_<format>.yml` for format parsers
- `pipeline_object_<object>.yml` for object mapping
- `pipeline_category_<category>.yml` for category-level transforms
- `pipeline_enrichment_<topic>.yml` for enrichment-only branches

Naming should describe branch intent, not source implementation detail.

## Common branching topologies

### 1) Two-way format split

Use when input may be JSON or text:

```yaml
- pipeline:
    name: '{{ IngestPipeline "pipeline_parser_json" }}'
    if: ctx.event?.original != null && ctx.event.original.startsWith('{')
    ignore_missing_pipeline: true
    tag: route_parser_json
- pipeline:
    name: '{{ IngestPipeline "pipeline_parser_text" }}'
    if: ctx.event?.original != null && !ctx.event.original.startsWith('{')
    ignore_missing_pipeline: true
    tag: route_parser_text
```

### 2) Category fan-out

Use when event category determines transform behavior:

```yaml
- pipeline:
    name: '{{ IngestPipeline "pipeline_category_system_activity" }}'
    if: ctx.ocsf?.category_uid == '1'
    ignore_missing_pipeline: true
    tag: route_category_system_activity
- pipeline:
    name: '{{ IngestPipeline "pipeline_category_network_activity" }}'
    if: ctx.ocsf?.category_uid == '4'
    ignore_missing_pipeline: true
    tag: route_category_network_activity
```

### 3) Object-based branch with class guard

Use when only some classes contain a specific object:

```yaml
- pipeline:
    name: '{{ IngestPipeline "pipeline_object_user" }}'
    if: ctx.ocsf?.class_uid != null && ['2005','3001','3002','3003'].contains(ctx.ocsf.class_uid) && ctx.ocsf.user != null
    ignore_missing_pipeline: true
    tag: route_object_user
```

### 4) Multi-branch graph (large integration pattern)

This is the pattern used by `amazon_security_lake`:
- `default.yml` does common parse/normalization
- object pipelines run conditionally by `class_uid` + object presence
- category pipelines run by `category_uid`
- some branches apply nested `foreach` processing

This yields maintainable sub-pipelines instead of one very large file.

## Design rules

- Keep `default.yml` focused on shared setup and routing.
- Ensure each sub-pipeline is safe to run independently (with guards).
- Prefer mutually intelligible branch conditions over deeply nested script logic.
- If multiple branches can run on one event, make processor side effects explicit.
- Add `description` in every pipeline file so intent is obvious in reviews.

## Validation checklist

- All routed sub-pipeline names resolve correctly through `IngestPipeline`.
- Branch conditions are null-safe (`ctx.a?.b != null` style).
- Branches do not overwrite each other unexpectedly.
- Pipeline tests include one fixture per route and one route-miss fixture.
