#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/"dev/builds/1.3.26-dev-ui-interaction-fix69.json"
DST_REL="dev/builds/1.3.26-dev-status-operator-stability-fix70.json"
DST=ROOT/DST_REL
PTR=ROOT/"dev/self-update.json"
HIST=ROOT/"dev/history.json"
NEW_BUILD="1.3.26-dev-status-operator-stability-fix70"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(i):
    b=base64.b64decode(i["content_base64"],validate=True)
    assert len(b)==i["size"] and sha(b)==i["sha256"]
    return b

pkg=json.loads(SRC.read_text(encoding="utf-8"))
files={i["path"]:decode(i) for i in pkg["files"]}

# --- background: compact normal-state badge ---
bg=files["background.js"].decode("utf-8")
bg,n=re.subn(r"(on:\s*\{\s*text:\s*')ON('\s*,\s*color:\s*'#23833B')",r"\1•\2",bg,count=1)
if n!=1: raise SystemExit("STATUS_BADGES.on not found")
files["background.js"]=bg.encode("utf-8")

# --- popup: detected VIENA user must render once, not as badge + readonly duplicate input ---
pjs=files["popup.js"].decode("utf-8")
old="""  if (userManualRow) userManualRow.style.display = autoDetected ? 'none' : '';"""
new="""  if (userManualRow) { userManualRow.hidden = autoDetected; userManualRow.style.setProperty('display', autoDetected ? 'none' : '', autoDetected ? 'important' : ''); }"""
if old not in pjs: raise SystemExit("popup userManualRow fragment missing")
pjs=pjs.replace(old,new,1)
files["popup.js"]=pjs.encode("utf-8")

ph=files["popup.html"].decode("utf-8")
css="""
/* fix70 — detected user is single-source in popup */
#userManualRow[hidden]{display:none!important}
"""
ph=ph.replace("</style>",css+"\n</style>",1)
files["popup.html"]=ph.encode("utf-8")

# --- full personalization: eliminate no-op button bounce and preserve viewport on real save/discard ---
home=files["js/97-home-ui.js"].decode("utf-8")

old_update="""function updateEditorActionState(){
      const status=$('editorFormStatus');
      if(!status||!editorDraft)return;
      if(editorIsDirty()&&!status.classList.contains('editor-error')){
        status.className='minor-status editor-dirty';
        status.textContent='Cambios sin guardar.';
      }
    }"""
new_update="""function updateEditorActionState(){
      const status=$('editorFormStatus');
      if(!status||!editorDraft)return;
      const dirty=editorIsDirty();
      const save=$('saveButtonEdit'),cancel=$('cancelButtonEdit');
      if(save)save.disabled=!dirty;
      if(cancel)cancel.disabled=!dirty;
      if(dirty&&!status.classList.contains('editor-error')){
        status.className='minor-status editor-dirty';
        status.textContent='Cambios sin guardar.';
      }else if(!dirty&&!status.classList.contains('editor-error')){
        status.className='minor-status';
        if(status.textContent==='Cambios sin guardar.')status.textContent='';
      }
    }"""
if old_update not in home: raise SystemExit("updateEditorActionState not found")
home=home.replace(old_update,new_update,1)

# Ensure initial render syncs button enabled state.
old_render_end="""$('editorFormStatus').textContent='';renderEditorLists()}"""
new_render_end="""$('editorFormStatus').textContent='';renderEditorLists();updateEditorActionState()}"""
if old_render_end not in home: raise SystemExit("render end not found")
home=home.replace(old_render_end,new_render_end,1)

