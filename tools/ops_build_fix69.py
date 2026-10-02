#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/"dev/builds/1.3.26-dev-ui-detail-polish-fix68.json"
DST_REL="dev/builds/1.3.26-dev-ui-interaction-fix69.json"
DST=ROOT/DST_REL
PTR=ROOT/"dev/self-update.json"
HIST=ROOT/"dev/history.json"
NEW_BUILD="1.3.26-dev-ui-interaction-fix69"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(i):
    b=base64.b64decode(i["content_base64"],validate=True)
    assert len(b)==i["size"] and sha(b)==i["sha256"]
    return b
def enc_css(s): return s.replace("\\","\\\\").replace('"','\\"').replace("\n","\\n")

pkg=json.loads(SRC.read_text(encoding="utf-8"))
files={i["path"]:decode(i) for i in pkg["files"]}
home=files["js/97-home-ui.js"].decode("utf-8")

css=r'''
/* fix69 — update spacing + stable template rendering */
.view[data-view="updates"] .stats.two{margin-bottom:10px!important}
.view[data-view="updates"] #updateMessage{margin-top:0!important}
.template-accordion,.template-card{overflow-anchor:none}
'''
marker='";\n  const HOME_BODY'
if marker not in home: raise SystemExit("HOME_CSS marker missing")
home=home.replace(marker,enc_css(css)+marker,1)

start=home.find("const fix68BaseRenderEditorForm=renderEditorForm;")
end=home.find("\n\n    $('addEditorTemplate').addEventListener",start)
if start<0 or end<0: raise SystemExit("fix68 render wrapper not found")
home=home[:start]+home[end+2:]

old_render="""function renderEditorForm(){const form=$('buttonEditorForm'),empty=$('buttonEditorEmpty');if(!editorDraft){form.hidden=true;empty.hidden=false;return}empty.hidden=true;form.hidden=false;const isSystem=editorSelection?.kind==='system';$('editingButtonName').textContent=editorDraft.nombre||'Nuevo botón';$('editingButtonBadge').textContent=isSystem?'SISTEMA':'PERSONAL';$('editingButtonMeta').textContent=`${buttonMetaText(editorDraft)}${isSystem?' · función base protegida':''}`;$('systemProtectionNote').hidden=!isSystem;$('customButtonNameWrap').hidden=isSystem;$('deleteCustomButton').hidden=isSystem||editorSelection?.kind==='new';$('customButtonName').value=isSystem?'':(editorDraft.nombre||'');$('templateCountBadge').textContent=buttonMetaText(editorDraft);const host=$('editorTemplates');host.replaceChildren();editorDraft.plantillas.forEach((t,i)=>host.append(makeTemplateCard(t,i)));$('editorFormStatus').textContent='';renderEditorLists()}"""
new_render="""function renderEditorForm(){const form=$('buttonEditorForm'),empty=$('buttonEditorEmpty');if(!editorDraft){form.hidden=true;if(empty){empty.hidden=false;empty.style.display='grid'}return}if(empty){empty.hidden=true;empty.style.display='none'}form.hidden=false;const isSystem=editorSelection?.kind==='system';$('editingButtonName').textContent=editorDraft.nombre||'Nuevo botón';$('editingButtonBadge').textContent=isSystem?'SISTEMA':'PERSONAL';$('editingButtonMeta').textContent=`${buttonMetaText(editorDraft)}${isSystem?' · función base protegida':''}`;$('systemProtectionNote').hidden=!isSystem;const nameWrap=$('customButtonNameWrap'),nameInput=$('customButtonName');nameWrap.hidden=false;nameInput.value=editorDraft.nombre||'';nameInput.readOnly=isSystem;nameInput.setAttribute('aria-readonly',isSystem?'true':'false');$('deleteCustomButton').hidden=isSystem||editorSelection?.kind==='new';$('templateCountBadge').textContent=buttonMetaText(editorDraft);const host=$('editorTemplates');host.replaceChildren();editorDraft.plantillas.forEach((t,i)=>host.append(makeTemplateCard(t,i)));$('editorFormStatus').textContent='';renderEditorLists()}"""
if old_render not in home: raise SystemExit("renderEditorForm block not found")
home=home.replace(old_render,new_render,1)

