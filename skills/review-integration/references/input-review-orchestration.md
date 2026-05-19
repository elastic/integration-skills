# Input review orchestration

How to route different input types through appropriate review depths.

## Review depth by input type

| Input type | Public skill to load | Private skill to load | Review depth |
|-----------|---------------------|----------------------|-------------|
| CEL | `cel-programs` + `checklists/cel-review-checklist.md` | `review-integration` references (version matrices, validator procedure) | Deep: version matrices, validator procedure, API conformance |
| HTTPJSON | `input-configurations` -> `httpjson-guide.md` + `checklists/httpjson-review-checklist.md` | API conformance (if docs available) | Medium: 10 validation rules, pagination, cursor persistence |
| AWS S3 | `input-configurations` -> `aws-s3-guide.md` | -- | Standard: common patterns + type-specific guide |
| HTTP Endpoint | `input-configurations` -> `http-endpoint-guide.md` | -- | Standard |
| WebSocket | `input-configurations` -> `websocket-guide.md` | -- | Standard (check for CEL program inside WebSocket) |
| TCP/UDP | `input-configurations` -> `tcp-udp-guide.md` | -- | Standard |
| Other types | `input-configurations` -> matching guide | -- | Standard: common patterns + type-specific guide |

## CEL-capable types

WebSocket and HTTP Endpoint inputs can contain embedded CEL programs (detected by `program:` key in the YAML). When detected, also load the CEL version matrices and validator procedure from `review-integration` references and apply CEL review depth.

## Common patterns (always)

Always load `input-configurations/references/common-input-patterns.md` regardless of type. Check: tags, forwarded/disable_host coupling, processors passthrough, no hardcoded values.
