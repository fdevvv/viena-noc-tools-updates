import base64
import hashlib
import json
import pathlib
import zipfile
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
OLD = "1.3.26-dev-popup-update-isolation-fix116"
NEW = "1.3.26-dev-fictitious-update-test-fix117"
OLD_PKG = ROOT / "dev" / "builds" / f"{OLD}.json"
NEW_PKG = ROOT / "dev" / "builds" / f"{NEW}.json"
POINTER = ROOT / "dev" / "self-update.json"
ZIP_OUT = ROOT / "downloads" / "VIENA_NOC_Tools_DEV_fix117.zip"

ptr = json.loads(POINTER.read_text(encoding="utf-8"))
if ptr.get("build") != OLD:
    raise SystemExit(f"DEV pointer moved: {ptr.get('build')}")

pkg = json.loads(OLD_PKG.read_text(encoding="utf-8"))
if pkg.get("build") != OLD:
    raise SystemExit(f"Unexpected base package: {pkg.get('build')}")

files = {}
meta_by_path = {}
for item in pkg["files"]:
    p = item["path"]
    files[p] = base64.b64decode(item["content_base64"])
    meta_by_path[p] = item

for p in ("popup.js", "background.js", "js/80-update-banner.js", "js/90-runtime-status.js"):
    text = files[p].decode("utf-8")
    if OLD not in text:
        raise SystemExit(f"{p}: FIX116 identity missing")
    files[p] = text.replace(OLD, NEW).encode("utf-8")

build = json.loads(files["build.json"].decode("utf-8"))
build["build"] = NEW
build["generated_at"] = "2026-10-03T18:15:00Z"
files["build.json"] = (json.dumps(build, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

integrity = json.loads(files["integrity-manifest.json"].decode("utf-8"))
integrity["build"] = NEW
integrity["files"] = {
    p: hashlib.sha256(data).hexdigest()
    for p, data in files.items()
    if p != "integrity-manifest.json"
}
files["integrity-manifest.json"] = (json.dumps(integrity, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

pkg["build"] = NEW
pkg["generated_at"] = "2026-10-03T18:15:00Z"
new_items = []
for item in pkg["files"]:
    p = item["path"]
    data = files[p]
    updated = dict(item)
    updated["size"] = len(data)
    updated["sha256"] = hashlib.sha256(data).hexdigest()
    updated["content_base64"] = base64.b64encode(data).decode("ascii")
    new_items.append(updated)
pkg["files"] = new_items

pkg_bytes = (json.dumps(pkg, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
NEW_PKG.write_bytes(pkg_bytes)
pkg_sha = hashlib.sha256(pkg_bytes).hexdigest()

pointer = {
    "schema": 1,
    "version": "1.3.26",
    "build": NEW,
    "channel": "DEV",
    "package_url": f"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/dev/builds/{NEW}.json",
    "package_sha256": pkg_sha,
    "notes": [
        "FIX117 FICTICIO: build de prueba para validar el nuevo flujo de actualización de FIX116.",
        "No agrega lógica funcional: conserva íntegramente FIX116 y sólo avanza la identidad del build.",
        "Usar para comprobar detección automática al abrir, Buscar actualización DEV sin bloqueo y CTA Actualizar DEV con carpeta vinculada."
    ]
}
POINTER.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

ZIP_OUT.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(ZIP_OUT, "w", compression=zipfile.ZIP_STORED) as zf:
    for p, data in files.items():
        zf.writestr(p, data)

# Remove the one-shot generator and its workflow from the resulting branch.
for rel in ("tools/tmp_make_fix117.py", ".github/workflows/tmp-fix117-fictitious.yml"):
    path = ROOT / rel
    if path.exists():
        path.unlink()

print(json.dumps({
    "build": NEW,
    "package_sha256": pkg_sha,
    "zip_sha256": hashlib.sha256(ZIP_OUT.read_bytes()).hexdigest(),
    "zip_size": ZIP_OUT.stat().st_size,
}, indent=2))
