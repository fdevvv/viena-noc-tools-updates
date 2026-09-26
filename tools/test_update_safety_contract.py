#!/usr/bin/env python3
import base64, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]

def die(msg):
    print("ERROR:",msg,file=sys.stderr)
    raise SystemExit(1)

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def resolve_pointer(path):
    pointer=load(ROOT/path)
    url=str(pointer.get("package_url",""))
    marker="/main/"
    if marker not in url:
        die(f"{path}: invalid package_url")
    rel=url.split(marker,1)[1]
    pkg=load(ROOT/rel)
    return pointer,rel,pkg

def text_file(pkg,path):
    item=next((x for x in pkg.get("files",[]) if x.get("path")==path),None)
    if not item:
        die(f"{pkg.get('build')}: missing {path}")
    try:
        return base64.b64decode(item["content_base64"],validate=True).decode("utf-8")
    except Exception as e:
        die(f"{pkg.get('build')}: cannot decode {path}: {e}")

def paths(pkg):
    return {str(x.get("path","")) for x in pkg.get("files",[])}

def assert_hardened(label,pkg,dev=False):
    build=json.loads(text_file(pkg,"build.json"))
    if int(build.get("updater_contract",0)) < 2:
        die(f"{label}: updater_contract < 2")

    updater=text_file(pkg,"js/95-local-updater.js")
    background=text_file(pkg,"background.js")
    popup=text_file(pkg,"popup.js")

    updater_tokens=[
      "viena_local_update_lock_v1",
      "viena_local_update_journal_v1",
      "viena_local_update_last_result_v1",
      "navigator?.locks?.request",
      "rollbackTouchedFiles",
      "failed_rolled_back_verified",
      "rollback_incomplete",
      "Se bloque",
      "resumePendingUpdate",
      "awaiting_reload",
      "verifyDirectoryAgainstIntegrity"
    ]
    for token in updater_tokens:
        if token not in updater:
            die(f"{label}: updater safety token missing: {token}")

    bg_tokens=[
      "reconcileUpdateJournalAfterRuntimeStart",
      "post_reload_verified",
      "post_reload_integrity_failed",
      "viena_local_update_journal_v1",
      "viena_local_update_lock_v1"
    ]
    for token in bg_tokens:
        if token not in background:
            die(f"{label}: background health token missing: {token}")

    if "recoverInterruptedLocalUpdate" not in popup:
        die(f"{label}: popup recovery missing")

    if dev:
        runtime_status=text_file(pkg,"js/90-runtime-status.js")
        popup_html=text_file(pkg,"popup.html")
        feature_tokens={
          "background.js":[
            "VIENA_BACKGROUND_UPDATE_START",
            "BACKGROUND_UPDATE_STATE_KEY",
            "importScripts('js/95-local-updater.js')",
            "resumeDetachedUpdateIfNeeded"
          ],
          "popup.js":[
            "VIENA_BACKGROUND_UPDATE_START",
            "refreshBackgroundUpdateState"
          ],
          "popup.html":[
            "backgroundUpdatePanel",
            "La actualización continúa aunque cierres este popup"
          ],
          "js/90-runtime-status.js":[
            "VIENA_BACKGROUND_UPDATE_PROGRESS",
            "Actualizando VIENA NOC Tools",
            "Podés seguir usando el resto del navegador"
          ],
          "js/95-local-updater.js":[
            "backgroundSupported",
            "globalThis.VienaLocalUpdater = api",
            "onProgress"
          ]
        }
        sources={
          "background.js":background,
          "popup.js":popup,
          "popup.html":popup_html,
          "js/90-runtime-status.js":runtime_status,
          "js/95-local-updater.js":updater
        }
        for path,tokens in feature_tokens.items():
            for token in tokens:
                if token not in sources[path]:
                    die(f"{label}: background-update feature token missing in {path}: {token}")

        # Regression guard for fix22: extension-owned standalone tabs must be trusted,
        # while arbitrary web tabs still fail the extension-origin prefix check.
        if "&& !sender?.tab &&" in background:
            die(f"{label}: standalone extension pages are still rejected by sender guard")
        for token in [
            "const url=senderUrl(sender);",
            "url.startsWith(chrome.runtime.getURL(''))",
            "BACKGROUND_UPDATE_STALE_MS"
        ]:
            if token not in background:
                die(f"{label}: fix22 background recovery token missing: {token}")
        for token in [
            "standaloneFolderMode",
            "pickAndLink({ requireRuntimeMatch: !hasRecoveryJournal })",
            "No se puede desvincular la carpeta mientras una actualización"
        ]:
            if token not in popup:
                die(f"{label}: fix22 standalone/recovery token missing: {token}")
        if "async function pickAndLink({ requireRuntimeMatch = true } = {})" not in updater:
            die(f"{label}: recovery-aware folder relink contract missing")
        if "Recuperación anterior descartada." not in background:
            die(f"{label}: obsolete recovery journal retirement missing")

        # Regression guard for fix24: update manifests are fetched by the
        # service worker, never directly from the VIENA content script.
        update_banner=text_file(pkg,"js/80-update-banner.js")
        if "raw.githubusercontent.com" in update_banner or "await fetch(" in update_banner:
            die(f"{label}: update banner still performs a direct remote fetch")
        for token in ["VIENA_UPDATE_BANNER_GET_STATE","IS_DEV_CONTENT"]:
            if token not in update_banner:
                die(f"{label}: fix24 background-owned banner token missing: {token}")

    p=paths(pkg)
    if dev:
        if str(pkg.get("profile","")) != "portable-replay-safe-v1":
            die(f"{label}: DEV candidate is not portable-replay-safe-v1")
        if str(pkg.get("mode","")) != "dev-delta":
            die(f"{label}: portable DEV candidate must use dev-delta")
        if {"updater.html","updater.js"} & p:
            die(f"{label}: portable DEV package contains fork-incompatible updater root artifacts")
        if pkg.get("patches") or pkg.get("remove"):
            die(f"{label}: portable DEV package must be replay-safe (no patches/remove)")
        for token in [
            "OPTIONAL_COMPAT_PACKAGE_FILES",
            "'updater.html'",
            "'updater.js'",
            "replaySafeDevDelta",
            "portable replay-safe"
        ]:
            if token not in updater:
                die(f"{label}: portable updater token missing: {token}")
    else:
        forbidden={"updater.html","updater.js"} & p
        if forbidden:
            die(f"{label}: RELEASE contains legacy-incompatible root artifacts: {sorted(forbidden)}")

    print(f"PASS update safety contract: {label} ({pkg.get('build')})")

def main():
    _,_,devpkg=resolve_pointer("dev/self-update.json")
    _,_,modern=resolve_pointer("release/latest.json")
    bootstrap_cfg=load(ROOT/"release/bootstrap.json")
    bootstrap=load(ROOT/bootstrap_cfg["package_path"])

    assert_hardened("DEV",devpkg,dev=True)
    assert_hardened("modern RELEASE",modern,dev=False)
    assert_hardened("legacy bootstrap",bootstrap,dev=False)

if __name__=="__main__":
    main()
