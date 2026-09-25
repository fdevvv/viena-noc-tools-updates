# VIENA NOC Tools — UPDATE SAFETY CONTRACT

> **PERMANENT PROJECT RULE**
>
> This document is part of the project handoff/context. It must be considered in every future DEV/RELEASE modification and included in every complete project handoff.
>
> Compatibility floor: **RELEASE 1.3.24**.

## Objective

A user on any supported public RELEASE from 1.3.24 onward must be able to reach a future RELEASE without encountering a package-format/updater incompatibility. Update failures must fail closed before destructive writes whenever possible, and failed writes must be recoverable.

No RELEASE pointer is published merely because the candidate itself is valid. The exact updater code already installed by supported old versions must be proven able to consume the candidate.

## 1. Immutable compatibility floor and permanent bootstrap

RELEASE 1.3.24 is the legacy compatibility floor.

Because the historical 1.3.24 updater rejects updater.html/updater.js while an old 1.3.25 updater variant requires them, a single future FULL package cannot satisfy both contracts simultaneously.

Therefore the permanent architecture is:

- version.json is frozen as the **legacy bootstrap pointer**.
- release/bootstrap.json defines that bootstrap.
- 1.3.24 always upgrades first to the validated bootstrap build 1.3.25-bootstrap-release-v3.
- the bootstrap runtime no longer reads version.json for RELEASE updates; it reads release/latest.json.
- release/latest.json is the only pointer that advances for modern RELEASE versions.
- a user returning on 1.3.24 months later must still be able to install the frozen bootstrap and then continue to the current modern release without touching every intermediate version.

The bootstrap package itself must always be accepted by the updater shipped in RELEASE 1.3.24.

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

## 3. Reachability / skip requirement

Before a modern RELEASE is published, the candidate must be validated using the **actual historical updater validator** from every supported modern updater contract.

The required paths are:

- 1.3.24 -> frozen bootstrap (tested independently and permanently);
- bootstrap -> candidate modern RELEASE;
- previous public modern RELEASE -> candidate;
- every other still-supported modern RELEASE updater contract -> candidate.

Users do not need to install every intermediate modern release. The only permanent staged hop is the legacy 1.3.24 -> bootstrap transition required by the historical contract fork.

Historical 1.3.25-release variants that predate the bootstrap architecture are quarantine contracts. A future modern promotion must remain blocked until all active quarantine installations are remediated or explicitly retired from support with evidence.

## 4. DEV reachability requirement

DEV has the same rule, with **DEV fix13 as the current compatibility floor**.

The fix13 updater requires these root files in a FULL DEV package:
- manifest.json
- build.json
- background.js
- popup.html
- popup.js
- icon128.png
- integrity-manifest.json
- updater.html
- updater.js

Therefore, while fix13 remains a supported possible installed DEV build, future DEV packages must continue carrying updater.html and updater.js as compatibility artifacts even though the new runtime no longer depends on them.

Before moving dev/self-update.json, validate:
- DEV fix13 updater -> candidate DEV;
- currently published DEV build -> candidate DEV;
- every other known DEV updater contract that may still be installed -> candidate DEV.

Never publish a DEV package that an older supported DEV updater cannot parse. A DEV pointer is not valid merely because the new package is internally correct.

## 5. Immutable artifacts

Public RELEASE packages are immutable.

Rules:
- never overwrite a package already referenced by a public pointer;
- create a new uniquely named artifact;
- calculate its SHA-256;
- verify the remote bytes;
- only then change the appropriate pointer.
- version.json is not a normal release pointer anymore and must remain frozen to release/bootstrap.json.
- modern releases advance only release/latest.json.

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

There are two different RELEASE pointers and they must never be conflated.

### Legacy bootstrap pointer

version.json is a frozen mirror of release/bootstrap.json. CI must fail if they diverge. If an invalid version.json change is pushed, the bootstrap pointer guard restores the previous value automatically.

### Modern pointer

release/latest.json is the only pointer that advances for normal RELEASE publication.

