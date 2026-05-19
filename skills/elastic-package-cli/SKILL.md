---
name: elastic-package-cli
description: "Use when developing or validating Elastic integrations with elastic-package commands such as build, check, lint, format, test, stack, service, install, profiles, and benchmark."
license: Apache-2.0
metadata:
  author: elastic
  version: "1.0"
---

# elastic-package CLI


## When to use

Use this skill when tasks include:
- validating package structure and formatting
- building a package artifact
- running pipeline or system tests
- managing local Elastic test stack lifecycle
- installing or checking package status in Kibana

## When not to use

Do not use this skill as the primary guide for:
- ECS field design decisions (use an ECS-focused skill)
- ingest processor design and parsing strategy (use an ingest-pipeline-focused skill)
- package layout architecture (use a package-structure-focused skill)

## Prerequisites

- `elastic-package` is installed and available in `PATH`
- container runtime is available (Docker or Podman)
- you run commands from a package directory (or pass `-C <package-dir>`)

## Core workflows

### 1) Validate and build loop

Run this sequence for routine local verification:

```bash
elastic-package format
elastic-package lint
elastic-package check
elastic-package build
```

Notes:
- `check` runs lint and build together and fails fast by default.
- use `format --fail-fast` when you want read-only verification without rewriting files.

### 2) Pipeline test loop (fast iteration)

Use Elasticsearch-only stack for quicker feedback:

```bash
elastic-package stack up -d --services=elasticsearch
elastic-package test pipeline
elastic-package test pipeline --generate
```

Then review generated expected files before keeping changes.

### 3) System test loop (end-to-end)

Use this when you need full ingest behavior with service provisioning:

```bash
elastic-package stack up -d
elastic-package service up
elastic-package test system
```

Use `--data-streams <name>` to scope tests and reduce run time.

## Practical command examples

```bash
# format package files
elastic-package format

# lint against package spec and templates
elastic-package lint

# combined validation workflow
elastic-package check

# build package artifact
elastic-package build

# start only Elasticsearch for pipeline tests
elastic-package stack up -d --services=elasticsearch

# run pipeline tests
elastic-package test pipeline

# regenerate expected pipeline outputs
elastic-package test pipeline --generate

# run end-to-end system tests
elastic-package test system
```

## Key flags cheat sheet

- global: `-C, --change-directory`, `-v, --verbose`
- stack: `-d, --daemon`, `-s, --services`, `--version`, `-p, --profile`
- pipeline tests: `-d, --data-streams`, `-g, --generate`, `-m, --fail-on-missing`
- system tests: `--setup`, `--tear-down`, `--no-provision`, `--variant`

## Quick command map

- validate/build: `format`, `lint`, `check`, `build`
- stack lifecycle: `stack up`, `stack status`, `stack down`
- testing: `test pipeline`, `test system`, `test static`, `test asset`, `test policy`, `test script`
- package lifecycle: `create`, `install`, `status`, `uninstall`
- support: `service up`, `profiles`, `benchmark`

## References

- Failure diagnosis and fixes: `references/troubleshooting.md`

