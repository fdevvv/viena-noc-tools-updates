#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

R = pathlib.Path(__file__).resolve().parents[1]
SRC = R / "dev/builds/1.3.26-dev-update-ui-manual-zip-fix87.json"
DST_REL = "dev/builds/1.3.26-dev-update-actions-layout-fix88.json"
DST = R / DST_REL
OLD = "1.3.26-dev-update-ui-manual-zip-fix87"
NEW = "1.3.26-dev-update-actions-layout-fix88"

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

# Keep the current functional buttons and only reorganize their visual container.
pair = re.compile(
    r'(?P<open><button\b[^>]*\bid=["\']openUpdate["\'][^>]*>.*?</button>)'
    r'\s*'
    r'(?P<manual><button\b[^>]*\bid=["\']manualReleaseZip["\'][^>]*>.*?</button>)',
    re.S
)
m = pair.search(html)
assert m, "update action buttons not found together"
assert 'class="viena-update-actions"' not in html

wrapped = (
    '<div class="viena-update-actions" aria-label="Acciones de actualización">'
    + m.group("open")
    + m.group("manual")
    + '</div>'
)
html = html[:m.start()] + wrapped + html[m.end():]

style = r"""
<style id="viena-update-actions-layout-fix88">
  .viena-update-actions{
    display:grid;
    grid-template-columns:minmax(0,1fr) minmax(0,1fr);
    gap:8px;
    margin-top:8px;
    align-items:stretch;
  }
  .viena-update-actions > button{
    width:100%!important;
    min-width:0!important;
    min-height:40px;
    margin:0!important;
    padding:8px 10px!important;
    border-radius:8px!important;
    line-height:1.2!important;
    white-space:normal!important;
    text-align:center!important;
    display:flex;
    align-items:center;
    justify-content:center;
  }
  .viena-update-actions #openUpdate{
    background:#eef6ff!important;
    border:1px solid #b8d6fb!important;
    color:#075fb8!important;
  }
  .viena-update-actions #manualReleaseZip{
    background:linear-gradient(180deg,#1684f6 0%,#0b69d1 100%)!important;
    border:1px solid #0b69d1!important;
    color:#fff!important;
    font-weight:700!important;
  }
  .viena-update-actions #manualReleaseZip:hover:not(:disabled){
    filter:brightness(.97);
  }
  .viena-update-actions:has(#manualReleaseZip[style*="display: none"]){
    grid-template-columns:1fr;
  }
  @media (max-width:340px){
    .viena-update-actions{grid-template-columns:1fr}
  }
</style>
"""
assert "</head>" in html
html = html.replace("</head>", style + "\n</head>", 1)
files["popup.html"] = html.encode("utf-8")

# Build identity follows the existing DEV chain without touching RELEASE.
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
        "Se reorganizan las acciones de actualización del popup para que Buscar actualización y Descargar ZIP manual queden alineadas y con la misma jerarquía visual.",
        "La descarga manual queda destacada como acción principal y Buscar actualización conserva un estilo secundario.",
        "El popup mantiene comportamiento responsive y, cuando la descarga manual no está habilitada para el usuario, Buscar actualización vuelve a ocupar todo el ancho."
    ]
})
(R / "dev/self-update.json").write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

hist = json.loads((R / "dev/history.json").read_text(encoding="utf-8"))
hist["current_build"] = NEW
hist["current_package"] = DST_REL
(R / "dev/history.json").write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Regression checks: preserve the manual ZIP eligibility/logic and the existing controls.
out = files["popup.html"].decode("utf-8")
popup_js = files["popup.js"].decode("utf-8")
assert 'class="viena-update-actions"' in out
assert 'id="openUpdate"' in out
assert 'id="manualReleaseZip"' in out
assert "new Set(['efoschi'])" in popup_js
assert "new Set(['mbruno'])" in popup_js
assert "VIENA_NOC_Tools_RELEASE_v${latest}.zip" in popup_js
print(json.dumps({
    "build": NEW,
    "package": DST_REL,
    "package_sha256": h(raw)
}, ensure_ascii=False, indent=2))
