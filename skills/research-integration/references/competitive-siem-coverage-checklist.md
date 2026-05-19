# Competitive SIEM Coverage Checklist

Use this checklist for **Research Track E** on every research run, regardless of the product's collection method. The goal is to determine whether IBM QRadar, Splunk, and Sumo Logic already have an integration or app for the product being researched, and to document what each covers and how it collects data.

This analysis feeds section 1.5 of the research brief and the detailed `references/competitive-siem-coverage.md` file.

---

## Competitor catalog search strategy

For each competitor below, search its official app/integration marketplace using the product name, vendor name, and common aliases. Use these as your primary starting points — do not rely on general web searches unless the catalog search is inconclusive.

| Competitor | Catalog URL | Notes |
|-----------|-------------|-------|
| IBM QRadar | `https://www.ibm.com/products/qradar-siem/integrations` | Also check IBM X-Force Exchange and DSM (Device Support Module) listings |
| Splunk | `https://splunkbase.splunk.com/apps` | Filter by the product/vendor name; check "Technology Add-ons" (TAs) specifically |
| Sumo Logic | `https://www.sumologic.com/help/docs/integrations/` | Also check the in-product App Catalog documentation |

### Search terms to try per competitor

- [ ] Exact product name (e.g., "Okta", "CrowdStrike Falcon")
- [ ] Vendor name alone (e.g., "Palo Alto", "Fortinet")
- [ ] Common product abbreviations or aliases (e.g., "CS Falcon", "PA Firewall")
- [ ] Technology category (e.g., "endpoint detection", "firewall", "identity provider") — useful when no direct product match is found
- [ ] Note whether a result is an exact match, a partial match (covers some features), or a near-miss (different product from same vendor)

---

## Per-competitor investigation items

For each competitor (IBM QRadar, Splunk, Sumo Logic), capture the following if an integration/app is found:

### Integration identity

- [ ] **Integration / app name:** exact name as listed in the catalog
- [ ] **Publisher / maintainer:** vendor-maintained, Splunk-built, IBM-built, or community/partner
- [ ] **Catalog page URL:** direct link to the listing
- [ ] **Version:** latest version number (if shown)
- [ ] **Last updated date:** indicates how actively maintained the integration is
- [ ] **Compatibility notes:** which SIEM platform versions are supported

### Data coverage

- [ ] **Supported data sources:** which log sources, event types, or API endpoints are covered
  - Be specific: "firewall traffic logs, threat prevention logs, URL filtering logs" not just "all logs"
- [ ] **Event types / log types listed:** enumerate them if the listing provides a breakdown
- [ ] **Coverage gaps:** which product data sources are NOT covered (if discoverable from the listing)
- [ ] **Known limitations:** data volume caps, filtering restrictions, unsupported event types

### Collection method

- [ ] **Collection mechanism:** how does the competitor collect data from the product?
  - API pull (REST, GraphQL, vendor SDK)
  - Syslog push (UDP/TCP, RFC 3164/5424, CEF, LEEF)
  - Agent/forwarder (Splunk Universal Forwarder, IBM WinCollect, etc.)
  - File-based / log shipping
  - Cloud delivery (S3, Event Hub, Pub/Sub)
  - Vendor-native forwarding (product pushes directly to SIEM)
- [ ] **Protocol / format details:** CEF, LEEF, JSON, key-value — note the wire format if documented
- [ ] **Authentication method:** how the SIEM authenticates to the product (if API-based)
- [ ] **Configuration requirements:** what the user must set up on both sides

### Quality signals

- [ ] **User ratings / reviews:** note star rating and review count if visible (Splunkbase shows these)
- [ ] **Downloads / installs:** popularity indicator (Splunkbase shows download counts)
- [ ] **Support tier:** Splunk-supported, vendor-supported, community-supported, or unsupported/archived
- [ ] **Documentation quality:** does the listing link to meaningful setup documentation?

---

## Comparison layer

After gathering per-competitor data, assess the overall competitive landscape:

- [ ] **Coverage breadth:** which competitor covers the most data sources / event types?
- [ ] **Collection method alignment:** is the predominant collection method the same across competitors, or do they differ? Does this align with or differ from the recommended Elastic collection method?
- [ ] **Maintenance status:** are the integrations actively maintained or stale?
- [ ] **Gaps Elastic could address:** data sources or event types none of the competitors cover, or cover poorly
- [ ] **Differentiators:** areas where Elastic's approach (e.g., ECS normalization, Elastic Agent, Fleet management) could provide a better experience than the competitive offerings

---

## Quality standards

- Only record integrations you have confirmed exist in the catalog. Do not infer or assume based on the vendor's general reputation.
- If no integration is found for a competitor, record that explicitly as "No integration found" — do not omit the competitor from the output.
- Mark any detail that could not be confirmed from the catalog listing or its linked documentation with `[UNVERIFIED]`.
- Prefer official marketplace/catalog pages over blog posts, press releases, or third-party reviews.
- If a catalog listing is ambiguous (e.g., covers multiple products under one app), note the ambiguity rather than claiming full coverage.

---

## Output

Write findings to `references/competitive-siem-coverage.md` in the working directory. Structure the file as:

1. **Summary table** — one row per competitor (used verbatim in research brief section 1.5)
2. **Per-competitor H2 sections** — full detail for each of IBM QRadar, Splunk, and Sumo Logic
3. **Comparison notes** — gaps, differentiators, and overall landscape assessment

Return a concise summary inline with: which competitors have integrations, the dominant collection method found, and the path to the written file.
