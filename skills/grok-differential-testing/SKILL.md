---
name: grok-differential-testing
description: "Use when reviewing or refactoring grok patterns in ingest pipelines — model the old and new patterns as regexes and diff their accept/reject behaviour across a message-shape matrix to catch silent parsing regressions, untested alternation branches, and catastrophic backtracking. Trigger phrases: 'did this grok change break anything', 'review this grok refactor', 'check the pattern change', 'grok regression'."
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# grok-differential-testing

Verify a change to grok patterns by diffing the behaviour of the **old** and **new** patterns
across a matrix of message shapes, instead of trusting the fixtures that happen to exist.

## When to use

Load this skill whenever tasks include:

- reviewing a PR that edits `patterns:` or `pattern_definitions:` in an ingest pipeline
- refactoring several near-duplicate grok patterns into one parameterized pattern
- making a previously required token optional (or vice versa)
- assessing a claim that a pattern change is backwards compatible or backtracking-safe

## When not to use

Do not use this skill as the primary guide for:

- designing new pipelines or choosing processors (`ingest-pipelines`)
- authoring pipeline test fixtures and expected outputs (`integration-testing` → `references/pipeline-testing.md`)
- dissect, kv, or other non-grok parser changes (the differential idea transfers, the harness does not)

## Why differential

A grok edit has a free oracle: **the previous pattern is the spec, minus the intended changes.**
Fixture tests only pin the shapes someone already thought of. The dangerous failure mode of a
grok refactor is the message shape nobody wrote a fixture for — a form the old pattern
accepted incidentally (a `%{DATA}` catch-all, a permissive separator) that the new, tidier
pattern silently rejects. Diffing old-vs-new over a generated shape matrix finds exactly the
cases where behaviour changed, and every disagreement is either an intended improvement
(which needs a fixture) or a regression (which needs a fix).

Grok non-matches are rarely silent: most integration pipelines route processor failures
through a top-level `on_failure` that sets `event.kind: pipeline_error`, so a lost shape
means dropped fields **and** an error-classified event. Check the pipeline's failure handling
and state the blast radius precisely in your report.

## Workflow

1. **Extract both pattern sets.** Get the old patterns from the git base
   (`git show <base>:<pipeline>.yml`) and the new ones from the working tree — including
   `pattern_definitions`, which is where refactors hide behaviour. Note the processor's
   `if:` condition so you test the right event type.

2. **Copy the harness.** Copy `references/grok_diff.py` into a scratch directory. It expands
   grok syntax (`%{NAME}`, `%{NAME:field}`, custom definitions) into plain Python regexes.
   Add any grok primitives the patterns use that the built-in table lacks — take their
   definitions from [elastic/go-grok](https://github.com/elastic/go-grok/tree/main/patterns)
   or the legacy [logstash pattern bank](https://github.com/logstash-plugins/logstash-patterns-core/tree/main/patterns).

3. **Build the shape matrix.** Combine, as concrete message strings:
   - every existing fixture message for the affected event types
     (`grep` the package's `_dev/test/pipeline/` inputs);
   - vendor-documented forms (link the doc in the case name);
   - **combinatorial toggles of every optional segment** — each one alone, all present,
     all absent. Three optional segments means at least 4–5 cases beyond the bundled-together one;
   - hostile variants: doubled/missing spaces, trailing `\r`, empty capture values
     (`[KEY=]`, `customername ` with nothing after), prefixes of the *wrong* shape
     (whatever a removed `%{DATA}` catch-all used to absorb — other event-type prefixes
     seen in the same pipeline are good candidates);
   - one long adversarial non-matching input for the timing check.

   Name each case and mark which are covered by repo fixtures — the uncovered ones become
   your fixture recommendations.

4. **Run the differential** (`diff()` in the harness) and classify each disagreement:

   | old | new | Meaning | Action |
   |-----|-----|---------|--------|
   | ✔ | ✘ | **Regression.** | Blocker unless explicitly intended and called out in the changelog. |
   | ✘ | ✔ | Newly enabled form. | Fine — but each one must gain a fixture, or it will rot. |
   | ✘ | ✘ | Pre-existing gap on a plausible form. | Note it; out of scope unless cheap. |
   | ✔ | ✔ | Compare **captures**, not just accept/reject. | A field that moved or emptied is also a regression. |

5. **Check alternation-branch coverage.** For every alternation in the new
   `pattern_definitions`, confirm at least one repo fixture exercises **each branch**.
   A branch that only the harness has ever matched will be broken silently by the next edit.
   Also probe empty-capture edges: does `[KEY=]` produce an empty-string keyword, and is
   that wanted, or should the class be `+` instead of `*`?

6. **Time the adversarial input** (`time_growth()` in the harness) at increasing sizes.
   Linear growth: fine. Superlinear: restructure the pattern — the standard fix is a
   negated character class (`[^\]]*`) instead of `.*?`/`%{DATA}` inside a repeated group.
   Elasticsearch's grok watchdog will interrupt runaway matches at runtime, but that is a
   mitigation, not a license: interrupted matches on a hot log path are a CPU tax and
   turn into per-event failures.

7. **Report.** Present the old/new verdict table, the branch-coverage findings, the timing
   result, and a concrete fixture list (message string + which gap it closes). If reviewing
   a PR, anchor findings to the pattern lines. Finish by running the real thing:
   `elastic-package test pipeline` is the final word, not the harness.

## Engine caveats

The harness uses Python `re` to approximate the Oniguruma/joni engine Elasticsearch embeds.
This is sound for differential analysis — both engines are backtracking NFA engines and the
constructs integration patterns use (alternation, optional groups, lazy/greedy quantifiers,
character classes) behave identically. It is **not** exact engine parity:

- possessive quantifiers (`*+`) and atomic groups `(?>...)` are not supported by Python `re` —
  if a pattern uses them, verify that piece with `elastic-package test pipeline` only;
- grok type suffixes (`%{NUMBER:field:float}`) affect output typing, not matching — the
  harness ignores them;
- Oniguruma named groups may contain dots (`(?<a.b.c>...)`); the harness rewrites them to
  valid Python names and reports captures under the original field name;
- timing numbers are indicative, not absolute — use the growth *curve*, not the wall-clock.

For ReDoS depth beyond the timing check, pipe the harness's expanded regex
(`expand()` output) into [regexploit](https://github.com/doyensec/regexploit), which
statically finds ambiguous-quantifier constructs and synthesizes worst-case inputs.

## References

- `references/grok_diff.py` — the harness: grok→regex expansion, first-match-wins pattern
  sets, differential runner with capture comparison, adversarial timing. Stdlib-only;
  run it bare for a self-test demonstrating the output format.
- `references/worked-example.md` — a real review that used this method
  ([elastic/integrations#20710](https://github.com/elastic/integrations/pull/20710)):
  a two-pattern-to-one grok refactor where the shape matrix surfaced an untested
  regression on a deliberately permissive catch-all, plus three fixture gaps.
