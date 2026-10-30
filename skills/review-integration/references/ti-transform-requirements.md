# Threat intelligence transform requirements

Threat intelligence (TI) integrations must keep a current, unexpired view of indicators of compromise (IOCs) in latest transforms. The transforms expire indicators, and Elastic Security's built-in indicator match rules depend on the transform labels to match only the transforms' destination indices, so TI transforms have requirements beyond the general [transform guide](transform-guide.md).

**Verified as of: 2026-10-26** (elastic/integrations main, all `ti_*` packages surveyed: 63 IOC latest transforms). These are repo conventions and change over time. When this date is stale, re-check against the cited PRs and current `ti_*` packages before flagging.

## When these requirements apply

**Indicator data stream:** a data stream in a package whose name starts with `ti_` that produces indicator documents: its pipeline sets `event.kind: enrichment` and populates `threat.indicator.*`. Elastic's built-in rules select indicator indices by `logs-ti_*` and `event.module: ti_*`, so packages outside the `ti_` prefix (even with the `threat_intel` category) are not read by them. Data streams in a `ti_*` package that carry alerts or vulnerabilities (for example `ti_rapid7_threat_command` `alert` / `vulnerability`) are not indicator data streams.

**IOC transform:** a `latest` transform in a `ti_*` package whose `source.index` reads one or more indicator data streams. Transforms that read `.alerts-security.alerts-*` (alert-copying transforms in `ti_google_threat_intelligence` and `ti_greynoise`) are not IOC transforms.

Decide whether a data stream is an indicator data stream by reading its pipeline. If it is ambiguous (for example `event.kind` is set in a script or copied from the source document), say so in the finding instead of guessing.

