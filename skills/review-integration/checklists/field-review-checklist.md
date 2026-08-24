# Field mapping review checklist

### Build configuration

- [ ] `_dev/build/build.yml` exists when any field files are present -- **HIGH** if missing
- [ ] ECS reference pinned to `git@v9.3.0` for standard integrations, or `git@v9.5.0` for packages with entity data streams (those using `event.kind: asset`) -- **HIGH** if wrong version; must match `ecs.version` set in the pipeline
- [ ] ECS pin consistent with `ecs.version` set in pipeline -- **HIGH** if mismatch

### base-fields.yml

- [ ] Exists in every data stream's `fields/` directory -- **HIGH** if missing
- [ ] Exactly 6 entries: `data_stream.type`, `data_stream.dataset`, `data_stream.namespace`, `event.module`, `event.dataset`, `@timestamp` -- **HIGH** if wrong entries
- [ ] All 6 entries use `external: ecs` (all are ECS fields; descriptions inherited from ECS) -- **HIGH** if missing
- [ ] `event.module` and `event.dataset` override `type: constant_keyword` with `value` -- **MEDIUM**
- [ ] `event.module` value matches package name -- **MEDIUM**
- [ ] `event.dataset` value matches `<package>.<stream>` -- **MEDIUM**
- [ ] `@timestamp` uses single-quoted key `'@timestamp'` with `external: ecs` -- **MEDIUM**

### ECS fields (ecs.yml)

- [ ] ECS fields set by the pipeline are declared in `fields/ecs.yml` using `name` + `external: ecs`. When the `conditions.kibana.version` floor is >= 8.13.0, declarations are required ONLY for `geo_point` on non-standard parent prefixes, `geo_shape`, `nested`, `flattened`, or where `elastic-package` fails validation; if the constraint admits stacks below 8.13, EVERY pipeline-set ECS field needs a declaration -- **HIGH** if missing in either case
- [ ] Standard keyword/date and standard-prefix geo ECS fields on packages with `conditions.kibana.version` floor >= 8.13.0 are covered by the `ecs@mappings` component template (applied by the stack from 8.13; package-spec version is not the gate) -- their absence from `ecs.yml` is NOT a finding, and existing `external: ecs` declarations are NOT removable-noise findings either
- [ ] No extra metadata on ECS fields beyond `name` and `external: ecs` (except where type/value overrides are explicitly needed) -- **LOW**

### Custom fields (fields.yml)

- [ ] Correct types: `keyword` for identifiers, `long`/`double` for numbers, `date` for timestamps, `ip` for IP addresses -- **HIGH** if wrong type
- [ ] Vendor-namespaced under appropriate group (not at root level) -- **MEDIUM**
- [ ] No `geo_point` fields at root level -- geo fields nested under parent entities (`source.geo`, `destination.geo`, etc.) -- **HIGH** if at root
- [ ] No duplicate field definitions across field files -- **MEDIUM**
- [ ] Every declared field should be written by the pipeline -- **MEDIUM** if orphan declaration

### Field descriptions

- [ ] Every field has a `description` set -- **LOW** if empty
- [ ] Descriptions are meaningful, not just the field name restated -- **LOW**

### ECS categorization values

- [ ] `event.kind`: only `alert`, `asset`, `enrichment`, `event`, `metric`, `state`, `pipeline_error`, `signal` -- **HIGH** if invalid
- [ ] `event.category`: only allowed values (api, authentication, configuration, database, driver, email, file, host, iam, intrusion_detection, library, malware, network, package, process, registry, session, threat, vulnerability, web) -- **HIGH** if invalid
- [ ] `event.type`: only allowed values (access, admin, allowed, change, connection, creation, deletion, denied, device, end, error, group, indicator, info, installation, protocol, start, user) -- **HIGH** if invalid
- [ ] `event.outcome`: only `failure`, `success`, `unknown` -- **HIGH** if invalid
- [ ] Values are semantically appropriate for the data source -- **MEDIUM**
- [ ] `event.kind: asset` and entity/inventory data streams (one-document-per-entity snapshots of users, hosts, devices, apps) go together: entity streams set `asset` (not `event` or `state`), and `asset` never appears on event logs, metric streams, or findings streams -- **MEDIUM** either way

### When reviewing a diff

Check: are new fields from changed pipeline processors declared? Are removed pipeline fields cleaned up from declarations? Do type changes in the pipeline match field type declarations?
