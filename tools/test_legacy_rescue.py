#!/usr/bin/env python3
import argparse
import base64
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

def die(msg):
    print("ERROR:", msg, file=sys.stderr)
    raise SystemExit(1)

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def decode_package(pkg, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for item in pkg.get("files", []):
        rel = pathlib.PurePosixPath(str(item["path"]))
        out = destination.joinpath(*rel.parts)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(base64.b64decode(item["content_base64"], validate=True))

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def assert_target(install, target_pkg):
    for item in target_pkg.get("files", []):
        rel = pathlib.PurePosixPath(str(item["path"]))
        path = install.joinpath(*rel.parts)
        if not path.exists():
            die(f"rescue output missing {item['path']}")
        got = sha256(path)
        if got != str(item["sha256"]).lower():
            die(f"rescue output SHA mismatch for {item['path']}")
    build = load(install / "build.json")
    if str(build.get("build", "")) != str(target_pkg.get("build", "")):
        die("rescue output build mismatch")

def run():
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-pwsh", action="store_true")
    args = ap.parse_args()

    pwsh = shutil.which("pwsh")
    if not pwsh:
        if args.require_pwsh:
            die("pwsh is required for legacy rescue integration test")
        print("SKIP legacy rescue integration: pwsh not available")
        return

    spec = load(ROOT / "release/rescue/legacy-1.3.25.json")
    target_path = ROOT / spec["target_bootstrap"]["package"]
    target_pkg = load(target_path)
    script = ROOT / spec["rescue_script"]
    if not script.read_bytes().startswith(b"\xef\xbb\xbf"):
        die("legacy rescue script must carry UTF-8 BOM for Windows PowerShell 5.1 compatibility")

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)

        for idx, source in enumerate(spec["source_contracts"]):
            install = root / f"install-{idx}"
            decode_package(load(ROOT / source["package"]), install)
            proc = subprocess.run(
                [
                    pwsh, "-NoProfile", "-File", str(script),
                    "-InstallPath", str(install),
                    "-PackagePath", str(target_path),
                ],
                text=True, capture_output=True
            )
            if proc.returncode != 0:
                die(f"{source['id']}: rescue failed\nstdout:{proc.stdout}\nstderr:{proc.stderr}")
            assert_target(install, target_pkg)
            backups = list(root.glob(f"{install.name}_BACKUP_*"))
            if len(backups) != 1:
                die(f"{source['id']}: expected exactly one backup, got {len(backups)}")
            old_build = load(backups[0] / "build.json")
            if str(old_build.get("build", "")) != str(spec.get("source_build", "")):
                die(f"{source['id']}: backup identity mismatch")
            print(f"PASS PowerShell rescue integration: {source['id']}")

        bad = root / "bad-source"
        decode_package(load(ROOT / spec["source_contracts"][0]["package"]), bad)
        updater = bad / "js" / "95-local-updater.js"
        updater.write_bytes(updater.read_bytes() + b"\n// tampered")
        proc = subprocess.run(
            [
                pwsh, "-NoProfile", "-File", str(script),
                "-InstallPath", str(bad),
                "-PackagePath", str(target_path),
            ],
            text=True, capture_output=True
        )
        if proc.returncode == 0:
            die("tampered historical updater fingerprint was accepted")
        if str(load(bad / "build.json").get("build", "")) != str(spec.get("source_build", "")):
            die("tampered-source rejection modified installation")
        print("PASS rescue rejects unknown/tampered source updater before migration")

        tampered_target = root / "tampered-bootstrap.json"
        tampered_target.write_bytes(target_path.read_bytes() + b"\n")
        clean = root / "clean-source"
        decode_package(load(ROOT / spec["source_contracts"][1]["package"]), clean)
        proc = subprocess.run(
            [
                pwsh, "-NoProfile", "-File", str(script),
                "-InstallPath", str(clean),
                "-PackagePath", str(tampered_target),
            ],
            text=True, capture_output=True
        )
        if proc.returncode == 0:
            die("tampered bootstrap package was accepted")
        if str(load(clean / "build.json").get("build", "")) != str(spec.get("source_build", "")):
            die("tampered-package rejection modified installation")
        print("PASS rescue rejects wrong bootstrap package SHA before migration")

if __name__ == "__main__":
    run()
