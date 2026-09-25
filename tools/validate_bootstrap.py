#!/usr/bin/env python3
import base64, hashlib, json, pathlib, subprocess, sys, tempfile
import validate_release_compat as release_validator

ROOT = pathlib.Path(__file__).resolve().parents[1]

def die(msg):
    print("ERROR:", msg, file=sys.stderr)
    raise SystemExit(1)

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def extract_file(pkg, path):
    item = next((x for x in pkg.get("files", []) if x.get("path") == path), None)
    if not item:
        die(f"bootstrap package missing {path}")
    try:
        return base64.b64decode(item["content_base64"], validate=True)
    except Exception as e:
        die(f"invalid base64 in {path}: {e}")

def main():
    cfg = load(ROOT/"release/bootstrap.json")
    pkg_path = ROOT/str(cfg["package_path"])
    if not pkg_path.exists():
        die(f"bootstrap package missing: {pkg_path}")
    got = sha256(pkg_path)
    want = str(cfg.get("package_sha256","")).lower()
    if got != want:
        die(f"bootstrap SHA mismatch: {got} != {want}")

    release_validator.validate_package(pkg_path)
    pkg = load(pkg_path)
    if str(pkg.get("version")) != str(cfg.get("latest")):
        die("bootstrap version != config latest")
    if str(pkg.get("channel","")).upper() != "RELEASE":
        die("bootstrap package is not RELEASE")

    build = json.loads(extract_file(pkg,"build.json").decode("utf-8"))
    if int(build.get("updater_contract",0)) < 2:
        die("bootstrap updater_contract must be >=2")
    if str(build.get("release_compatibility_floor","")) != "1.3.24":
        die("bootstrap release compatibility floor missing")
    if str(build.get("update_channel","")) != str(cfg.get("modern_pointer","")):
        die("bootstrap build does not declare modern pointer")

    expected_modern = "release/latest.json"
    for embedded in ["background.js","popup.js"]:
        text = extract_file(pkg,embedded).decode("utf-8")
        if expected_modern not in text:
            die(f"{embedded} does not use modern pointer {expected_modern}")
        if "/version.json" in text and "VIENA_UPDATE_MANIFEST_URL" in text:
            # DEV manifest constants are allowed; the RELEASE manifest constant itself must be modern.
            line = next((ln for ln in text.splitlines() if "VIENA_UPDATE_MANIFEST_URL" in ln and "const " in ln), "")
            if expected_modern not in line:
                die(f"{embedded} still points RELEASE updates to version.json")

    source_pkg = load(ROOT/"release/v1.3.24-package.json")
    updater_bytes = extract_file(source_pkg,"js/95-local-updater.js")
    with tempfile.TemporaryDirectory() as td:
        up = pathlib.Path(td)/"updater-1.3.24.js"
        up.write_bytes(updater_bytes)
        proc = subprocess.run([
            "node", str(ROOT/"tools/run_updater_validate.mjs"),
            str(up), str(pkg_path),
            str(pkg.get("version","")), str(pkg.get("build","")), "RELEASE"
        ], text=True, capture_output=True)
        if proc.returncode:
            die(f"exact 1.3.24 updater rejected bootstrap\nstdout:{proc.stdout}\nstderr:{proc.stderr}")

    print(f"PASS bootstrap: exact 1.3.24 updater -> {cfg['package_path']}")
    print(f"PASS bootstrap SHA: {got}")
    print("PASS bootstrap switches RELEASE checks to release/latest.json")

if __name__ == "__main__":
    main()
