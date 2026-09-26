#!/usr/bin/env python3
import argparse, base64, hashlib, json, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

def die(msg):
    print("ERROR:", msg, file=sys.stderr)
    raise SystemExit(1)

def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

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
        path = install.joinpath(*pathlib.PurePosixPath(str(item["path"])).parts)
        if not path.exists() or sha256(path) != str(item["sha256"]).lower():
            die(f"repair output mismatch: {item['path']}")
    if load(install/"build.json").get("build") != target_pkg.get("build"):
        die("repair output build mismatch")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--require-pwsh",action="store_true")
    args=ap.parse_args()
    pwsh=shutil.which("pwsh")
    if not pwsh:
        if args.require_pwsh: die("pwsh is required")
        print("SKIP v4->v5 repair integration: pwsh unavailable")
        return

    spec=load(ROOT/"release/rescue/bootstrap-v4-to-v5.json")
    source_path=ROOT/spec["source"]["package"]
    target_path=ROOT/spec["target"]["package"]
    script=ROOT/spec["script"]
    if not script.read_bytes().startswith(b"\xef\xbb\xbf"):
        die("repair script must carry UTF-8 BOM")

    source_pkg=load(source_path)
    target_pkg=load(target_path)

    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        install=root/"install-v4"
        decode_package(source_pkg,install)
        proc=subprocess.run([pwsh,"-NoProfile","-File",str(script),"-InstallPath",str(install),"-PackagePath",str(target_path)],text=True,capture_output=True)
        if proc.returncode != 0:
            die(f"v4->v5 repair failed\nstdout:{proc.stdout}\nstderr:{proc.stderr}")
        assert_target(install,target_pkg)
        backups=list(root.glob("install-v4_BACKUP_BEFORE_V5_*"))
        if len(backups)!=1 or load(backups[0]/"build.json").get("build")!=spec["source"]["build"]:
            die("repair backup validation failed")
        print("PASS v4->v5 repair integration")

        tampered=root/"tampered-source"
        decode_package(source_pkg,tampered)
        p=tampered/"js"/"90-runtime-status.js"
        p.write_bytes(p.read_bytes()+b"\n//tampered")
        proc=subprocess.run([pwsh,"-NoProfile","-File",str(script),"-InstallPath",str(tampered),"-PackagePath",str(target_path)],text=True,capture_output=True)
        if proc.returncode == 0:
            die("tampered v4 source was accepted")
        if load(tampered/"build.json").get("build")!=spec["source"]["build"]:
            die("tampered-source rejection modified installation")
        print("PASS repair rejects tampered v4 before write")

        clean=root/"clean-source"
        decode_package(source_pkg,clean)
        bad_target=root/"bad-target.json"
        bad_target.write_bytes(target_path.read_bytes()+b"\n")
        proc=subprocess.run([pwsh,"-NoProfile","-File",str(script),"-InstallPath",str(clean),"-PackagePath",str(bad_target)],text=True,capture_output=True)
        if proc.returncode == 0:
            die("tampered v5 package was accepted")
        if load(clean/"build.json").get("build")!=spec["source"]["build"]:
            die("tampered-target rejection modified installation")
        print("PASS repair rejects tampered v5 before write")

if __name__=="__main__":
    main()
