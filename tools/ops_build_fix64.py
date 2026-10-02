#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "dev/builds/1.3.26-dev-folder-popup-polish-fix63.json"
DST_REL = "dev/builds/1.3.26-dev-editor-entry-cleanup-fix64.json"
DST = ROOT / DST_REL
PTR = ROOT / "dev/self-update.json"
HIST = ROOT / "dev/history.json"
NEW_BUILD = "1.3.26-dev-editor-entry-cleanup-fix64"

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

# 8) Popup -> new full-view editor directly. Do not call the legacy VIENA modal.
popup_js = files["popup.js"].decode("utf-8")
start = popup_js.find("// Editor global de botones:")
end = popup_js.find("\n}\n", start)
if start < 0 or end < 0:
    raise SystemExit("legacy popup editor block not found")
# Preserve final branch-closing brace by replacing only the editor block.
old_block = popup_js[start:end]
new_block = """// Botones y plantillas: abrir la nueva vista completa directamente en Personalización.
const openButtonEditorBtn = document.getElementById('openButtonEditor');
const buttonEditorStatusEl = document.getElementById('buttonEditorStatus');
if (openButtonEditorBtn) {
  openButtonEditorBtn.addEventListener('click', async () => {
    openButtonEditorBtn.disabled = true;
    if (buttonEditorStatusEl) buttonEditorStatusEl.textContent = 'Abriendo editor…';
    try {
      const targetUrl = chrome.runtime.getURL('popup.html?full=1#personalization');
      const extensionPrefix = chrome.runtime.getURL('popup.html?full=1');
      const tabs = await chrome.tabs.query({});
      const existing = tabs.find(tab => tab?.id && String(tab.url || '').startsWith(extensionPrefix));
      if (existing?.id) {
        await chrome.tabs.update(existing.id, { active: true, url: targetUrl });
        if (existing.windowId != null) {
          try { await chrome.windows.update(existing.windowId, { focused: true }); } catch (_) {}
        }
      } else {
        let current = null;
        try {
          const active = await chrome.tabs.query({ active: true, currentWindow: true });
          current = active[0] || null;
        } catch (_) {}
        const options = { url: targetUrl, active: true };
        if (Number.isInteger(current?.index)) options.index = current.index + 1;
        await chrome.tabs.create(options);
      }
      if (buttonEditorStatusEl) buttonEditorStatusEl.textContent = '';
      window.close();
    } catch (error) {
      const msg = String(error?.message || error || 'No se pudo abrir el editor.');
      if (buttonEditorStatusEl) buttonEditorStatusEl.textContent = msg;
      showToast(msg, 'error');
      openButtonEditorBtn.disabled = false;
    }
  });
}
"""
popup_js = popup_js[:start] + new_block + popup_js[end:]
files["popup.js"] = popup_js.encode("utf-8")

# 9) Editor cleanup: no large empty state; make search purpose explicit; improve field focus spacing.
home = files["js/97-home-ui.js"].decode("utf-8")

subs = [
    (
        'aria-label=\\\"Buscar botones\\\"><span>\\u2315</span><input id=\\\"buttonSearch\\\" type=\\\"search\\\" placeholder=\\\"Buscar bot\\u00f3n\\u2026\\\"',
        'aria-label=\\\"Buscar entre mis botones personales\\\"><span>\\u2315</span><input id=\\\"buttonSearch\\\" type=\\\"search\\\" placeholder=\\\"Buscar entre mis botones\\u2026\\\"'
    ),
    (
        'id=\\\"buttonEditorEmpty\\\" class=\\\"editor-empty\\\">Seleccion\\u00e1 un bot\\u00f3n para editar sus plantillas.',
        'id=\\\"buttonEditorEmpty\\\" class=\\\"editor-empty\\\">Cargando editor de botones\\u2026'
    ),
]
for old,new in subs:
    if old not in home:
        raise SystemExit(f"home markup fragment not found: {old[:100]!r}")
    home = home.replace(old,new,1)

css_marker = "/* fix64 — editor entry cleanup */"
if css_marker not in home:
    css = r'''
/* fix64 — editor entry cleanup */
.editor-empty{
  min-height:84px!important;
  padding:18px 16px!important;
  display:grid;
  place-items:center;
  text-align:center;
  color:#6f8498;
  background:#f8fbfe;
  border:1px dashed #d6e2ed;
  border-radius:10px;
}
.editor-field{
  display:grid!important;
  gap:7px!important;
  margin:13px 0 15px!important;
  color:#516b84!important;
  font-size:11.5px!important;
  font-weight:650;
}
.editor-field input{
  margin-top:0!important;
  min-height:38px;
  padding:8px 10px!important;
  border-radius:8px!important;
}
.editor-field input:focus-visible,
.editor-search input:focus-visible{
  outline:2px solid rgba(10,99,197,.25);
  outline-offset:2px;
  border-color:#5d9bd8!important;
  box-shadow:none!important;
}
.editor-search{margin-bottom:5px!important}
.editor-search:after{
  content:"Filtra únicamente tus botones personales";
  display:block;
  margin:5px 2px 0 1px;
  color:#8395a7;
  font-size:9.5px;
  line-height:1.25;
}
@media(max-width:760px){
  .editor-empty{min-height:68px!important;padding:14px 12px!important}
}
'''
    marker = '";\n  const HOME_BODY'
    if marker not in home:
        raise SystemExit("HOME_CSS marker not found")
    home = home.replace(marker, encode_js_css(css)+marker,1)

