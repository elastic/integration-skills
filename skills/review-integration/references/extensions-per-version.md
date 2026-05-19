# Registered mito extensions per beats version

Which CEL extensions are registered in each beats release. A function is only available if its extension is registered AND the shipped mito version includes that function.

## Extension registration table

| First beats version | Extensions added | Cumulative set |
|-------------------|-----------------|----------------|
| v8.6.0 | Collections, Crypto, File, Globals, HTTP, JSON, Limit, MIME, Regexp\*, Time, Try | Collections, Crypto, File, Globals, HTTP, JSON, Limit, MIME, Regexp\*, Time, Try |
| v8.7.0 | Strings | + Strings |
| v8.9.0 | XML | + XML |
| v8.11.0 | Debug | + Debug |
| v8.18.0 / v9.0.0 | Printf | + Printf |
| v8.19.0 / v9.1.0 | AWS | + AWS |

Full set as of v9.3.0: AWS, Collections, Crypto, Debug, File, Globals, HTTP, JSON, Limit, MIME, Printf, Regexp\*, Strings, Time, Try, XML.

### Notes

- **Regexp** is conditional: only registered when the `regexp` config block is present in the integration config. If a CEL program uses `re_match`, `re_find`, etc., the integration must have a `regexp` config section.
- **Globals** provides variables (`now`, `useragent`, `env`, `remaining_executions`), not functions. It is always registered.
- **Coverage** and **Dump** appear in mito's extension list but are diagnostic/testing aids, not registered in the beats CEL input. Do not count them as available extensions.
- **Limit** registration changed at v9.3.0: registered via `LimitWithApply` instead of `Limit`, enabling in-evaluation rate limit updates. This is a behavioral change, not a new extension.

## Mito lib extensions by version

What exists in the mito library at each tagged version. This is distinct from what beats registers -- mito may define extensions that beats never registers.

| mito version | Extensions in lib |
|-------------|-------------------|
| v1.0.0 | Collections, Coverage, Crypto, Debug, Dump, File, Globals, HTTP, JSON, Limit, MIME, Regexp, Strings, Time, Try, XML |
| v1.4.0 | (no new extensions) |
| v1.5.0 | (no new extensions) |
| v1.6.0 | (no new extensions) |
| v1.7.0 | (no new extensions) |
| v1.9.0 | (no new extensions) |
| v1.10.0 | (no new extensions) |
| v1.13.1 | (no new extensions) |
| v1.15.0 | (no new extensions) |
| v1.16.0 | + Printf |
| v1.17.0 | (no new extensions) |
| v1.19.0 | (no new extensions) |
| v1.21.0 | + AWS |
| v1.22.0 | (no new extensions) |
| v1.23.0 | (no new extensions) |
| v1.24.0 | (no new extensions) |
| v1.25.0 | (no new extensions) |
| v1.25.1 | (no new extensions) |

The key distinction: mito v1.16.0 added Printf to the library, but beats did not register it until v8.18.0 / v9.0.0. Similarly, mito v1.21.0 added AWS, but beats did not register it until v8.19.0 / v9.1.0. Always check both the mito version (for function existence) and the beats version (for extension registration).
