# Worked example: elastic/integrations#20710 (citrix_adc)

A real review that used this method end-to-end:
[the review](https://github.com/elastic/integrations/pull/20710#pullrequestreview-4960138153)
on [elastic/integrations#20710](https://github.com/elastic/integrations/pull/20710).

## The change under review

The `citrix_adc` SSLVPN pipeline parsed `ICASTART` events with two near-duplicate grok
patterns that had a coverage gap (bracket prefix **and** `SSLRelayAddress` together matched
neither). The PR collapsed them into one pattern built from three optional
`pattern_definitions` segments, and swapped a `%{DATA} ?` catch-all prefix in the sibling
`ICAEND_CONNSTAT` patterns for the same bracket-only `ICA_PREFIX` definition:

```
ICA_PREFIX:    (?:(?:\[[^\]]*\]%{SPACE})*?\[ICAUUID=(?<...ica_uuid>[^\]]*)\]%{SPACE}|(?:\[[^\]]*\]%{SPACE})+)?
CLIENT_IP_OPT: (?:Client_ip %{IP:...client_ip}%{SEP})?
SSL_RELAY_OPT: (?:SSLRelayAddress %{IP:...}:%{INT:...}%{SEP})?
```

The PR's own fixtures covered 4 shapes; all passed. Everything looked green.

## What the differential found

Both old and new pattern sets were modelled as regexes and diffed over 17 message shapes
(repo fixtures + vendor-documented forms + combinatorial toggles + hostile variants):

| Finding | Method step that caught it |
|---|---|
| `%{DATA} ?` → `ICA_PREFIX` narrowing: `Client_ip …` and `Context …@… - SessionId: …` prefixes parsed in the old version, fail in the new one — all ~18 ICAEND fields dropped and `event.kind: pipeline_error` set | Hostile variants: feed the removed catch-all prefixes of the *wrong* shape, seen elsewhere in the same pipeline |
| The UUID-less branch of the `ICA_PREFIX` alternation — the branch the changelog names — was exercised by **zero** repo fixtures | Alternation-branch coverage check |
| The changelog claimed `client.geo`/`client.as` enrichment, but the only fixture used `Client_ip 0.0.0.0`, which no geo/ASN database resolves — the claim was never asserted | Capture comparison + reading the expected output, not just the verdict |
| `Client_ip` alone (no prefix, no relay) — the form the change exists for — had no fixture | Combinatorial toggles of optional segments |
| `[ICAUUID=]` captures an empty-string keyword because the class is `[^\]]*` not `[^\]]+` | Empty-capture edge probe |
| The backtracking-safety comment was **verified true**: 80 bracket blocks (1801 chars) on a non-matching line, <0.01 ms, linear growth | Adversarial timing |

The headline regression was invisible to the PR's test suite precisely because the old
pattern's permissiveness was undocumented — no fixture had ever pinned it. The differential
made the old behaviour the spec and surfaced the narrowing in minutes.

## Takeaways

- The `%{DATA}` you delete is load-bearing until proven otherwise. Find what it absorbed
  by feeding prefixes from *other* event types in the same pipeline.
- "All tests pass" measures the fixtures, not the change. Diff against the old pattern.
- Verify performance claims in comments; do not just read them. This one was true —
  saying so with numbers is as valuable as finding it false.
- Every alternation branch needs a fixture, or the next refactor breaks it silently.
