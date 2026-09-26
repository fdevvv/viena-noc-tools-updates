#!/usr/bin/env python3
import base64, hashlib, json, pathlib, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parents[1]

def die(msg):
    print("ERROR:",msg,file=sys.stderr)
    raise SystemExit(1)

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def pointer():
    p=load(ROOT/"dev/self-update.json")
    url=str(p.get("package_url",""))
    marker="/main/"
    if marker not in url:
        die("DEV package_url no apunta a main")
    rel=url.split(marker,1)[1]
    path=ROOT/rel
    if not path.exists():
        die(f"DEV package no existe: {rel}")
    raw=path.read_bytes()
    if sha256(raw)!=str(p.get("package_sha256","")).lower():
        die("DEV pointer SHA no coincide con package")
    pkg=json.loads(raw.decode("utf-8"))
    if str(pkg.get("version","")) != str(p.get("version","")):
        die("DEV pointer/package version mismatch")
    if str(pkg.get("build","")) != str(p.get("build","")):
        die("DEV pointer/package build mismatch")
    if str(pkg.get("channel","")).upper() != "DEV":
        die("DEV candidate channel must be DEV")
    return p,rel,path,pkg

def updater_bytes(package_path):
    pkg=load(package_path)
    item=next((f for f in pkg.get("files",[]) if f.get("path")=="js/95-local-updater.js"),None)
    if not item:
        die(f"{package_path}: sin updater")
    try:
        b=base64.b64decode(item["content_base64"],validate=True)
    except Exception as e:
        die(f"{package_path}: updater base64 invalido: {e}")
    if sha256(b)!=str(item.get("sha256","")).lower():
        die(f"{package_path}: historical updater SHA interno invalido")
    return b, pkg

def validate_portable_profile(hist,target):
    profile=hist.get("portable_profile") or {}
    if not profile:
        return
    if str(target.get("profile","")) != str(profile.get("id","")):
        die(f"DEV candidate must use portable profile {profile.get('id')}")
    if str(target.get("mode","")) != str(profile.get("mode","")):
        die(f"DEV portable candidate mode must be {profile.get('mode')}")
    if target.get("patches"):
        die("DEV portable candidate must not contain patches")
    if target.get("remove"):
        die("DEV portable candidate must not remove files")

    paths=[str(x.get("path","")) for x in target.get("files",[])]
    if len(paths) != len(set(paths)):
        die("DEV portable candidate contains duplicate paths")

    forbidden=set(map(str,profile.get("forbidden_package_paths",[])))
    bad=sorted(forbidden & set(paths))
    if bad:
        die(f"DEV portable candidate contains forked legacy paths: {bad}")

    required=set(map(str,profile.get("required_root_files",[])))
    missing=sorted(required-set(paths))
    if missing:
        die(f"DEV portable candidate missing required portable files: {missing}")

    invalid=sorted(
        p for p in paths
        if p not in required and not (p.startswith("js/") and p.endswith(".js") and "\\" not in p and ".." not in p)
    )
    if invalid:
        die(f"DEV portable candidate has unauthorized paths: {invalid}")

    file_map={str(x.get("path","")):x for x in target.get("files",[])}
    integrity_item=file_map.get("integrity-manifest.json")
    if not integrity_item:
        die("DEV portable candidate missing integrity-manifest.json")
    try:
        integrity=json.loads(base64.b64decode(integrity_item["content_base64"],validate=True).decode("utf-8"))
    except Exception as e:
        die(f"DEV portable integrity manifest invalid: {e}")

    inventory=integrity.get("files")
    if not isinstance(inventory,dict) or not inventory:
        die("DEV portable integrity inventory invalid")
    expected=set(paths)-{"integrity-manifest.json"}
    if set(inventory)!=expected:
        missing_inv=sorted(expected-set(inventory))
        extra_inv=sorted(set(inventory)-expected)
        die(f"DEV portable integrity inventory mismatch missing={missing_inv} extra={extra_inv}")
    for path,expected_hash in inventory.items():
        if str(file_map[path].get("sha256","")).lower()!=str(expected_hash).lower():
            die(f"DEV portable integrity hash mismatch for {path}")

def package_text(target,path):
    item=next((x for x in target.get("files",[]) if str(x.get("path",""))==path),None)
    if not item:
        die(f"DEV candidate missing runtime identity file: {path}")
    try:
        return base64.b64decode(item["content_base64"],validate=True).decode("utf-8")
    except Exception as e:
        die(f"DEV candidate cannot decode {path}: {e}")

