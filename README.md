<p align="center">
  <img alt="Elastic logo" src="https://www.elastic.co/static-res/images/elastic-logo-200.png" width="200">
</p>

<p align="center">
  <a href="LICENSE.txt"><img alt="License" src="https://img.shields.io/badge/license-Apache%202.0-blue"></a>
</p>

# Integration Skills

Agent workflows for building and maintaining Elastic integrations — works with Cursor, Claude Code, Codex, and any LLM-powered coding environment.

> **Beta** — This is the initial release. Skills are under active development — expect changes, and please [report any issues](https://github.com/elastic/integration-skills/issues/new?template=bug_report.yml) you find.

## What is this?

**Integration Skills** is a public collection of agentic workflows that cover the full lifecycle of building, reviewing, and maintaining [Elastic integration packages](https://github.com/elastic/integrations). The skills are LLM-agnostic by design: they work with whatever AI-powered coding environment you already use — Cursor, Claude Code, Codex, or anything else that can read skill/instruction files from a directory.

The toolkit is organized around two top-level skills that cover the core lifecycle of an Elastic integration:

- **`/research-integration`** — Researches a vendor, product, or feature before you start building. Investigates API documentation, data collection methods, sample data formats, and ECS mapping candidates. Produces a structured research brief that feeds directly into `/create-integration`.
- **`/create-integration`** — Scaffolds a new integration package end-to-end: package creation, data stream scaffolding, manifest configuration, CEL programs, ingest pipelines, field mappings, and system tests.

Together, these skills turn integration development from a slow, manual process into a fast, structured, agent-assisted workflow.

## Who this is for

This toolkit is designed for engineers who:

- Build or maintain Elastic integration packages — whether as contributors to [`elastic/integrations`](https://github.com/elastic/integrations), as Elastic partners, or as independent developers building custom integrations
- Are familiar with the Elastic Stack (Elasticsearch, Kibana, Elastic Agent) at an integration-development level
- Want structured, repeatable, agent-assisted workflows instead of figuring out each integration from scratch

## Recommended knowledge

You will get the most out of these skills if you are comfortable with:

- **Elastic Agent and integrations** — how integration packages are structured, how data streams work, and the basics of the `elastic-package` CLI. The [Elastic integrations developer guide](https://www.elastic.co/docs/extend/integrations) is the canonical reference.
- **Elastic Common Schema (ECS)** — field naming conventions and event categorization. See the [ECS reference](https://www.elastic.co/docs/reference/ecs/ecs-field-reference).
- **Ingest pipelines** — Elasticsearch ingest pipeline fundamentals (processors, conditions, error handling). See the [ingest pipeline docs](https://www.elastic.co/docs/manage-data/ingest/transform-enrich/ingest-pipelines).
- **CEL programs** (for REST API integrations) — the Common Expression Language as used in Elastic Agent's CEL input type. See the [Elastic Agent CEL input docs](https://www.elastic.co/docs/reference/beats/filebeat/filebeat-input-cel).

## Getting started

### Requirements

The following tools must be installed and available on `$PATH` for the agent workflows to function.

| Tool | Purpose | Install |
|------|---------|---------|
| [Docker](https://docs.docker.com/get-docker/) | Runs the Elastic Stack for system tests and service containers | [Official docs](https://docs.docker.com/get-docker/) |
| [elastic-package](https://github.com/elastic/elastic-package) | CLI for building, linting, formatting, and testing integration packages | `go install github.com/elastic/elastic-package@latest` |
| [celfmt](https://github.com/elastic/celfmt) | Canonical formatter and simplifier for CEL programs in agent integration configs | `go install github.com/elastic/celfmt/cmd/celfmt@latest` |
| [stream](https://github.com/elastic/stream) | Mock service for testing integration scripts | `go install github.com/elastic/stream@latest` |
| [mito](https://github.com/elastic/mito) | CEL debugging and playground tool for prototyping against live or mock data | `go install github.com/elastic/mito/cmd/mito@latest` |
| [ceplx](https://github.com/efd6/ceplx) | CEL cyclomatic and cognitive complexity assessment tool | `go install github.com/efd6/ceplx/cmd/ceplx@latest` |
| [kbdash](https://github.com/efd6/kbdash) | Extracts structured text descriptions from Kibana dashboard JSON for readable diffs | `go install github.com/efd6/kbdash@latest` |

All Go tools require a working [Go](https://go.dev/dl/) installation with `$GOPATH/bin` on your `$PATH`.

### npx (Recommended)

The fastest way to install skills is with the skills CLI. No need to clone this repository — just run:

```bash
npx skills add elastic/integration-skills
```

This launches an interactive prompt to select skills and target agents. The CLI copies each skill folder into the correct location for the agent to discover.

Install a specific skill by name:

```bash
npx skills add elastic/integration-skills --skill cel-programs
```

Install to specific agents (see [supported agents](https://github.com/vercel-labs/skills?tab=readme-ov-file#supported-agents)):

```bash
npx skills add elastic/integration-skills -a cursor -a claude-code
```

List available skills without installing:

```bash
npx skills add elastic/integration-skills --list
```

Install all skills to all agents (non-interactive):

```bash
npx skills add elastic/integration-skills --all
```

| Flag | Description |
|------|-------------|
| -a, --agent | Target specific agents (see [Supported agents](https://github.com/vercel-labs/skills?tab=readme-ov-file#supported-agents)) |
| -s, --skill | Install specific skills by name |
| -g, --global | Install to user home instead of project directory |
| -y, --yes | Skip confirmation prompts |
| --all | Install all skills to all agents without prompts |
| --list | List available skills without installing |

### Claude Code (plugin marketplace)

If you use [Claude Code](https://claude.ai/code), you can install the skills natively through the Claude Code plugin marketplace. This path supports `autoUpdate`, so your local copy stays current whenever the skills are updated upstream.

**Register the marketplace and install the plugin:**

```
/plugin marketplace add elastic/integration-skills
/plugin install integration-skills@elastic-integration-skills
```

Once installed, skills are namespaced under the plugin name when invoked explicitly (e.g. `/integration-skills:create-integration`). They still trigger automatically from their descriptions, so you can also just describe what you want and the agent picks the right skill.

**Auto-update:** After installation, Claude Code keeps the plugin current in the background. No manual `npx skills update` step needed.

### Local clone

If you prefer to work from a local checkout, or your environment does not have Node.js / npx, clone the repository and copy the `skills/` folder into the config directory your agent expects:

```bash
git clone https://github.com/elastic/integration-skills.git
cd integration-skills
cp -r skills ~/.cursor/skills    # or ~/.claude/skills or your agent's config directory
```

### Updating skills

Check whether any installed skills have changed upstream:

```bash
npx skills check
```

Pull the latest versions of all installed skills:

```bash
npx skills update
```

**Working with the integrations repository:** If you are developing integrations against [`elastic/integrations`](https://github.com/elastic/integrations), run these skills from a checkout of that repo or point your agent at that tree. This gives the agent the real package layout, shared conventions, and surrounding packages for context. Several `elastic-package` commands (system tests, workspace-aware workflows) also require an integrations-style workspace to run correctly.

## Skills reference

### Top-level skills

These skills map directly to the lifecycle of building and maintaining an Elastic integration. You invoke them by name in your agent.

#### `/research-integration`

Researches a vendor, product, or feature before building an integration. Launches parallel research subagents to investigate data collection methods, API documentation, sample data formats, field schemas, and ECS mapping candidates. Writes a structured research brief to `research_results/<product_slug>/` that feeds directly into `/create-integration`.

**Invoke this first** when building an integration for a product you haven't worked with before. Pass the research output as context when you run `/create-integration`.

```bash
/research-integration I want to create a Checkpoint Harmony Endpoint integration with alerts, threat events, and audit logs
```

#### `/create-integration`

Scaffolds a new Elastic integration package end-to-end: package creation, data stream scaffolding, manifest configuration, CEL program building, ingest pipeline creation, field mappings, and system testing. Also handles adding data streams to an existing package — automatically provides the target package, stream details, and the correct skill routes to the workflow.

**Recommended flow:** run `/research-integration` first, then pass the research brief as input for the highest-quality output.

```bash
/create-integration @research_results/checkpoint_harmony/ Package name: checkpoint_harmony, single data stream "event" using CEL input
```

---

### Domain skills

In addition to the top-level skills, you can invoke any domain skill directly when you need focused help on a specific area:

| Skill | What it covers |
|-------|---------------|
| `/cel-programs` | CEL program authoring, pagination patterns, auth patterns, rate limiting, error handling |
| `/ingest-pipelines` | Ingest pipeline processors, grok patterns, Painless scripts, error handling |
| `/ecs-field-mappings` | ECS field mapping strategy, event categorization, custom fields |
| `/input-configurations` | Input templates for all supported input types: CEL, HTTPJSON, syslog, filestream, AWS S3, Azure Event Hub, GCP Pub/Sub, and more |
| `/package-spec` | Manifest rules, changelog schema, format version features |
| `/integration-testing` | Pipeline testing, system testing, test fixture authoring |
| `/elastic-package-cli` | `elastic-package` CLI usage and troubleshooting |
| `/dashboard-guidelines` | Kibana dashboard authoring standards |
| `/dashboard-review` | Kibana dashboard review procedures |
| `/anonymize-logs` | Test data anonymization conventions |

## Reporting bugs

Found a bug, unexpected behavior, or a skill that consistently produces wrong output? [Open a bug report](https://github.com/elastic/integration-skills/issues/new?template=bug_report.yml).

Want to suggest a new skill or improvement? [Open a feature request](https://github.com/elastic/integration-skills/issues/new?template=feature_request.yml).

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute.

## Specification

Skills in this repository follow the [Agent Skills](https://agentskills.io/) open standard for packaging procedural knowledge for AI agents.

## License

This project is licensed under the [Apache License 2.0](LICENSE.txt).
