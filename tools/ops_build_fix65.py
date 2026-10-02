#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "dev/builds/1.3.26-dev-editor-entry-cleanup-fix64.json"
DST_REL = "dev/builds/1.3.26-dev-icon-modal-confirm-fix65.json"
DST = ROOT / DST_REL
PTR = ROOT / "dev/self-update.json"
HIST = ROOT / "dev/history.json"
NEW_BUILD = "1.3.26-dev-icon-modal-confirm-fix65"

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
home = files["js/97-home-ui.js"].decode("utf-8")

mount_marker = "document.body.innerHTML=HOME_BODY;"
mount_insert = '''document.body.innerHTML=HOME_BODY;
    const personalizationView=document.querySelector('.view[data-view="personalization"]');
    const personalizationHead=personalizationView?.querySelector('.page-head');
    const iconPanel=personalizationView?.querySelector('.icon-panel');
    if(personalizationHead&&iconPanel){
      const appearanceLabel=document.createElement('div');
      appearanceLabel.className='personalization-block-label';
      appearanceLabel.innerHTML='<span>Apariencia</span><small>Personalización visual de la extensión</small>';
      personalizationHead.insertAdjacentElement('afterend',appearanceLabel);
      appearanceLabel.insertAdjacentElement('afterend',iconPanel);
      const editorLabel=document.createElement('div');
      editorLabel.className='personalization-block-label editor-block-label';
      editorLabel.innerHTML='<span>Botones y plantillas</span><small>Configuración operativa</small>';
      iconPanel.insertAdjacentElement('afterend',editorLabel);
    }'''
if mount_marker not in home:
    raise SystemExit("HOME mount marker not found")
home = home.replace(mount_marker, mount_insert, 1)

modal_markup = '''<div id=\\"uiConfirmOverlay\\" class=\\"ui-confirm-overlay\\" hidden aria-hidden=\\"true\\">
  <div class=\\"ui-confirm-dialog\\" role=\\"dialog\\" aria-modal=\\"true\\" aria-labelledby=\\"uiConfirmTitle\\" aria-describedby=\\"uiConfirmMessage\\">
    <div class=\\"ui-confirm-icon\\" aria-hidden=\\"true\\">!</div>
    <div class=\\"ui-confirm-copy\\"><h3 id=\\"uiConfirmTitle\\">Confirmar acción</h3><p id=\\"uiConfirmMessage\\"></p></div>
    <div class=\\"ui-confirm-actions\\"><button id=\\"uiConfirmCancel\\" class=\\"btn secondary\\" type=\\"button\\">Cancelar</button><button id=\\"uiConfirmAccept\\" class=\\"btn danger solid-danger\\" type=\\"button\\">Eliminar</button></div>
  </div>
</div>
'''
toast_marker = '<div id=\\"toast\\" class=\\"toast\\"></div>'
if toast_marker not in home:
    raise SystemExit("toast markup marker not found")
home = home.replace(toast_marker, modal_markup.replace('\\n','\\\\n') + toast_marker, 1)

show_toast = "function showToast(text,type=''){const el=$('toast');if(!el)return;el.textContent=text;el.className='toast show'+(type?` ${type}`:'');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.className='toast',2500)}"
if show_toast not in home:
    raise SystemExit("showToast helper not found")
confirm_helper = show_toast + '''
    let uiConfirmResolver=null;
    function closeUiConfirm(result=false){
      const overlay=$('uiConfirmOverlay');if(!overlay)return;
      overlay.hidden=true;overlay.setAttribute('aria-hidden','true');
      document.removeEventListener('keydown',onUiConfirmKey);
      const resolve=uiConfirmResolver;uiConfirmResolver=null;
      if(resolve)resolve(Boolean(result));
    }
    function onUiConfirmKey(event){if(event.key==='Escape')closeUiConfirm(false)}
    function requestUiConfirm({title='Confirmar acción',message='',confirmLabel='Eliminar'}={}){
      const overlay=$('uiConfirmOverlay'),titleEl=$('uiConfirmTitle'),messageEl=$('uiConfirmMessage'),accept=$('uiConfirmAccept'),cancel=$('uiConfirmCancel');
      if(!overlay||!titleEl||!messageEl||!accept||!cancel)return Promise.resolve(false);
      if(uiConfirmResolver)closeUiConfirm(false);
      titleEl.textContent=title;messageEl.textContent=message;accept.textContent=confirmLabel;
      overlay.hidden=false;overlay.setAttribute('aria-hidden','false');
      return new Promise(resolve=>{
        uiConfirmResolver=resolve;
        const cleanup=()=>{accept.removeEventListener('click',acceptOnce);cancel.removeEventListener('click',cancelOnce);overlay.removeEventListener('click',backdropOnce)};
        const acceptOnce=()=>{cleanup();closeUiConfirm(true)};
        const cancelOnce=()=>{cleanup();closeUiConfirm(false)};
        const backdropOnce=e=>{if(e.target===overlay){cleanup();closeUiConfirm(false)}};
        accept.addEventListener('click',acceptOnce);
        cancel.addEventListener('click',cancelOnce);
        overlay.addEventListener('click',backdropOnce);
        document.addEventListener('keydown',onUiConfirmKey);
        setTimeout(()=>cancel.focus(),0);
      });
    }'''