# Ensure successful refresh selects system before leaving empty-state visible.
old = """async function refreshButtonEditor({keepSelection=true}={}){const badge=$('editorConnection');badge.textContent='Conectando…';badge.className='status';try{const r=await editorMessage({type:'VIENA_BUTTON_EDITOR_STATE'});buttonEditorState=r.state;badge.textContent='Conectado a VIENA';badge.className='status ok';const prev=keepSelection?editorSelection:null;renderEditorLists();if(prev?.kind==='custom'&&buttonEditorState.personales.some(x=>x.id===prev.id))selectEditorButton('custom',prev.id);else if(prev?.kind==='system'&&buttonEditorState.sistema)selectEditorButton('system',buttonEditorState.sistema.id);else if(buttonEditorState.sistema)selectEditorButton('system',buttonEditorState.sistema.id)}catch(err){buttonEditorState=null;editorDraft=null;editorSelection=null;renderEditorLists();renderEditorForm();badge.textContent='VIENA no disponible';badge.className='status warn';$('buttonEditorEmpty').textContent=String(err?.message||err)}}"""
new = """async function refreshButtonEditor({keepSelection=true}={}){const badge=$('editorConnection');badge.textContent='Conectando…';badge.className='status';const empty=$('buttonEditorEmpty');if(empty){empty.hidden=false;empty.textContent='Cargando editor de botones…'}try{const r=await editorMessage({type:'VIENA_BUTTON_EDITOR_STATE'});buttonEditorState=r.state;badge.textContent='Conectado a VIENA';badge.className='status ok';const prev=keepSelection?editorSelection:null;if(prev?.kind==='custom'&&buttonEditorState.personales.some(x=>x.id===prev.id))selectEditorButton('custom',prev.id);else if(prev?.kind==='system'&&buttonEditorState.sistema)selectEditorButton('system',buttonEditorState.sistema.id);else if(buttonEditorState.sistema)selectEditorButton('system',buttonEditorState.sistema.id);else{renderEditorLists();renderEditorForm()}}catch(err){buttonEditorState=null;editorDraft=null;editorSelection=null;renderEditorLists();renderEditorForm();badge.textContent='VIENA no disponible';badge.className='status warn';$('buttonEditorEmpty').textContent=String(err?.message||err)}}"""
if old not in home:
    raise SystemExit("refreshButtonEditor fragment not found")
home = home.replace(old,new,1)

files["js/97-home-ui.js"] = home.encode("utf-8")

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

order=[item["path"] for item in pkg["files"]]
pkg["build"]=NEW_BUILD
pkg["generated_at"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
pkg["files"]=[]
for path in order:
    raw=files[path]
    pkg["files"].append({"path":path,"size":len(raw),"sha256":sha(raw),"content_base64":base64.b64encode(raw).decode("ascii")})

raw_pkg=(json.dumps(pkg,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
DST.write_bytes(raw_pkg)
package_sha=sha(raw_pkg)

ptr=json.loads(PTR.read_text(encoding="utf-8"))
ptr.update({
    "schema":1,
    "version":"1.3.26",
    "build":NEW_BUILD,
    "channel":"DEV",
    "package_url":f"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/{DST_REL}",
    "package_sha256":package_sha,
    "notes":[
        "Botones y plantillas abre directamente la nueva vista completa en Personalización y deja de invocar el editor viejo de VIENA.",
        "El popup se cierra al transferir el foco al editor nuevo.",
        "El editor ya no reserva un bloque vacío grande; Completar Tarea se selecciona automáticamente y la búsqueda aclara que filtra sólo botones personales."
    ]
})
PTR.write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist=json.loads(HIST.read_text(encoding="utf-8"))
hist["current_build"]=NEW_BUILD
hist["current_package"]=DST_REL
note="fix64 routes popup personalization to the new full-view editor, closes the popup, and removes the oversized editor empty state while clarifying personal-button search."
if note not in hist.get("notes",[]):
    hist.setdefault("notes",[]).append(note)
HIST.write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

assert len(pkg["files"])==28
assert b"popup.html?full=1#personalization" in files["popup.js"]
assert b"VIENA_OPEN_BUTTON_EDITOR" not in files["popup.js"]
assert b"Buscar entre mis botones" in files["js/97-home-ui.js"]
assert b"min-height:84px" in files["js/97-home-ui.js"]

print(json.dumps({"build":NEW_BUILD,"package":DST_REL,"files":len(pkg["files"]),"sha256":package_sha},indent=2))
