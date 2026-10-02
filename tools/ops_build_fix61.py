#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "dev/builds/1.3.26-dev-icon-personalization-polish-fix60.json"
DST_REL = "dev/builds/1.3.26-dev-ui-foundation-fix61.json"
DST = ROOT / DST_REL
PTR = ROOT / "dev/self-update.json"
HIST = ROOT / "dev/history.json"
NEW_BUILD = "1.3.26-dev-ui-foundation-fix61"

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def decode_file(item):
    raw = base64.b64decode(item["content_base64"], validate=True)
    assert len(raw) == item["size"]
    assert sha(raw) == item["sha256"]
    return raw

pkg = json.loads(SRC.read_text(encoding="utf-8"))
files = {item["path"]: decode_file(item) for item in pkg["files"]}

home = files["js/97-home-ui.js"].decode("utf-8")

replacements = [
    (
        "const ASSIGN_KEY='viena_asignacion_apellido';",
        "const ASSIGN_KEY='viena_asignar_multiple_filtro';"
    ),
    (
        "if(['general','tools','personalization','updates','diagnostics'].includes(start))setSection(start);",
        "if(['general','personalization','updates'].includes(start))setSection(start);else setSection('general');"
    ),
]

for old, new in replacements:
    if old not in home:
        raise SystemExit(f"expected fragment not found: {old[:120]!r}")
    home = home.replace(old, new, 1)

def replace_function(source, start_marker, end_marker, replacement):
    a = source.find(start_marker)
    if a < 0:
        raise SystemExit(f"function start not found: {start_marker}")
    b = source.find(end_marker, a)
    if b < 0:
        raise SystemExit(f"function end not found after: {start_marker}")
    return source[:a] + replacement + source[b:]

home = replace_function(
    home,
    "function setSection(name){",
    "\n    \n    document.querySelectorAll('[data-section]')",
    "function setSection(name){if(name==='tools'||name==='diagnostics')name='general';document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.dataset.view===name));document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.section===name));history.replaceState(null,'',`#${name}`)}"
)

home = replace_function(
    home,
    "function renderToolScaffolds(){",
    "\n    \n    const faviconCache",
    "function renderToolScaffolds(){const html=Object.keys(PLATFORM_LABELS).map(toolMarkup).join('');$('toolGridGeneral').innerHTML=html;if($('toolGridFull'))$('toolGridFull').innerHTML=html;const quick=$('quickTabs');if(quick){quick.innerHTML=Object.entries(PLATFORM_LABELS).filter(([k])=>k!=='viena').map(([k,v])=>`<button class=\\\"chip\\\" data-quick=\\\"${k}\\\">${v}</button>`).join('');document.querySelectorAll('[data-quick]').forEach(b=>b.addEventListener('click',()=>runPlatformAction(b.dataset.quick,'open',b)))}document.querySelectorAll('.tool-row').forEach(row=>row.querySelector('[data-action]').addEventListener('click',e=>runPlatformAction(row.dataset.tool,e.currentTarget.dataset.action,e.currentTarget)))}"
)


# HOME_BODY is embedded as a JavaScript string, so its quotes/unicode are escaped.
markup_subs = [
    (r'<button class=\\\"nav-item\\\" data-section=\\\"tools\\\">.*?</button>', ''),
    (r'<button class=\\\"nav-item\\\" data-section=\\\"diagnostics\\\">.*?</button>', ''),
    (r'<button class=\\\"link-btn\\\" data-go=\\\"tools\\\">.*?</button>', '<span class=\\\"muted\\\">Accesos operativos</span>'),
    (r'<button class=\\\"link-btn\\\" data-go=\\\"diagnostics\\\">.*?</button>', '<span class=\\\"muted\\\">Datos compartidos</span>'),
    (r'<article class=\\\"panel\\\"><div class=\\\"panel-head\\\"><h2>Pesta\\u00f1as operativas</h2>.*?</article>', ''),
]
for pattern, repl in markup_subs:
    home2, n = re.subn(pattern, repl, home, count=1)
    if n != 1:
        raise SystemExit(f"embedded markup fragment not found: {pattern}")
    home = home2