# Harden template anchor: sync + two RAFs, only around template toggle.
old_toggle="""const toggle=()=>{const anchorTop=card.getBoundingClientRect().top;expandedTemplateIndex=expandedTemplateIndex===index?-1:index;renderEditorForm();const next=document.querySelector(`#editorTemplates .template-card[data-template-index="${index}"]`);if(next){const delta=next.getBoundingClientRect().top-anchorTop;if(Math.abs(delta)>.5)window.scrollBy(0,delta)}};"""
new_toggle="""const toggle=()=>{const anchorTop=card.getBoundingClientRect().top;expandedTemplateIndex=expandedTemplateIndex===index?-1:index;renderEditorForm();const keepAnchor=()=>{const next=document.querySelector(`#editorTemplates .template-card[data-template-index="${index}"]`);if(next){const delta=next.getBoundingClientRect().top-anchorTop;if(Math.abs(delta)>.5)window.scrollBy(0,delta)}};keepAnchor();requestAnimationFrame(()=>{keepAnchor();requestAnimationFrame(keepAnchor)})};"""
if old_toggle not in home: raise SystemExit("toggle anchor not found")
home=home.replace(old_toggle,new_toggle,1)

# Discard: no render if nothing changed; otherwise retain exact page scroll.
old_cancel="""$('cancelButtonEdit').addEventListener('click',async()=>{if(editorIsDirty()){const ok=await requestUiConfirm({title:'Descartar cambios',message:'Hay cambios sin guardar. Si continuás, se perderán.',confirmLabel:'Descartar'});if(!ok)return}const item=selectedEditorItem();if(item){const openIndex=expandedTemplateIndex;editorDraft=cloneEditorData(item);expandedTemplateIndex=Math.max(-1,Math.min(openIndex,editorDraft.plantillas.length-1));renderEditorForm();showToast('Cambios descartados.','warning')}else if(buttonEditorState?.sistema)selectEditorButton('system',buttonEditorState.sistema.id)});"""
new_cancel="""$('cancelButtonEdit').addEventListener('click',async()=>{if(!editorIsDirty())return;const ok=await requestUiConfirm({title:'Descartar cambios',message:'Hay cambios sin guardar. Si continuás, se perderán.',confirmLabel:'Descartar'});if(!ok)return;const scrollY=window.scrollY;const item=selectedEditorItem();if(item){const openIndex=expandedTemplateIndex;editorDraft=cloneEditorData(item);expandedTemplateIndex=Math.max(-1,Math.min(openIndex,editorDraft.plantillas.length-1));renderEditorForm();window.scrollTo(0,scrollY);requestAnimationFrame(()=>window.scrollTo(0,scrollY));showToast('Cambios descartados.','warning')}else if(buttonEditorState?.sistema)selectEditorButton('system',buttonEditorState.sistema.id)});"""
if old_cancel not in home: raise SystemExit("cancel handler not found")
home=home.replace(old_cancel,new_cancel,1)

# Save: no-op if clean; preserve viewport when rendering returned state.
old_save_start="""$('saveButtonEdit').addEventListener('click',async e=>{if(!editorDraft)return;const btn=e.currentTarget,original=btn.textContent;"""
new_save_start="""$('saveButtonEdit').addEventListener('click',async e=>{if(!editorDraft||!editorIsDirty())return;const scrollY=window.scrollY;const btn=e.currentTarget,original=btn.textContent;"""
if old_save_start not in home: raise SystemExit("save handler start not found")
home=home.replace(old_save_start,new_save_start,1)

old_save_render="""renderEditorForm();$('editorFormStatus').className='minor-status editor-ok';"""
new_save_render="""renderEditorForm();window.scrollTo(0,scrollY);requestAnimationFrame(()=>window.scrollTo(0,scrollY));$('editorFormStatus').className='minor-status editor-ok';"""
if old_save_render not in home: raise SystemExit("save render fragment not found")
home=home.replace(old_save_render,new_save_render,1)

# Remove the fix69 direct page action path that can emit console errors.
# The background service worker remains the single owner of chrome.action.setIcon.
start=home.find("    async function iconDataUrlToImageDataPage")
end=home.find("    document.querySelectorAll('[data-icon-variant]')",start)
if start<0 or end<0: raise SystemExit("direct icon page block missing")
replacement="""    async function chooseExtensionIcon(variant,button){if(button)button.disabled=true;const status=$('iconSelectionStatus');if(status){status.textContent='Aplicando…';status.className='status'}try{const r=await chrome.runtime.sendMessage({type:'VIENA_EXTENSION_ICON_SET',variant:String(variant)});if(!r?.ok)throw new Error(r?.detail||'No se pudo cambiar el icono');paintIconSelection(r.variant||variant);showToast('Icono de la extensión actualizado.','success')}catch(err){if(status){status.textContent='Error';status.className='status error'}showToast(String(err?.message||err),'error')}finally{if(button?.isConnected)button.disabled=false}}
"""
home=home[:start]+replacement+home[end:]

