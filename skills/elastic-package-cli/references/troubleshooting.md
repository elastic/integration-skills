# Troubleshooting elastic-package CLI workflows

Use this page when stack startup, tests, or package operations fail unexpectedly.

## Stack does not start (`stack up` fails)

**Symptoms**
- `elastic-package stack up` exits early.
- service containers restart continuously.

**Likely causes**
- Docker/Podman memory is too low.
- required images cannot be pulled.
- local ports are already in use.

**Fixes**
1. Increase container runtime memory allocation.
2. Re-run with verbose logs:
   ```bash
   elastic-package stack up -d -v
   elastic-package stack status
   ```
3. Confirm required ports are free (`9200`, `5601` and others used by enabled services).
4. If image pulls fail, verify network/proxy settings and retry.

## Elasticsearch-only stack command fails

**Symptoms**
- `elastic-package stack up -d --services=elasticsearch` does not start or exits.

**Likely causes**
- invalid `--services` value or profile misconfiguration.
- cached stack state is unhealthy.

**Fixes**
1. Confirm command syntax exactly:
   ```bash
   elastic-package stack up -d --services=elasticsearch
   ```
2. Check health:
   ```bash
   elastic-package stack status
   ```
3. Reset local stack state:
   ```bash
   elastic-package stack down
   elastic-package clean
   ```
4. Retry with `-v` for detailed diagnostics.

## TLS/certificate connection errors

**Symptoms**
- install/status commands fail with TLS verify errors.
- API calls to Kibana/Elasticsearch report certificate validation failures.

**Likely causes**
- self-signed or custom certs not trusted by local environment.

**Fixes**
1. For package install testing only, use:
   ```bash
   elastic-package install --tls-skip-verify
   ```
2. Prefer correcting trust configuration in your profile/environment for long-term use.

## Not in package context

**Symptoms**
- commands fail because package root cannot be detected.

**Likely causes**
- current working directory is not a package directory.

**Fixes**
1. Change into package directory before running package-scoped commands.
2. Or use `-C`:
   ```bash
   elastic-package -C packages/<package-name> check
   ```

## Pipeline tests fail after parser changes

**Symptoms**
- `elastic-package test pipeline` fails with expected vs actual differences.

**Likely causes**
- expected outputs are stale.
- field mappings or event shape changed intentionally.

**Fixes**
1. Re-run scoped test first:
   ```bash
   elastic-package test pipeline --data-streams <data-stream>
   ```
2. If changes are intentional, regenerate:
   ```bash
   elastic-package test pipeline --data-streams <data-stream> --generate
   ```
3. Review generated expected files before keeping them.

## Missing tests fail gates

**Symptoms**
- pipeline/system tests fail due to missing test fixtures.

**Likely causes**
- `--fail-on-missing` enabled with incomplete fixtures.

**Fixes**
1. Add required fixtures under `_dev/test/...`.
2. Temporarily run without `--fail-on-missing` while scaffolding.
3. Re-enable `--fail-on-missing` before final validation.

## System tests fail during setup/provision

**Symptoms**
- `elastic-package test system` fails in setup or service provisioning.

**Likely causes**
- package service stack not started.
- invalid service config/variant.

**Fixes**
1. Bring up stack and package service explicitly:
   ```bash
   elastic-package stack up -d
   elastic-package service up
   ```
2. Run phased diagnostics:
   ```bash
   elastic-package test system --setup
   elastic-package test system --no-provision
   elastic-package test system --tear-down
   ```
3. If needed, pass explicit config with `--config-file`.

## System test teardown fails (agent policy / Fleet)

**Symptoms**
- Teardown after `elastic-package test system` fails because an **agent policy** or Fleet resource is still referenced or cannot be deleted.

**Fixes**
1. Do not try to repair Fleet state manually — reset the local stack:
   ```bash
   elastic-package stack down
   elastic-package stack up -d -v
   ```
2. Rerun `elastic-package build` (if the package changed) and `elastic-package test system`.

See the `integration-testing` skill → `references/system-testing.md` (Teardown failures section) for the same guidance in context.

## Profile issues (`-p`, `profiles`)

**Symptoms**
- commands use unexpected stack config.
- tests work only with one profile but not another.

**Likely causes**
- wrong profile selected, or profile config drift.

**Fixes**
1. Inspect profiles:
   ```bash
   elastic-package profiles list
   ```
2. Set intended default:
   ```bash
   elastic-package profiles use <profile-name>
   ```
3. Or pass `-p <profile-name>` explicitly per command.

## Generic debugging checklist

```bash
elastic-package version
elastic-package stack status
elastic-package test pipeline -v
elastic-package test system -v
```

If behavior still looks inconsistent, capture verbose output and stack status before rerunning commands.
