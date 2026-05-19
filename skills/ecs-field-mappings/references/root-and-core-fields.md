# ECS root and core fields

Use this page as a quick lookup for ECS fields that appear most often in integrations.

## Base (root) fields

These are top-level fields in ECS and commonly expected in events.

| Field | Type | Why it matters |
| --- | --- | --- |
| `@timestamp` | `date` | Required event time used by queries, timelines, and dashboards. |
| `message` | `match_only_text` | Human-readable log message for quick triage. |
| `tags` | `keyword[]` | Lightweight event annotations (environment, source, flags). |

## Core ECS field sets used frequently in integrations

### Event and ECS metadata

| Field set | Typical fields | Typical use |
| --- | --- | --- |
| `event` | `event.kind`, `event.category`, `event.type`, `event.outcome`, `event.action`, `event.original`, `event.dataset`, `event.module` | Classify and describe what happened. |
| `ecs` | `ecs.version` | Declares ECS version the pipeline targets. |
| `data_stream` | `data_stream.type`, `data_stream.dataset`, `data_stream.namespace` | Data stream routing and naming dimensions. |
| `log` | `log.level`, `log.logger`, `log.file.path`, `log.offset` | Source logging context. |
| `error` | `error.message`, `error.type`, `error.stack_trace` | Mainly used for integration error reporting. |

### Network and transport

| Field set | Typical fields | Typical use |
| --- | --- | --- |
| `source` | `source.ip`, `source.port`, `source.address`, `source.bytes` | Origin side of connection/event. |
| `destination` | `destination.ip`, `destination.port`, `destination.address`, `destination.bytes` | Target side of connection/event. |
| `network` | `network.transport`, `network.protocol`, `network.type`, `network.direction` | Shared network context and protocol shape. |
| `url` | `url.original`, `url.path`, `url.domain`, `url.query` | Parsed URI details for HTTP and proxy logs. |
| `http` | `http.request.method`, `http.response.status_code`, `http.version` | HTTP semantics and response details. |
| `dns` | `dns.question.name`, `dns.question.type`, `dns.answers` | DNS query/answer activity. |
| `geo` | `source.geo.*`, `destination.geo.*`, `client.geo.*`, `host.geo.*`, `observer.geo.*`, `server.geo.*` | Geo enrichment from GeoIP; always nested under an entity prefix — never at document root. |

### Identity, host, and runtime context

| Field set | Typical fields | Typical use |
| --- | --- | --- |
| `host` | `host.name`, `host.hostname`, `host.ip`, `host.os.name`, `host.architecture` | Host identity and platform details. |
| `user` | `user.name`, `user.id`, `user.email`, `user.roles` | Primary actor information. |
| `service` | `service.name`, `service.type`, `service.version`, `service.address` | Service endpoint and runtime metadata. |
| `observer` | `observer.type`, `observer.name`, `observer.vendor`, `observer.product` | Device/system that observed the event. |
| `container` | `container.id`, `container.name`, `container.runtime`, `container.image.name` | Containerized runtime details. |
| `cloud` | `cloud.provider`, `cloud.account.id`, `cloud.region`, `cloud.instance.id` | Cloud resource and tenancy context. |
| `process` | `process.name`, `process.pid`, `process.executable`, `process.args` | Process lifecycle and command context. |
| `file` | `file.path`, `file.name`, `file.extension`, `file.size` | File and filesystem activity. |
| `related` | `related.ip`, `related.hosts`, `related.user`, `related.hash` | Pivot fields for cross-event correlation. |
| `user_agent` | `user_agent.original`, `user_agent.name`, `user_agent.version` | Browser/client fingerprint extraction. |

## Field file samples: `agent.yml` and `beats.yml`

### `agent.yml`

Non-ECS fields populated by Elastic Agent or Beats but not covered by ECS. Include only when the input type emits these fields.

```yaml
- name: cloud
  title: Cloud
  group: 2
  type: group
  fields:
    - name: image.id
      type: keyword
      description: Image ID for the cloud instance.
    - name: instance.id
      type: keyword
      description: Instance ID of the host machine.
- name: host
  title: Host
  group: 2
  type: group
  fields:
    - name: containerized
      type: boolean
      description: If the host is a container.
    - name: os.build
      type: keyword
      description: OS build information.
    - name: os.codename
      type: keyword
      description: OS codename, if any.
- name: input.type
  type: keyword
  description: Input type.
- name: log.offset
  type: long
  description: Log offset.
```

### `beats.yml`

Filebeat/Beats-specific fields not covered by ECS. Minimal form:

```yaml
- name: input.type
  type: keyword
  description: Type of Filebeat input.
- name: log.offset
  type: long
  description: Log offset.
```

Some inputs also emit `log.flags` or `log.file.*` sub-fields — add them here when present in source data.

## Notes for implementation authors

- Prefer ECS fields whenever semantics match to keep cross-integration queries simple.
- If no ECS field exists for your data, add namespaced custom fields under your package namespace in `fields.yml`.
- Keep categorization fields (`event.*`) within allowed ECS values.
- List every ECS field the pipeline sets in `ecs.yml` with `name` + `external: ecs`.
- Ensure `_dev/build/build.yml` exists with `dependencies.ecs.reference: "git@v9.3.0"`.
