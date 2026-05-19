# CEL function reference

Functions available in the CEL input, organized by mito extension. Each extension must be registered in beats for its functions to be available. Functions present since mito v1.0.0 are unmarked; later additions show the first mito version.

## Extension availability

| First beats version   | Extensions registered                                                                      |
|-----------------------|--------------------------------------------------------------------------------------------|
| v8.6.0                | Collections, Crypto, File, Globals, HTTP, JSON, Limit, MIME, Regexp\*, Time, Try           |
| v8.7.0                | + Strings                                                                                  |
| v8.9.0                | + XML                                                                                      |
| v8.11.0               | + Debug                                                                                    |
| v8.18.0 / v9.0.0     | + Printf                                                                                   |
| v8.19.0 / v9.1.0     | + AWS                                                                                      |

Regexp is conditional on `regexp` config being present. Globals provides variables (`now`, `useragent`, `env`, `remaining_executions`) not functions. The `as` macro is from Collections.

Full set as of v9.3.0: AWS, Collections, Crypto, Debug, File, Globals, HTTP, JSON, Limit, MIME, Printf, Regexp\*, Strings, Time, Try, XML.

## Functions by extension

### AWS

Registered from v8.19.0 / v9.1.0. All functions added in mito v1.21.0.

| Function               | First mito version | Description                                                    |
|------------------------|---------------------|----------------------------------------------------------------|
| `sign_aws_from_env`    | v1.21.0             | Sign request using AWS environment credentials                 |
| `sign_aws_from_shared` | v1.21.0             | Sign using shared credentials file and profile                 |
| `sign_aws_from_static` | v1.21.0             | Sign using explicit access key, secret, optional session token |

### Collections

Registered from v8.6.0. Also registers the `as` macro.

| Function       | First mito version | Description                                  |
|----------------|---------------------|----------------------------------------------|
| `collate`      | v1.0.0              | Walk dot-separated paths, collect matches    |
| `drop`         | v1.0.0              | Copy with paths removed                      |
| `drop_empty`   | v1.0.0              | Recursively remove empty entries             |
| `flatten`      | v1.0.0              | Flatten nested list one level                |
| `max`          | v1.0.0              | Max of list or two values                    |
| `min`          | v1.0.0              | Min of list or two values                    |
| `with`         | v1.0.0              | Merge map, overwrite existing keys           |
| `with_replace` | v1.0.0              | Merge, only replace existing keys            |
| `with_update`  | v1.0.0              | Merge, only add new keys                     |
| `zip`          | v1.5.0              | Build map from two lists                     |
| `keys`         | v1.9.0              | List of map's keys                           |
| `values`       | v1.9.0              | List of map's values                         |
| `tail`         | v1.12.0             | Elements after first or after index          |
| `front`        | v1.17.0             | First n elements                             |
| `sum`          | v1.17.0             | Sum list of int or double                    |

### Crypto

Registered from v8.6.0.

| Function           | First mito version | Description                  |
|--------------------|---------------------|------------------------------|
| `base64`           | v1.0.0              | Base64 encode                |
| `base64_raw`       | v1.0.0              | Base64 encode (no padding)   |
| `hex`              | v1.0.0              | Hex encode                   |
| `hmac`             | v1.0.0              | HMAC digest                  |
| `sha1`             | v1.0.0              | SHA-1 hash                   |
| `sha256`           | v1.0.0              | SHA-256 hash                 |
| `uuid`             | v1.0.0              | Generate UUID                |
| `md5`              | v1.2.0              | MD5 hash                     |
| `base64_decode`    | v1.10.0             | Base64 decode                |
| `base64_raw_decode`| v1.10.0             | Base64 decode (no padding)   |
| `hex_decode`       | v1.19.0             | Hex decode                   |

### Debug

Registered from v8.11.0.

| Function | First mito version | Description                                       |
|----------|---------------------|---------------------------------------------------|
| `debug`  | v1.6.0              | Log tag and value, return value unchanged (non-strict) |

### File

Registered from v8.6.0.

| Function | First mito version | Description           |
|----------|---------------------|-----------------------|
| `dir`    | v1.0.0              | List directory entries |
| `file`   | v1.0.0              | Read file contents     |

### HTTP

Registered from v8.6.0. All functions added in v1.0.0.

| Function               | First mito version | Description                      |
|------------------------|---------------------|----------------------------------|
| `basic_authentication` | v1.0.0              | Encode basic auth header         |
| `do_request`           | v1.0.0              | Execute a prepared request       |
| `format_query`         | v1.0.0              | Encode query parameters          |
| `format_url`           | v1.0.0              | Build URL from components        |
| `get`                  | v1.0.0              | HTTP GET                         |
| `get_request`          | v1.0.0              | Build GET request without sending|
| `head`                 | v1.0.0              | HTTP HEAD                        |
| `parse_query`          | v1.0.0              | Parse query string               |
| `parse_url`            | v1.0.0              | Parse URL into components        |
| `post`                 | v1.0.0              | HTTP POST                        |
| `post_request`         | v1.0.0              | Build POST request without sending|
| `request`              | v1.0.0              | Build generic request            |

### JSON

Registered from v8.6.0.

| Function                              | First mito version | Description                                |
|---------------------------------------|---------------------|--------------------------------------------|
| `decode_json`                         | v1.0.0              | Decode JSON bytes to value                 |
| `decode_json_stream`                  | v1.0.0              | Decode newline-delimited JSON              |
| `encode_json`                         | v1.0.0              | Encode value to JSON bytes                 |
| `decode_json_string_numbers`          | v1.22.0             | Decode JSON, preserving number precision   |
| `decode_json_stream_string_numbers`   | v1.22.0             | Decode NDJSON, preserving number precision |

