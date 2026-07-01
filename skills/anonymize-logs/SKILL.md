---
name: anonymize-logs
description: >-
  Anonymize and sanitize customer-provided log files before they are committed
  as pipeline test fixtures or sample events. Performs a line-by-line review
  and replaces all sensitive values inline, preserving log structure and format
  exactly — never reformats, re-indents, or restructures content. Invoke
  manually with /anonymize-logs.
---

# Anonymize Logs

Sanitize customer-provided log files so they are safe to commit to source control.

## What you provide

| Input | How to provide |
|-------|----------------|
| Log file(s) to sanitize | `@`-mention files or paste inline |
| Output location (optional) | free text path, defaults to same directory with `.sanitized` suffix |
| In-place override (optional) | say "in place" to overwrite the original |

## Golden rule — never reformat the content

**Only replace sensitive values. Do not touch anything else.**

The ingest pipeline parser depends on exact whitespace, delimiters, quoting, and line structure.

- **NDJSON** (one JSON object per line): do not pretty-print, re-indent, or restructure. Each line must remain a single compact JSON object on one line.
- **Syslog / CEF / key-value logs**: do not add or remove spaces, change quoting, or normalize field order.
- **Multiline logs**: preserve line grouping exactly.
- Replace only the *values* that identify real people, systems, or organizations — preserve field names, delimiters, structural tokens, and everything else character-for-character.

## Workflow

### Step 1 — Line-by-line replacement

Read every line and replace all sensitive values inline. Cover at minimum:

