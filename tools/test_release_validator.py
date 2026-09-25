#!/usr/bin/env python3
import argparse, base64, copy, json, pathlib, tempfile
import validate_release_compat as v

ROOT = pathlib.Path(__file__).resolve().parents[1]

def pointer_package(pointer_file):
    p = json.loads((ROOT/pointer_file).read_text(encoding="utf-8"))
    rel = p["package_url"].split("/main/",1)[1]
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def expect_reject(name, pkg):
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
        json.dump(pkg, f, separators=(",",":"))
        path = pathlib.Path(f.name)
    try:
        try:
            v.validate_package(path)
        except SystemExit:
            print("PASS reject:", name)
            return
        raise AssertionError(f"validator accepted invalid case: {name}")
    finally:
        path.unlink(missing_ok=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pointer-file", default="release/latest.json")
    args=ap.parse_args()
    base = pointer_package(args.pointer_file)

    x=copy.deepcopy(base); x["channel"]="DEV"; expect_reject("wrong channel",x)
    x=copy.deepcopy(base); x["mode"]="dev-delta"; expect_reject("release delta mode",x)
    x=copy.deepcopy(base); x["files"][0]["size"]+=1; expect_reject("wrong size",x)
    x=copy.deepcopy(base); x["files"][0]["sha256"]="0"*64; expect_reject("wrong file sha",x)
    x=copy.deepcopy(base); x["files"].append(copy.deepcopy(x["files"][0])); expect_reject("duplicate path",x)

    x=copy.deepcopy(base)
    bad=copy.deepcopy(x["files"][0]); bad["path"]="updater.html"
    x["files"].append(bad); expect_reject("legacy-incompatible root path",x)

    x=copy.deepcopy(base)
    bad=copy.deepcopy(x["files"][0]); bad["path"]="../escape.js"
    x["files"].append(bad); expect_reject("path traversal",x)

    x=copy.deepcopy(base)
    x["files"]=[f for f in x["files"] if f["path"]!="manifest.json"]
    expect_reject("missing required file",x)

    x=copy.deepcopy(base)
    man=next(f for f in x["files"] if f["path"]=="manifest.json")
    raw=base64.b64decode(man["content_base64"])
    obj=json.loads(raw.decode("utf-8")); obj["version"]="9.9.9"
    new=(json.dumps(obj,separators=(",",":"))).encode("utf-8")
    man["content_base64"]=base64.b64encode(new).decode("ascii")
    man["size"]=len(new); man["sha256"]=v.sha256_bytes(new)
    expect_reject("manifest version mismatch",x)

    print("PASS adversarial validator suite")

if __name__=="__main__":
    main()