old_toggle="const toggle=()=>{expandedTemplateIndex=expandedTemplateIndex===index?-1:index;renderEditorForm()};"
new_toggle="""const toggle=()=>{const anchorTop=card.getBoundingClientRect().top;expandedTemplateIndex=expandedTemplateIndex===index?-1:index;renderEditorForm();const next=document.querySelector(`#editorTemplates .template-card[data-template-index="${index}"]`);if(next){const delta=next.getBoundingClientRect().top-anchorTop;if(Math.abs(delta)>.5)window.scrollBy(0,delta)}};"""
if old_toggle not in home: raise SystemExit("template toggle block not found")
home=home.replace(old_toggle,new_toggle,1)

old_select="""function selectEditorButton(kind,id){let item=null;if(kind==='system')item=buttonEditorState?.sistema;else item=buttonEditorState?.personales?.find(g=>g.id===id);if(!item)return;editorSelection={kind,id:item.id};editorDraft=cloneEditorData(item);expandedTemplateIndex=0;renderEditorForm()}"""
new_select="""function selectEditorButton(kind,id,{preserveExpanded=false}={}){let item=null;if(kind==='system')item=buttonEditorState?.sistema;else item=buttonEditorState?.personales?.find(g=>g.id===id);if(!item)return;const previousExpanded=expandedTemplateIndex;editorSelection={kind,id:item.id};editorDraft=cloneEditorData(item);expandedTemplateIndex=preserveExpanded?Math.max(-1,Math.min(previousExpanded,editorDraft.plantillas.length-1)):0;renderEditorForm()}"""
if old_select not in home: raise SystemExit("selectEditorButton block not found")
home=home.replace(old_select,new_select,1)

old_refresh="if(prev?.kind==='custom'&&buttonEditorState.personales.some(x=>x.id===prev.id))selectEditorButton('custom',prev.id);else if(prev?.kind==='system'&&buttonEditorState.sistema)selectEditorButton('system',buttonEditorState.sistema.id);"
new_refresh="if(prev?.kind==='custom'&&buttonEditorState.personales.some(x=>x.id===prev.id))selectEditorButton('custom',prev.id,{preserveExpanded:true});else if(prev?.kind==='system'&&buttonEditorState.sistema)selectEditorButton('system',buttonEditorState.sistema.id,{preserveExpanded:true});"
if old_refresh not in home: raise SystemExit("refresh selection fragment not found")
home=home.replace(old_refresh,new_refresh,1)

old_cancel="const item=selectedEditorItem();if(item){editorDraft=cloneEditorData(item);expandedTemplateIndex=0;renderEditorForm();showToast('Cambios descartados.','warning')}"
new_cancel="const item=selectedEditorItem();if(item){const openIndex=expandedTemplateIndex;editorDraft=cloneEditorData(item);expandedTemplateIndex=Math.max(-1,Math.min(openIndex,editorDraft.plantillas.length-1));renderEditorForm();showToast('Cambios descartados.','warning')}"
if old_cancel not in home: raise SystemExit("cancel reset fragment not found")
home=home.replace(old_cancel,new_cancel,1)

old_save="const item=selectedEditorItem();editorDraft=cloneEditorData(item);expandedTemplateIndex=0;renderEditorForm();$('editorFormStatus').className='minor-status editor-ok';"
new_save="const item=selectedEditorItem();const openIndex=expandedTemplateIndex;editorDraft=cloneEditorData(item);expandedTemplateIndex=Math.max(-1,Math.min(openIndex,editorDraft.plantillas.length-1));renderEditorForm();$('editorFormStatus').className='minor-status editor-ok';"
if old_save not in home: raise SystemExit("save reset fragment not found")
home=home.replace(old_save,new_save,1)