### Limit

Registered from v8.6.0.

| Function     | First mito version | Description                                                      |
|--------------|---------------------|------------------------------------------------------------------|
| `rate_limit` | v1.0.0              | Apply rate limiting. Two overloads: named policy, generic prefix |

Named policies: `"okta"`, `"draft"`.

**Behavior change at v9.3.0:** registered via `LimitWithApply` instead of `Limit`. The `apply` callback fires during evaluation, updating the HTTP client immediately. Before v9.3.0, the return map had to be placed in `state.rate_limit` and only took effect on the next evaluation cycle. From v9.3.0, rate limit changes take effect between requests within the same evaluation. Not back-ported to 8.19.

### MIME

Registered from v8.6.0.

| Function | First mito version | Description            |
|----------|---------------------|------------------------|
| `mime`   | v1.0.0              | Detect MIME type       |

### Printf

Registered from v8.18.0 / v9.0.0.

| Function  | First mito version | Description                      |
|-----------|---------------------|----------------------------------|
| `sprintf` | v1.16.0             | `fmt.Sprintf`-style formatting   |

### Regexp

Registered from v8.6.0. Conditional on `regexp` config being present. All functions use named precompiled patterns from the `regexp` config block.

| Function                 | First mito version | Description                    |
|--------------------------|---------------------|--------------------------------|
| `re_match`               | v1.0.0              | Test pattern match             |
| `re_find`                | v1.0.0              | First match                    |
| `re_find_all`            | v1.0.0              | All matches                    |
| `re_find_submatch`       | v1.0.0              | First match with subgroups     |
| `re_find_all_submatch`   | v1.0.0              | All matches with subgroups     |
| `re_replace_all`         | v1.0.0              | Replace all matches            |

### Strings

Registered from v8.7.0. All functions added in v1.0.0 except where noted.

| Function                      | First mito version | Description                        |
|-------------------------------|---------------------|------------------------------------|
| `compare`                     | v1.0.0              | Lexicographic string comparison    |
| `contains_any`               | v1.0.0              | Contains any chars from set        |
| `contains_substr`            | v1.0.0              | Contains substring                 |
| `count`                       | v1.0.0              | Count non-overlapping occurrences  |
| `equal_fold`                  | v1.0.0              | Case-insensitive equality          |
| `fields`                      | v1.0.0              | Split on whitespace                |
| `has_prefix`                  | v1.0.0              | Starts with prefix                 |
| `has_suffix`                  | v1.0.0              | Ends with suffix                   |
| `index`                       | v1.0.0              | Index of first occurrence          |
| `index_any`                   | v1.0.0              | Index of first char from set       |
| `join`                        | v1.0.0              | Join list with separator           |
| `last_index`                  | v1.0.0              | Index of last occurrence           |
| `last_index_any`             | v1.0.0              | Index of last char from set        |
| `repeat`                      | v1.0.0              | Repeat string n times              |
| `replace`                     | v1.0.0              | Replace first n occurrences        |
| `replace_all`                 | v1.0.0              | Replace all occurrences            |
| `split`                       | v1.0.0              | Split on separator                 |
| `split_after`                 | v1.0.0              | Split after separator              |
| `split_after_n`              | v1.0.0              | Split after separator, limit n     |
| `split_n`                     | v1.0.0              | Split on separator, limit n        |
| `substring`                   | v1.0.0              | Extract substring by index         |
| `to_lower`                    | v1.0.0              | Lowercase                          |
| `to_title`                    | v1.0.0              | Title case                         |
| `to_upper`                    | v1.0.0              | Uppercase                          |
| `to_valid_utf8`              | v1.0.0              | Replace invalid UTF-8              |
| `trim`                        | v1.0.0              | Trim chars from both ends          |
| `trim_left`                   | v1.0.0              | Trim chars from left               |
| `trim_prefix`                 | v1.0.0              | Remove prefix                      |
| `trim_right`                  | v1.0.0              | Trim chars from right              |
| `trim_space`                  | v1.0.0              | Trim whitespace                    |
| `trim_suffix`                 | v1.0.0              | Remove suffix                      |
| `valid_utf8`                  | v1.0.0              | Check valid UTF-8                  |
| `canonical_mime_header_key`  | v1.23.0             | Canonicalize MIME header key       |

### Time

Registered from v8.6.0.

| Function     | First mito version | Description                    |
|--------------|---------------------|--------------------------------|
| `format`     | v1.0.0              | Format timestamp as string     |
| `parse_time` | v1.0.0              | Parse string to timestamp      |
| `round`      | v1.20.0             | Round duration or timestamp    |
| `truncate`   | v1.24.0             | Truncate duration or timestamp |

**`now` global vs `now()` function:** The `now` global is a fixed value set once per evaluation by the beats input. The `now()` function calls `time.Now()` each invocation. Within a single evaluation the global is stable; the function is not. CEL programs should use the `now` global for consistency.

### Try

Registered from v8.6.0. Both functions are non-strict.

| Function   | First mito version | Description                          |
|------------|---------------------|--------------------------------------|
| `try`      | v1.0.0              | Evaluate expression, catch errors    |
| `is_error` | v1.0.0              | Test whether value is an error       |

### XML

Registered from v8.9.0.

| Function     | First mito version | Description                               |
|--------------|---------------------|-------------------------------------------|
| `decode_xml` | v1.0.0              | Decode XML. Optional XSD name for type hints |

## Determining minimum beats version

For quick lookups, check the extension availability table above and the per-function mito version annotations. For systematic version verification during formal reviews, use the `review-integration` skill which has the full beats-to-mito mapping table and the step-by-step verification procedure in its references.
