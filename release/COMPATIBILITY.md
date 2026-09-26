# VIENA NOC Tools — RELEASE compatibility

Compatibility floor: **RELEASE 1.3.24**.

## Permanent architecture

There are two different RELEASE pointers and they have different jobs:

- `version.json` is the frozen legacy bootstrap pointer.
- `release/bootstrap.json` defines the immutable bootstrap package.
- RELEASE 1.3.24 must always install `1.3.25-bootstrap-release-v3` first.
- the bootstrap runtime then reads `release/latest.json`.
- `release/latest.json` is the only pointer that advances for normal modern RELEASE publication.

Do **not** move `version.json` to publish a new RELEASE.

## Portable RELEASE package contract

Modern RELEASE artifacts remain on the portable root subset so the permanent
bootstrap/updater contract stays monotonic.

Allowed root files:

- manifest.json
- build.json
- background.js
- popup.html
- popup.js
- icon128.png
- integrity-manifest.json

Additional files are allowed only as `js/*.js`.

Do not make `updater.html`, `updater.js` or any new root artifact mandatory.
New updater/UI behavior must live under `js/*.js` or reuse an existing allowed
root file.

## Historical 1.3.25 fork

Two historical packages report the same public identity
`1.3.25 / 1.3.25-release / RELEASE`, but they do not share one automatic
upgrade path:

- `release/v1.3.25-package.json`: its updater requires
  `updater.html` and `updater.js` in a FULL package.
- `release/v1.3.25-bridge-1.3.24-v2-package.json`: its updater accepts the
  portable bootstrap, but the runtime still reads `version.json` and RELEASE
  availability is based on semantic version. Because the bootstrap is also
  version 1.3.25, the runtime does not offer that same-version build transition.

A static `version.json` cannot serve a special legacy package without also
serving it to 1.3.24. Therefore the historical 1.3.25 fork is remediated once
through the audited rescue profile:

`release/rescue/legacy-1.3.25.json`

and script:

`release/rescue/rescue-legacy-1.3.25.ps1`

After rescue, the installed build is `1.3.25-bootstrap-release-v5-runtime-coherence-fix` and all
subsequent RELEASE updates use `release/latest.json`.

## Required reachability matrix

Before any modern RELEASE publication, prove:

1. `1.3.24 -> bootstrap-v3` with the exact 1.3.24 updater.
2. each historical `1.3.25-release` contract -> audited rescue -> bootstrap-v3.
3. `bootstrap-v3 -> candidate` with the exact bootstrap updater.
4. every other supported modern updater -> candidate.
5. previous modern RELEASE -> candidate.

Historical source contracts must be tested as they actually shipped. Do not
replace them with a reconstructed or "equivalent" validator.

## Publication gate

The standard path is `.github/workflows/promote-release.yml`.

Before `release/latest.json` can move, the workflow must:

1. require explicit `PROMOTE` authorization;
2. stage the candidate modern pointer;
3. validate frozen `version.json -> bootstrap`;
4. validate the legacy 1.3.25 rescue contract and PowerShell integration;
5. require all active legacy 1.3.25 quarantine installations to be remediated;
6. validate the candidate package and pointer;
7. run adversarial validation;
8. run the historical updater/rescue matrix;
9. run update-safety, JS and destructive-storage checks;
10. verify the immutable artifact already exists remotely with the same SHA;
11. only then commit/push `release/latest.json`.

The two historical 1.3.25 entries remain `quarantine: true` in
`release/public-history.json` until registry evidence confirms they have been
remediated. Do not clear that flag merely to unblock a publication.

If any compatibility/rescue test is uncertain or fails, do not publish.
