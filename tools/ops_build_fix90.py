#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

R = pathlib.Path(__file__).resolve().parents[1]
SRC = R / "dev/builds/1.3.26-dev-manual-zip-label-fix89.json"
DST_REL = "dev/builds/1.3.26-dev-update-button-size-fix90.json"
DST = R / DST_REL
OLD = "1.3.26-dev-manual-zip-label-fix89"
NEW = "1.3.26-dev-update-button-size-fix90"

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

# Mark the existing "Buscar actualización" button without changing its behavior.
m = re.search(r'(<button\\b[^>]*>)(.*?Buscar actualización.*?)(</button>)', html, re.I | re.S)
if not m:
    labels=[]
    for bm in re.finditer(r'<button\\b[^>]*>(.*?)</button>', html, re.I|re.S):
        label=re.sub(r'<[^>]+>',' ',bm.group(1))
        label=' '.join(label.split())
        labels.append(label[:140])
    raise AssertionError("Buscar actualización button not found. Buttons="+repr(labels))
open_tag = m.group(1)
if 'class=' in open_tag:
    open_tag = re.sub(r"class=([\"'])(.*?)\\1",
                      lambda mm: f'class={mm.group(1)}{mm.group(2)} viena-update-equal-size{mm.group(1)}',
                      open_tag, count=1)
else:
    open_tag = open_tag[:-1] + ' class="viena-update-equal-size">'
html = html[:m.start()] + open_tag + m.group(2) + m.group(3) + html[m.end():]

# Mark current update/install and manual ZIP buttons. Logic/ids stay intact.
for button_id in ("openUpdate", "manualReleaseZip"):
    pattern = rf"(<button\\b[^>]*\\bid=[\"']{button_id}[\"'][^>]*>)"
    mm = re.search(pattern, html, re.I)
    assert mm, f"{button_id} not found"
    tag = mm.group(1)
    if 'class=' in tag:
        tag2 = re.sub(r"class=([\"'])(.*?)\\1",
                      lambda x: f'class={x.group(1)}{x.group(2)} viena-update-equal-size{x.group(1)}',
                      tag, count=1)
    else:
        tag2 = tag[:-1] + ' class="viena-update-equal-size">'
    html = html[:mm.start()] + tag2 + html[mm.end():]

css = r"""
<style id="viena-update-button-size-fix90">
  .viena-update-equal-size{
    box-sizing:border-box!important;
    width:100%!important;
    min-width:0!important;
    height:52px!important;
    min-height:52px!important;
    max-height:52px!important;
    padding:8px 10px!important;
    display:flex!important;
    align-items:center!important;
    justify-content:center!important;
    text-align:center!important;
    line-height:1.15!important;
    white-space:normal!important;
    overflow:hidden!important;
  }
  .viena-update-actions{
    align-items:start!important;
  }
  .viena-update-actions > .viena-update-equal-size{
    align-self:start!important;
  }
</style>
"""
assert "</head>" in html
html = html.replace("</head>", css + "\n</head>", 1)

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
integ["files"] = {p: h(b) for p,b in files.items() if p != "integrity-manifest.json"}
files["integrity-manifest.json"] = (json.dumps(integ, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

pkg["build"] = NEW
pkg["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
pkg["files"] = []
for path in order:
    b = files[path]
    pkg["files"].append({
        "path":path,
        "size":len(b),
        "sha256":h(b),
        "content_base64":base64.b64encode(b).decode("ascii")
    })

raw = (json.dumps(pkg, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
DST.write_bytes(raw)

ptr = json.loads((R/"dev/self-update.json").read_text(encoding="utf-8"))
ptr.update({
    "build":NEW,
    "package_url":"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/"+DST_REL,
    "package_sha256":h(raw),
    "notes":[
        "Se iguala el alto visual de Buscar actualización, Actualizar y Descargar ZIP en el popup.",
        "Se evita que Buscar actualización se estire verticalmente cuando aparecen dos acciones en la columna contigua.",
        "No se modifica ninguna lógica de actualización, descarga manual ni elegibilidad por usuario."
    ]
})
(R/"dev/self-update.json").write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist = json.loads((R/"dev/history.json").read_text(encoding="utf-8"))
hist["current_build"] = NEW
hist["current_package"] = DST_REL
(R/"dev/history.json").write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

# Regression checks
out = files["popup.html"].decode("utf-8")
assert out.count("viena-update-equal-size") >= 4  # 3 buttons + CSS selector
assert 'height:52px!important;' in out
assert 'id="manualReleaseZip"' in out
assert 'id="openUpdate"' in out
assert "new Set(['efoschi'])" in popup
assert "new Set(['mbruno'])" in popup
assert "VIENA_NOC_Tools_RELEASE_v${latest}.zip" in popup
print(json.dumps({"build":NEW,"package":DST_REL,"package_sha256":h(raw)},ensure_ascii=False,indent=2))