home = home.replace(show_toast, confirm_helper, 1)

old_template = "del.addEventListener('click',()=>{if(editorDraft.plantillas.length<=1){showToast('El botón necesita al menos una plantilla.','error');return}editorDraft.plantillas.splice(index,1);expandedTemplateIndex=Math.max(0,Math.min(expandedTemplateIndex,editorDraft.plantillas.length-1));renderEditorForm()})"
new_template = "del.addEventListener('click',async()=>{if(editorDraft.plantillas.length<=1){showToast('El botón necesita al menos una plantilla.','error');return}const ok=await requestUiConfirm({title:'Eliminar plantilla',message:`¿Querés eliminar “${t.nombre||'Plantilla sin nombre'}”? Esta acción se aplicará al guardar los cambios.`,confirmLabel:'Eliminar plantilla'});if(!ok)return;editorDraft.plantillas.splice(index,1);expandedTemplateIndex=Math.max(0,Math.min(expandedTemplateIndex,editorDraft.plantillas.length-1));renderEditorForm();showToast('Plantilla quitada del borrador. Guardá los cambios para confirmar.','warning')})"
if old_template not in home:
    raise SystemExit("template delete handler not found")
home = home.replace(old_template, new_template, 1)

old_button = "$('deleteCustomButton').addEventListener('click',async e=>{if(editorSelection?.kind!=='custom'||!editorDraft)return;if(!confirm(`¿Eliminar “${editorDraft.nombre}” y todas sus plantillas?`))return;const btn=e.currentTarget;btn.disabled=true;try{const r=await editorMessage({type:'VIENA_BUTTON_EDITOR_DELETE_GROUP',id:editorSelection.id});buttonEditorState=r.state;editorSelection={kind:'system',id:buttonEditorState.sistema.id};editorDraft=cloneEditorData(buttonEditorState.sistema);expandedTemplateIndex=0;renderEditorForm();showToast('Botón personal eliminado.','success')}catch(err){showToast(String(err?.message||err),'error')}finally{btn.disabled=false}});"
new_button = "$('deleteCustomButton').addEventListener('click',async e=>{if(editorSelection?.kind!=='custom'||!editorDraft)return;const ok=await requestUiConfirm({title:'Eliminar botón',message:`¿Querés eliminar “${editorDraft.nombre}” y todas sus plantillas? Esta acción no se puede deshacer.`,confirmLabel:'Eliminar botón'});if(!ok)return;const btn=e.currentTarget;btn.disabled=true;try{const r=await editorMessage({type:'VIENA_BUTTON_EDITOR_DELETE_GROUP',id:editorSelection.id});buttonEditorState=r.state;editorSelection={kind:'system',id:buttonEditorState.sistema.id};editorDraft=cloneEditorData(buttonEditorState.sistema);expandedTemplateIndex=0;renderEditorForm();showToast('Botón personal eliminado.','success')}catch(err){showToast(String(err?.message||err),'error')}finally{btn.disabled=false}});"
if old_button not in home:
    raise SystemExit("button delete handler not found")
home = home.replace(old_button, new_button, 1)