- **Authentication artifacts**: API keys, bearer tokens, passwords, OAuth tokens, base64-encoded credentials, private keys and certs (PEM blocks, SSH private keys), TLS/SSH fingerprints (JA3/JA4 hashes, SSH host key fingerprints, certificate fingerprints), DHCP fingerprints, partial secrets (`token_prefix`, `password_hash_prefix`, `hashed_token`) — partial exposure still identifies the credential
- **Personal identifiers**: email addresses (including CC/BCC lists, delegate/owner/creator email variants), usernames, display names, employee IDs, phone numbers, principal names (e.g. `user@tenant.onmicrosoft.com`), email subjects and body text
- **Organizational identifiers**: company names, tenant IDs (including `home_tenant_id`, `resource_tenant_id`, `aad_tenant_id` variants), account IDs, subscription IDs, billing account IDs, org slugs embedded in paths or JSON fields, org unit paths (e.g. `orgunit_path`, `org_unit_path`), department names and IDs, cost center IDs, Windows SIDs (Security Identifiers) in pipe names, task names, or registry paths
- **Infrastructure identifiers**: internal hostnames, FQDNs, private IP addresses, MAC addresses, internal URLs (staging/prod hostnames, internal tool domains), cloud resource IDs (ARNs, S3 bucket names, GCP project IDs, Azure subscription/resource names), Kubernetes cluster names, node names, pod names, and namespace names, container names and IDs, database hostnames and names (including `database.host`, `database.name`, `database_principal_name`), Windows domain topology fields (domain controller hostnames, NT domain names, `domain_controller_object_guid`, `domain_controller_object_sid`)
- **Device and hardware identifiers**: serial numbers, hardware UUIDs, machine IDs, device UUIDs, BIOS/firmware version strings that are unique to a specific device
- **File system paths**: process command lines, file paths, registry key paths, and log file paths that embed usernames, org names, or internal system structure (e.g. `C:\Users\alice\`, `/home/bob/`, `HKLM\...\S-1-5-21-...`)
- **Connection strings**: database URIs, Redis URLs, any connection string that includes credentials or internal hostnames
- **Resource ownership**: owner email, creator email, last-modified-by identity, delegate user email, assignee email, impersonator fields — any field that names a specific person as the actor on a resource
- **Tracking identifiers**: session IDs, request/correlation IDs, transaction IDs, or any long opaque string tied to a real entity
- **Hash values**: replace when they could be derived from sensitive input (password hashes, HMAC secrets) — preserve file hashes (MD5, SHA1, SHA256 of file content) and other content-addressable references (git SHAs, TLS cert hashes used as identifiers)
- **Geographic specifics**: precise GPS coordinates, real street addresses — city and country names are generally safe to keep

Apply placeholder conventions and shape rules (see below) as you go.

### Step 2 — Verify structure is intact

Confirm after sanitization:
- Line count is unchanged
- JSON lines are still valid JSON (for NDJSON files):
  ```bash
  python3 -c "
  import json, sys
  with open('FILE') as f:
      for i, line in enumerate(f, 1):
          line = line.strip()
          if line:
              try: json.loads(line)
              except Exception as e: print(f'Line {i}: {e}')
  "
  ```
- Timestamps still match the format the pipeline uses for date parsing
- Enum / status / action values that pipeline conditions branch on are untouched

## Placeholder conventions

Use consistent, realistic-looking replacements — not `REDACTED` strings, which break format-sensitive parsers.

| Type | Replacement |
|------|-------------|
| Email | `user@example.com`, `admin@example.org` |
| IPv4 | RFC 5737 ranges: `198.51.100.10`, `203.0.113.20`, `192.0.2.30` |
| IPv6 | `2001:db8::10` |
| Hostname / FQDN | `host-1.example.local`, `srv-web-01.example.internal` |
| Domain | `example.com`, `example.org`, `example.net` |
| UUID | `89a1d5c1-2b3e-4f67-8a9b-0c1d2e3f4a5b` |
| API key / token | `sk_test_example_key_1234567890`, `dGVzdC10b2tlbi0xMjM0NTY3ODk=` |
| Username | `alice.johnson`, `bob.smith` |
| Display name | `Alice Johnson`, `Bob Smith` |
| Org / company name | `Example Corp`, `Acme Inc` |
| Account / tenant ID | `000000000000`, `example-tenant-id` |
| Cloud resource ID | `arn:aws:iam::000000000000:user/example-user` |
| S3 bucket name | `example-bucket` |
| MAC address | `00-00-5E-00-53-23` (RFC 7042 documentation range) |
| Serial number | `SN000000000001` |
| Device / machine ID | use a synthetic UUID or `device-id-example-000001` |
| Windows SID | `S-1-5-21-000000000-000000000-000000000-1000` |
| File path (Windows) | `C:\Users\example-user\AppData\...` |
| File path (Unix) | `/home/example-user/...` or use `~` |
| Kubernetes cluster | `example-cluster`, `example-node-1` |
| Phone number | `734-555-0100` (555 range is reserved for fiction) |
| Database host / name | `db-host.example.local`, `example_database` |
| Department / org unit | `example-department`, `/example-org/example-unit` |
| Hashed / partial token | replace with full synthetic token of same format |
| DHCP fingerprint | `example-dhcp-fingerprint-000001` |
| JA4 fingerprint | replace with same-length hex string |
| Transaction / sequence / event ID (numeric) | synthetic integer of the **same digit count** — e.g. `48273915` → `10000002` |
| Session / request / correlation ID | same-length synthetic string (preserve length and charset), not a descriptive name |

**Consistency rule**: map identical original values to identical placeholders throughout the file. If the same IP appears 10 times, it must become the same replacement IP all 10 times — so cross-event correlations remain testable.

## Shape rule — replacements must match the original format

Every replacement must have the same shape as the original value. The parser and pipeline conditions depend on value format, not just field presence.

- **Numeric ID → numeric ID**: `/d/123/edit` → `/d/456/edit`, not `/d/example-document-id/edit`
- **Transaction / sequence / event ID → same-shape number**: these are *tracking identifiers*, not metrics — mask them, preserving digit count. e.g. CEF `cn1=48273915 cn2=3061847` → `cn1=10000002 cn2=1000002`
- **UUID → UUID**: a real UUID must become a synthetic UUID of the same version, not a descriptive string
- **URL → URL**: replace only the sensitive segment (hostname, path ID) — preserve the scheme, path structure, and query string shape
  - `https://docs.google.com/drawings/d/123/edit` → `https://docs.google.com/drawings/d/000000000000/edit` (replace the ID, not the host — `docs.google.com` is a public service name, not an org identifier)
  - `https://internal.corp.com/api/v1/resource` → `https://host-redacted.example.local/api/v1/resource` (replace the internal hostname, keep the path)
- **String ID → same-length or same-format string**: opaque alphanumeric IDs should become opaque alphanumeric placeholders of similar length, not descriptive names
- **Hostname in a URL vs. standalone hostname**: only replace hostnames that identify real internal infrastructure — public well-known hostnames (`docs.google.com`, `api.github.com`, `s3.amazonaws.com`) identify a service, not an organization, and do not need to be replaced

**Malformed or garbage values must not be replaced.** If a value looks broken, synthetic, or contains no real identifying information (e.g. `http://1=Y +z\\`, `00/00/0000`, `N/A`, empty strings, placeholder-looking values), leave it exactly as-is. Replacing a malformed value with a well-formed placeholder changes the shape and can alter pipeline behaviour — a grok that fails on the original will now succeed on the sanitized version, masking the real error.

If you are unsure what shape to use, look at neighbouring values of the same field type in the same file and match their format.

## What to preserve

Do not replace:
- Protocol names, action verbs, event types, severity levels (`ALLOW`, `DENY`, `INFO`, `ERROR`)
- HTTP status codes, port numbers, numeric metric values (counts, sizes, durations) — but **not** transaction / sequence / event IDs, which are tracking identifiers and must be masked (see above)
- Field names and keys
- Timestamps (format and timezone must stay intact)
- Structural tokens (brackets, braces, pipes, commas, tabs)
- Public well-known service hostnames in URLs (`docs.google.com`, `api.github.com`, etc.) — replace the path ID if it is sensitive, not the host
- File hashes (MD5, SHA1, SHA256 of file content) — these are content-addressable and safe; do not replace them
- User agent strings (`Mozilla/5.0 ...`) — these reveal browser/OS type but not identity; safe to keep
- City and country names in geo enrichment fields — replace only precise coordinates and street addresses
