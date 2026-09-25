#!/usr/bin/env python3
import base64, hashlib, json, pathlib, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parents[1]

def die(msg):
    print("ERROR:",msg,file=sys.stderr)
    raise SystemExit(1)

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def pointer():
    p=json.loads((ROOT/"dev/self-update.json").read_text(encoding="utf-8"))
    url=str(p.get("package_url",""))
    marker="/main/"
    if marker not in url: die("DEV package_url no apunta a main")
    rel=url.split(marker,1)[1]
    path=ROOT/rel
    if not path.exists(): die(f"DEV package no existe: {rel}")
    raw=path.read_bytes()
    if sha256(raw)!=str(p.get("package_sha256","")).lower():
        die("DEV pointer SHA no coincide con package")
    return p,rel,path,json.loads(raw.decode("utf-8"))

def updater_bytes(package_path):
    pkg=json.loads(package_path.read_text(encoding="utf-8"))
    item=next((f for f in pkg.get("files",[]) if f.get("path")=="js/95-local-updater.js"),None)
    if not item: die(f"{package_path}: sin updater")
    b=base64.b64decode(item["content_base64"],validate=True)
    if sha256(b)!=str(item.get("sha256","")).lower(): die("historical updater SHA interno inválido")
    return b

def main():
    hist=json.loads((ROOT/"dev/history.json").read_text(encoding="utf-8"))
    ptr,rel,target_path,target=pointer()

    # DEV fix13 package contract: 9 mandatory root files + js/*.js.
    required={
      "manifest.json","build.json","background.js","popup.html","popup.js",
      "icon128.png","integrity-manifest.json","updater.html","updater.js"
    }
    paths=[str(x.get("path","")) for x in target.get("files",[])]
    missing=sorted(required-set(paths))
    invalid=sorted(p for p in paths if p not in required and not (p.startswith("js/") and p.endswith(".js") and "\\" not in p and ".." not in p))
    if missing: die(f"DEV candidate incompatible with fix13, missing: {missing}")
    if invalid: die(f"DEV candidate has paths fix13 rejects: {invalid}")

    floor=hist["compatibility_floor"]
    source=ROOT/floor["updater_package"]
    ub=updater_bytes(source)
    if sha256(ub)!=floor["updater_sha256"]:
        die("DEV floor updater fingerprint changed")

    with tempfile.TemporaryDirectory() as td:
        td=pathlib.Path(td)
        up=td/"legacy-updater.js"; up.write_bytes(ub)
        cmd=[
          "node",str(ROOT/"tools/run_updater_validate.mjs"),str(up),str(target_path),
          str(target.get("version","")),str(target.get("build","")),str(target.get("channel",""))
        ]
        proc=subprocess.run(cmd,text=True,capture_output=True)
        if proc.returncode:
            die(f"DEV fix13 -> candidate FAILED\nstdout:{proc.stdout}\nstderr:{proc.stderr}")

    print(f"PASS DEV exact updater matrix: fix13 -> {rel}")
    print(f"PASS DEV pointer SHA: {ptr.get('package_sha256')}")

if __name__=="__main__":
    main()
