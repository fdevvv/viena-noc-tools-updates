#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

R = pathlib.Path(__file__).resolve().parents[1]
SRC = R / "dev/builds/1.3.26-dev-update-buttons-final-align-fix91.json"
DST_REL = "dev/builds/1.3.26-dev-fullview-general-updates-fix92.json"
DST = R / DST_REL
OLD = "1.3.26-dev-update-buttons-final-align-fix91"
NEW = "1.3.26-dev-fullview-general-updates-fix92"

def h(b):
    return hashlib.sha256(b).hexdigest()

pkg = json.loads(SRC.read_text(encoding="utf-8"))
files = {}
order = []
for item in pkg["files"]:
    raw = base64.b64decode(item["content_base64"], validate=True)
    assert h(raw) == item["sha256"]
    files[item["path"]] = raw
    order.append(item["path"])

home = files["js/97-home-ui.js"].decode("utf-8")

# 1) Full-view navigation: only General + Personalización.
nav_marker = 'data-section=\\\"updates\\\"'
nav_i = home.find(nav_marker)
assert nav_i >= 0, "updates nav marker not found"
nav_a = home.rfind('<button', 0, nav_i)
nav_b = home.find('</button>', nav_i)
assert nav_a >= 0 and nav_b >= 0, "updates nav button bounds not found"
home = home[:nav_a] + home[nav_b + len('</button>'):]

# 2) General: keep an optimized read-only update summary; management stays in popup.
general_marker = '<h2>Actualizaciones</h2>'
general_i = home.find(general_marker)
assert general_i >= 0, "General updates card marker not found"
general_a = home.rfind('<article class=\\\"panel\\\">', 0, general_i)
general_b = home.find('</article>', general_i)
assert general_a >= 0 and general_b >= 0, "General updates card bounds not found"
general_update_replacement = r'''<article class=\"panel update-overview-panel\">
            <div class=\"panel-head\"><h2>Actualizaciones</h2><span class=\"status ok\">Resumen</span></div>
            <div class=\"update-summary\"><div><span>Instalada</span><b id=\"summaryInstalled\">—</b></div><div><span>Disponible</span><b id=\"summaryAvailable\">Comprobando…</b></div></div>
            <div id=\"summaryFolder\" class=\"info-line\">Carpeta vinculada: comprobando…</div>
            <div class=\"minor-status update-overview-note\">La instalación, búsqueda de actualizaciones y vinculación de carpeta se administran desde el popup.</div>
          </article>'''
home = home[:general_a] + general_update_replacement + home[general_b + len('</article>'):]

# 3) Remove the visible full-page Updates section. Keep its DOM IDs hidden for
# compatibility with the already-working updater bindings and event listeners.
compat = r'''<div id=\"fullViewUpdateCompat\" hidden aria-hidden=\"true\">
        <button id=\"checkUpdates\" type=\"button\"></button>
        <span id=\"updateStateBadge\"></span>
        <span id=\"updatesInstalled\"></span>
        <span id=\"updatesAvailable\"></span>
        <div id=\"updateMessage\"></div>
        <button id=\"runUpdateNow\" type=\"button\" hidden></button>
        <button id=\"manualReleaseZipFull\" type=\"button\" hidden></button>
        <div id=\"fullUpdateProgress\"></div>
        <span id=\"folderBadge\"></span>
        <div id=\"folderDetail\"></div>
        <button id=\"openFolderManager\" type=\"button\"></button>
      </div>'''

updates_view_pattern = r'<section class=\\"view\\" data-view=\\"updates\\">.*?</section>'
home2, n = re.subn(updates_view_pattern, compat, home, count=1, flags=re.S)
assert n == 1, "visible updates view not found"
home = home2

# 4) Any stale #updates route now resolves to General.
old_set = "function setSection(name){if(!['general','personalization','updates'].includes(name))name='general';"
new_set = "function setSection(name){if(!['general','personalization'].includes(name))name='general';"
assert old_set in home
home = home.replace(old_set, new_set, 1)

# Startup route guard from older full-view versions, if present.
home = home.replace(
    "if(['general','personalization','updates'].includes(start))setSection(start);else setSection('general');",
    "if(['general','personalization'].includes(start))setSection(start);else setSection('general');"
)

# 5) Responsive polish specifically for the two-item navigation and summary card.
css_marker = "/* fix92 — full-view nav cleanup + General update summary */"
assert css_marker not in home
inject = r'''
/* fix92 — full-view nav cleanup + General update summary */
.update-overview-panel{display:flex;flex-direction:column;min-height:0}
.update-overview-panel .update-summary{margin-bottom:9px}
.update-overview-note{margin-top:10px;padding-top:9px;border-top:1px solid #e2ebf4}
@media(max-width:760px){
  .nav{grid-template-columns:repeat(2,minmax(0,1fr))!important}
}
@media(max-width:560px){
  .update-overview-panel .update-summary{grid-template-columns:1fr}
}
'''
marker = '";\n  const HOME_BODY'
escaped = inject.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')
assert marker in home, "HOME_CSS insertion marker missing"
home = home.replace(marker, escaped + marker, 1)

files["js/97-home-ui.js"] = home.encode("utf-8")

# Build identity only; preserve all existing functional files.
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
    raw = files[path]
    pkg["files"].append({
        "path": path,
        "size": len(raw),
        "sha256": h(raw),
        "content_base64": base64.b64encode(raw).decode("ascii")
    })

raw_pkg = (json.dumps(pkg, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
DST.write_bytes(raw_pkg)

ptr = json.loads((R/"dev/self-update.json").read_text(encoding="utf-8"))
ptr.update({
    "build": NEW,
    "package_url": "https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/" + DST_REL,
    "package_sha256": h(raw_pkg),
    "notes": [
        "La vista completa queda simplificada a General y Personalización; se elimina la pestaña redundante de Actualizaciones.",
        "General mantiene un resumen compacto con versión instalada, versión disponible y estado de la carpeta vinculada.",
        "Las acciones de actualizar, descargar ZIP y vincular carpeta continúan administrándose desde el popup sin modificar su lógica."
    ]
})
(R/"dev/self-update.json").write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

hist = json.loads((R/"dev/history.json").read_text(encoding="utf-8"))
hist["current_build"] = NEW
hist["current_package"] = DST_REL
(R/"dev/history.json").write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Regression assertions.
out = files["js/97-home-ui.js"].decode("utf-8")
assert 'data-section=\\\"updates\\\"' not in out
assert 'data-view=\\\"updates\\\"' not in out
assert 'data-section=\\\"general\\\"' in out
assert 'data-section=\\\"personalization\\\"' in out
assert 'id=\\\"summaryInstalled\\\"' in out
assert 'id=\\\"summaryAvailable\\\"' in out
assert 'id=\\\"summaryFolder\\\"' in out
assert 'id=\\\"fullViewUpdateCompat\\\"' in out
assert 'id=\\\"runUpdateNow\\\"' in out
assert 'id=\\\"openFolderManager\\\"' in out
assert "['general','personalization'].includes(name)" in out
print(json.dumps({"build":NEW,"package":DST_REL,"sha256":h(raw_pkg)},ensure_ascii=False,indent=2))
