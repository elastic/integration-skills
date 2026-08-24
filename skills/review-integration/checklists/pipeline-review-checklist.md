# Ingest pipeline review checklist

Severity-tagged checklist. Each item: what to check, violation criteria, severity.

### Prohibited patterns (quick reject)

- [ ] Pipeline does NOT set `event.ingested` -- managed by Elasticsearch -- **HIGH**
- [ ] Pipeline does NOT use `preserve_duplicate_custom_fields` tag pattern -- **HIGH**
- [ ] Pipeline does NOT have a trailing `remove` processor deleting `event.original` based on absence of `preserve_original_event` tag -- deprecated pattern -- **HIGH**

### JSE00001 (event.original preservation)

- [ ] Rename `message` to `event.original` (if absent) with description and tag -- **HIGH** if missing
- [ ] Remove `message` when `event.original` is set, with description and tag -- **HIGH** if missing
- [ ] No additional processors modifying `event.original` after the initial rename -- **MEDIUM**

### Pipeline-level on_failure

- [ ] on_failure block present at pipeline level -- **HIGH** if missing
- [ ] First action: append full `error.message` using `_ingest.on_failure_*` template variables -- **HIGH** if wrong template
- [ ] Second: set `event.kind: pipeline_error` -- **HIGH** if missing
- [ ] Third: append `preserve_original_event` to `tags` -- **MEDIUM** if missing
- [ ] Order matters: error.message THEN event.kind THEN tags -- **MEDIUM** if wrong order

### ECS version

- [ ] Pipeline sets `ecs.version: 9.3.0` for standard streams, or `ecs.version: 9.5.0` for entity data streams (those with `event.kind: asset`) -- **HIGH** if wrong version; must match the `build.yml` ECS pin

### Processor-level checks

- [ ] Every processor has a `tag` field -- **MEDIUM** if missing
- [ ] ECS field mapping uses `rename` where possible, not `set` + `copy_from` duplication -- **MEDIUM**
- [ ] Mustache template syntax uses triple braces with single quotes: `'{{{field.name}}}'` not double braces `"{{field.name}}"` (double braces HTML-escape). Exception: `{{ IngestPipeline "..." }}` is Go template, not Mustache -- **MEDIUM**
- [ ] Grok patterns anchored with `^...$` for full-line matching -- **MEDIUM**
- [ ] `@timestamp` set from a parsed date field, not left as default ingest time -- **HIGH** if no date parsing
- [ ] Type conversions: numeric fields use `convert` processor for long/double -- **MEDIUM**

### Enrichment

- [ ] In NEW pipelines, geoip processors have an `if` condition checking field existence (e.g., `if: ctx.source?.ip != null`) in addition to `ignore_missing: true` -- the geoip database lookup is the expensive case worth guarding. Bare `ignore_missing: true` on user_agent, and on geoip in existing pipelines, is NOT a finding (see `references/conflict-resolutions.md`) -- **MEDIUM** (new pipelines, geoip only)
- [ ] When geoip is used for geolocation (e.g., `source.geo`), there must be a companion ASN lookup using `database_file: GeoLite2-ASN.mmdb` targeting `*.as`, followed by renames `*.as.asn` to `*.as.number` and `*.as.organization_name` to `*.as.organization.name` -- **HIGH** if geo enrichment present but ASN missing
- [ ] `related.ip` populated with every IP field the pipeline sets, one append per field, `allow_duplicates: false`, guarded by `if` condition -- **HIGH** if IP fields not in related.ip

### ECS categorization

- [ ] `event.kind`, `event.category`, `event.type`, `event.outcome` use only allowed ECS values -- **HIGH** if invalid values
- [ ] `event.category` and `event.type` are arrays: must use `append` processor, not `set` -- **HIGH** if using set
- [ ] Categorization values are semantically appropriate for the data (not just valid but correct) -- **MEDIUM**

### CEL-only opening processors

- [ ] CEL-opening Agentless block (`remove` processor for agentless metadata `organization`/`division`/`team` when all are strings, tagged `remove_agentless_tags`, followed by `terminate` processor on the collector-error placeholder shape): required only on NEW CEL data streams in packages whose manifest enables agentless deployment (`deployment_modes.agentless.enabled: true`), or where sibling pipelines in the same package already carry the block (consistency). On existing pre-Agentless pipelines its absence is NOT a finding (at most a LOW modernization note) -- **MEDIUM** when missing in those two cases only
- [ ] These processors must NOT be present for non-CEL streams -- **MEDIUM** if present for wrong input type

### Performance

- [ ] Cheap checks (conditionals, renames) before expensive operations (grok, geoip, user_agent) -- **LOW**
- [ ] Dissect preferred over grok when the format is fixed/delimited -- **LOW**

### Security

- [ ] No hardcoded sensitive values in processors -- **CRITICAL**
- [ ] Credential-shaped policy vars referenced by the stream (tokens, secrets, passwords, API keys) are declared with `secret: true` in the manifest -- **HIGH** if plain

### When reviewing a diff

Prioritize: the changed processors, their error handling (do they have processor-level on_failure or at least correct pipeline-level handling?), and their field declarations (are the new fields declared in fields/ files?).
