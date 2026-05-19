# ECS categorization cheatsheet

Use this guide when selecting `event.kind`, `event.category`, `event.type`, and `event.outcome`.

## Core rules

- Use only ECS allowed values.
- `event.category` and `event.type` are arrays.
- If no allowed value fits, leave the field empty.
- Use `event.action` for source-specific verbs (for example `blocked`, `dropped`, `authenticated`).
- Set `event.outcome` only when success/failure applies.

## `event.kind` allowed values

| Value | Use when | Notes |
| --- | --- | --- |
| `alert` | External detection/alert event | Used for alerts from external security systems. |
| `asset` | Inventory/entity snapshot records | Asset and identity inventory style records. |
| `enrichment` | Enrichment/context feeds | IOC/context datasets that enrich other events. |
| `event` | General event/log | Most common value for integration logs. |
| `metric` | Numeric measurements | Time series metrics such as cpu/memory/rate. |
| `pipeline_error` | Ingest/parsing failure | Use in ingest `on_failure` paths. |
| `signal` | Reserved for Kibana alerting framework | Do not set this in data ingestion pipelines. |
| `state` | Non-numeric state snapshots | For periodic categorical state measurements. |

## `event.category` allowed values and typical `event.type` pairings

| Category | Typical `event.type` values |
| --- | --- |
| `api` | `access`, `admin`, `allowed`, `change`, `creation`, `deletion`, `denied`, `end`, `info`, `start`, `user` |
| `authentication` | `start`, `end`, `info` |
| `configuration` | `access`, `change`, `creation`, `deletion`, `info` |
| `database` | `access`, `change`, `info`, `error` |
| `driver` | `change`, `end`, `info`, `start` |
| `email` | `info` |
| `file` | `access`, `change`, `creation`, `deletion`, `info` |
| `host` | `access`, `change`, `end`, `info`, `start` |
| `iam` | `admin`, `change`, `creation`, `deletion`, `group`, `info`, `user` |
| `intrusion_detection` | `allowed`, `denied`, `info` |
| `library` | `start` |
| `malware` | `info` |
| `network` | `access`, `allowed`, `connection`, `denied`, `end`, `info`, `protocol`, `start` |
| `package` | `access`, `change`, `deletion`, `info`, `installation`, `start` |
| `process` | `access`, `change`, `end`, `info`, `start` |
| `registry` | `access`, `change`, `creation`, `deletion` |
| `session` | `start`, `end`, `info` |
| `threat` | `indicator` |
| `vulnerability` | `info` |
| `web` | `access`, `error`, `info` |

## `event.type` allowed values

| Value | Meaning |
| --- | --- |
| `access` | Something was accessed. |
| `admin` | Administrative object activity. |
| `allowed` | Something was allowed. |
| `change` | Something changed. |
| `connection` | Connection/flow event, usually network. |
| `creation` | Something was created. |
| `deletion` | Something was deleted. |
| `denied` | Something was denied. |
| `device` | Device object related activity. |
| `end` | Something ended. |
| `error` | Error event type (not pipeline parse failures). |
| `group` | Group object related activity. |
| `indicator` | IOC indicator event. |
| `info` | Informational event. |
| `installation` | Installation event. |
| `protocol` | Protocol detail/analysis event. |
| `start` | Something started. |
| `user` | User object related activity. |

## `event.outcome` allowed values

| Value | Meaning | Common usage |
| --- | --- | --- |
| `success` | Successful result | Successful auth, successful HTTP response, successful policy action. |
| `failure` | Failed result | Failed auth, blocked/failed operation from producer perspective. |
| `unknown` | Attempt observed, result unknown | Request-only view where response/outcome is not known. |

Do not set `event.outcome` for purely informational or metric/state events where outcome does not apply.

## Worked examples

### Firewall blocked connection (block succeeded)

- `event.kind`: `event`
- `event.category`: `["network"]`
- `event.type`: `["connection", "denied"]`
- `event.outcome`: `success`
- `event.action`: `dropped`

### Failed user creation attempt

- `event.kind`: `event`
- `event.category`: `["iam"]`
- `event.type`: `["user", "creation"]`
- `event.outcome`: `failure`

### Web access log

- `event.kind`: `event`
- `event.category`: `["web"]`
- `event.type`: `["access"]`
- `event.outcome`: `success` or `failure` (often derived from HTTP status)

### File inventory listing (no action outcome)

- `event.kind`: `event`
- `event.category`: `["file"]`
- `event.type`: `["info"]`
- `event.outcome`: not set

