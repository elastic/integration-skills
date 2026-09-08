# Input review orchestration

How to route different input types through appropriate review depths.

## Review depth by input type

| Input type | Build skill / guide to load | Review references to load | Review depth |
|-----------|---------------------|----------------------|-------------|
| CEL | `cel-programs` + `checklists/cel-review-checklist.md` | `review-integration` references (version matrices, validator procedure) | Deep: version matrices, validator procedure, API conformance |
| HTTPJSON | `input-configurations` -> `httpjson-guide.md` + `checklists/httpjson-review-checklist.md` | API conformance (if docs available) | Medium: 10 validation rules, pagination, cursor persistence |
| Entity Analytics | `checklists/entity-analytics-review-checklist.md` | `references/entity-analytics-provider-matrix.md` (provider sync/marker/deletion semantics, legacy vs minimal-state) | Medium: config-only input — checklist + provider matrix; no program review |
| AWS S3 | `input-configurations` -> `aws-s3-guide.md` | -- | Standard: common patterns + type-specific guide |
| HTTP Endpoint | `input-configurations` -> `http-endpoint-guide.md` | -- | Standard |
| WebSocket | `input-configurations` -> `websocket-guide.md` | -- | Standard (check for CEL program inside WebSocket) |
| TCP/UDP | `input-configurations` -> `tcp-udp-guide.md` | -- | Standard |
| Other types | `input-configurations` -> matching guide | -- | Standard: common patterns + type-specific guide |

## CEL-capable types

WebSocket and HTTP Endpoint inputs can contain embedded CEL programs (detected by `program:` key in the YAML). When detected, also load the CEL version matrices and validator procedure from `review-integration` references and apply CEL review depth.

## Common patterns (always)

Always load `input-configurations/references/common-input-patterns.md` regardless of type. Check: tags, forwarded/disable_host coupling, processors passthrough, no hardcoded values.

## Federated Identity (when detected)

When `review-integration` Federated Identity detection fires, also load `input-configurations/references/federated-identity-aws.md` regardless of input type (including CEL). Check: `iac_template_url` uses `cloudformation-federated-identity-aws-<version>.yml` with no `param_ElasticResourceId` (not the GuardDuty-only CFT); `identity_federation` vars are `[role_arn, supports_identity_federation]` (no `external_id`); `use_cloud_connectors` only on federation-eligible inputs — nested under `auth.aws:` for `cel` / `httpjson`, top-level for `aws-cloudwatch` / `aws/metrics`; `aws-s3` is pinned with `deployment_modes: ["default"]`.

Coverage, not sampling: enumerate every stream template under every agentless-enabled policy template. Each federation-eligible one (`cel`, `httpjson`, `aws-cloudwatch`, `aws/metrics`) must render `use_cloud_connectors` — a missing one is **HIGH** (the `aws` 8.1.3 AccessDenied regression was two unsampled `aws/metrics` streams). Pinned inputs (`aws-s3` with `deployment_modes: ["default"]`) sit under the same template and must **not** render it; do not flag them. `aws/metrics` has no dedicated guide — apply the **Stream template** flat shape from `federated-identity-aws.md` directly. Each federated stream should carry a `_dev/test/policy/test-<input>-agentless-cloud-connector.yml` fixture — **MEDIUM** if absent. A major bump for the floor raise pairs a `breaking-change` entry with the `enhancement` entry — flag a lone `enhancement` on a `1.x → 2.0.0` jump as **MEDIUM**.
