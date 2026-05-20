# CEL complexity baselines

Per-pattern-class complexity baselines from a survey of 316 CEL programs
in elastic/integrations, measured with `ceplx`. The reviewer uses these
to challenge generated programs that exceed expected complexity for their
pattern class.

**Source:** `ceplx` survey of `elastic/integrations` (May 2026), joined
with `celir` taxonomy classifications. Raw data in
`~/thinking/cel_complexity/ceplx-joined.csv`.

## How to use

1. Classify the program using `references/cel-taxonomy.md`.
2. Look up the class in the tables below.
3. If the class has n >= 10, use the class-specific baselines.
4. If n < 10, use the global percentiles as a fallback.
5. A program above p90 for its class needs justification — the API's
   requirements may warrant it, but the burden is on the generator to
   explain why.

## Skip threshold

Skip the review when **both** conditions hold:
- The program's cognitive complexity is below the class p50
- Total cognitive complexity is below 40

These programs are simple enough that review overhead is not justified.

## By pagination pattern

Only classes with n >= 10 are reliable baselines. Classes with smaller
samples are included for reference but should be used cautiously.

| Pattern | n | cyc_med | cyc_p90 | cog_med | cog_p75 | cog_p90 | cog_max |
|---------|---|---------|---------|---------|---------|---------|---------|
| `offset` | 19 | 16 | 39 | 47 | 73 | 169 | 169 |
| `cursor_token` | 16 | 11 | 15 | 27 | 42 | 49 | 54 |
| `worklist_expansion` | 15 | 26 | 49 | 88 | 172 | 307 | 391 |
| `none` | 15 | 7 | 12 | 18 | 26 | 41 | 43 |
| `multi_entity_orchestration` | 13 | 35 | 52 | 143 | 156 | 234 | 325 |
| `next_url_in_body` | 10 | 16 | 34 | 52 | 78 | 168 | 168 |
| `page_number` | 8 | 18 | 31 | 73 | 82 | 82 | 82 |
| `graphql_relay` | 6 | 9 | 35 | 31 | 51 | 64 | 64 |
| `export_blob` | 5 | 34 | 35 | 132 | 134 | 134 | 134 |
| `link_header` | 4 | 18 | 24 | 49 | 94 | 94 | 94 |
| `async_job_polling` | 4 | 40 | 58 | 131 | 252 | 252 | 252 |

Composite patterns (e.g., `offset + time_window`) have very small
samples (n <= 4) and are not listed as reliable baselines.

## By state management pattern

| Pattern | n | cyc_med | cyc_p90 | cog_med | cog_p75 | cog_p90 | cog_max |
|---------|---|---------|---------|---------|---------|---------|---------|
| `state_machine` | 21 | 35 | 51 | 107 | 212 | 234 | 268 |
| `stateless` | 18 | 7 | 13 | 18 | 29 | 43 | 47 |
| `timestamp_cursor` | 11 | 14 | 20 | 46 | 69 | 73 | 110 |
| `multi_field_cursor` | 7 | 17 | 64 | 41 | 104 | 296 | 296 |
| `time_window` | 6 | 25 | 38 | 110 | 170 | 210 | 210 |
| `job_cursor` | 5 | 40 | 58 | 114 | 131 | 252 | 252 |

## Global percentiles (fallback)

When the pattern class has n < 10, use these global baselines derived
from all 316 programs:

| Metric | p25 | p50 | p75 | p90 | max |
|--------|-----|-----|-----|-----|-----|
| Cyclomatic | 8 | 16 | 30 | 43 | 73 |
| Cognitive | 19 | 47 | 107 | 172 | 391 |

## Interpreting ceplx diagnostic output

Run `ceplx -diag -json program.cel` to get per-node complexity
contributions. The reviewer should focus on:

- **High-cost comprehensions**: `.map()` and `.filter()` inside nested
  `.as()` chains multiply cognitive cost
- **Deep ternary nesting**: each level of `? ... : ...` inside `.as()`
  adds both cyclomatic and cognitive complexity
- **Logical chains**: `&&` / `||` chains inside conditions add
  cyclomatic complexity
- **`.as()` depth**: each level amplifies the cognitive cost of
  everything inside it

The diagnostic output identifies which nodes contribute most, guiding
specific refactoring suggestions (extract pre-bindings, inline
single-use bindings, split branches into separate evaluations).

## Reviewer challenge examples

Given a `cursor_token` program with cognitive complexity 85:

> "This is a cursor_token program. The p90 for cursor_token is 49
> (n=16). Your program's cognitive complexity is 85, which is well
> above the baseline. The diagnostic shows 40 points from the nested
> ternary at line 25 inside a 3-level `.as()` chain. Can this be
> flattened with pre-bindings?"

Given a `graphql_relay` program with cognitive complexity 35:

> "This is a graphql_relay program. The p50 is 31, p90 is 64 (n=6,
> treat as approximate). Your program is within expected range. No
> complexity challenge."
