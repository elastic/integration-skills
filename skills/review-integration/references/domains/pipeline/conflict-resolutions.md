# Conflict resolutions — pipeline

Canonical review exceptions for standalone and hosted reviewers. Read the
[shared conflict resolutions](../conflicts-core.md) first.

## geoip/user_agent if-guards vs ignore_missing

**Conflict**: The pipeline review checklist historically demanded an `if` existence guard on geoip and user_agent processors, while the `ingest-pipelines` canonical examples historically showed bare `ignore_missing: true` (the geoip examples now carry the guard). Many shipped integrations follow the older unguarded pattern.

**Resolution**: The guard is a performance improvement, not a correctness rule. New pipelines should guard geoip (the expensive database-lookup case) — flag MEDIUM. Missing guards on geoip in existing pipelines are not findings. user_agent never requires the guard; bare `ignore_missing: true` is always acceptable there.

## preserve_duplicate_custom_fields on a new stream that reroutes into legacy streams

**Conflict**: `ingest-pipelines/SKILL.md` prohibits adding a `preserve_duplicate_custom_fields` manifest variable, tag, or conditional to any new or updated pipeline, and the pipeline rubric rates a new data stream that declares it HIGH. But a new data stream that only collects and then `reroute`s into existing data streams whose pipelines still gate field removal on the tag needs some way to pass the user's choice through, otherwise rerouted events always lose the duplicate fields and behave differently from the same events collected by the legacy input.

**Resolution**: On a new rerouting stream, the manifest variable and the stream-template `tags` entry are acceptable **only if** every reroute target pipeline in the package honours the tag and the new stream's own pipeline adds no `preserve_duplicate_custom_fields` conditional. Report it as LOW with the reason (pass-through for reroute targets) so the debt stays visible; do not report HIGH. If the new stream's own pipeline contains the `remove ... if !ctx.tags.contains('preserve_duplicate_custom_fields')` conditional, or the stream does not reroute, the exception does not apply and the rubric's HIGH stands.