def const_value(source,name,path):
    m=re.search(rf"\bconst\s+{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]",source)
    if not m:
        die(f"DEV candidate missing {name} in {path}")
    return m.group(1)

def validate_runtime_identity(target):
    expected=str(target.get("build",""))
    if not expected:
        die("DEV candidate build is empty")

    background=package_text(target,"background.js")
    banner=package_text(target,"js/80-update-banner.js")
    runtime=package_text(target,"js/90-runtime-status.js")
    build_json=json.loads(package_text(target,"build.json"))
    manifest=json.loads(package_text(target,"manifest.json"))

    actual={
        "background.js:VIENA_BUILD_ID": const_value(background,"VIENA_BUILD_ID","background.js"),
        "js/80-update-banner.js:CONTENT_BUILD_ID": const_value(banner,"CONTENT_BUILD_ID","js/80-update-banner.js"),
        "js/90-runtime-status.js:BUILD_ID": const_value(runtime,"BUILD_ID","js/90-runtime-status.js"),
    }
    bad={k:v for k,v in actual.items() if v!=expected}
    if bad:
        die(f"DEV runtime build identity mismatch expected={expected} actual={bad}")

    if str(build_json.get("build",""))!=expected:
        die("DEV build.json build does not match package build")
    if str(build_json.get("version",""))!=str(target.get("version","")):
        die("DEV build.json version does not match package version")
    if str(build_json.get("channel","")).upper()!="DEV":
        die("DEV build.json channel must be DEV")
    if str(manifest.get("version",""))!=str(target.get("version","")):
        die("DEV manifest version does not match package version")
    if "DEV" not in str(manifest.get("name","")).upper():
        die("DEV manifest name must identify the DEV channel")

    print(f"PASS DEV runtime identity coherence: {expected}")

def main():
    hist=load(ROOT/"dev/history.json")
    ptr,rel,target_path,target=pointer()
    validate_portable_profile(hist,target)
    validate_runtime_identity(target)

    contracts=hist.get("contracts")
    if not contracts:
        floor=hist.get("compatibility_floor") or {}
        contracts=[{
            "id": floor.get("id","dev-floor"),
            "package": floor.get("updater_package"),
            "updater_sha256": floor.get("updater_sha256"),
            "must_support_future_upgrade": True,
        }]

    harness=ROOT/"tools/run_updater_validate.mjs"
    tested=0
    with tempfile.TemporaryDirectory() as td:
        td=pathlib.Path(td)
        for idx,contract in enumerate(contracts):
            if not contract.get("must_support_future_upgrade",False):
                continue
            source_rel=str(contract.get("package",""))
            if not source_rel:
                die(f"{contract.get('id')}: historical package missing from history")
            source=ROOT/source_rel
            if not source.exists():
                die(f"{contract.get('id')}: historical source package missing: {source_rel}")
            ub,source_pkg=updater_bytes(source)
            fingerprint=str(contract.get("updater_sha256","")).lower()
            if not fingerprint or sha256(ub)!=fingerprint:
                die(f"{contract.get('id')}: historical updater fingerprint changed")
            if str(source_pkg.get("build","")) == str(target.get("build","")):
                continue

            up=td/f"historical-{idx}.js"
            up.write_bytes(ub)
            cmd=[
                "node",str(harness),str(up),str(target_path),
                str(target.get("version","")),str(target.get("build","")),str(target.get("channel",""))
            ]
            proc=subprocess.run(cmd,text=True,capture_output=True)
            if proc.returncode:
                die(
                    f"{contract.get('id')} ({source_pkg.get('build')}) -> {target.get('build')} FAILED\n"
                    f"stdout:{proc.stdout}\nstderr:{proc.stderr}"
                )
            print(f"PASS exact DEV updater: {contract.get('id')} -> {rel}")
            tested += 1

    if tested < 2:
        die(f"DEV updater matrix too small: tested={tested}; expected historical fork coverage")
    print(f"PASS DEV exact updater matrix: tested={tested}, target={rel}")
    print(f"PASS DEV pointer SHA: {ptr.get('package_sha256')}")
    print(f"PASS DEV profile: {target.get('profile') or target.get('mode')}")

if __name__=="__main__":
    main()
