#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "dev/builds/1.3.26-dev-ui-motion-toast-fix62.json"
DST_REL = "dev/builds/1.3.26-dev-folder-popup-polish-fix63.json"
DST = ROOT / DST_REL
PTR = ROOT / "dev/self-update.json"
HIST = ROOT / "dev/history.json"
NEW_BUILD = "1.3.26-dev-folder-popup-polish-fix63"

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def decode_file(item):
    raw = base64.b64decode(item["content_base64"], validate=True)
    assert len(raw) == item["size"]
    assert sha(raw) == item["sha256"]
    return raw

def encode_js_css(css: str) -> str:
    return css.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

pkg = json.loads(SRC.read_text(encoding="utf-8"))
files = {item["path"]: decode_file(item) for item in pkg["files"]}

# 6) Open folder manager/setup immediately next to the extension tab/current tab.
home = files["js/97-home-ui.js"].decode("utf-8")
old = "$('refreshAll').addEventListener('click',refreshAll);$('refreshTools').addEventListener('click',refreshOperational);$('checkUpdates').addEventListener('click',refreshUpdates);$('openFolderManager').addEventListener('click',()=>chrome.tabs.create({url:chrome.runtime.getURL('updater.html')}));"
new = """async function openAdjacentExtensionTab(url){let current=null;try{current=await chrome.tabs.getCurrent()}catch(_){}if(!current?.id){try{const tabs=await chrome.tabs.query({active:true,currentWindow:true});current=tabs[0]||null}catch(_){}}const options={url,active:true};if(Number.isInteger(current?.index))options.index=current.index+1;return chrome.tabs.create(options)}
    $('refreshAll').addEventListener('click',refreshAll);$('refreshTools')?.addEventListener('click',refreshOperational);$('checkUpdates').addEventListener('click',refreshUpdates);$('openFolderManager').addEventListener('click',()=>openAdjacentExtensionTab(chrome.runtime.getURL('updater.html')));"""
if old not in home:
    raise SystemExit("full-view folder manager handler not found")
home = home.replace(old, new, 1)
files["js/97-home-ui.js"] = home.encode("utf-8")

popup_js = files["popup.js"].decode("utf-8")
old = """async function openFolderSetupPage(mode = 'link') {
  const url = chrome.runtime.getURL(`popup.html?standalone=1&mode=${encodeURIComponent(mode)}`);
  await chrome.tabs.create({ url, active: true });
}"""
new = """async function openFolderSetupPage(mode = 'link') {
  const url = chrome.runtime.getURL(`popup.html?standalone=1&mode=${encodeURIComponent(mode)}`);
  let current = null;
  try { current = await chrome.tabs.getCurrent(); } catch (_) {}
  if (!current?.id) {
    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      current = tabs[0] || null;
    } catch (_) {}
  }
  const options = { url, active: true };
  if (Number.isInteger(current?.index)) options.index = current.index + 1;
  await chrome.tabs.create(options);
}"""
if old not in popup_js:
    raise SystemExit("popup folder setup handler not found")
popup_js = popup_js.replace(old, new, 1)
files["popup.js"] = popup_js.encode("utf-8")

