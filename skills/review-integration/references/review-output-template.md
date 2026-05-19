# Review output template

Use this format when writing `tmp/integration-review.md`.

## Template

```markdown
# Integration Review: {package_name}

## Automated Validation

- format: PASS/FAIL
- lint: PASS/FAIL (list errors)
- check: PASS/FAIL (list errors)
- test pipeline: PASS/FAIL/SKIPPED (N passed, M failed)
- test system: PASS/FAIL/SKIPPED

---

## Package Root

Covers root `manifest.yml`, `changelog.yml`, `_dev/build/build.yml`, and
package-level structure. Only include if root-level files are in scope.

### Manifest

[If no actionable issues: "✅ *Reviewed — No actionable issues found.*"]

[Otherwise:]

**Issue 1: {title}**
**Severity:** {severity_emoji} {severity}
**Location:** `{file_path}` line {line_number}

**Problem:** {description}
**Recommendation:**
```yaml
{corrected code}
```

### Changelog

[Same per-issue format. Only include if changelog.yml is in scope.]

### Build Configuration

[Same per-issue format. Only include if _dev/build/build.yml is in scope.]

---

## Data Stream: `{data_stream_name}`

Repeat this section for each data stream in scope. Each data stream may have
findings in multiple sub-domains.

### Manifest

[Data stream manifest.yml issues. Same per-issue format.]

### Input

[Agent stream template issues -- covers CEL, HTTPJSON, AWS S3, TCP/UDP, and
all other input types under agent/stream/*.yml.hbs. Same per-issue format.]

### Pipeline

[Ingest pipeline issues under elasticsearch/ingest_pipeline/. Same per-issue
format.]

### Field Mapping

[Field files under fields/. Same per-issue format.]

### Tests

[Pipeline and system test issues under _dev/test/. Same per-issue format.]

**Suggestions**
1. {non-critical suggestion}
2. ...

---

[Repeat the "Data Stream" section above for each data stream in scope.]

---

## Dashboards

Covers kibana/ assets at the package root. Only include if kibana/**/*.json
files are in scope.

[Same per-issue format.]

---

## Transforms

Covers elasticsearch/transform/ at the package root. Only include if
transform files are in scope.

[Same per-issue format.]

---

## Documentation

Covers _dev/build/docs/README.md and other doc files. Only include if
documentation files are in scope.

[Same per-issue format.]

---

## Data Anonymization

Cross-cutting: covers real data found in any committed file (test fixtures,
mock responses, sample events, default manifest values). Only include if
anonymization issues were found.

[Same per-issue format.]

---

## Cross-Domain Consistency

Issues spanning multiple files or domains (pipeline fields not declared in
ecs.yml, build.yml ECS pin mismatch, unused manifest variables, etc.). Only
include if cross-domain issues were found.

[Same per-issue format.]

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | {count} |
| 🟠 High | {count} |
| 🟡 Medium | {count} |
| 🔵 Low | {count} |

**Total Actionable Items:** {total}

**Verdict:** {APPROVED / APPROVED_WITH_SUGGESTIONS / NEEDS_CHANGES}
```

## Per-issue format

Every issue must follow this structure:

```markdown
**Issue N: {title}**
**Severity:** {severity_emoji} {severity}
**Location:** `{file_path}` line {line_number}

**Problem:** {clear description of what is wrong and why it matters}
**Recommendation:**
```{language}
{corrected code showing the full processor/block/section -- must be copy-pasteable}
```
```

## Rendering rules

1. **FILTER OUT** positive comments. Never include "no issues found", "compliant", "done well", "excellent", "correct" as findings.
2. **KEEP ONLY** actionable items: issues, warnings, errors, suggestions, recommendations.
3. **CONSOLIDATE** duplicates: merge the same issue found in multiple files into one finding.
4. **PRESERVE** code snippets: keep all YAML/CEL/JSON examples in recommendations. Show the full processor, field definition, or config block -- not just the changed line.
5. **NUMBER** issues sequentially within each section: "Issue 1:", "Issue 2:".
6. **GROUP** findings by location in the package hierarchy: package root sections first, then per-data-stream, then dashboards/transforms/docs/anonymization/cross-domain.
7. **OMIT** sections not in scope entirely. Do not create empty sections for domains not reviewed.
8. **REQUIRE** `**Location:**` for every issue with exact file path and line number. If line number is unknown, use line 1.
9. **EVERY** recommendation must include a code block showing the corrected code.
10. If a section was reviewed and has no issues, write one line: "✅ *Reviewed — No actionable issues found.*"
11. **OMIT** confidence scores, uncertainty areas, and internal review metadata from the output.

## Severity values

- 🔴 Critical
- 🟠 High
- 🟡 Medium
- 🔵 Low

## Verdict rules

- Any critical or high finding -> NEEDS_CHANGES
- Only medium/low findings -> APPROVED_WITH_SUGGESTIONS
- No findings -> APPROVED
