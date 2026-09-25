#!/usr/bin/env python3
import argparse, base64, json, pathlib, subprocess, sys, tempfile

def semver(v):
    try:
        p = tuple(int(x) for x in str(v).split("."))
        return p if len(p) == 3 else (-1,-1,-1)
    except Exception:
        return (-1,-1,-1)

def die(msg):
    print("ERROR:", msg, file=sys.stderr)
    raise SystemExit(1)

def pointer_package(root, pointer_file):
    pointer = json.loads((root/pointer_file).read_text(encoding="utf-8"))
    url = str(pointer.get("package_url",""))
    marker = "/main/"
    if marker not in url:
        die("version.json package_url no apunta a main")
    rel = url.split(marker,1)[1]
    path = root/rel
    if not path.exists():
        die(f"package del pointer no existe: {rel}")
    return pointer, rel, path, json.loads(path.read_text(encoding="utf-8"))

def updater_from_package(package_path):
    pkg = json.loads(package_path.read_text(encoding="utf-8"))
    item = next((x for x in pkg.get("files",[]) if x.get("path") == "js/95-local-updater.js"), None)
    if not item:
        die(f"{package_path}: no contiene js/95-local-updater.js")
    try:
        return base64.b64decode(item["content_base64"], validate=True)
    except Exception as e:
        die(f"{package_path}: updater base64 inválido: {e}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--pointer-file", default="release/latest.json")
    args = ap.parse_args()
    root = pathlib.Path(args.repo_root)
    history = json.loads((root/"release/public-history.json").read_text(encoding="utf-8"))
    pointer, target_rel, target_path, target = pointer_package(root, args.pointer_file)
    tv = semver(target.get("version"))
    if tv == (-1,-1,-1):
        die("target version inválida")

    harness = root/"tools/run_updater_validate.mjs"
    tested = 0
    skipped = 0
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        for idx, src in enumerate(history.get("contracts", [])):
            if not src.get("must_support_future_upgrade", False):
                continue
            if src.get("route") == "bootstrap_only":
                continue
            sv = semver(src.get("version"))
            if sv >= tv:
                skipped += 1
                continue
            source_path = root/str(src["package"])
            if not source_path.exists():
                die(f"historical source package missing: {source_path}")
            updater_path = td/f"updater-{idx}.js"
            updater_path.write_bytes(updater_from_package(source_path))
            cmd = [
                "node", str(harness), str(updater_path), str(target_path),
                str(target.get("version","")), str(target.get("build","")), str(target.get("channel",""))
            ]
            proc = subprocess.run(cmd, text=True, capture_output=True)
            if proc.returncode != 0:
                q = " [QUARANTINED CONTRACT]" if src.get("quarantine") else ""
                die(
                    f"{src.get('id')} ({src.get('version')}) -> {target.get('version')} FAILED{q}\n"
                    f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
                )
            print(f"PASS exact historical updater: {src.get('id')} -> {target_rel}")
            tested += 1

    print(f"PASS update matrix: tested={tested}, skipped_same_or_newer={skipped}, target={target_rel}")

if __name__ == "__main__":
    main()
