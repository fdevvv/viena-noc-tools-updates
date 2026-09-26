#!/usr/bin/env python3
import argparse
import base64
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

def die(msg):
    print("ERROR:", msg, file=sys.stderr)
    raise SystemExit(1)

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def extract(pkg, path):
    item = next((x for x in pkg.get("files", []) if x.get("path") == path), None)
    if not item:
        die(f"{pkg.get('build')}: missing {path}")
    try:
        raw = base64.b64decode(item["content_base64"], validate=True)
    except Exception as exc:
        die(f"{pkg.get('build')}: invalid base64 in {path}: {exc}")
    if len(raw) != int(item.get("size", -1)):
        die(f"{pkg.get('build')}: wrong size for {path}")
    got = sha256_bytes(raw)
    want = str(item.get("sha256", "")).lower()
    if got != want:
        die(f"{pkg.get('build')}: wrong SHA for {path}: {got} != {want}")
    return raw, want

def run_historical_validator(root, updater_bytes, package_path, expected_version, expected_channel):
    harness = root / "tools/run_updater_validate.mjs"
    with tempfile.TemporaryDirectory() as td:
        updater_path = pathlib.Path(td) / "updater.js"
        updater_path.write_bytes(updater_bytes)
        return subprocess.run(
            [
                "node", str(harness), str(updater_path), str(package_path),
                str(expected_version), "", str(expected_channel)
            ],
            text=True, capture_output=True
        )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--require-retired", action="store_true")
    args = ap.parse_args()
    root = pathlib.Path(args.repo_root).resolve()

    spec = load(root / "release/rescue/legacy-1.3.25.json")
    history = load(root / "release/public-history.json")
    bootstrap_cfg = load(root / "release/bootstrap.json")

    if spec.get("schema") != 1 or spec.get("role") != "legacy-release-rescue":
        die("legacy rescue spec schema/role invalid")

    base = spec.get("base_public_bootstrap") or {}
    base_rel = str(base.get("package", ""))
    base_path = root / base_rel
    if not base_path.exists():
        die(f"base public bootstrap package missing: {base_rel}")
    base_raw = base_path.read_bytes()
    base_sha = sha256_bytes(base_raw)
    if base_sha != str(base.get("package_sha256", "")).lower():
        die(f"base public bootstrap SHA mismatch: {base_sha}")
    if base_rel != str(bootstrap_cfg.get("package_path", "")):
        die("base public bootstrap != release/bootstrap.json package")
    if base_sha != str(bootstrap_cfg.get("package_sha256", "")).lower():
        die("base public bootstrap SHA != release/bootstrap.json SHA")

    base_pkg = json.loads(base_raw.decode("utf-8"))
    if str(base_pkg.get("build", "")) != str(base.get("build", "")):
        die("base public bootstrap build mismatch")

    target = spec.get("target_bootstrap") or {}
    target_rel = str(target.get("package", ""))
    target_path = root / target_rel
    if not target_path.exists():
        die(f"rescue bootstrap package missing: {target_rel}")

    target_raw = target_path.read_bytes()
    target_sha = sha256_bytes(target_raw)
    if target_sha != str(target.get("package_sha256", "")).lower():
        die(f"rescue target SHA mismatch: {target_sha}")

    target_pkg = json.loads(target_raw.decode("utf-8"))
    if str(target_pkg.get("version", "")) != str(target.get("version", "")):
        die("rescue target version mismatch")
    if str(target_pkg.get("build", "")) != str(target.get("build", "")):
        die("rescue target build mismatch")
    if str(target_pkg.get("channel", "")).upper() != str(target.get("channel", "")).upper():
        die("rescue target channel mismatch")

    allowed_changes = set((spec.get("policy") or {}).get("rescue_target_changes_limited_to") or [])
    base_files = {str(x.get("path", "")): x for x in base_pkg.get("files", [])}
    target_files = {str(x.get("path", "")): x for x in target_pkg.get("files", [])}
    if set(base_files) != set(target_files):
        die("rescue target changed the bootstrap file set")
    changed = {
        path for path in base_files
        if str(base_files[path].get("sha256", "")).lower() != str(target_files[path].get("sha256", "")).lower()
    }
    if not changed:
        die("rescue target is unexpectedly byte-identical to the public bootstrap")
    unexpected = sorted(changed - allowed_changes)
    if unexpected:
        die(f"rescue target changed unauthorized files: {unexpected}")
    required_changes = {"background.js", "build.json", "integrity-manifest.json", "popup.html", "popup.js"}
    if not required_changes.issubset(changed):
        die(f"rescue target missing expected controlled changes: {sorted(required_changes - changed)}")

    _, build_sha = extract(target_pkg, "build.json")
    build = json.loads(extract(target_pkg, "build.json")[0].decode("utf-8"))
    if int(build.get("updater_contract", 0)) < 2:
        die("bootstrap updater_contract < 2")
    if str(build.get("release_compatibility_floor", "")) != "1.3.24":
        die("bootstrap release compatibility floor mismatch")
    if str(build.get("update_channel", "")) != str(target.get("modern_pointer", "")):
        die("bootstrap does not switch to modern pointer")

    popup = extract(target_pkg, "popup.js")[0].decode("utf-8")
    popup_html = extract(target_pkg, "popup.html")[0].decode("utf-8")
    if "const channelLabel = isDevRuntime() ? 'DEV' : 'RELEASE'" not in popup:
        die("rescue target popup does not render channel dynamically")
    if "brandVersionEl.textContent = `v${chrome.runtime.getManifest().version} DEV" in popup:
        die("rescue target still hardcodes DEV in runtime branding")
    if 'class="version">v1.3.25 DEV' in popup_html:
        die("rescue target fallback HTML still hardcodes DEV")

    history_by_id = {str(x.get("id")): x for x in history.get("contracts", [])}
    active_quarantine = []

    for source in spec.get("source_contracts", []):
        cid = str(source.get("id", ""))
        hist = history_by_id.get(cid)
        if not hist:
            die(f"rescue source missing from public-history: {cid}")
        if str(hist.get("route", "")) != "legacy_rescue":
            die(f"{cid}: public-history route must be legacy_rescue")
        if bool(hist.get("quarantine")):
            active_quarantine.append(cid)

        source_rel = str(source.get("package", ""))
        if source_rel != str(hist.get("package", "")):
            die(f"{cid}: rescue spec package != public-history package")
        source_path = root / source_rel
        if not source_path.exists():
            die(f"{cid}: source package missing: {source_rel}")
        pkg = load(source_path)

        if str(pkg.get("version", "")) != str(spec.get("source_version", "")):
            die(f"{cid}: source version mismatch")
        if str(pkg.get("build", "")) != str(spec.get("source_build", "")):
            die(f"{cid}: source build mismatch")
        if str(pkg.get("channel", "")).upper() != str(spec.get("source_channel", "")).upper():
            die(f"{cid}: source channel mismatch")

        updater, updater_sha = extract(pkg, "js/95-local-updater.js")
        if updater_sha != str(source.get("updater_sha256", "")).lower():
            die(f"{cid}: historical updater fingerprint mismatch")

        for rel in ("background.js", "popup.js"):
            text = extract(pkg, rel)[0].decode("utf-8")
            if "version.json" not in text:
                die(f"{cid}: {rel} no longer proves legacy version.json routing")
        background = extract(pkg, "background.js")[0].decode("utf-8")
        if "compareVersions(data.latest,installed)>0" not in background:
            die(f"{cid}: RELEASE runtime is no longer proven to be semver-only for update availability")

        proc = run_historical_validator(
            root, updater, target_path, target.get("version", ""), target.get("channel", "RELEASE")
        )
        expected = str(source.get("bootstrap_validator_result", ""))
        if expected == "accept" and proc.returncode != 0:
            die(f"{cid}: expected historical validator to accept bootstrap\nstdout:{proc.stdout}\nstderr:{proc.stderr}")
        if expected == "reject" and proc.returncode == 0:
            die(f"{cid}: expected historical validator to reject bootstrap")
        if expected not in {"accept", "reject"}:
            die(f"{cid}: invalid bootstrap_validator_result")
        print(f"PASS legacy source contract: {cid} updater={updater_sha} bootstrap_validator={expected}")

    script_path = root / str(spec.get("rescue_script", ""))
    if not script_path.exists():
        die("legacy rescue script missing")
    script = script_path.read_text(encoding="utf-8")
    required_script_tokens = [
        str(target.get("package_sha256", "")),
        str(spec.get("source_version", "")),
        str(spec.get("source_build", "")),
        str(target.get("build", "")),
        str(target.get("modern_pointer", "")),
        "AllowedSourceUpdaterSha256",
        "PackagePath",
        "integrity-manifest.json",
        "Rollback",
    ]
    for source in spec.get("source_contracts", []):
        required_script_tokens.append(str(source.get("updater_sha256", "")))
    for token in required_script_tokens:
        if token not in script:
            die(f"rescue script missing contract token: {token}")

    if args.require_retired and active_quarantine:
        die(
            "legacy 1.3.25 quarantine is still active; remediate registered installations before promotion: "
            + ", ".join(active_quarantine)
        )

    print(f"PASS legacy rescue base: {base_rel} sha256={base_sha}")
    print(f"PASS legacy rescue controlled changes: {sorted(changed)}")
    print(f"PASS legacy rescue target: {target_rel} sha256={target_sha}")
    print("PASS legacy rescue script is bound to the audited historical updater fingerprints")
    if active_quarantine:
        print("INFO active legacy quarantine:", ", ".join(active_quarantine))
    else:
        print("PASS no active legacy quarantine remains")

if __name__ == "__main__":
    main()
