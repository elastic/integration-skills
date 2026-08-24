---
name: anonymize-logs
description: >-
  Anonymize and sanitize customer-provided log files. Performs a line-by-line
  review and replaces all sensitive values inline, preserving log structure and
  format exactly — never reformats, re-indents, or restructures content. Use
  when sanitizing customer logs, sample events, or test fixtures. Invoke
  manually with /anonymize-logs.
---

# Anonymize Logs

Sanitize customer-provided logs so they are safe to share or commit. Replace identity only; keep the original structure, delimiters, quoting, field order, and line breaks.

Input may be a file or a single syslog / KV / NDJSON line. Output must match that shape — do not pretty-print, wrap, truncate, or “fix” values as part of sanitization.

## What you provide

| Input | How to provide |
|-------|----------------|
| Log file(s) to sanitize | `@`-mention files or paste inline |
| Output location (optional) | free text path, defaults to same directory with `.sanitized` suffix |
| In-place override (optional) | say "in place" to overwrite the original |

## Golden rule — never reformat the content

**Only replace sensitive values. Do not touch anything else.**

Parsers and anyone reviewing the log depend on exact whitespace, delimiters, quoting, and line structure.

- **NDJSON** (one JSON object per line): do not pretty-print, re-indent, or restructure. Each line must remain a single compact JSON object on one line.
- **Syslog / CEF / key-value logs**: do not add or remove spaces, change quoting, or normalize field order.
- **Multiline logs**: preserve line grouping exactly.
- Replace only the *values* that identify real people, systems, or organizations — preserve field names, delimiters, structural tokens, and everything else character-for-character.
- Do **not** add, remove, or rewrite a syslog PRI / RFC5424 header. Do not prefix a bare line with `<134>` (or any PRI) “to look more like syslog.”
- **Truncation is never an anonymization strategy.** Do not delete repeating fields, drop trailing KV pairs, or cut off the remainder of a line to “finish” sanitization. Use the two-pass map instead.

## Workflow

### Step 1 — Two-pass replacement

Do not replace as you read. Distinct originals that collapse to one placeholder, or a first-occurrence-only replace that leaves later copies, are both failures.

1. Scan the whole file/line and build a map: `original value → placeholder` for every sensitive token (including nested ones: URL query params, hex dwords inside compound IDs, path segments).
2. If two originals differ, they **must** get different placeholders. If they are identical, they **must** get the same placeholder.
3. Apply the map globally (all occurrences).
4. Scan again for leftovers (IPs inside URLs, hex IPs inside vendor IDs, hostnames that look like product names).

Cover at minimum:

- **Authentication artifacts**: API keys, bearer tokens, passwords, OAuth tokens, base64-encoded credentials, private keys and certs (PEM blocks, SSH private keys), TLS/SSH fingerprints (JA3/JA4 hashes, SSH host key fingerprints, certificate fingerprints), DHCP fingerprints, partial secrets (`token_prefix`, `password_hash_prefix`, `hashed_token`) — partial exposure still identifies the credential
- **Personal identifiers**: email addresses (including CC/BCC lists, delegate/owner/creator email variants), usernames, display names, employee IDs, phone numbers, principal names (e.g. `user@tenant.onmicrosoft.com`), email subjects and body text
- **Organizational identifiers**: company names, tenant IDs (including `home_tenant_id`, `resource_tenant_id`, `aad_tenant_id` variants), account IDs, subscription IDs, billing account IDs, org slugs embedded in paths or JSON fields, org unit paths (e.g. `orgunit_path`, `org_unit_path`), department names and IDs, cost center IDs, Windows SIDs (Security Identifiers) in pipe names, task names, or registry paths
- **Infrastructure identifiers**: internal hostnames, FQDNs, private IP addresses, MAC addresses, internal URLs (staging/prod hostnames, internal tool domains), cloud resource IDs (ARNs, S3 bucket names, GCP project IDs, Azure subscription/resource names), Kubernetes cluster names, node names, pod names, and namespace names, container names and IDs, database hostnames and names (including `database.host`, `database.name`, `database_principal_name`), Windows domain topology fields (domain controller hostnames, NT domain names, `domain_controller_object_guid`, `domain_controller_object_sid`)
- **Device and hardware identifiers**: serial numbers, hardware UUIDs, machine IDs, device UUIDs, BIOS/firmware version strings that are unique to a specific device, including values in `device_id` / `serial` / similar fields
- **File system paths**: process command lines, file paths, registry key paths, and log file paths that embed usernames, org names, or internal system structure (e.g. `C:\Users\alice\`, `/home/bob/`, `HKLM\...\S-1-5-21-...`)
- **Connection strings**: database URIs, Redis URLs, any connection string that includes credentials or internal hostnames
- **Resource ownership**: owner email, creator email, last-modified-by identity, delegate user email, assignee email, impersonator fields — any field that names a specific person as the actor on a resource
- **Tracking identifiers**: session IDs, request/correlation IDs, transaction IDs, or any long opaque string tied to a real entity
- **Hash values**: replace when they could be derived from sensitive input (password hashes, HMAC secrets) — preserve file hashes (MD5, SHA1, SHA256 of file content) and other content-addressable references (git SHAs, TLS cert hashes used as identifiers)
- **Geographic specifics**: precise GPS coordinates, real street addresses — city and country names in geo enrichment fields are generally safe to keep. City/site tokens in inventory or topology fields (location hierarchies, hostname building codes) are identifiers — replace those.

Also cover nested and compound identifiers (below).

Apply placeholder conventions and shape rules (see below) as you go.

#### Nested and compound identifiers

These are commonly missed. Include them in the map, including tokens nested inside URLs, compound IDs, and path segments.

**IPv4 hidden in hex compound IDs.** Some vendor IDs look like `{0x00000001,0x1,0xcb007114,0x00000002}`. A hex dword may be an IPv4 address (try **both** endiannesses). If you replace `origin` / `src` / `dst` IPs, decode each dword as IPv4. If either decoding is a plausible public/private IP and does not match the already-substituted origin, replace that dword with the hex encoding of the **same** documentation IP you used for origin (keep `0x` + 8 hex digits). Keep the surrounding `{0x…,0x…}` shape; only the IP-bearing dword changes. Example: `0xcb007114` → `203.0.113.20` (big-endian); if origin was replaced with `198.51.100.10`, use `0xc633640a`.

**Topology-encoded hostnames.** Not a DNS name: `SW-BLDG-01`, `CHI-FW-01`, `DC1-VPN-MGMT`. In hostname / syslog-host / device-name fields, replace site/role/building codes. **Do not** replace vendor syslog **message IDs** like `%NAME-6-302018` — those are product mnemonics, not hostnames. Placeholder: `host-1.example.local` or `example-fw-01` matching original length class (short token vs FQDN).

**Policy / ACL / access-group names.** In policy, ACL, or access-group values, replace `\d{8,14}` date-like runs → `20240101000000` (same digit length); `vs\d+` → `vs01` (or drop vs/date suffix: `example-policy`); VLAN numbers in names → `vlan100`. Keep the token class (still looks like a policy name). Example: `vlan200-20240115103000` → `vlan100-20240101000000`.

**Interface names.** `ethN-MM.VLAN` → `eth1-01.100` (preserve `eth` + dotted subunit shape). `IF-<org>-…` / location words → `IF-Example` (keep an `IF-` prefix if present). Generic `inside` / `outside` / `lan` / `wan` **may stay** if they are interface **roles**, not site names. Prefer replacing when the token is a customer site or org.

**Windows / SMB paths with org units.** Replace directory components **above the last two levels** with generic segments (`example-department`, `E01`, `EXAMPLE-UNIT`). Keep depth, backslashes, and the final filename (`Thumbs.db`) if it is a generic OS file. Year folders like `\2026\` can stay (not identifying).

**Prefix-preserving opaque IDs.** SaaS and identity-platform IDs often have a short type prefix plus a long mixed-case suffix. Replace the **suffix**, **keep the prefix**. Same original → same placeholder. Also replace **base64 blobs in URL paths** with same-length synthetic base64. Replace real-looking app/role display names with generic equivalents (`Example Application Role Management`).

**Device serials and MDM IDs.** Long hex/alnum values in `device_id` / `serial` / `DeviceId` (and similar) → synthetic same charset/length (`SN000000000001`, `SEC123ABCDEFG45H`). Do not leave a real device or MDM serial.

**Identity-store names and group hierarchies.** `<NAME>-AD` / identity store → `EXAMPLE-AD`. Hash-delimited hierarchies: keep structural prefixes such as `Location#All Locations#` / `Device Type#All Device Types#`; replace the **leaf** if it is a real city/site (`Example-Site`). Real-looking store names even after username sanitization must still be replaced.

**IPs nested in URLs and query strings.** After replacing top-level `src_ip` / `dst_ip`, **scan URL query and path** for `ip=`, `src=`, `dst=`, and dotted quads. Use the same RFC 5737 IP already used for that host if it appeared elsewhere; else `198.51.100.10`. Do this even when the surrounding URL is malformed.

**OCSP / AIA / CRL certificate paths.** `http://ocsp.digicert.com/AAAAAAAAAAAAAAAAAAAAAAAAAAAA` — host may stay (public CA), **path is cert serial/issuer material**. If hostname matches `ocsp.` / `crl.` / `cacerts.` (public or not), replace the path with a **same-length** synthetic base64/hex string (zeros or `A`). Keep `/` count and charset class.

**JNDI / interpolation probes in usernames.** If a field contains `${jndi:` or `${lower:` or `${::-`, replace the **entire field value** with a synthetic username (`alice.johnson`, or `Lab1's User` if the original quoting/apostrophe should be preserved). Do not leave probe URLs. Preserve surrounding quoting.

**Public destination hostnames in customer telemetry.** Public hosts (`docs.google.com`, `api.github.com`) can stay when they are the **log-source vendor API**. In firewall, proxy, DNS, UTM, and content-filter events, destination hostnames and destination IPs are customer telemetry. Replace them even if they are well-known consumer sites (`youtube.com`) or public unicast IPs. Keep **product** hosts that are the log **source** vendor API (`api.github.com` in a GitHub audit log).

### Step 2 — Verify structure is intact

Confirm after sanitization:

- Line count is unchanged; do not drop trailing KV pairs
- Output length must be **≥ 70%** of input length unless the only change is replacing long tokens with same-shape placeholders (a 2k URL can shrink if you shorten a query, but **do not delete the rest of the syslog line**). If you would need to delete repeating fields to “finish” anonymization, you are doing it wrong — use the two-pass map instead
- Second leftover scan: URL `ip=` / `src=` / `dst=` / dotted quads, hex dwords inside compound IDs, host-like topology tokens, device serials, prefix-preserving opaque IDs
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
- Timestamps still match the original format (including timezone abbreviations — see What to preserve)
- Enum / status / action values that parsers or conditions branch on are untouched

## Placeholder conventions

Use consistent, realistic-looking replacements — not `REDACTED` strings, which break format-sensitive parsers.

| Type | Replacement |
|------|-------------|
| Email | `user@example.com`, `admin@example.org` |
| IPv4 | RFC 5737 ranges: `198.51.100.10`, `203.0.113.20`, `192.0.2.30` |
| IPv6 | `2001:db8::10` |
| Hostname / FQDN | `host-1.example.local`, `srv-web-01.example.internal` |
| Topology hostname | `host-1.example.local` |
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
| MDM / vendor-prefixed device ID | same charset and length (`SEC123ABCDEFG45H`) |
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
| Transaction / sequence / event-instance ID (numeric) | synthetic integer matching the original digit count — e.g. `48273915` → `10000002` |
| Session / request / correlation ID | same-length synthetic string (preserve length and charset), not a descriptive name |
| Hex dword in a compound ID | 8 hex digits, `0x` prefix; encode the same RFC 5737 IP used for `origin` / `src` |
| Policy / ACL with date | `example-policy`, `vlan100-20240101000000` |
| Interface `ethN-MM.VLAN` | `eth1-01.100` |
| Opaque ID with type prefix | keep prefix, synthetic suffix |
| Identity store | `EXAMPLE-AD` |
| Location hierarchy leaf | `Example-Site` |
| OCSP / CRL / AIA path | same-length `A`/`0` base64 |
| JNDI username | `alice.johnson` (preserve quotes) |

**Consistency rule**: map identical original values to identical placeholders throughout the file. If the same IP appears 10 times, it must become the same replacement IP all 10 times — so cross-event correlations remain testable. Build the full map first, then apply it globally. Distinct originals **must** get distinct placeholders — do not collapse 30 usernames into `alice.johnson`. Nested copies (the same IP in `src`, in a URL `ip=`, and in a hex compound ID) must all use that original’s placeholder.

## Shape rule — replacements must match the original format

Every replacement must have the same shape as the original value. Parsers and downstream processing depend on value format, not just field presence.

- **Numeric ID → numeric ID**: `/d/123/edit` → `/d/456/edit`, not `/d/example-document-id/edit`
- **Transaction / sequence / event-instance ID → same-shape number**: when the value is a per-event tracking identifier, mask it, preserving digit count. e.g. CEF `cn1=48273915 cn2=3061847` → `cn1=10000002 cn2=1000002`
- **UUID → UUID**: a real UUID must become a synthetic UUID of the same version, not a descriptive string
- **URL → URL**: replace only the sensitive segment (hostname, path ID, nested `ip=` / `src=` / `dst=`) — preserve the scheme, path structure, query string shape, **and any illegal characters**
  - `https://docs.google.com/drawings/d/123/edit` → `https://docs.google.com/drawings/d/000000000000/edit` (replace the ID, not the host — `docs.google.com` is a public service name, not an org identifier; this applies to **vendor API** logs)
  - `https://internal.corp.com/api/v1/resource` → `https://host-redacted.example.local/api/v1/resource` (replace the internal hostname, keep the path)
  - In firewall / proxy / UTM telemetry, also replace destination hosts and IPs (see What to preserve). Do **not** rewrite a malformed URL to `https://example.com/path` or `/some/api`
- **String ID → same-length or same-format string**: opaque alphanumeric IDs should become opaque alphanumeric placeholders of similar length, not descriptive names
- **Hostname in a URL vs. standalone hostname**: only replace hostnames that identify real internal infrastructure **or customer-visited destinations in firewall/proxy/UTM logs**. Public well-known hostnames (`docs.google.com`, `api.github.com`, `s3.amazonaws.com`) identify a service, not an organization, in **SaaS/vendor API logs** and do not need to be replaced there

**Malformed or garbage values must not be replaced.** If a value looks broken, synthetic, or contains no real identifying information (e.g. `http://1=Y +z\\`, `00/00/0000`, `N/A`, empty strings, placeholder-looking values), leave it exactly as-is. Replacing a malformed value with a well-formed placeholder changes the shape. You may still replace *embedded identity* inside a malformed token (real IP, hostname, user) as long as the malformation survives — extra quotes, unencoded `{` `}`, spaces in URLs, truncated fields, U+FFFD.

If you are unsure what shape to use, look at neighbouring values of the same field type in the same file and match their format.

## What to preserve

Do not replace:

- Protocol names, action verbs, event types, severity levels (`ALLOW`, `DENY`, `INFO`, `ERROR`)
- Product-defined event codes/type IDs, such as Windows event IDs — these describe event semantics, not customer-specific event instances
- Vendor syslog message IDs (`%NAME-6-302018`) — product mnemonics, not hostnames
- HTTP status codes, port numbers, numeric metric values (counts, sizes, durations)
- Field names and keys
- Timestamps (format and timezone must stay intact). **Do not** change timezone abbreviations, epoch values, or clock fields:
  - Do not change `Jun 27 14:06:33.189 JST` to `Jul 24 00:47:24.618 CET`
  - Do not offset or otherwise change epoch / Unix timestamps, even by a small amount. Leave numeric clock fields (eventtime, epoch millis, and similar) byte-for-byte unchanged.
  - Do not replace `JST`, `EDT`, `EST`, `Eastern`, `(GMT-3:00)Buenos Aires, Georgetown` with another zone. Date parsers key off the abbreviation; swapping JST→CET both breaks parse **and** still encodes a geography (the wrong one). Privacy for timezone abbreviations is out of scope — leave them as-is
- Structural tokens (brackets, braces, pipes, commas, tabs)
- Public well-known service hostnames in URLs (`docs.google.com`, `api.github.com`, etc.) when they are the **log-source vendor API** — replace the path ID if it is sensitive, not the host.
  In firewall, proxy, DNS, UTM, and content-filter events, destination hostnames and destination IPs are customer telemetry. Replace them even if they are well-known consumer sites (`youtube.com`) or public unicast IPs. Keep **product** hosts that are the log **source** vendor API (`api.github.com` in a GitHub audit log).
- File hashes (MD5, SHA1, SHA256 of file content) — these are content-addressable and safe; do not replace them
- User agent strings (`Mozilla/5.0 ...`) — these reveal browser/OS type but not identity; safe to keep
- City and country names in geo enrichment fields — replace only precise coordinates and street addresses
- Syslog PRI / RFC5424 headers — do not add, remove, or rewrite them