Validate:
- latest is the intended version;
- package_url points to an already-existing immutable artifact;
- remote package SHA-256 equals package_sha256;
- package version/build/channel match the publication target;
- no stale download_url fallback points to an older build;
- minimum/mandatory values are intentional;
- source_package/promotion metadata are coherent when produced by the promotion workflow.

Never move release/latest.json before the package exists and is remotely verified.

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

Updater contract v2 uses a persistent update journal, an exclusive update lock, retry/recovery state, verified rollback, and a post-reload health check. These mechanisms are mandatory for modern DEV/RELEASE packages and are regression-tested in CI.

A browser/OS/power interruption must leave enough durable state to detect the interrupted operation. A FULL immutable package may then be safely re-applied to finish recovery. If rollback is attempted after a caught write failure, the rollback itself is verified.

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
- prevent concurrent install operations with both Web Locks (when available) and a persistent stale-safe lock;
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

Update status is stored locally with technical-only success/failure state, target build and updater contract. The installation registry already reports build identity, which distinguishes the modern bootstrap build from historical 1.3.25-release variants. Additional remote telemetry must not be added unless the registry endpoint schema is verified first, and must never include operational ticket content.

## 15. Publication order

Mandatory order:

1. Finish DEV candidate.
2. Validate candidate internally.
3. Validate DEV fix13/current supported DEV contracts -> candidate DEV.
4. User tests DEV.
5. Build a new immutable RELEASE artifact from the approved DEV source.
6. Never overwrite an existing RELEASE artifact.
7. Stage release/latest.json locally/in CI through the manual promotion workflow.
8. Validate frozen version.json -> bootstrap and exact 1.3.24 -> bootstrap.
9. Run the modern historical-updater matrix against the staged candidate.
10. Run adversarial tests.
11. Run JS/integrity/manifest/BUILD_ID/update-safety checks.
12. Verify the remote immutable artifact SHA.
13. Only if every gate is green, commit release/latest.json.
14. Verify release/latest.json remotely.
15. Test at least one real Chrome update through the oldest relevant route before considering publication closed.

The workflow .github/workflows/promote-release.yml is the standard promotion path. Direct manual edits of release/latest.json are not an accepted publication process.

## 16. Failure rule

If any test is uncertain, incomplete or fails:
- do not publish the RELEASE;
- do not move the pointer;
- do not “try it on users”;
- fix DEV/candidate first.

## 17. Context / handoff rule

Every complete VIENA NOC Tools handoff must preserve this update-safety contract, including:
- compatibility floor 1.3.24;
- frozen legacy bootstrap architecture;
- modern release/latest.json channel;
- staged reachability/skip requirement;
- updater-contract monotonicity;
- immutable artifacts;
- historical-updater matrix;
- adversarial tests;
- storage preservation;
- rollback/recovery requirements;
- package-before-pointer ordering;
- DEV previous-build reachability test.

This section is permanent unless Emanuel explicitly changes the support floor or publication policy.

## 18. Pointer self-healing and publication authorization

The repository includes:
- a modern pointer guard that automatically restores the previous release/latest.json if a pushed pointer fails the safety matrix;
- a legacy bootstrap pointer guard that restores version.json if it no longer mirrors release/bootstrap.json;
- a manual workflow_dispatch promotion workflow requiring an explicit PROMOTE confirmation.

The GitHub connection used by ChatGPT currently has no administration permission to configure branch protection/rulesets. Repository-level required-status-check enforcement should be enabled manually in GitHub if administrative hard blocking is desired. Until then, the transactional promotion workflow plus automatic pointer rollback are the fail-safe controls.

## 19. Historical 1.3.25 quarantine

The historical build 1.3.25-release may use an updater contract incompatible with both the 1.3.24 floor and the modern bootstrap contract.

Such installations are identifiable by build identity and must be remediated once using release/rescue/rescue-legacy-1.3.25.ps1 or another explicitly verified rescue procedure.

The rescue:
- verifies the exact source build;
- verifies the immutable bootstrap package and each file;
- backs up the installation directory;
- writes identity files last;
- verifies the final files;
- restores the backup on failure;
- does not clear Chrome storage.

A modern RELEASE promotion above 1.3.25 remains blocked by the historical updater matrix while a quarantine contract is still marked active.
