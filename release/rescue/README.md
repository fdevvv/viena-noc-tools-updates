# Legacy 1.3.25 rescue

This directory contains the one-time migration path for the two historical public
RELEASE 1.3.25 contracts that cannot be moved safely through the normal static
update pointer.

## Why a rescue is required

Both historical variants report:

- version: `1.3.25`
- build: `1.3.25-release`
- channel: `RELEASE`
- RELEASE update pointer: `version.json`

But their updater contracts forked:

- `release/v1.3.25-package.json` requires `updater.html` and `updater.js` in a FULL package.
- `release/v1.3.25-bridge-1.3.24-v2-package.json` uses the portable root set, but its RELEASE runtime decides availability by semantic version only.

The permanent public bootstrap is also version 1.3.25. Therefore bridge-v2 does not
offer the bootstrap as an update, while the older 1.3.25 updater rejects the
portable bootstrap package. Moving `version.json` to a special package would
also expose that package to 1.3.24 and would break the frozen 1.3.24 bootstrap
route.

The audited source fingerprints, frozen public bootstrap base, and rescue-only target bootstrap are declared in:

`release/rescue/legacy-1.3.25.json`

## Rescue behavior

`rescue-legacy-1.3.25.ps1`:

1. verifies source version/build/channel;
2. verifies `js/95-local-updater.js` against one of the two audited historical SHA-256 fingerprints;
3. downloads the immutable rescue bootstrap v5 package derived from public bootstrap-v3, or accepts `-PackagePath` only for controlled CI/integration testing;
4. validates package SHA, schema/app identity, mode, paths, sizes, per-file SHA and integrity inventory;
5. verifies updater contract >= 2, compatibility floor 1.3.24 and `release/latest.json` as the next channel;
6. creates a full sibling backup of the installation directory;
7. writes non-identity files first and `manifest.json`, `integrity-manifest.json`, `build.json` last;
8. verifies every written file and the final identity;
9. restores the backup on a caught write/verification failure.
10. verifies the popup channel label is dynamic so RELEASE cannot render as DEV;
11. verifies runtime/content-script build identity is coherent, preventing permanent false `TAB` states;
12. is stored with a UTF-8 BOM so the downloaded script parses correctly in Windows PowerShell 5.1.

The script does not clear or migrate Chrome storage. The same unpacked extension
folder is preserved, so the extension ID/storage association remains intact.

Normal use:

```powershell
pwsh -NoProfile -File .\release\rescue\rescue-legacy-1.3.25.ps1 -InstallPath "C:\ruta\a\VIENA NOC Tools"
```

After `RESCATE OK`, reload the unpacked extension from `chrome://extensions`.
The installed build becomes `1.3.25-bootstrap-release-v5-runtime-coherence-fix`; all later RELEASE
checks use `release/latest.json`.

## CI and promotion gate

Run:

```bash
python3 tools/validate_legacy_rescue.py
python3 tools/test_legacy_rescue.py --require-pwsh
```

A modern RELEASE promotion must additionally pass:

```bash
python3 tools/validate_legacy_rescue.py --require-retired
```

The two historical contracts remain `quarantine: true` in
`release/public-history.json` until the installation registry confirms that
all active legacy 1.3.25 installations have been remediated. Only then should
that quarantine flag be retired. Do not disable the gate merely to publish.


## Repair for installations that already received rescue v4

The first real v4 rescue exposed a build-identity mismatch: the extension runtime
reported `1.3.25-bootstrap-release-v4-channel-fix`, while
`js/90-runtime-status.js` and `js/80-update-banner.js` still reported the
public bootstrap-v3 build. That makes every open operational tab look permanently
stale even after reload.

Already-migrated v4 installations must not rerun the legacy rescue script.
Use the audited one-time repair:

`release/rescue/repair-bootstrap-v4-to-v5.ps1`

Contract:

`release/rescue/bootstrap-v4-to-v5.json`

The repair verifies the complete v4 installation against the audited v4
integrity manifest, verifies the immutable v5 package, creates a sibling backup,
writes identity files last, verifies the final target, and rolls back on failure.
It preserves Chrome storage and the unpacked installation directory.