css_marker = '/* fix61 — shared state + navigation cleanup + responsive foundation */'
if css_marker not in home:
    inject = r'''
/* fix61 — shared state + navigation cleanup + responsive foundation */
.active-pill:before{display:none!important}
.content{min-width:0}
.grid.two{grid-template-columns:repeat(2,minmax(0,1fr))}
.panel,.tool-row,.operator-grid>div,.update-summary>div,.stats>div{min-width:0}
.panel h2,.tool-name,.stats b,.operator-grid b,.update-summary b{overflow-wrap:anywhere}
@media(max-width:1180px){
  .layout{grid-template-columns:195px minmax(0,1fr)}
  .content{padding:18px}
  .topbar-note{display:none}
}
@media(max-width:980px){
  .grid.two{grid-template-columns:1fr}
  .stats.three{grid-template-columns:repeat(3,minmax(0,1fr))}
}
@media(max-width:760px){
  .topbar{height:auto;min-height:68px;padding:10px 14px}
  .brand-title{font-size:clamp(18px,4vw,23px)}
  .layout{display:block;min-height:0}
  .sidebar{position:sticky;top:0;z-index:20;padding:8px 10px}
  .nav{grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
  .nav-item{justify-content:center;padding:9px 7px;font-size:11px;white-space:nowrap}
  .nav-item span{width:auto;font-size:15px}
  .side-card{display:none}
  .content{padding:12px}
  .page-head{align-items:flex-start;flex-direction:column}
  .page-head .btn{width:100%}
  .operator-grid,.update-summary{grid-template-columns:1fr}
}
@media(max-width:560px){
  .topbar{gap:9px}
  .brand-mark{width:40px;height:40px;border-radius:10px;font-size:16px}
  .active-pill{padding:7px 10px}
  .grid.two{gap:10px}
  .stats.three{grid-template-columns:1fr}
  .tool-grid{grid-template-columns:1fr}
  .panel{padding:12px}
  .nav-item{font-size:0}
  .nav-item span{font-size:17px}
}
'''
    marker = '\";\n  const HOME_BODY'
    escaped = inject.replace('\\\\','\\\\\\\\').replace('\"','\\\\"').replace('\n','\\n')
    if marker not in home:
        raise SystemExit("HOME_CSS marker not found")
    home = home.replace(marker, escaped + marker, 1)

files["js/97-home-ui.js"] = home.encode("utf-8")

# Update runtime identity only; preserve functional logic.
for path, const_name in [
    ("background.js", "VIENA_BUILD_ID"),
    ("js/80-update-banner.js", "CONTENT_BUILD_ID"),
    ("js/90-runtime-status.js", "BUILD_ID"),
]:
    text = files[path].decode("utf-8")
    import re
    pat = rf"(const\s+{const_name}\s*=\s*['\"])([^'\"]+)(['\"])"
    text2, n = re.subn(pat, rf"\g<1>{NEW_BUILD}\g<3>", text, count=1)
    if n != 1:
        raise SystemExit(f"could not update {const_name} in {path}")
    files[path] = text2.encode("utf-8")

build = json.loads(files["build.json"].decode("utf-8"))
build["build"] = NEW_BUILD
build["version"] = "1.3.26"
build["channel"] = "DEV"
files["build.json"] = (json.dumps(build, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

# Regenerate integrity inventory.
inventory = {}
for path, raw in files.items():
    if path != "integrity-manifest.json":
        inventory[path] = sha(raw)
integrity = json.loads(files["integrity-manifest.json"].decode("utf-8"))
integrity["build"] = NEW_BUILD
integrity["files"] = inventory
files["integrity-manifest.json"] = (json.dumps(integrity, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

order = [item["path"] for item in pkg["files"]]
pkg["build"] = NEW_BUILD
pkg["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
pkg["files"] = []
for path in order:
    raw = files[path]
    pkg["files"].append({
        "path": path,
        "size": len(raw),
        "sha256": sha(raw),
        "content_base64": base64.b64encode(raw).decode("ascii"),
    })

raw_pkg = (json.dumps(pkg, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
DST.write_bytes(raw_pkg)
package_sha = sha(raw_pkg)

ptr = json.loads(PTR.read_text(encoding="utf-8"))
ptr.update({
    "schema": 1,
    "version": "1.3.26",
    "build": NEW_BUILD,
    "channel": "DEV",
    "package_url": f"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/{DST_REL}",
    "package_sha256": package_sha,
    "notes": [
        "Se unifica el apellido para asignación entre popup y vista completa usando la misma clave persistente.",
        "La vista completa simplifica el navbar a General, Personalización y Actualizaciones, eliminando accesos duplicados.",
        "General concentra estado, herramientas, operador y actualización con una base responsive para resoluciones de escritorio y ventanas reducidas."
    ]
})
PTR.write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

hist = json.loads(HIST.read_text(encoding="utf-8"))
hist["current_build"] = NEW_BUILD
hist["current_package"] = DST_REL
note = "fix61 unifies assignment surname state, removes duplicated full-view navigation and establishes the responsive General layout foundation."
if note not in hist.get("notes", []):
    hist.setdefault("notes", []).append(note)
HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

assert len(pkg["files"]) == 28
assert b"viena_asignar_multiple_filtro" in files["js/97-home-ui.js"]
assert b'data-section="tools"' not in files["js/97-home-ui.js"]
assert b'data-section="diagnostics"' not in files["js/97-home-ui.js"]

print(json.dumps({"build": NEW_BUILD, "package": DST_REL, "files": len(pkg["files"]), "sha256": package_sha}, indent=2))