The [latest transform requirement](#a-latest-transform-is-required) applies to every indicator data stream. The rest of this file applies to IOC transforms and their source data streams.

## Package and index naming: why `ti_` matters

Name threat intelligence packages `ti_<vendor>`, and name IOC transform destinations `logs-<package>_latest.<name>-<version>` (with alias `logs-<package>_latest.<name>`). Every IOC transform on main follows this.

Elasticsearch grants the `kibana_system` role privileges on these index names in [`KibanaOwnedReservedRoleDescriptors.java`](https://github.com/elastic/elasticsearch/blob/main/x-pack/plugin/core/src/main/java/org/elasticsearch/xpack/core/security/authz/store/KibanaOwnedReservedRoleDescriptors.java):

- `logs-ti_*.*-*` (source data streams): `delete_index`, so the package's ILM policy can run its delete phase, plus `read` and `view_index_metadata` for transforms.
- `logs-ti_*_latest.*` (destinations): create, write, delete and manage privileges for transforms.

Both are needed because Fleet installs ILM policies and, by default, runs transforms as `kibana_system`. ILM runs each policy's actions with the stored credentials of the user who last created or updated it, so a package's delete phase runs as `kibana_system` and fails without `delete_index` on the source indices.

A package outside these names gets none of this. Fixing it needs an Elasticsearch role change, as in [elastic/elasticsearch#160185](https://github.com/elastic/elasticsearch/pull/160185) for `xm_cyber`, then backports to every supported branch, then raising the package's Kibana version floor to the releases that contain them. That is significant friction, especially for vendor and external contributions. Following the `ti_` naming avoids it.

The transform's `_meta.managed` flag does not affect any of this; the privileges are matched by index name. `managed: true` is the repo norm for TI transforms (50 of 63).

## A latest transform is required

Every indicator data stream must be read by an IOC latest transform. External contributions sometimes add a new `ti_*` package or indicator data stream with no transform at all; flag this.

A transform is required for two reasons:

1. **Indicator expiration.** Threat intelligence indicators expire: feeds mark them as expired, revoked or decayed, and packages compute an expiry from `ioc_expiration_duration`. A raw data stream cannot drop an expired indicator; it keeps every ingested copy until index lifecycle deletes the backing index, and indicator match rules keep matching it until then. Only the latest transform's `retention_policy` removes indicators when they expire (see [Destination retention: IOC expiration](#destination-retention-ioc-expiration)).
2. **Built-in detection rules depend on it.** Elastic's built-in Threat Intel Indicator Match rules read `logs-ti_*` and rely on the transform split: raw sources labelled `labels.is_ioc_transform_source: "true"` are excluded, and the latest destination is what they match against (see [Transform source label](#transform-source-label)). An indicator data stream without a transform has no label and no destination, so the rules match the raw data stream directly, including every expired and superseded copy of each indicator.

The transform also deduplicates: each poll ingests the same indicators again, and the destination keeps one current entry per indicator for queries, dashboards and rules.

The transform needs:

- an `elasticsearch/transform/<name>/` directory with `transform.yml`, `fields/` (including the labels and fields below) and `manifest.yml` with `start: true` and a `destination_index_template` (all `ti_*` transforms ship one)
- the source labels and destination fields in this file
- a README section explaining the destination index and its alias, that indicator match rules and queries should use the alias, and how IOC expiration works. `ti_misp` and `ti_otx` are good examples.

Known gaps as of the verified date (existing issues, not regressions in an unrelated PR):

- `ti_mandiant_advantage`: the `threat_intelligence` data stream has no transform.
- `ti_misp` `threat` and `ti_otx` `threat`: legacy data streams without transforms; each package's other data stream (`threat_attributes` / `pulses_subscribed`) has one and is the recommended data stream in the README.

Known source retention gaps as of the verified date (43 of 66 IOC source data streams have all three pieces):

- No ILM policy and no `lifecycle.yml`: all 16 `ti_google_threat_intelligence` IOC sources, `ti_flashpoint` `indicator`, `ti_greynoise` `ip`.
- `lifecycle.yml` only (no ILM): `ti_opencti` `indicator`.
- ILM policy file not referenced by `ilm_policy`: `ti_eclecticiq` `threat` (also no `lifecycle.yml`), `ti_threatq` `threat`.
- No `lifecycle.yml`: `ti_abusech` `yaraify`, `ti_ticura` `indicator`.

## Source data stream retention

The raw data stream is only a staging area for the transform: it holds every ingested copy of every indicator, while the destination holds the current one. Keeping raw copies for long only duplicates storage, so every IOC source data stream must bound its retention, with short values. The source only needs to keep data until the transform has processed it (the transform runs every 30s).

Retention has to be defined twice, because each deployment type uses a different mechanism ([#21858](https://github.com/elastic/integrations/pull/21858) documents this for `ti_abusech` and `ti_misp`):

| Deployment | Mechanism | Package file |
|---|---|---|
| Self-managed and Elastic Cloud Hosted | ILM policy | `data_stream/<name>/elasticsearch/ilm/default_policy.json`, referenced from the data stream `manifest.yml` |
| Serverless | Data stream lifecycle (DLM); ILM is not available | `data_stream/<name>/lifecycle.yml` |

Where both are shipped, the ILM policy applies on stateful deployments and `lifecycle.yml` is not used there.

ILM policy (`ti_abusech` `sslblacklist`):

```json
{
    "policy": {
        "phases": {
            "hot": {
                "actions": {
                    "rollover": {
                        "max_age": "1d",
                        "max_size": "50gb"
                    },
                    "set_priority": {
                        "priority": 100
                    }
                }
            },
            "delete": {
                "min_age": "2d",
                "actions": {
                    "delete": {}
                }
            }
        }
    }
}
```

Data stream `manifest.yml`, referencing the policy by its installed name `<type>-<package>.<data_stream>-<file name>`:

```yaml
type: logs
title: SSL Blacklisted Certificates
ilm_policy: logs-ti_abusech.sslblacklist-default_policy
```

`lifecycle.yml`:

```yaml
data_retention: "5d"
```

Notes:

- **Both are required.** ILM alone leaves Serverless with unbounded retention; `lifecycle.yml` alone leaves stateful deployments on the stack's default `logs` ILM policy, which does not delete data.
- **The ILM policy must be referenced.** A policy file under `elasticsearch/ilm/` without `ilm_policy` in the data stream manifest is installed but not applied to the data stream.
- **Typical values** across `ti_*` IOC sources: ILM rollover after `1d`–`2d` and delete after `2d`–`7d`; `data_retention` of `5d` or `7d`. Longer retention needs a reason (for example a feed that is only fetched weekly).
- **Document it.** Follow the "Data retention" README section introduced by [#21858](https://github.com/elastic/integrations/pull/21858) (`ti_abusech`, `ti_misp`): a per-data-stream table with the ILM policy name, its rollover and delete ages, and the Serverless `data_retention`; a paragraph explaining that ILM applies on self-managed and Elastic Cloud Hosted while Serverless uses the [data stream lifecycle](https://www.elastic.co/docs/manage-data/lifecycle/data-stream#data-streams-lifecycle-how-it-works), both counted per backing index from rollover (so a document stays for the retention plus up to one rollover interval); and override steps for both:
  - Stateful: edit the package policy (`PUT _ilm/policy/<name>`), noting that a package upgrade reinstalls it, or set `index.lifecycle.name` in the data stream's `logs-<package>.<data_stream>@custom` [component template](https://www.elastic.co/docs/reference/fleet/data-streams), which Fleet keeps across upgrades; either applies from the next rollover.
  - Serverless: `PUT _data_stream/<name>/_lifecycle` with `{"data_retention": "..."}`.

## Transform source label

Elastic's built-in Threat Intel Indicator Match rules ([elastic/detection-rules `rules/threat_intel/`](https://github.com/elastic/detection-rules/tree/main/rules/threat_intel)) read `logs-ti_*`, which matches both the raw source data streams and the latest destination indices. They skip raw documents only through this clause in their threat query:

```
not labels.is_ioc_transform_source:"true"
```

Every source data stream that feeds an IOC latest transform must therefore define:

```yaml
# data_stream/<name>/fields/is-ioc-transform-source-true.yml
- name: labels.is_ioc_transform_source
  type: constant_keyword
  value: "true"
  description: Indicates whether an IOC is in the raw source data stream, or the in latest destination index.
```

And each transform destination must define:

```yaml
# elasticsearch/transform/<name>/fields/is-ioc-transform-source-false.yml
- name: labels.is_ioc_transform_source
  type: constant_keyword
  value: "false"
  description: Indicates whether an IOC is in the raw source data stream, or the in latest destination index.
```

Without the source label, the built-in rules match every ingested version of every indicator in the raw data stream (up to their 30-day window), not just the latest state. Indicators that the transform has updated, deduplicated or expired keep matching, and alerts get duplicate enrichments.

`labels.is_transform_source` (the generic label some non-TI packages use) is **not** a substitute: the built-in rules do not check it. A package that only sets `labels.is_transform_source` has this problem.

The destination label is not needed for the rules to work (documents without the field pass the `not ... : "true"` clause). It keeps destinations consistent with other TI packages and gives dashboards and saved searches a filter to tell latest data from raw data.

## Unique key

```yaml
latest:
  unique_key:
    # Namespace is deliberately excluded: threat indicators are global, so the
    # same indicator from different namespaces should deduplicate to one entry.
    - event.dataset
    - threat.indicator.file.hash.md5
    - threat.indicator.file.hash.sha256
  sort: "@timestamp"
```

- Never include `data_stream.namespace`. Indicators are global; the same indicator ingested in two namespaces should deduplicate to one entry ([#20002](https://github.com/elastic/integrations/pull/20002)). No `ti_*` transform includes it.
- Include `event.dataset` when the transform reads more than one data stream, so the same indicator from different feeds stays separate (53 of 63 transforms do this). Single-source transforms may key on a vendor ID instead (for example `ti_opencti` `event.id`, `ti_threatq` `threatq.id`, `ti_domaintools` `domaintools.domain`).
- The rest of the key is the indicator's natural identity: a vendor indicator ID, or the indicator value fields.

## Destination field definitions

- **`data_stream.namespace` as `keyword`, not `constant_keyword`.** A `constant_keyword` without a value is locked by the first document, and documents from any other namespace are rejected, which stops the transform ([#20002](https://github.com/elastic/integrations/pull/20002)).
- **`event.ingested` mapped statically** (`external: ecs`). `ecs@mappings` only maps fields dynamically when a document is indexed. A destination whose source data stream is empty (for example a disabled data stream) then has no `event.ingested` mapping, and detection rules that use `event.ingested` as their timestamp override report the index as missing the field. [#14082](https://github.com/elastic/integrations/pull/14082) added the missing definition to `ti_anomali`; [#22123](https://github.com/elastic/integrations/pull/22123) proposes it for all `ti_*` transforms (open as of the verified date). Add a comment saying why, so later cleanups do not remove it:

  ```yaml
  # elasticsearch/transform/<name>/fields/ecs.yml
  # Mapped statically so empty destination indices still expose the field to
  # detection rules that use it as the timestamp override.
  - name: event.ingested
    external: ecs
  ```

## Destination retention: IOC expiration

TI destinations expire indicators instead of keeping them for a fixed period:

- **Computed expiry (most packages).** Packages with an `ioc_expiration_duration` data stream variable (16 packages, default `90d`) compute an expiry timestamp in the pipeline, typically `last_seen` (or `first_seen`) plus the duration, into a vendor field such as `<vendor>.<stream>.deleted_at`. The transform then retains on that field with a short `max_age`:

  ```yaml
  retention_policy:
    time:
      field: abusech.malware.deleted_at
      max_age: 1m
  ```

- **Vendor expiry.** When the feed provides an expiry or validity date, retain on it the same way (for example `ti_eset` `eset.valid_until`, `max_age: 1m`).
- **Time-based fallback.** Feeds without any expiry signal retain on `@timestamp` or `event.ingested` with a fixed `max_age` (for example `30d` or `7d`).

A destination with no `retention_policy` keeps expired indicators matchable forever.

## Sync, frequency and alias

- `sync.time.field: event.ingested` with `delay: 120s`. All 63 transforms use `delay: 120s`; 60 sync on `event.ingested`. The longer delay accounts for refresh lag on Serverless.
- `frequency: 30s` (57 of 63). Indicators should reach the destination quickly; the built-in rules run hourly with a 5-minute lookback.
- `dest.aliases` with `move_on_creation: true` (61 of 63), so consumers keep reading the current destination after an upgrade recreates it.

## Known non-compliant packages

As of the verified date, these packages label their IOC sources and destinations with `labels.is_transform_source` instead of `labels.is_ioc_transform_source`:

- `ti_google_threat_intelligence`
- `ti_cyware_intel_exchange`
- `ti_flashpoint`
- `ti_greynoise`

This list is a point-in-time snapshot. Verify against the package's `fields/` files. In a review of one of these packages, report the missing label as an existing issue unless the PR touches the transforms or their source data streams, in which case report it as a finding.

## TI transform review checklist

- [ ] Package is named `ti_<vendor>` and IOC destinations are `logs-<package>_latest.*`, so `kibana_system` has the privileges ILM and transforms need -- **HIGH** if not, for a new TI package with transforms or ILM
- [ ] Every indicator data stream is read by an IOC latest transform -- **HIGH** for a new package or new indicator data stream; report known gaps in existing packages as existing issues
- [ ] README documents the destination alias, that rules and queries should use it, and IOC expiration -- **MEDIUM** if missing
- [ ] Every IOC source data stream ships an ILM policy in `elasticsearch/ilm/`, references it with `ilm_policy` in its manifest, and ships `lifecycle.yml` -- **HIGH** if a new source data stream has neither; **MEDIUM** if one of the three is missing
- [ ] Source retention is short (days, not months) -- **MEDIUM** if long without a stated reason
- [ ] README documents source retention per deployment type and how to change it -- **LOW** if missing
- [ ] Every IOC source data stream defines `labels.is_ioc_transform_source` as `constant_keyword` `"true"` -- **HIGH** if missing or set only as `labels.is_transform_source`
- [ ] Each IOC transform destination defines `labels.is_ioc_transform_source` as `constant_keyword` `"false"` -- **MEDIUM** if missing
- [ ] `unique_key` does not include `data_stream.namespace` -- **HIGH** if it does
- [ ] `unique_key` includes `event.dataset` when the transform reads more than one data stream -- **MEDIUM** if missing
- [ ] Destination maps `data_stream.namespace` as `keyword` -- **HIGH** if `constant_keyword`
- [ ] Destination maps `event.ingested` statically (`external: ecs`) -- **MEDIUM** if missing
- [ ] Destination `retention_policy` present, on an expiry field when the source provides or computes one -- **HIGH** if missing
- [ ] Sync on `event.ingested` with `delay: 120s` -- **MEDIUM** if wrong field, **LOW** if delay differs
- [ ] `frequency: 30s` -- **LOW**
- [ ] `dest.aliases` with `move_on_creation: true` -- **MEDIUM** if missing
- [ ] Destination index suffix and `fleet_transform_version` bumped when destination field definitions change, so existing installs get the new mapping (repo practice, as in #20002 and #22123) -- **HIGH** if not bumped
