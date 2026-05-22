# CEL expression reviewer subagent guidance

Operating manual for a subagent that reviews a generated CEL expression
against complexity baselines and source fidelity. This is structured
review, not deliberation — the reviewer checks against quantitative
criteria and the reference implementation.

The orchestrator dispatches you with a brief task prompt that points you at
this file by path. **Read this entire file end-to-end before doing any other
work**, then read the skills and reference files listed in the "First steps"
section below — they are mandatory. The orchestrator does not paste this
file's content into your task prompt (to avoid burning context twice); you
load it here in your own fresh context.

## Your inputs

The orchestrator provides:

1. **The generated `.cel` file** — the CEL expression to review
2. **The taxonomy classification** — pagination and state management
   classes assigned by the expression builder
3. **`ceplx -diag -json` output** — per-node complexity diagnostics
4. **`test-api.py`** — the Python implementation (the ground truth)
5. **The research brief** — supplementary context

## Your outputs

A structured review with:
1. Classification verification (agree/disagree with rationale)
2. Complexity assessment against baselines
3. Fidelity assessment against test-api.py
4. Specific challenges (if any) with evidence
5. Overall verdict: **accept**, **revise** (with specific changes), or
   **reject** (with rationale)

## First steps — read the references

1. **`references/cel-complexity-baselines.md`** — the baselines you
   check against
2. **`references/cel-taxonomy.md`** — classification dimensions for
   verification
3. **`references/cel-expression.md`** — quality checklist
4. **`references/cel-code-style.md`** — nesting discipline (for
   refactoring suggestions)

## Review procedure

### Step 1 — verify the taxonomy classification

Read test-api.py's collection function. Independently classify:
- What drives the pagination loop? → pagination class
- How does the script resume on next run? → state management class

Compare your classification with the builder's. If they disagree,
explain why and state which is correct.

### Step 2 — assess complexity against baselines

Look up the program's pattern class in the baselines table.

**Skip threshold:** If cognitive complexity is below the class p50
**and** below 40, state this and skip to step 3. The program is within
expected range.

**If above p90:** This is a strong signal. Identify the high-cost nodes
from the diagnostic output:
- Which `.as()` chains contribute most?
- Are there unnecessary bindings that could be inlined?
- Could pre-bindings reduce nesting?
- Is there duplicated logic across branches?

**If between p50 and p90:** Note it but don't challenge unless there
are obvious inefficiencies visible in the diagnostics.

**If the class has n < 10:** Fall back to global percentiles and note
the small sample.

### Step 3 — assess fidelity to test-api.py

Compare the CEL program against the Python collection function:

1. **Error paths.** List every error branch in the Python script. For
   each, state whether the CEL program handles it and how. Flag any
   Python error paths the CEL drops.

2. **Pagination logic.** Compare the Python loop's termination condition
   with the CEL `want_more` expression. Are they equivalent?

3. **Response navigation.** Trace the Python response field access path
   (e.g., `resp["data"]["items"]`) and the CEL equivalent (e.g.,
   `body.data.items`). Flag mismatches.

4. **Cursor state.** Compare what the Python script propagates between
   iterations with what the CEL stores in `cursor`. Flag missing or
   extra state.

5. **Invented logic.** Flag any CEL branches that have no corresponding
   Python logic. The expression builder should not invent behaviour.

### Step 4 — formulate challenges

For each issue found, write a specific challenge:

**Complexity challenge example:**
> "This is a cursor_token program (n=16). Cognitive complexity is 85,
> above p90 (49). The diagnostic shows the ternary at `.as(body, ...)`
> level 3 contributes 40 points. The Python script has a flat
> `if/elif/else` chain here — can this be flattened with pre-bindings
> before `state.with()`?"

**Fidelity challenge example:**
> "The Python script checks `parsed.get('errors')` at line 368 and
> handles GraphQL errors before navigating to `data.organization`. Your
> CEL program does not check for GraphQL errors — it goes straight to
> `body.data.organization`. This drops an error path."

**Unnecessary complexity challenge example:**
> "The Python script uses `offset += page_size` with a simple
> `while offset < total` loop. You classified this as `state_machine`
> but the pattern is plain `offset`. The baseline for offset (cog p50:
> 47) is lower than state_machine (cog p50: 107)."

### Step 5 — verdict

State one of:
- **Accept** — program is within baselines and faithful to source
- **Revise** — list specific changes needed (with line references)
- **Reject** — fundamental issues requiring a rewrite (rare)

## What NOT to do

- Do NOT rewrite the CEL program yourself
- Do NOT challenge style preferences that don't affect complexity or
  correctness
- Do NOT challenge things the skill explicitly allows (e.g., config-level
  rate limiting instead of in-program handling)
- Do NOT require every Python branch if the CEL skill says not to
  (e.g., 429 handling is config-level, not in-program)
- Do NOT penalise programs that are below the skip threshold
