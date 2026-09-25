# VIENA NOC Tools — UPDATE SAFETY CONTRACT

> **PERMANENT PROJECT RULE**
>
> This document is part of the project handoff/context. It must be considered in every future DEV/RELEASE modification and included in every complete project handoff.
>
> Compatibility floor: **RELEASE 1.3.24**.

## Objective

A user on any supported public RELEASE from 1.3.24 onward must be able to reach a future RELEASE without encountering a package-format/updater incompatibility. Update failures must fail closed before destructive writes whenever possible, and failed writes must be recoverable.

No RELEASE pointer is published merely because the candidate itself is valid. The exact updater code already installed by supported old versions must be proven able to consume the candidate.

## 1. Immutable compatibility floor

Every public RELEASE package must be accepted by the updater shipped in RELEASE 1.3.24.

Portable package paths are restricted to:

Root:
- manifest.json
- build.json
- background.js
- popup.html
- popup.js
- icon128.png
- integrity-manifest.json

Additional code:
- js/*.js

A public package must not depend on a new root-level file while 1.3.24 remains supported.

## 2. Updater-contract monotonicity

A new public updater may become more permissive, but it must **never become more restrictive than the compatibility floor**.

In particular:
- it must not add new mandatory package files;
- it must not require updater.html, updater.js or any other new root artifact;
- it must continue accepting all paths required by the 1.3.24 contract;
- optional future capabilities must live under js/*.js or reuse existing allowed root files;
- RELEASE packages themselves continue using only the compatibility-floor portable subset even if a newer updater could accept more.

This rule prevents a newer installed updater from blocking a future package that still has to be consumable by 1.3.24.

## 3. Direct-skip requirement

Before a RELEASE is published, the candidate must be validated using the **actual historical updater validator** from every supported public updater contract.

At minimum:
- 1.3.24 -> candidate
- 1.3.25 -> candidate, for every updater-contract variant that may actually be installed
- previous public RELEASE -> candidate
- every other still-supported public RELEASE -> candidate

A user must not need to install every intermediate release unless an explicitly documented one-time migration is unavoidable.

## 4. DEV reachability requirement

DEV has the same rule.

Before moving dev/self-update.json, validate:
- currently published DEV build -> candidate DEV
- any known DEV bootstrap contract that is still installed -> candidate DEV

Never publish a DEV package that the previous DEV updater cannot parse. A DEV pointer is not valid merely because the new package is internally correct.

## 5. Immutable artifacts

Public RELEASE packages are immutable.

Rules:
- never overwrite a package already referenced by a public pointer;
- create a new uniquely named artifact;
- calculate its SHA-256;
- verify the remote bytes;
- only then change version.json.

DEV builds also use immutable per-build snapshots under dev/builds/. The DEV pointer is separate from the artifact.

## 6. Package validation

Before any pointer move validate:
- schema/app identity;
- target version/build/channel;
- mode;
- allowed paths;
- no traversal/absolute/backslash paths;
- no duplicate paths;
- required files;
- Base64 validity;
- declared size for every file;
- SHA-256 for every file;
- manifest JSON validity and version;
- build.json identity;
- integrity-manifest identity;
- complete integrity inventory;
- no integrity references to absent files;
- no unexpected remove list in RELEASE;
- no RELEASE text patches;
- no stale BUILD_ID values;
- JavaScript syntax for every .js file;
- required manifest structure;
- no unexpected permission/host-permission expansion without explicit review.

## 7. Pointer/package validation

version.json is the final commit in the publication sequence.

Validate:
- latest is the intended version;
- package_url points to the already-existing immutable artifact;
- remote package SHA-256 equals package_sha256;
- package version/build/channel match the publication target;
- no stale download_url fallback points to an older build;
- minimum/mandatory values are intentional.

Never move the pointer before the package exists and is remotely verified.

## 8. Actual historical-updater test

Static similarity is not sufficient.

CI/prepublication tests must execute or faithfully emulate the validatePackage logic shipped inside the historical updater package against the candidate.

This is specifically intended to catch:
- new required files;
- newly rejected paths;
- package mode changes;
- channel assumptions;
- schema changes;
- integrity-rule changes.

## 9. Adversarial tests

The release gate must reject simulations of:
- wrong package SHA;
- wrong per-file SHA;
- wrong file size;
- corrupted/truncated JSON;
- invalid Base64;
- missing required file;
- duplicate file;
- unauthorized root path;
- path traversal;
- incorrect channel;
- incorrect version/build;
- manifest mismatch;
- build.json mismatch;
- integrity mismatch;
- incomplete integrity inventory;
- package not yet present remotely;
- stale pointer;
- downgrade attempt;
- unexpected remove operation;
- invalid JS syntax.

## 10. Write safety and rollback

Updater behavior must preserve:
- validation before first write;
- backup of files that will be touched;
- delayed identity files, especially build.json, until the payload is written;
- post-write SHA verification;
- final full-inventory verification;
- rollback on caught write/verification error.

Future updater versions should additionally use a persistent update journal/recovery marker so a browser/OS/power interruption can be detected and repaired on the next run.

Important limitation: the updater already installed in 1.3.24 cannot be retroactively changed. Its first jump is protected by the strict portable package contract and full-package retryability; stronger crash-recovery behavior applies after a newer updater has been installed.

## 11. Storage preservation

Updates must not clear or rename established persistent data without an explicit migration:
- chrome.storage.local
- installation ID
- VIENA user metadata
- personal templates
- template overrides
- learned/contextual reasons
- installation registry state
- local updater folder metadata

No chrome.storage.local.clear() or equivalent destructive reset is permitted in an ordinary update.

## 12. Folder/channel/version safety

Before writing:
- selected folder must be a valid VIENA NOC Tools installation;
- folder identity must match the running extension;
- DEV cannot overwrite RELEASE;
- RELEASE cannot overwrite DEV;
- accidental downgrade is blocked;
- target version/build/channel must match the announced package;
- permission loss must abort before writing.

## 13. Concurrency/network/cache

Updater must:
- prevent concurrent install operations;
- disable repeated update actions while applying;
- use HTTPS only;
- use no-store/cache-busting for pointer/package reads;
- use timeouts;
- treat HTTP/network errors as non-destructive failures;
- never continue from an unverifiable partial download.

## 14. Post-update health

After writing:
- verify every target hash;
- verify final version/build/channel;
- verify integrity-manifest;
- keep UI in “Aplicando actualización…” until the runtime transition is complete;
- verify the new runtime reports the expected build after reload.

Installation registry should record update success/failure reason and updater-contract/build information where possible, without collecting operational ticket content.

## 15. Publication order

Mandatory order:

1. Finish DEV candidate.
2. Validate candidate internally.
3. Validate previous DEV -> candidate DEV.
4. User tests DEV.
5. Build a new immutable RELEASE artifact from the approved DEV source.
6. Run compatibility matrix from every supported public updater contract.
7. Run adversarial tests.
8. Run JS/integrity/manifest/BUILD_ID checks.
9. Verify remote artifact SHA.
10. Only then move version.json.
11. Verify version.json remotely.
12. Test at least one real Chrome update from the compatibility floor or oldest active version before considering publication closed.

## 16. Failure rule

If any test is uncertain, incomplete or fails:
- do not publish the RELEASE;
- do not move the pointer;
- do not “try it on users”;
- fix DEV/candidate first.

## 17. Context / handoff rule

Every complete VIENA NOC Tools handoff must preserve this update-safety contract, including:
- compatibility floor 1.3.24;
- direct-skip requirement;
- updater-contract monotonicity;
- immutable artifacts;
- historical-updater matrix;
- adversarial tests;
- storage preservation;
- rollback/recovery requirements;
- package-before-pointer ordering;
- DEV previous-build reachability test.

This section is permanent unless Emanuel explicitly changes the support floor or publication policy.
