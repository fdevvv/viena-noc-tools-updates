#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import validate_release_compat as validator

DANGEROUS = [
    re.compile(rb"chrome\.storage\.local\.clear\s*\("),
    re.compile(rb"indexedDB\.deleteDatabase\s*\("),
]

def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)

def changed_candidates():
    event = os.environ.get("EVENT_NAME", "")
    if event == "pull_request":
        base = os.environ.get("BASE_SHA", "")
        head = os.environ.get("HEAD_SHA", "")
    else:
        base = os.environ.get("BEFORE_SHA", "")
        head = os.environ.get("CURRENT_SHA", "")
    if not base or not head:
        die("missing git diff range")
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}..{head}"],
        cwd=ROOT, text=True, capture_output=True
    )
    if proc.returncode:
        die(f"git diff failed: {proc.stderr}")
    return [
        ROOT / line.strip()
        for line in proc.stdout.splitlines()
        if re.fullmatch(r"release/.+package\.json", line.strip())
    ]

def text_file(pkg, path):
    item = next((x for x in pkg.get("files", []) if x.get("path") == path), None)
    if not item:
        die(f"{pkg.get('build')}: missing {path}")
    try:
        return base64.b64decode(item["content_base64"], validate=True).decode("utf-8")
    except Exception as exc:
        die(f"{pkg.get('build')}: cannot decode {path}: {exc}")

def validate_runtime_identity(path, pkg):
    build = str(pkg.get("build", ""))
    manifest = json.loads(text_file(pkg, "manifest.json"))
    build_json = json.loads(text_file(pkg, "build.json"))
    background = text_file(pkg, "background.js")
    banner = text_file(pkg, "js/80-update-banner.js")
    runtime = text_file(pkg, "js/90-runtime-status.js")
    popup = text_file(pkg, "popup.js")
    popup_html = text_file(pkg, "popup.html")

    if manifest.get("name") != "VIENA NOC Tools":
        die(f"{path}: RELEASE manifest name/branding is not canonical")
    if str(build_json.get("update_channel", "")) != "release/latest.json":
        die(f"{path}: build.json does not route RELEASE through release/latest.json")
    if "release/latest.json" not in background or "refs/heads/main/version.json" in background:
        die(f"{path}: background RELEASE channel routing is stale")
    if "release/latest.json" not in popup or "refs/heads/main/version.json" in popup:
        die(f"{path}: popup RELEASE channel routing is stale")
    if "VIENA NOC Tools DEV — activa" in background:
        die(f"{path}: DEV badge branding leaked into RELEASE")
    if "Probar aviso en VIENA DEV" in popup_html:
        die(f"{path}: DEV popup fallback branding leaked into RELEASE")

    for name, source in [
        ("background.js", background),
        ("js/80-update-banner.js", banner),
        ("js/90-runtime-status.js", runtime),
    ]:
        if build not in source:
            die(f"{path}: {name} does not embed the candidate build {build}")

    stale = re.findall(r"1\.3\.\d+-(?:dev|release)-[A-Za-z0-9._-]+", "\n".join([background, banner, runtime]))
    stale = sorted({value for value in stale if value != build})
    if stale:
        die(f"{path}: stale embedded runtime build IDs: {stale}")


EXPECTED_FIX26_UPDATER_SHA256 = "b1706c0d6ff08200dbe89c2b9a6b254947861d6790699656277f45a7a98cb367"

def semver(value):
    try:
        parts = tuple(int(x) for x in str(value).split("."))
        return parts if len(parts) == 3 else (-1, -1, -1)
    except Exception:
        return (-1, -1, -1)

def package_file_bytes(pkg, path):
    item = next((x for x in pkg.get("files", []) if x.get("path") == path), None)
    if not item:
        die(f"{pkg.get('build')}: missing {path}")
    try:
        return base64.b64decode(item["content_base64"], validate=True)
    except Exception as exc:
        die(f"{pkg.get('build')}: cannot decode {path}: {exc}")

