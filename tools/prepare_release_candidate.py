#!/usr/bin/env python3
"""
Build an immutable RELEASE candidate directly from a validated portable DEV package.

This is intentionally a build-time identity/channel promotion only. Functional source
comes from the DEV package byte-for-byte except for the small set of RELEASE identity
surfaces listed below. The RELEASE integrity manifest and optional operator ZIP are
rebuilt deterministically.

It never modifies release/latest.json or version.json.
"""
import argparse
import base64
import hashlib
import json
import pathlib
import re
import sys
import zipfile
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME_BUILD_FILES = ("background.js", "js/80-update-banner.js", "js/90-runtime-status.js")
REQUIRED_ROOT = {
    "manifest.json", "build.json", "background.js", "popup.html", "popup.js",
    "icon128.png", "integrity-manifest.json",
}
FORBIDDEN_ROOT = {"updater.html", "updater.js"}


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def decode_files(pkg):
    out = {}
    order = []
    for item in pkg.get("files", []):
        path = str(item.get("path", ""))
        if not path or path in out:
            die(f"invalid/duplicate DEV file path: {path!r}")
        try:
            raw = base64.b64decode(item.get("content_base64", ""), validate=True)
        except Exception as exc:
            die(f"invalid base64 in {path}: {exc}")
        if len(raw) != int(item.get("size", -1)):
            die(f"DEV size mismatch in {path}")
        if sha256(raw) != str(item.get("sha256", "")).lower():
            die(f"DEV SHA mismatch in {path}")
        out[path] = raw
        order.append(path)
    return out, order


def text(files, path):
    if path not in files:
        die(f"missing required source file: {path}")
    try:
        return files[path].decode("utf-8")
    except UnicodeDecodeError as exc:
        die(f"{path} is not UTF-8: {exc}")


def set_text(files, path, value):
    files[path] = value.encode("utf-8")


def replace_required(source, old, new, label):
    count = source.count(old)
    if count < 1:
        die(f"{label}: required token not found: {old}")
    return source.replace(old, new)


def package_rel_from_pointer(pointer):
    url = str(pointer.get("package_url", ""))
    for marker in ("/refs/heads/main/", "/main/"):
        if marker in url:
            return pathlib.PurePosixPath(url.split(marker, 1)[1])
    die(f"unsupported package_url: {url}")


def transplant_release_history(popup, current_release_popup):
    start = "const OPERATOR_RELEASE_HISTORY = ["
    end = "\n\nfunction renderOperatorReleaseHistory()"
    a = popup.find(start)
    b = popup.find(end, a)
    c = current_release_popup.find(start)
    d = current_release_popup.find(end, c)
    if min(a, b, c, d) < 0:
        # History is presentation-only. If a future UI removes it, do not invent it.
        return popup
    return popup[:a] + current_release_popup[c:d] + popup[b:]


