#!/usr/bin/env python3
import argparse
import base64
import json
import pathlib
import subprocess
import sys
import tempfile

def semver(v):
    try:
        p = tuple(int(x) for x in str(v).split("."))
        return p if len(p) == 3 else (-1, -1, -1)
    except Exception:
        return (-1, -1, -1)

def die(msg):
    print("ERROR:", msg, file=sys.stderr)
    raise SystemExit(1)

def pointer_package(root, pointer_file):
    pointer = json.loads((root / pointer_file).read_text(encoding="utf-8"))
    url = str(pointer.get("package_url", ""))
    marker = "/main/"
    if marker not in url:
        die(f"{pointer_file} package_url no apunta a main")
    rel = url.split(marker, 1)[1]
    path = root / rel
    if not path.exists():
        die(f"package del pointer no existe: {rel}")
    return pointer, rel, path, json.loads(path.read_text(encoding="utf-8"))

def updater_from_package(package_path):
    pkg = json.loads(package_path.read_text(encoding="utf-8"))
    item = next((x for x in pkg.get("files", []) if x.get("path") == "js/95-local-updater.js"), None)
    if not item:
        die(f"{package_path}: no contiene js/95-local-updater.js")
    try:
        return base64.b64decode(item["content_base64"], validate=True)
    except Exception as e:
        die(f"{package_path}: updater base64 inválido: {e}")

def run_validator(harness, updater_bytes, target_path, target):
    with tempfile.TemporaryDirectory() as td:
        updater_path = pathlib.Path(td) / "updater.js"
        updater_path.write_bytes(updater_bytes)
        return subprocess.run(
            [
                "node", str(harness), str(updater_path), str(target_path),
                str(target.get("version", "")), str(target.get("build", "")),
                str(target.get("channel", ""))
            ],
            text=True, capture_output=True
        )

def validate_rescue_infrastructure(root):
    cmd = [
        sys.executable,
        str(root / "tools/validate_legacy_rescue.py"),
        "--repo-root", str(root)
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode:
        die(f"legacy rescue validation failed\nstdout: {proc.stdout}\nstderr: {proc.stderr}")
    if proc.stdout.strip():
        print(proc.stdout.strip())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--pointer-file", default="release/latest.json")
    args = ap.parse_args()

    root = pathlib.Path(args.repo_root).resolve()
    history = json.loads((root / "release/public-history.json").read_text(encoding="utf-8"))
    pointer, target_rel, target_path, target = pointer_package(root, args.pointer_file)
    tv = semver(target.get("version"))
    if tv == (-1, -1, -1):
        die("target version inválida")

    validate_rescue_infrastructure(root)

    harness = root / "tools/run_updater_validate.mjs"
    tested = 0
    skipped = 0
    rescue_routes = 0

    rescue_spec = json.loads((root / str(history.get("legacy_rescue_profile", ""))).read_text(encoding="utf-8"))
    rescue_target = rescue_spec.get("target_bootstrap") or {}
    rescue_target_rel = str(rescue_target.get("package", ""))
    if not rescue_target_rel or not (root / rescue_target_rel).exists():
        die("legacy rescue target is missing from the matrix")

    for src in history.get("contracts", []):
        if not src.get("must_support_future_upgrade", False):
            continue

        route = str(src.get("route", ""))
        if route == "bootstrap_only":
            skipped += 1
            continue

        if route == "legacy_rescue":
            if str(src.get("rescue_profile", "")) != str(history.get("legacy_rescue_profile", "")):
                die(f"{src.get('id')}: rescue_profile inconsistente")
            print(
                f"PASS rescue route registered: {src.get('id')} -> "
                f"{rescue_target.get('build')} -> {target_rel}"
            )
            rescue_routes += 1
            tested += 1
            continue

        if route != "modern":
            die(f"{src.get('id')}: route desconocida/no soportada: {route}")

        sv = semver(src.get("version"))
        if sv >= tv:
            skipped += 1
            continue

        source_path = root / str(src["package"])
        if not source_path.exists():
            die(f"historical source package missing: {source_path}")

        proc = run_validator(
            harness,
            updater_from_package(source_path),
            target_path,
            target
        )
        if proc.returncode != 0:
            die(
                f"{src.get('id')} ({src.get('version')}) -> {target.get('version')} FAILED\n"
                f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
            )
        print(f"PASS exact historical updater: {src.get('id')} -> {target_rel}")
        tested += 1

    if rescue_routes < 2:
        die("expected both historical 1.3.25 rescue contracts in matrix")

    print(
        f"PASS update matrix: tested={tested}, rescue_routes={rescue_routes}, "
        f"skipped_same_or_newer={skipped}, target={target_rel}"
    )

if __name__ == "__main__":
    main()
