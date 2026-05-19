---
name: create-integration
description: "Use when creating a new Elastic integration package, scaffolding data streams, answering package layout or structure questions, or running the end-to-end integration build workflow. Covers package topology, scaffold commands, post-scaffold edits, and full orchestration of CEL/pipeline/test subagents."
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# create-integration

## When to use

Use this skill when tasks include:
- creating a new integration package from scratch
- scaffolding data streams and applying post-scaffold edits
- understanding package topology, file placement, and manifest patterns
- running the end-to-end build workflow (scaffold → data collection setup → pipeline → system tests → review)
- questions about package structure, layout, or `manifest.yml` shape

## IMPORTANT: Loading references

This skill has four reference files. Load the appropriate one(s) based on your task:

**When creating a full integration (end-to-end):**
→ **MUST read `references/create-workflow.md` fully before starting.** This contains the complete orchestration workflow, all phases, subagent delegation instructions, and guardrails.

**When adding data streams to an existing package:**
→ **MUST read `references/add-datastream-workflow.md` fully before starting.** This covers verifying the package, scaffolding streams, and the CEL → pipeline → system-test sequence.

**When scaffolding a package or data stream, or applying post-scaffold edits:**
→ Read `references/scaffold-commands.md` for the scaffold commands, post-scaffold checklist, and common pitfalls.

**When reviewing or understanding package topology and file layout:**
→ Read `references/package-layout.md` for canonical trees, manifest patterns, and review checklists for both integration and input packages.

## What to provide when creating an integration

Include any combination of the following:

| Input | How to provide | Examples |
|-------|----------------|----------|
| Package name | free text | `my_vendor` |
| Product / vendor | free text | "Acme Firewall appliance" |
| Data delivery method | free text | "REST API with pagination", "syslog over TCP/UDP", "S3 bucket" |
| API / log documentation | paste URLs | `https://docs.acme.com/api/v2` |
| Sample data | `@`-mention files | `@samples/acme_event.json` |
| Research brief | `@`-mention file | `@notes/acme-research-brief.md` |
| Constraints | free text | "CEL input only", "single data stream" |

### Example invocations

```
Create a new "acme_firewall" integration for Acme Firewall appliance.
  API docs: https://docs.acme.com/api/v2/events
  Auth: Bearer token header. Pagination: offset-based with total_count.
  @samples/acme_events.json. Single data stream "event" using cel input.
```

```
New syslog integration "my_appliance" with tcp,udp inputs.
  @notes/research-brief.md. Two streams: "log" (syslog) and "traffic" (syslog).
```

## What to provide when adding data streams to an existing package

Use `@`-mentions for files/folders and paste links inline.

| Input | How to provide | Examples |
|-------|----------------|----------|
| Target package | free text or `@`-mention | `acme_firewall`, `@packages/acme_firewall` |
| Stream name | free text | `audit`, `traffic`, `alert` |
| Stream type | free text | `logs` (default) or `metrics` |
| Input type(s) | free text | `cel`, `tcp,udp`, `filestream`, `http_endpoint`, `aws-s3` |
| API / log docs | paste URLs | `https://docs.acme.com/api/audit` |
| Sample data | `@`-mention files | `@samples/audit_event.json`, `@samples/traffic.log` |
| Research brief | `@`-mention file | `@notes/acme-audit-brief.md` |
| Constraints | free text | "reuse package-level auth vars", "separate pipeline per event type" |
| Acceptance criteria | free text | "parse all syslog fields, map to ECS" |

### Example invocations

```
Add "audit" stream to @packages/acme_firewall using cel input.
  API endpoint: /api/v2/audit_logs
  Pagination: timestamp cursor.
  @samples/acme_audit.json
```

```
Add "traffic" and "threat" streams to acme_firewall.
  Both use tcp,udp inputs (syslog).
  @samples/traffic.log @samples/threat.log
```

## Subagents overview

Do **not** load CEL, pipeline, ECS, or field-mapping skills yourself. Delegate to subagents that load their own domain skills.

All specialised work is delegated to the platform's **generic / general-purpose subagent** (Cursor: `generalPurpose` Task agent; Claude Code: `general-purpose` Task agent; or the equivalent on other platforms). Each task prompt must embed the relevant `*-subagent-guidance.md` file verbatim at the top — that file is the subagent's operating manual (skill-load sequence, workflow, scope, reporting contract); the subagent will not load its skill automatically. Full dispatch rules and per-step detail live in `references/create-workflow.md` and `references/add-datastream-workflow.md`.

| Embedded guidance file | When to use |
|----------|-------------|
| `/research-integration` skill (orchestrates its own research subagents) | Vendor/API research before building, when no research brief is provided |
| `cel-programs/references/builder-subagent-guidance.md` | Each CEL data stream — mock API, CEL program (incremental mito build), `cel.yml.hbs` template, manifest vars, initial field mappings |
| `integration-testing/references/builder-setup-subagent-guidance.md` | Each non-CEL data stream — data collection setup (docker-compose, sample logs, agent stream template, system test config, manifest var cleanup) |
| `ingest-pipelines/references/builder-subagent-guidance.md` | Each data stream's pipeline and field definitions |
| `integration-testing/references/builder-system-test-subagent-guidance.md` | System test execution after pipeline work completes, for any testable input (CEL, tcp, udp, http_endpoint, logfile, kafka, pubsub) |
| `review-integration/references/reviewer-subagent-guidance.md` | Quality review after all streams are built — classifies files by domain, loads relevant domain skills and checklists via the `review-integration` skill, returns severity-ranked, domain-tagged findings |

For **cloud storage inputs** (aws-s3, gcs, azure-blob-storage, azure-eventhub): skip data collection setup and system tests. The scaffold provides a usable template; trim vars to match needs. See `references/create-workflow.md` for details.

## References

- `references/create-workflow.md` — full phases 1–8 for creating a new integration, subagent instructions, guardrails, data anonymization
- `references/add-datastream-workflow.md` — phases 1–4 for adding data streams to an existing package, CEL/pipeline/system-test sequence
- `references/scaffold-commands.md` — scaffold commands, post-scaffold edits, base-fields.yml format
- `references/package-layout.md` — integration and input package topology, manifest patterns