files["js/97-home-ui.js"]=home.encode("utf-8")

# Runtime identity.
for path,const_name in [("background.js","VIENA_BUILD_ID"),("js/80-update-banner.js","CONTENT_BUILD_ID"),("js/90-runtime-status.js","BUILD_ID")]:
    txt=files[path].decode("utf-8")
    txt,n=re.subn(rf"(const\s+{const_name}\s*=\s*['\"])([^'\"]+)(['\"])",rf"\g<1>{NEW_BUILD}\g<3>",txt,count=1)
    if n!=1: raise SystemExit(f"identity missing: {path}")
    files[path]=txt.encode("utf-8")

build=json.loads(files["build.json"].decode("utf-8"))
build.update({"build":NEW_BUILD,"version":"1.3.26","channel":"DEV"})
files["build.json"]=(json.dumps(build,ensure_ascii=False,indent=2)+"\n").encode("utf-8")

integrity=json.loads(files["integrity-manifest.json"].decode("utf-8"))
integrity["build"]=NEW_BUILD
integrity["files"]={p:sha(b) for p,b in files.items() if p!="integrity-manifest.json"}
files["integrity-manifest.json"]=(json.dumps(integrity,ensure_ascii=False,indent=2)+"\n").encode("utf-8")

order=[i["path"] for i in pkg["files"]]
pkg["build"]=NEW_BUILD
pkg["generated_at"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
pkg["files"]=[]
for p in order:
    b=files[p]
    pkg["files"].append({"path":p,"size":len(b),"sha256":sha(b),"content_base64":base64.b64encode(b).decode("ascii")})
raw=(json.dumps(pkg,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
DST.write_bytes(raw)
package_sha=sha(raw)

ptr=json.loads(PTR.read_text(encoding="utf-8"))
ptr.update({
    "schema":1,"version":"1.3.26","build":NEW_BUILD,"channel":"DEV",
    "package_url":f"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/{DST_REL}",
    "package_sha256":package_sha,
    "notes":[
      "El estado normal de la extensión usa un badge verde mínimo para no tapar el icono.",
      "El Usuario VIENA detectado se muestra una sola vez en Operador.",
      "Guardar/Descartar ya no provocan saltos de scroll y se desactivan cuando no hay cambios.",
      "Se refuerza el anclaje visual al abrir/cerrar plantillas y se elimina la ruta duplicada de cambio de icono desde la página."
    ]
})
PTR.write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist=json.loads(HIST.read_text(encoding="utf-8"))
hist["current_build"]=NEW_BUILD
hist["current_package"]=DST_REL
hist.setdefault("notes",[]).append("fix70: compact active badge, single detected VIENA user, stable editor viewport, and single-owner toolbar icon application.")
HIST.write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

checks={
  "compact badge":"text: '•'" in files["background.js"].decode("utf-8"),
  "single auto user":"userManualRow.hidden = autoDetected" in files["popup.js"].decode("utf-8"),
  "no direct action":"applyExtensionIconFromPage" not in files["js/97-home-ui.js"].decode("utf-8"),
  "dirty buttons":"save.disabled=!dirty" in files["js/97-home-ui.js"].decode("utf-8"),
  "scroll stable":"requestAnimationFrame(()=>window.scrollTo(0,scrollY))" in files["js/97-home-ui.js"].decode("utf-8"),
  "anchor stable":"requestAnimationFrame(()=>{keepAnchor();requestAnimationFrame(keepAnchor)})" in files["js/97-home-ui.js"].decode("utf-8"),
}
bad=[k for k,v in checks.items() if not v]
if bad: raise SystemExit("FAILED: "+", ".join(bad))
print(json.dumps({"build":NEW_BUILD,"sha256":package_sha,"checks":checks},ensure_ascii=False,indent=2))
