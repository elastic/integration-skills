# Contributing to Integration Skills

Thanks for your interest in improving Integration Skills. This repository contains agent workflows (skills) for building and maintaining Elastic integrations. Contributions are primarily documentation and workflow improvements — the skills themselves are markdown files with reference materials.

## Reporting bugs

If a skill produces wrong output, fails unexpectedly, or behaves inconsistently, [open a bug report](https://github.com/elastic/integration-skills/issues/new?template=bug_report.yml). The template will ask for the skill name, your agent environment, reproduction steps, and relevant output.

**Important:** Strip credentials, API keys, and any other sensitive data from logs and output before submitting.

## Suggesting improvements

Have an idea for a new skill, a better workflow, or an improvement to an existing skill? [Open a feature request](https://github.com/elastic/integration-skills/issues/new?template=feature_request.yml).

## Contributing changes

1. **Fork** the repository and create a branch from `main`.
2. Make your changes. Skills live under `skills/` — each skill has a `SKILL.md` and optionally a `references/` directory with supporting material.
3. Test your changes by loading the modified skill into your agent environment (Cursor, Claude Code, etc.) and verifying the workflow produces correct output.
4. **Open a pull request** against `main` with a clear description of what changed and why.

### What makes a good contribution

- Fixes to incorrect or outdated guidance in skill files
- New reference material that improves skill output quality (processor patterns, field mapping examples, test fixtures)
- Improvements to skill workflows that make them more reliable across different LLMs
- New skills that address gaps in the integration development lifecycle
- Typo and clarity fixes

### Scope

This repository contains skills (structured markdown and reference docs), not application code. The core deliverable is the `skills/` directory. Each skill follows the [Agent Skills](https://agentskills.io/) open standard.

## Code of conduct

This project follows the [Elastic Community Code of Conduct](https://www.elastic.co/community/codeofconduct). By participating, you agree to uphold this code.
