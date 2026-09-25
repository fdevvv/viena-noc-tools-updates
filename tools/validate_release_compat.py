#!/usr/bin/env python3
import argparse, base64, hashlib, json, pathlib, re, sys

LEGACY_ROOT = {
    "manifest.json","build.json","background.js","popup.html","popup.js",
    "icon128.png","integrity-manifest.json"
}
REQUIRED = LEGACY_ROOT.copy()
JS_RE = re.compile(r"^js/[A-Za-z0-9._-]+\.js$")

def die(msg):
    print("ERROR:", msg, file=sys.stderr)
    raise SystemExit(1)

def safe_path(path):
    return path in LEGACY_ROOT or bool(JS_RE.fullmatch(path))

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def validate_package(path):
    raw = path.read_bytes()
    pkg = json.loads(raw.decode("utf-8"))
    if pkg.get("schema") != 1 or pkg.get("app") != "VIENA NOC Tools":
        die(f"{path}: package schema/app inválido")
    if str(pkg.get("channel","")).upper() != "RELEASE":
        die(f"{path}: channel debe ser RELEASE")
    if pkg.get("mode","full") != "full":
        die(f"{path}: RELEASE debe usar mode=full")
    files = pkg.get("files")
    if not isinstance(files,list) or not files:
        die(f"{path}: files inválido")
    seen, decoded = set(), {}
    for item in files:
        p = str(item.get("path",""))
        if p in seen: die(f"{path}: archivo duplicado {p}")
        seen.add(p)
        if not safe_path(p): die(f"{path}: ruta incompatible con updater 1.3.24: {p}")
        try: b = base64.b64decode(item.get("content_base64",""), validate=True)
        except Exception as e: die(f"{path}: base64 inválido en {p}: {e}")
        if len(b) != int(item.get("size",-1)): die(f"{path}: size incorrecto en {p}")
        got = sha256_bytes(b)
        if got != str(item.get("sha256","")).lower(): die(f"{path}: SHA incorrecto en {p}")
        decoded[p] = b
    missing = sorted(REQUIRED - seen)
    if missing: die(f"{path}: faltan archivos requeridos: {missing}")

    manifest = json.loads(decoded["manifest.json"].decode("utf-8"))
    build = json.loads(decoded["build.json"].decode("utf-8"))
    integ = json.loads(decoded["integrity-manifest.json"].decode("utf-8"))
    version, build_id = str(pkg.get("version","")), str(pkg.get("build",""))
    if manifest.get("version") != version: die(f"{path}: manifest.version != package.version")
    if str(build.get("version","")) != version or str(build.get("build","")) != build_id or str(build.get("channel","")).upper() != "RELEASE":
        die(f"{path}: build.json no coincide con package")
    if str(integ.get("version","")) != version or str(integ.get("build","")) != build_id or str(integ.get("channel","")).upper() != "RELEASE":
        die(f"{path}: integrity-manifest no coincide con package")
    inv = integ.get("files")
    if not isinstance(inv,dict): die(f"{path}: integrity.files inválido")
    for p,h in inv.items():
        if not safe_path(p): die(f"{path}: integrity contiene ruta incompatible con 1.3.24: {p}")
        if p not in decoded: die(f"{path}: integrity referencia archivo ausente: {p}")
        if sha256_bytes(decoded[p]) != str(h).lower(): die(f"{path}: integrity mismatch: {p}")
    print(f"PASS {path}: compatible con updater 1.3.24, {len(files)} archivos")
    return sha256_bytes(raw)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--package")
    ap.add_argument("--pointer", action="store_true")
    ap.add_argument("--pointer-file", default="version.json")
    args = ap.parse_args()
    root = pathlib.Path(args.repo_root)
    if args.pointer:
        vpath = root/args.pointer_file
        v = load_json(vpath)
        url = str(v.get("package_url",""))
        marker = "/main/"
        if marker not in url: die("version.json package_url no apunta a main")
        rel = url.split(marker,1)[1]
        p = root/rel
        got = validate_package(p)
        want = str(v.get("package_sha256","")).lower()
        if got != want: die(f"version.json package_sha256 no coincide: {got} != {want}")
        print(f"PASS {args.pointer_file} -> {rel}: SHA correcto")
    if args.package:
        validate_package(root/args.package)
    if not args.pointer and not args.package:
        die("usar --pointer y/o --package")

if __name__ == "__main__":
    main()