# 7) Popup visual/typographic compacting. Keep business logic/IDs untouched.
popup = files["popup.html"].decode("utf-8")
marker = "/* fix63 — compact corporate popup */"
if marker not in popup:
    css = r'''
/* fix63 — compact corporate popup */
:root{
  --navy:#082f5b;
  --navy2:#0a4a87;
  --blue:#0a63c5;
  --blue2:#0855aa;
  --ink:#102f50;
  --text:#1c3a5a;
  --muted:#687e95;
  --line:#d9e3ed;
  --soft:#f6f9fc;
  --soft2:#edf4fb;
  --shadow:0 8px 24px rgba(10,44,82,.09);
}
html,body{width:448px;max-width:448px;min-width:448px}
body{
  font-family:"Segoe UI",system-ui,-apple-system,BlinkMacSystemFont,Arial,sans-serif;
  font-size:12px;
  line-height:1.35;
  letter-spacing:0;
  background:#f3f6f9;
}
.app-header{
  padding:11px 13px;
  background:linear-gradient(115deg,#082f5b 0%,#0a4882 62%,#0b5da8 100%);
  box-shadow:0 5px 16px rgba(5,38,74,.18);
}
.header-main{gap:9px}
.mark{width:38px;height:38px;border-radius:10px;font-size:15px;background:linear-gradient(145deg,#0a65c9,#08498a)}
.brand-title{font-size:18px;font-weight:760;letter-spacing:-.15px}
.brand-meta{font-size:10.5px;margin-top:3px}
.header-actions{gap:6px}
.active-pill{padding:6px 9px;font-size:11px;gap:5px;box-shadow:none}
.active-pill:before{width:7px;height:7px;box-shadow:none}
.icon-button{width:34px;height:34px;border-radius:8px;font-size:17px}
.main{padding:9px}
.card{padding:10px;margin-bottom:8px;border-radius:10px;box-shadow:0 1px 6px rgba(12,49,88,.04)}
.section-head{margin-bottom:8px;gap:8px}
.section-title{font-size:13.5px;font-weight:760;color:var(--navy)}
.section-icon{width:21px;height:21px;border-radius:6px;font-size:12px;color:var(--blue)}
.section-action{font-size:10.5px;font-weight:700}
.platform-grid{gap:6px}
.platform-row{min-height:42px;padding:6px 7px;gap:7px;border-radius:8px}
.platform-icon-wrap{width:24px;height:24px;flex-basis:24px;border-radius:6px}
.viena-platform-icon{width:15px;height:15px}
.platform-name{font-size:11.5px;font-weight:720}
.platform-state{font-size:9.8px;font-weight:760}
.platform-state:not(.closed):not(.reload):not(:empty):before{width:6px;height:6px;margin-right:4px}
.platform-action{padding:4px 7px;font-size:9.8px}
.runtime-strip{margin-top:7px;padding:7px 8px;border-radius:8px}
.runtime-version{font-size:9.8px}
.runtime-pill{padding:4px 7px;font-size:9.8px}
.runtime-dot{width:6px;height:6px}
.operator-grid{grid-template-columns:148px minmax(0,1fr);gap:7px;align-items:stretch}
.operator-box{padding:8px 9px;border-radius:8px}
.operator-label{font-size:9.8px;margin-bottom:4px;line-height:1.25}
.operator-value,.user-auto-value{font-size:13px;font-weight:760;line-height:1.25}
.user-auto-panel{align-items:center}
.user-auto-badge{font-size:8.5px;padding:3px 5px}
.input-row{gap:5px;align-items:flex-end}
input{height:31px;padding:6px 7px;border-radius:6px;font-size:11.5px}
input:focus{box-shadow:0 0 0 2px rgba(10,99,197,.12)}
.btn{padding:7px 9px;border-radius:6px;font-size:11px;font-weight:730}
.statusline,.hint{font-size:9.7px;line-height:1.35}
.assign-warning{margin-top:5px;padding:6px 7px;font-size:9.6px}
.personalization-row{gap:8px;padding:7px 8px;border-radius:8px}
.personalization-icon{width:30px;height:30px;border-radius:8px;font-size:16px}
.personalization-copy b{font-size:11.5px;margin-bottom:1px}
.personalization-copy span{font-size:9.8px;line-height:1.3}
.chevron{font-size:16px}
.update-summary{gap:6px}
.update-box{padding:7px 8px;border-radius:8px}
.update-label{font-size:9px}
.update-value{font-size:12.5px;margin-top:2px}
.update-status{margin-top:6px;padding:7px 8px;font-size:9.8px}
.install-folder{margin-top:6px;padding:7px 8px;border-radius:8px}
.install-folder-title,.install-folder-state,.update-progress{font-size:9.7px}
.install-folder-actions{gap:5px;margin-top:6px}
.advanced{margin-top:6px;padding-top:6px}
.advanced summary,.release-history summary{font-size:9.8px}
.quick-tabs{gap:4px}
.chip{padding:4px 7px;font-size:9.7px}
footer{padding:0 9px 9px;font-size:9px}
@media(max-width:460px){
  html,body{width:100%;min-width:0;max-width:none}
}
'''
    popup = popup.replace("</style>", css + "\n</style>", 1)

# Tighten operator copy without changing IDs/storage behavior.
popup = popup.replace("Este usuario se obtiene de tu sesión de VIENA y no puede modificarse.",
                      "Detectado desde tu sesión de VIENA.")
popup = popup.replace("Ingresá tu apellido. Se usa para localizarte en Usuarios de VIENA.",
                      "Se usa para localizarte en Usuarios de VIENA.")

files["popup.html"] = popup.encode("utf-8")

# Runtime identity.
for path, const_name in [
    ("background.js", "VIENA_BUILD_ID"),
    ("js/80-update-banner.js", "CONTENT_BUILD_ID"),
    ("js/90-runtime-status.js", "BUILD_ID"),
]:
    text = files[path].decode("utf-8")
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
        "Administrar carpeta y la selección estable de carpeta se abren junto a la pestaña actual, no al final de Chrome.",
        "El popup se compacta a 448 px y adopta tipografía Segoe UI/system con jerarquía, alineación y espaciado revisados.",
        "La paleta se desplaza a un azul marino más corporativo y la sección Operador queda más compacta y legible."
    ]
})
PTR.write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

hist = json.loads(HIST.read_text(encoding="utf-8"))
hist["current_build"] = NEW_BUILD
hist["current_package"] = DST_REL
note = "fix63 opens folder management adjacent to the extension/current tab and compacts/refines the popup UI without changing popup business logic."
if note not in hist.get("notes", []):
    hist.setdefault("notes", []).append(note)
HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

assert len(pkg["files"]) == 28
assert marker.encode() in files["popup.html"]
assert b"width:448px" in files["popup.html"]
assert b"openAdjacentExtensionTab" in files["js/97-home-ui.js"]
assert b"options.index = current.index + 1" in files["popup.js"]

print(json.dumps({"build":NEW_BUILD,"package":DST_REL,"files":len(pkg["files"]),"sha256":package_sha},indent=2))