old_icon="""async function chooseExtensionIcon(variant,button){if(button)button.disabled=true;const status=$('iconSelectionStatus');if(status){status.textContent='Aplicando…';status.className='status'}try{const r=await chrome.runtime.sendMessage({type:'VIENA_EXTENSION_ICON_SET',variant:String(variant)});if(!r?.ok)throw new Error(r?.detail||'No se pudo cambiar el icono');paintIconSelection(r.variant);showToast('Icono de la extensión actualizado.','success')}catch(err){if(status){status.textContent='Error';status.className='status error'}showToast(String(err?.message||err),'error')}finally{if(button?.isConnected)button.disabled=false}}"""
new_icon="""async function iconDataUrlToImageDataPage(dataUrl,size){const img=new Image();img.src=dataUrl;await img.decode();const canvas=document.createElement('canvas');canvas.width=size;canvas.height=size;const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.clearRect(0,0,size,size);ctx.drawImage(img,0,0,size,size);return ctx.getImageData(0,0,size,size)}
    async function applyExtensionIconFromPage(value){const v=String(value||'1'),assets=globalThis.VIENA_ICON_VARIANTS?.[v];if(!assets)throw new Error('Icono no disponible');const imageData={};for(const size of [16,32,48,128])imageData[size]=await iconDataUrlToImageDataPage(assets[String(size)],size);await chrome.action.setIcon({imageData});await chrome.storage.local.set({[ICON_VARIANT_KEY]:v});return v}
    async function chooseExtensionIcon(variant,button){if(button)button.disabled=true;const status=$('iconSelectionStatus');if(status){status.textContent='Aplicando…';status.className='status'}try{let applied=String(variant||'1');try{const r=await chrome.runtime.sendMessage({type:'VIENA_EXTENSION_ICON_SET',variant:applied});if(r?.ok&&r.variant)applied=String(r.variant)}catch(_){}applied=await applyExtensionIconFromPage(applied);paintIconSelection(applied);showToast('Icono de la extensión actualizado.','success')}catch(err){if(status){status.textContent='Error';status.className='status error'}showToast(String(err?.message||err),'error')}finally{if(button?.isConnected)button.disabled=false}}"""
if old_icon not in home: raise SystemExit("icon chooser block not found")
home=home.replace(old_icon,new_icon,1)

files["js/97-home-ui.js"]=home.encode("utf-8")

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
        "Se corrige el espacio entre las cards de versión y el mensaje de estado en Actualizaciones.",
        "El cambio de icono se aplica también desde la página de la extensión para actualizar inmediatamente el icono de la barra.",
        "Las plantillas mantienen su posición visual al abrirse y ya no rebotan al guardar o descartar cambios; se conserva la plantilla abierta."
    ]
})
PTR.write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist=json.loads(HIST.read_text(encoding="utf-8"))
hist["current_build"]=NEW_BUILD
hist["current_package"]=DST_REL
note="fix69 fixes updates-card spacing, adds a direct toolbar-icon application path, anchors accordion toggles to the clicked row, and removes global FLIP animation/reset behavior that caused save/discard bounce."
if note not in hist.get("notes",[]): hist.setdefault("notes",[]).append(note)
HIST.write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

assert len(pkg["files"])==28
h=files["js/97-home-ui.js"].decode("utf-8")
checks={
  "update gap":'margin-bottom:10px!important' in h and 'fix69 — update spacing' in h,
  "no global flip":'fix68BaseRenderEditorForm' not in h,
  "anchor toggle":"window.scrollBy(0,delta)" in h,
  "preserve expanded":"preserveExpanded:true" in h and "const openIndex=expandedTemplateIndex" in h,
  "direct icon":"applyExtensionIconFromPage" in h and "chrome.action.setIcon({imageData})" in h,
  "system name visible":"nameWrap.hidden=false" in h and "nameInput.readOnly=isSystem" in h,
  "stale loading hidden":"empty.style.display='none'" in h,
}
bad=[k for k,v in checks.items() if not v]
if bad: raise SystemExit("FAILED: "+", ".join(bad))
print(json.dumps({"build":NEW_BUILD,"package":DST_REL,"files":len(pkg["files"]),"sha256":package_sha,"checks":checks},ensure_ascii=False,indent=2))
