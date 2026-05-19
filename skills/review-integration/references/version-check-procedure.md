# Version compatibility check procedure

Systematic procedure for verifying that every CEL function and config option used in a PR is compatible with the integration's declared minimum beats version.

## For CEL functions

For each CEL function used in the program:

1. **List all CEL functions the program uses.** Read the `program` block in `cel.yml.hbs` and identify every function call.

2. **Look up each function in the per-extension tables** (in `cel-function-reference.md` or the tables in this skill) to find the first mito version that includes it.

3. **Check the extension is registered at the target beats version.** Use `extensions-per-version.md` to verify the function's extension is registered at the declared minimum. If the extension was added later (e.g., AWS at v8.19.0), that becomes a version floor.

4. **Find the first beats release that ships mito >= the required version.** Use `beats-mito-version-matrix.md`. Scan the table for the earliest beats release whose mito column is >= the required mito version.

5. **Verify `conditions.kibana.version` allows that beats version.** The version constraint in the root `manifest.yml` must permit the beats version found in step 4. If the constraint excludes it, the function is not available at the declared minimum and this is a compatibility error.

Take the maximum across all functions. That is the true minimum beats version.

## For config options

1. **List all config options the integration uses.** Check top-level options, `resource.*` options, and `auth.*` options.

2. **Find the latest "First beats version" row** in `config-options-by-version.md` among all options used.

3. **Verify `conditions.kibana.version` allows that version.** Same check as step 5 above.

## Combined minimum

The integration's true minimum beats version is the maximum of:
- The function-derived minimum (from the CEL functions procedure)
- The config-derived minimum (from the config options procedure)

If the declared `conditions.kibana.version` is lower than this combined minimum, flag it.

## Worked example

Program using `sign_aws_from_static` and `truncate`:

**Step 1 -- List functions:**
- `sign_aws_from_static` (AWS extension)
- `truncate` (Time extension)

**Step 2 -- Look up mito versions:**
- `sign_aws_from_static`: first mito version is v1.21.0
- `truncate`: first mito version is v1.24.0

**Step 3 -- Check extension registration:**
- AWS extension: registered from v8.19.0 / v9.1.0
- Time extension: registered from v8.6.0

**Step 4 -- Find first beats with required mito:**
- `sign_aws_from_static` needs mito >= v1.21.0. From the matrix: v8.19.0 ships v1.22.0 (>= v1.21.0). First qualifying: v8.19.0.
- `truncate` needs mito >= v1.24.0. From the matrix: v9.3.0 ships v1.24.0. First qualifying: v9.3.0.

**Step 5 -- Maximum across all functions:** v9.3.0

**Verification:** If the manifest says `conditions.kibana.version: "^8.19.0 || ^9.1.0"`:
- FAIL. Neither `^8.19.0` (mito v1.22.0 < v1.24.0) nor `^9.1.0` (mito v1.22.0 < v1.24.0) includes v9.3.0.
- Correct constraint: `^9.3.0`
- Review comment: "`truncate` (Time extension) requires mito v1.24.0, first available in v9.3.0. Current constraint `^8.19.0 || ^9.1.0` does not include v9.3.0. Update to `^9.3.0`."
