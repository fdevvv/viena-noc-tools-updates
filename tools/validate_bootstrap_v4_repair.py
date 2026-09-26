#!/usr/bin/env python3
import base64, hashlib, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]

def die(msg):
    print("ERROR:",msg,file=sys.stderr); raise SystemExit(1)

def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def extract(pkg,path):
    item=next((x for x in pkg.get("files",[]) if x.get("path")==path),None)
    if not item: die(f"missing {path}")
    raw=base64.b64decode(item["content_base64"],validate=True)
    if len(raw)!=int(item["size"]) or hashlib.sha256(raw).hexdigest()!=str(item["sha256"]).lower():
        die(f"invalid payload {path}")
    return raw

def main():
    spec=load(ROOT/"release/rescue/bootstrap-v4-to-v5.json")
    if spec.get("role")!="bootstrap-v4-runtime-coherence-repair": die("invalid repair role")
    src=spec["source"]; tgt=spec["target"]
    sp=ROOT/src["package"]; tp=ROOT/tgt["package"]
    if sha(sp)!=src["package_sha256"]: die("source package SHA mismatch")
    if sha(tp)!=tgt["package_sha256"]: die("target package SHA mismatch")
    s=load(sp); t=load(tp)
    for obj,cfg,label in ((s,src,"source"),(t,tgt,"target")):
        if obj.get("version")!=cfg["version"] or obj.get("build")!=cfg["build"] or str(obj.get("channel","")).upper()!=cfg["channel"]:
            die(f"{label} identity mismatch")
    if hashlib.sha256(extract(s,"integrity-manifest.json")).hexdigest()!=src["integrity_manifest_sha256"]:
        die("source integrity-manifest SHA mismatch")
    expected=tgt["build"]
    if f"const VIENA_BUILD_ID = '{expected}'" not in extract(t,"background.js").decode("utf-8"):
        die("target background build mismatch")
    if f"const BUILD_ID = '{expected}'" not in extract(t,"js/90-runtime-status.js").decode("utf-8"):
        die("target runtime-status build mismatch")
    if f"const CONTENT_BUILD_ID='{expected}'" not in extract(t,"js/80-update-banner.js").decode("utf-8"):
        die("target update-banner build mismatch")
    script=ROOT/spec["script"]
    if not script.read_bytes().startswith(b"\xef\xbb\xbf"): die("repair script lacks UTF-8 BOM")
    text=script.read_text(encoding="utf-8-sig")
    for token in (src["build"],src["integrity_manifest_sha256"],tgt["build"],tgt["package_sha256"],tgt["modern_pointer"]):
        if token not in text: die(f"repair script missing token: {token}")
    print("PASS v4->v5 repair contract")

if __name__=="__main__":
    main()