def validate_fix26_regressions(path, pkg):
    background = text_file(pkg, "background.js")
    popup = text_file(pkg, "popup.js")
    popup_html = text_file(pkg, "popup.html")
    banner = text_file(pkg, "js/80-update-banner.js")
    updater = text_file(pkg, "js/95-local-updater.js")

    if hashlib.sha256(package_file_bytes(pkg, "js/95-local-updater.js")).hexdigest() != EXPECTED_FIX26_UPDATER_SHA256:
        die(f"{path}: js/95-local-updater.js drifted from the validated fix26 updater")

    if "&& !sender?.tab &&" in background:
        die(f"{path}: legacy sender.tab rejection returned")
    for token in [
        "const url=senderUrl(sender);",
        "url.startsWith(chrome.runtime.getURL(''))",
        "VIENA_BACKGROUND_UPDATE_RESUME",
        "BACKGROUND_UPDATE_STALE_MS",
        "Recuperación anterior descartada.",
    ]:
        if token not in background:
            die(f"{path}: fix22/fix23 background token missing: {token}")

    if "raw.githubusercontent.com" in banner or "await fetch(" in banner:
        die(f"{path}: fix24 regression: update banner performs a direct remote fetch")
    for token in ["VIENA_UPDATE_BANNER_GET_STATE", "IS_DEV_CONTENT"]:
        if token not in banner:
            die(f"{path}: fix24 token missing: {token}")

    if "const PAGE_WINDOW = typeof window !== 'undefined' ? window : null;" not in updater:
        die(f"{path}: updater is not service-worker safe")

    for token in ["standaloneFolderPage", "standaloneFolderSelect", "standalone-folder-root"]:
        if token not in popup_html:
            die(f"{path}: fix25/fix26 standalone UI token missing: {token}")
    for token in [
        "performStandaloneFolderLink",
        "closeStandaloneFolderPage",
        "document.documentElement.classList.add('standalone-folder-root')",
        "No se seleccionó ninguna carpeta.",
    ]:
        if token not in popup:
            die(f"{path}: fix25/fix26 standalone behavior token missing: {token}")
    if "html.standalone-folder-root,html.standalone-folder-root body{width:100%;min-width:0;max-width:none" not in popup_html:
        die(f"{path}: fix26 standalone centering rule missing")

    print(f"PASS fix22-fix26 regression guards: {path}")

def updater_from_package(package_path):
    source = json.loads(package_path.read_text(encoding="utf-8"))
    return package_file_bytes(source, "js/95-local-updater.js")

def validate_candidate_matrix(path, pkg):
    history = json.loads((ROOT / "release/public-history.json").read_text(encoding="utf-8"))
    target_version = semver(pkg.get("version"))
    if target_version == (-1, -1, -1):
        die(f"{path}: invalid target version for matrix")

    harness = ROOT / "tools/run_updater_validate.mjs"
    tested = []
    for src in history.get("contracts", []):
        if not src.get("must_support_future_upgrade", False):
            continue
        if str(src.get("route", "")) != "modern":
            continue
        if semver(src.get("version")) >= target_version:
            continue
        source_path = ROOT / str(src.get("package", ""))
        if not source_path.exists():
            die(f"{path}: historical source package missing: {source_path}")
        with tempfile.TemporaryDirectory() as td:
            updater_path = pathlib.Path(td) / "updater.js"
            updater_path.write_bytes(updater_from_package(source_path))
            proc = subprocess.run(
                [
                    "node", str(harness), str(updater_path), str(path),
                    str(pkg.get("version", "")), str(pkg.get("build", "")), str(pkg.get("channel", ""))
                ],
                text=True, capture_output=True
            )
        if proc.returncode:
            die(
                f"{path}: {src.get('id')} -> candidate FAILED\n"
                f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
            )
        tested.append(str(src.get("id")))
        print(f"PASS candidate historical updater: {src.get('id')} -> {path.relative_to(ROOT)}")

    required = {"release-1.3.25-bootstrap-v3", "release-1.3.26-modern", "release-1.3.27-modern"}
    missing = required - set(tested)
    if missing:
        die(f"{path}: candidate matrix missing required modern sources: {sorted(missing)}")

    bootstrap = json.loads((ROOT / "release/bootstrap.json").read_text(encoding="utf-8"))
    bootstrap_package = str(bootstrap.get("package_path", ""))
    bootstrap_contract = next(
        (x for x in history.get("contracts", []) if str(x.get("package", "")) == bootstrap_package),
        None
    )
    if not bootstrap_contract or str(bootstrap_contract.get("id", "")) not in tested:
        die(f"{path}: 1.3.24 -> bootstrap -> candidate composition is not covered")

    print(
        f"PASS candidate matrix: 1.3.24 -> bootstrap -> {pkg.get('version')}; "
        f"modern sources={','.join(tested)}"
    )


def validate_js(path, pkg):
    if pkg.get("remove"):
        die(f"{path}: RELEASE package must not remove files")
    if pkg.get("patches"):
        die(f"{path}: RELEASE package must not contain text patches")
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        for item in pkg["files"]:
            if not item["path"].endswith(".js"):
                continue
            raw = base64.b64decode(item["content_base64"], validate=True)
            for pattern in DANGEROUS:
                if pattern.search(raw):
                    die(f"{path}: destructive storage operation in {item['path']}")
            out = td / item["path"].replace("/", "__")
            out.write_bytes(raw)
            subprocess.run(["node", "--check", str(out)], check=True)

def main():
    candidates = changed_candidates()
    if not candidates:
        print("No changed immutable RELEASE packages.")
        return
    for path in candidates:
        print(f"Validating immutable RELEASE candidate: {path.relative_to(ROOT)}")
        validator.validate_package(path)
        pkg = json.loads(path.read_text(encoding="utf-8"))
        validate_runtime_identity(path.relative_to(ROOT), pkg)
        validate_fix26_regressions(path.relative_to(ROOT), pkg)
        validate_js(path.relative_to(ROOT), pkg)
        validate_candidate_matrix(path, pkg)
        print(f"PASS immutable RELEASE candidate: {path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