def promote(dev_pkg, release_version, release_build, generated_at, current_release_pkg=None):
    if str(dev_pkg.get("channel", "")).upper() != "DEV":
        die("source package must be channel DEV")
    if dev_pkg.get("mode") != "dev-delta":
        die("source DEV package must use mode=dev-delta")
    if dev_pkg.get("patches") or dev_pkg.get("remove"):
        die("source DEV package must be replay-safe (no patches/remove)")

    files, order = decode_files(dev_pkg)
    paths = set(files)
    missing = REQUIRED_ROOT - paths
    if missing:
        die(f"source DEV package missing required files: {sorted(missing)}")
    forbidden = FORBIDDEN_ROOT & paths
    if forbidden:
        die(f"source DEV package contains forbidden root updater artifacts: {sorted(forbidden)}")

    source_build = str(dev_pkg.get("build", ""))
    source_updater_sha = sha256(files["js/95-local-updater.js"])

    manifest = json.loads(text(files, "manifest.json"))
    manifest["name"] = "VIENA NOC Tools"
    manifest["version"] = release_version
    desc = str(manifest.get("description", ""))
    desc = desc.replace(" Canal DEV aislado para pruebas.", "")
    manifest["description"] = desc
    if isinstance(manifest.get("action"), dict):
        manifest["action"]["default_title"] = "VIENA NOC Tools"
    set_text(files, "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    source_build_json = json.loads(text(files, "build.json"))
    release_build_json = {
        "version": release_version,
        "build": release_build,
        "channel": "RELEASE",
        "generated_at": generated_at,
        "updater_contract": max(2, int(source_build_json.get("updater_contract", 2))),
        "release_compatibility_floor": str(source_build_json.get("release_compatibility_floor", "1.3.24")),
        "update_channel": "release/latest.json",
    }
    set_text(files, "build.json", json.dumps(release_build_json, ensure_ascii=False, indent=2) + "\n")

    background = text(files, "background.js")
    background = replace_required(background, source_build, release_build, "background.js")
    background = background.replace(
        "https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/version.json",
        "https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/release/latest.json",
    )
    background = background.replace("VIENA NOC Tools DEV", "VIENA NOC Tools")
    set_text(files, "background.js", background)

    banner = text(files, "js/80-update-banner.js")
    banner = replace_required(banner, source_build, release_build, "js/80-update-banner.js")
    banner = banner.replace("Prueba DEV del aviso de actualización", "Prueba del aviso de actualización")
    set_text(files, "js/80-update-banner.js", banner)

    runtime = text(files, "js/90-runtime-status.js")
    runtime = replace_required(runtime, source_build, release_build, "js/90-runtime-status.js")
    set_text(files, "js/90-runtime-status.js", runtime)

    popup_html = text(files, "popup.html")
    popup_html = re.sub(
        r"v\d+\.\d+\.\d+\s+·\s+Manifest V3",
        f"v{release_version} · Manifest V3",
        popup_html,
        count=1,
    )
    popup_html = popup_html.replace("Probar aviso en VIENA DEV", "Probar aviso en VIENA")
    set_text(files, "popup.html", popup_html)

    popup = text(files, "popup.js")
    popup = popup.replace(
        "https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/version.json",
        "https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/release/latest.json",
    )
    popup = popup.replace("version.json no contiene latest válido", "release/latest.json no contiene latest válido")
    # The validated DEV popup is the source of truth for operator-facing RELEASE history.
    # Do not overwrite it with an older published RELEASE history.
    set_text(files, "popup.js", popup)

    # The validated updater is functional code, not channel identity. It must remain byte-identical.
    if sha256(files["js/95-local-updater.js"]) != source_updater_sha:
        die("updater drift during RELEASE promotion")

    # Rebuild integrity after all identity changes.
    inventory = {}
    for path in order:
        if path == "integrity-manifest.json":
            continue
        inventory[path] = sha256(files[path])
    integrity = {
        "schema": 1,
        "version": release_version,
        "channel": "RELEASE",
        "build": release_build,
        "files": inventory,
    }
    set_text(files, "integrity-manifest.json", json.dumps(integrity, ensure_ascii=False, indent=2) + "\n")

    # Fail closed on the regressions that previously cost us release time.
    bg = text(files, "background.js")
    up = text(files, "js/95-local-updater.js")
    bn = text(files, "js/80-update-banner.js")
    ph = text(files, "popup.html")
    pj = text(files, "popup.js")

    if "&& !sender?.tab &&" in bg:
        die("legacy sender.tab rejection returned")
    for token in ("const url=senderUrl(sender);", "url.startsWith(chrome.runtime.getURL(''))"):
        if token not in bg:
            die(f"standalone sender guard token missing: {token}")
    if "raw.githubusercontent.com" in bn or "await fetch(" in bn:
        die("update banner performs a direct remote fetch")
    for token in ("VIENA_UPDATE_BANNER_GET_STATE", "IS_DEV_CONTENT"):
        if token not in bn:
            die(f"background-owned banner token missing: {token}")
    if "const PAGE_WINDOW = typeof window !== 'undefined' ? window : null;" not in up:
        die("updater is not service-worker safe")
    for token in ("standaloneFolderPage", "standaloneFolderSelect", "standalone-folder-root"):
        if token not in ph:
            die(f"standalone UI token missing: {token}")
    for token in (
        "performStandaloneFolderLink",
        "closeStandaloneFolderPage",
        "document.documentElement.classList.add('standalone-folder-root')",
    ):
        if token not in pj:
            die(f"standalone behavior token missing: {token}")

    for path in RUNTIME_BUILD_FILES:
        body = text(files, path)
        if release_build not in body:
            die(f"{path} does not embed RELEASE build id")
        if source_build in body:
            die(f"{path} still embeds DEV build id")

    if "refs/heads/main/version.json" in bg or "refs/heads/main/version.json" in pj:
        die("legacy version.json routing leaked into RELEASE")
    if "release/latest.json" not in bg or "release/latest.json" not in pj:
        die("RELEASE routing to release/latest.json is missing")

    items = []
    for path in order:
        raw = files[path]
        items.append({
            "path": path,
            "size": len(raw),
            "sha256": sha256(raw),
            "content_base64": base64.b64encode(raw).decode("ascii"),
        })

    return {
        "schema": 1,
        "app": "VIENA NOC Tools",
        "version": release_version,
        "build": release_build,
        "channel": "RELEASE",
        "generated_at": generated_at,
        "files": items,
        "remove": [],
        "mode": "full",
    }, files, source_updater_sha


def write_zip(path, files, order):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in order:
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, files[name])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev-package", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--candidate", type=int, default=1)
    ap.add_argument("--output")
    ap.add_argument("--zip-output")
    ap.add_argument("--generated-at")
    args = ap.parse_args()

    dev_path = ROOT / pathlib.PurePosixPath(args.dev_package)
    if not dev_path.exists():
        die(f"DEV package not found: {args.dev_package}")
    dev_pkg = load_json(dev_path)

    source_build = str(dev_pkg.get("build", ""))
    suffix = source_build
    marker = "-dev-"
    if marker in suffix:
        suffix = suffix.split(marker, 1)[1]
    suffix = re.sub(r"[^A-Za-z0-9._-]+", "-", suffix).strip("-") or "validated-dev"
    release_build = f"{args.version}-release-{suffix}-candidate{args.candidate}"

    generated_at = args.generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    current_release = load_json(ROOT / "release/latest.json")
    current_release_path = ROOT / package_rel_from_pointer(current_release)
    current_release_pkg = load_json(current_release_path) if current_release_path.exists() else None

    output_rel = pathlib.PurePosixPath(args.output) if args.output else pathlib.PurePosixPath(
        f"release/v{args.version}-{suffix}-candidate{args.candidate}-package.json"
    )
    if output_rel.is_absolute() or ".." in output_rel.parts or not str(output_rel).startswith("release/"):
        die("output must be an immutable path under release/")
    output_path = ROOT / output_rel
    if output_path.exists():
        die(f"refusing to overwrite immutable RELEASE candidate: {output_rel}")

    pkg, files, updater_sha = promote(
        dev_pkg=dev_pkg,
        release_version=args.version,
        release_build=release_build,
        generated_at=generated_at,
        current_release_pkg=current_release_pkg,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(pkg, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    output_path.write_bytes(raw)

    order = [item["path"] for item in pkg["files"]]
    zip_rel = pathlib.PurePosixPath(args.zip_output) if args.zip_output else pathlib.PurePosixPath(
        f"downloads/VIENA_NOC_Tools_RELEASE_v{args.version}_candidate{args.candidate}.zip"
    )
    zip_path = ROOT / zip_rel
    if zip_path.exists():
        die(f"refusing to overwrite existing ZIP: {zip_rel}")
    write_zip(zip_path, files, order)

    print(json.dumps({
        "candidate": str(output_rel),
        "candidate_sha256": sha256(raw),
        "zip": str(zip_rel),
        "zip_sha256": sha256(zip_path.read_bytes()),
        "version": args.version,
        "build": release_build,
        "source_dev_package": args.dev_package,
        "source_dev_build": source_build,
        "updater_sha256": updater_sha,
        "file_count": len(pkg["files"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
