# HTTPJSON review checklist

Severity-tagged checklist for reviewing `httpjson.yml.hbs` templates. Items are grouped by template section. Severity levels: **CRITICAL**, **HIGH**, **MEDIUM**, **LOW**.

## Structure

- [ ] `interval` uses Handlebars variable (`{{interval}}`) -- **HIGH**
- [ ] Request tracer path matches the input type name -- **MEDIUM**
- [ ] Request tracer uses correct format for target stack version (conditional vs block) -- **LOW**
- [ ] SSL/proxy/timeout blocks present when needed -- **LOW**

## Request

- [ ] URL uses Handlebars variable for base URL -- **MEDIUM**
- [ ] Headers configured correctly for the target API -- **MEDIUM**
- [ ] Query parameters match API documentation -- **HIGH**
- [ ] Date formats use Go reference time correctly (`2006-01-02T15:04:05Z`) -- **MEDIUM**
- [ ] `request.method` matches API requirements (GET vs POST) -- **HIGH**

## Response

- [ ] `response.split.target` points to the correct array field -- **HIGH**
- [ ] `ignore_empty_value: true` on split -- **MEDIUM**
- [ ] `keep_parent: true` present when nested splits need parent fields -- **MEDIUM**
- [ ] Map-type split used when response is an object, not an array -- **MEDIUM**

## Pagination

- [ ] Has termination condition (conditional evaluating to empty string when done) -- **CRITICAL**
- [ ] `fail_on_template_error: true` on all pagination set transforms with conditionals -- **HIGH**
- [ ] Time parameters preserved during pagination (not overwritten by pagination transforms) -- **HIGH**
- [ ] POST requests include `response.request_body_on_pagination: true` -- **HIGH**
- [ ] Offset/page math is correct (zero-index vs one-index) -- **MEDIUM**
- [ ] Pagination pattern matches API documentation -- **HIGH**

## Cursor

- [ ] Tracks the correct field from the API response -- **HIGH**
- [ ] `ignore_empty_value: true` on cursor entries -- **MEDIUM**
- [ ] Empty page scenario handled if API returns cursors with empty data arrays -- **MEDIUM**
- [ ] Initial value set via `default` on request transforms for first poll cycle -- **MEDIUM**
- [ ] First-page-only update used when appropriate (to avoid cursor advancing past data) -- **LOW**

## Authentication

- [ ] Auth method matches API documentation -- **HIGH**
- [ ] No hardcoded credentials in the template -- **CRITICAL**
- [ ] Mutual exclusion correct when multiple auth methods are supported -- **MEDIUM**
- [ ] OAuth2 scopes and endpoint params match API requirements -- **MEDIUM**
- [ ] Credential variables use `type: password` in manifest -- **HIGH**

## Common patterns

- [ ] `preserve_original_event` is conditional (`{{#if}}`) -- **MEDIUM**
- [ ] `forwarded` tag and `publisher_pipeline.disable_host` are coupled -- **MEDIUM**
- [ ] Custom processors passthrough at top level -- **LOW**
- [ ] All user-configurable values use Handlebars variables -- **HIGH**
