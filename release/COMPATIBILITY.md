# VIENA NOC Tools — RELEASE compatibility floor

Compatibility floor: **RELEASE 1.3.24**.

Every future public RELEASE package must be installable by the updater shipped in 1.3.24.

## Immutable package contract

Allowed root files:

- manifest.json
- build.json
- background.js
- popup.html
- popup.js
- icon128.png
- integrity-manifest.json

Additional files are allowed only as `js/*.js`.

Do not add a new root-level HTML, JS, JSON or other file to a public package while 1.3.24 remains supported.

## Architecture rule

New updater/UI behavior must live in `js/*.js` or reuse an already allowed root file. In particular, future RELEASE packages must not depend on `updater.html` or `updater.js`.

## Publication gate

Before moving `version.json`:

1. Validate package with `python3 tools/validate_release_compat.py --package release/<candidate>.json`.
2. Validate the final pointer with `python3 tools/validate_release_compat.py --pointer`.
3. Verify update paths:
   - 1.3.24 -> candidate
   - 1.3.25 -> candidate
   - previous public RELEASE -> candidate
4. Verify storage is preserved.
5. Move `version.json` only after the package is already remote and verified.

If any compatibility check fails, the RELEASE must not be published.
