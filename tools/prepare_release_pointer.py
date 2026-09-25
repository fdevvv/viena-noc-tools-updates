#!/usr/bin/env python3
import argparse, hashlib, json, pathlib, sys
import validate_release_compat as validator

ROOT=pathlib.Path(__file__).resolve().parents[1]

def die(msg):
    print("ERROR:",msg,file=sys.stderr)
    raise SystemExit(1)

def semver(v):
    try:
        p=tuple(int(x) for x in str(v).split("."))
        if len(p)!=3: raise ValueError()
        return p
    except Exception:
        die(f"invalid semver: {v}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidate",required=True)
    ap.add_argument("--notes",default="")
    ap.add_argument("--minimum",default="1.3.25")
    ap.add_argument("--mandatory",action="store_true")
    args=ap.parse_args()

    rel=pathlib.PurePosixPath(args.candidate)
    if rel.is_absolute() or ".." in rel.parts or not str(rel).startswith("release/") or not str(rel).endswith(".json"):
        die("candidate must be an immutable JSON artifact under release/")
    if str(rel) in {"release/latest.json","release/bootstrap.json"}:
        die("candidate cannot be a pointer/config file")
    path=ROOT/rel
    if not path.exists(): die(f"candidate not found: {rel}")

    validator.validate_package(path)
    pkg=json.loads(path.read_text(encoding="utf-8"))
    current=json.loads((ROOT/"release/latest.json").read_text(encoding="utf-8"))
    if semver(pkg["version"]) <= semver(current["latest"]):
        die(f"candidate version {pkg['version']} must be greater than current modern release {current['latest']}")
    if pkg.get("remove"): die("RELEASE candidate must not remove files")
    if pkg.get("patches"): die("RELEASE candidate must not contain text patches")

    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    notes=[x.strip() for x in args.notes.splitlines() if x.strip()]
    if not notes:
        notes=[f"VIENA NOC Tools {pkg['version']}"]

    pointer={
      "schema":2,
      "role":"modern-release",
      "latest":str(pkg["version"]),
      "minimum":args.minimum,
      "mandatory":bool(args.mandatory),
      "notes":notes[:8],
      "package_url":f"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/{rel}",
      "package_sha256":digest,
      "source_package":str(rel),
      "promotion_gate":"release-update-safety-v2"
    }
    (ROOT/"release/latest.json").write_text(json.dumps(pointer,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"PREPARED release/latest.json -> {rel} ({digest})")

if __name__=="__main__":
    main()
