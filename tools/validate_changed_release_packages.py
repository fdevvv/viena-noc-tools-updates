#!/usr/bin/env python3
import base64
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
        validate_js(path.relative_to(ROOT), pkg)
        print(f"PASS immutable RELEASE candidate: {path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