css = r'''
/* fix65 — icon placement + in-app confirmations */
.personalization-block-label{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin:4px 2px 8px;color:#173f6f}
.personalization-block-label span{font-size:12px;font-weight:850;letter-spacing:.01em}
.personalization-block-label small{font-size:10px;color:#7890a5}
.editor-block-label{margin-top:14px}
.icon-panel{margin-top:0!important;border-color:#cbddeb!important;box-shadow:0 6px 18px rgba(11,57,101,.06)!important}
.icon-panel .panel-head{margin-bottom:10px}
.icon-choice-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
.ui-confirm-overlay[hidden]{display:none!important}
.ui-confirm-overlay{position:fixed;inset:0;z-index:10000;display:grid;place-items:center;padding:20px;background:rgba(5,24,43,.42);backdrop-filter:blur(2px);animation:viena-confirm-backdrop-in .14s ease-out both}
.ui-confirm-dialog{width:min(430px,calc(100vw - 32px));display:grid;grid-template-columns:36px minmax(0,1fr);gap:12px;padding:16px;border-radius:12px;background:#fff;border:1px solid #d7e2ed;box-shadow:0 22px 60px rgba(4,29,54,.28);animation:viena-confirm-in .16s ease-out both}
.ui-confirm-icon{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;background:#fff2f0;color:#b42318;font-size:18px;font-weight:900}
.ui-confirm-copy h3{margin:1px 0 5px;font-size:15px;color:#113b68}
.ui-confirm-copy p{margin:0;color:#5d7288;font-size:11.5px;line-height:1.45}
.ui-confirm-actions{grid-column:1/-1;display:flex;justify-content:flex-end;gap:8px;margin-top:4px}
.btn.solid-danger{background:#b42318;color:#fff;border-color:#b42318}
.btn.solid-danger:hover{background:#971d14;border-color:#971d14}
@keyframes viena-confirm-backdrop-in{from{opacity:0}to{opacity:1}}
@keyframes viena-confirm-in{from{opacity:0;transform:translateY(6px) scale(.985)}to{opacity:1;transform:none}}
@media(max-width:760px){.personalization-block-label{align-items:flex-start;flex-direction:column;gap:2px}.icon-choice-grid{grid-template-columns:1fr}}
@media(max-width:520px){.ui-confirm-dialog{grid-template-columns:1fr;padding:14px}.ui-confirm-icon{width:30px;height:30px}.ui-confirm-actions{display:grid;grid-template-columns:1fr 1fr}}
@media(prefers-reduced-motion:reduce){.ui-confirm-overlay,.ui-confirm-dialog{animation:none!important}}
'''
marker = '";\n  const HOME_BODY'
if marker not in home:
    raise SystemExit("HOME_CSS marker not found")
home = home.replace(marker, encode_js_css(css)+marker, 1)

files["js/97-home-ui.js"] = home.encode("utf-8")

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

inventory = {path:sha(raw) for path,raw in files.items() if path != "integrity-manifest.json"}
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
ptr.update({"schema":1,"version":"1.3.26","build":NEW_BUILD,"channel":"DEV","package_url":f"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/{DST_REL}","package_sha256":package_sha,"notes":[
    "El selector de icono se mueve al inicio de Personalización, antes del editor, con una sección Apariencia visible.",
    "Las eliminaciones de botones y plantillas usan un modal propio de VIENA NOC Tools y dejan de usar confirmaciones nativas del navegador.",
    "Eliminar una plantilla queda como cambio de borrador hasta Guardar cambios; eliminar un botón confirma que la acción es irreversible."
]})
PTR.write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist=json.loads(HIST.read_text(encoding="utf-8"))
hist["current_build"]=NEW_BUILD
hist["current_package"]=DST_REL
note="fix65 moves extension icon personalization to the top of Personalización and replaces native destructive confirmations with an in-extension modal."
if note not in hist.get("notes",[]): hist.setdefault("notes",[]).append(note)
HIST.write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

assert len(pkg["files"])==28
assert b"personalization-block-label" in files["js/97-home-ui.js"]
assert b"uiConfirmOverlay" in files["js/97-home-ui.js"]
assert b"requestUiConfirm" in files["js/97-home-ui.js"]
assert not re.search(rb"\bconfirm\s*\(", files["js/97-home-ui.js"])
assert not re.search(rb"\balert\s*\(", files["js/97-home-ui.js"])

print(json.dumps({"build":NEW_BUILD,"package":DST_REL,"files":len(pkg["files"]),"sha256":package_sha},indent=2))