#!/usr/bin/env python3
import base64, hashlib, json, pathlib
from datetime import datetime, timezone

R = pathlib.Path(__file__).resolve().parents[1]
SRC = R / "dev/builds/1.3.26-dev-update-actions-layout-fix88.json"
DST_REL = "dev/builds/1.3.26-dev-manual-zip-label-fix89.json"
DST = R / DST_REL
OLD = "1.3.26-dev-update-actions-layout-fix88"
NEW = "1.3.26-dev-manual-zip-label-fix89"

def h(b):
    return hashlib.sha256(b).hexdigest()

pkg = json.loads(SRC.read_text(encoding="utf-8"))
files = {}
order = []
for item in pkg["files"]:
    b = base64.b64decode(item["content_base64"], validate=True)
    assert h(b) == item["sha256"]
    files[item["path"]] = b
    order.append(item["path"])

html = files["popup.html"].decode("utf-8")
popup = files["popup.js"].decode("utf-8")

# Minimal visual fix: shorten the manual ZIP label so both update actions fit on one line.
assert '>Descargar ZIP manual</button>' in html
html = html.replace('>Descargar ZIP manual</button>', '>Descargar ZIP</button>', 1)

old_dynamic = "manualReleaseZipBtn.textContent = `Descargar ZIP manual · v${target.latest}`;"
new_dynamic = "manualReleaseZipBtn.textContent = `Descargar ZIP · v${target.latest}`;"
assert old_dynamic in popup
popup = popup.replace(old_dynamic, new_dynamic, 1)

# Keep both actions visually balanced and prevent accidental wrapping at normal popup width.
old_css = "white-space:normal!important;"
assert old_css in html
html = html.replace(old_css, "white-space:nowrap!important;", 1)

files["popup.html"] = html.encode("utf-8")
files["popup.js"] = popup.encode("utf-8")

for path in ("background.js", "js/80-update-banner.js", "js/90-runtime-status.js"):
    s = files[path].decode("utf-8")
    assert OLD in s, f"{OLD} missing in {path}"
    files[path] = s.replace(OLD, NEW, 1).encode("utf-8")

build = json.loads(files["build.json"].decode("utf-8"))
build["build"] = NEW
files["build.json"] = (json.dumps(build, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

integ = json.loads(files["integrity-manifest.json"].decode("utf-8"))
integ["build"] = NEW
integ["files"] = {p: h(b) for p, b in files.items() if p != "integrity-manifest.json"}
files["integrity-manifest.json"] = (json.dumps(integ, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

pkg["build"] = NEW
pkg["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
pkg["files"] = []
for path in order:
    b = files[path]
    pkg["files"].append({
        "path": path,
        "size": len(b),
        "sha256": h(b),
        "content_base64": base64.b64encode(b).decode("ascii")
    })

raw = (json.dumps(pkg, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
DST.write_bytes(raw)

ptr = json.loads((R / "dev/self-update.json").read_text(encoding="utf-8"))
ptr.update({
    "build": NEW,
    "package_url": "https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/" + DST_REL,
    "package_sha256": h(raw),
    "notes": [
        "Se acorta el texto del botón de descarga manual para evitar el salto de línea en el popup.",
        "Buscar actualización DEV y Descargar ZIP quedan alineados, con la misma altura y en una sola línea.",
        "No se modifica la lógica de actualización ni la disponibilidad exclusiva del ZIP manual."
    ]
})
(R / "dev/self-update.json").write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

hist = json.loads((R / "dev/history.json").read_text(encoding="utf-8"))
hist["current_build"] = NEW
hist["current_package"] = DST_REL
(R / "dev/history.json").write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Regression checks
assert 'Descargar ZIP · v${target.latest}' in popup
assert 'Descargar ZIP manual · v${target.latest}' not in popup
assert 'white-space:nowrap!important;' in html
assert "new Set(['efoschi'])" in popup
assert "new Set(['mbruno'])" in popup
assert "VIENA_NOC_Tools_RELEASE_v${latest}.zip" in popup
print(json.dumps({"build": NEW, "package": DST_REL, "package_sha256": h(raw)}, ensure_ascii=False, indent=2))
