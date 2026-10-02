#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/"dev/builds/1.3.26-dev-icon-modal-confirm-fix65.json"
DST_REL="dev/builds/1.3.26-dev-editor-actions-regression-fix66.json"
DST=ROOT/DST_REL
PTR=ROOT/"dev/self-update.json"
HIST=ROOT/"dev/history.json"
NEW_BUILD="1.3.26-dev-editor-actions-regression-fix66"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(i):
    b=base64.b64decode(i["content_base64"],validate=True)
    assert len(b)==i["size"] and sha(b)==i["sha256"]
    return b
def enc_css(s): return s.replace("\\","\\\\").replace('"','\\"').replace("\n","\\n")

pkg=json.loads(SRC.read_text(encoding="utf-8"))
files={i["path"]:decode(i) for i in pkg["files"]}
home=files["js/97-home-ui.js"].decode("utf-8")

# Point 12: clearer editor actions.
old_footer='''<div class=\\\"editor-footer-actions\\\">\\n                  <button id=\\\"deleteCustomButton\\\" class=\\\"btn danger\\\" hidden>Eliminar bot\\u00f3n</button>\\n                  <span></span>\\n                  <button id=\\\"cancelButtonEdit\\\" class=\\\"btn secondary\\\">Cancelar</button>\\n                  <button id=\\\"saveButtonEdit\\\" class=\\\"btn primary\\\">Guardar cambios</button>\\n                </div>'''
new_footer='''<div class=\\\"editor-footer-actions\\\">\\n                  <div class=\\\"editor-danger-zone\\\"><button id=\\\"deleteCustomButton\\\" class=\\\"btn danger\\\" hidden>Eliminar bot\\u00f3n</button></div>\\n                  <div class=\\\"editor-action-hint\\\">Los cambios del editor se aplican al guardar.</div>\\n                  <div class=\\\"editor-main-actions\\\"><button id=\\\"cancelButtonEdit\\\" class=\\\"btn secondary\\\">Descartar cambios</button><button id=\\\"saveButtonEdit\\\" class=\\\"btn primary\\\">Guardar cambios</button></div>\\n                </div>'''
if old_footer not in home: raise SystemExit("footer markup not found")
home=home.replace(old_footer,new_footer,1)

# Move Add template next to template heading at runtime.
mount="document.body.innerHTML=HOME_BODY;"
inject="""document.body.innerHTML=HOME_BODY;
    const addTemplateButton=$('addEditorTemplate');
    const templateSectionHead=document.querySelector('.editor-section-head');
    if(addTemplateButton&&templateSectionHead){
      addTemplateButton.classList.add('template-add-action');
      templateSectionHead.appendChild(addTemplateButton);
    }"""
if mount not in home: raise SystemExit("mount marker missing")
home=home.replace(mount,inject,1)

# Dirty-state helper.
marker="function cloneEditorData(value){return JSON.parse(JSON.stringify(value??null))}"
helper=marker+"""
    function editorIsDirty(){
      if(!editorDraft||!editorSelection)return false;
      if(editorSelection.kind==='new')return true;
      const current=selectedEditorItem();
      if(!current)return false;
      const a=cloneEditorData(editorDraft),b=cloneEditorData(current);
      return JSON.stringify(a)!==JSON.stringify(b);
    }
    function updateEditorActionState(){
      const status=$('editorFormStatus');
      if(!status||!editorDraft)return;
      if(editorIsDirty()&&!status.classList.contains('editor-error')){
        status.className='minor-status editor-dirty';
        status.textContent='Cambios sin guardar.';
      }
    }"""
if marker not in home: raise SystemExit("clone helper missing")
home=home.replace(marker,helper,1)

# Inputs update dirty indicator.
home=home.replace("nameInput.addEventListener('input',()=>{t.nombre=nameInput.value;name.textContent=t.nombre||'Plantilla sin nombre'});reasonInput.addEventListener('input',()=>{t.motivo=reasonInput.value});msg.addEventListener('input',()=>{t.mensaje=msg.value;preview.textContent=t.mensaje||'Sin mensaje'});",
"nameInput.addEventListener('input',()=>{t.nombre=nameInput.value;name.textContent=t.nombre||'Plantilla sin nombre';updateEditorActionState()});reasonInput.addEventListener('input',()=>{t.motivo=reasonInput.value;updateEditorActionState()});msg.addEventListener('input',()=>{t.mensaje=msg.value;preview.textContent=t.mensaje||'Sin mensaje';updateEditorActionState()});",1)

home=home.replace("editorDraft.nombre=e.target.value}});","editorDraft.nombre=e.target.value;updateEditorActionState()}});",1)

old_add="$('addEditorTemplate').addEventListener('click',()=>{if(!editorDraft)return;editorDraft.plantillas.push({id:'',nombre:'',motivo:'',mensaje:'',motivosConocidos:[]});expandedTemplateIndex=editorDraft.plantillas.length-1;renderEditorForm()});"
new_add="$('addEditorTemplate').addEventListener('click',()=>{if(!editorDraft)return;editorDraft.plantillas.push({id:'',nombre:'',motivo:'',mensaje:'',motivosConocidos:[]});expandedTemplateIndex=editorDraft.plantillas.length-1;renderEditorForm();updateEditorActionState();showToast('Plantilla agregada al borrador. Guardá los cambios para aplicarla.','warning')});"
if old_add not in home: raise SystemExit("add template handler missing")
home=home.replace(old_add,new_add,1)

old_cancel="$('cancelButtonEdit').addEventListener('click',()=>{const item=selectedEditorItem();if(item){editorDraft=cloneEditorData(item);expandedTemplateIndex=0;renderEditorForm()}else if(buttonEditorState?.sistema)selectEditorButton('system',buttonEditorState.sistema.id)});"
new_cancel="$('cancelButtonEdit').addEventListener('click',async()=>{if(editorIsDirty()){const ok=await requestUiConfirm({title:'Descartar cambios',message:'Hay cambios sin guardar. Si continuás, se perderán.',confirmLabel:'Descartar'});if(!ok)return}const item=selectedEditorItem();if(item){editorDraft=cloneEditorData(item);expandedTemplateIndex=0;renderEditorForm();showToast('Cambios descartados.','warning')}else if(buttonEditorState?.sistema)selectEditorButton('system',buttonEditorState.sistema.id)});"
if old_cancel not in home: raise SystemExit("cancel handler missing")
home=home.replace(old_cancel,new_cancel,1)

old_save="$('saveButtonEdit').addEventListener('click',async e=>{if(!editorDraft)return;const btn=e.currentTarget;btn.disabled=true;$('editorFormStatus').className='minor-status';$('editorFormStatus').textContent='Guardando…';try{let r;if(editorSelection.kind==='system')r=await editorMessage({type:'VIENA_BUTTON_EDITOR_SAVE_SYSTEM',plantillas:editorDraft.plantillas});else r=await editorMessage({type:'VIENA_BUTTON_EDITOR_SAVE_GROUP',id:editorSelection.kind==='custom'?editorSelection.id:'',nombre:editorDraft.nombre,plantillas:editorDraft.plantillas});buttonEditorState=r.state;const savedId=editorSelection.kind==='system'?buttonEditorState.sistema.id:r.item?.id;editorSelection={kind:editorSelection.kind==='system'?'system':'custom',id:savedId};const item=selectedEditorItem();editorDraft=cloneEditorData(item);expandedTemplateIndex=0;renderEditorForm();$('editorFormStatus').className='minor-status editor-ok';$('editorFormStatus').textContent='Cambios guardados.';showToast('Editor de botones actualizado.','success')}catch(err){$('editorFormStatus').className='minor-status editor-error';$('editorFormStatus').textContent=String(err?.message||err);showToast(String(err?.message||err),'error')}finally{btn.disabled=false}});"
new_save="$('saveButtonEdit').addEventListener('click',async e=>{if(!editorDraft)return;const btn=e.currentTarget,original=btn.textContent;btn.disabled=true;btn.textContent='Guardando…';$('editorFormStatus').className='minor-status';$('editorFormStatus').textContent='Guardando cambios…';try{let r;if(editorSelection.kind==='system')r=await editorMessage({type:'VIENA_BUTTON_EDITOR_SAVE_SYSTEM',plantillas:editorDraft.plantillas});else r=await editorMessage({type:'VIENA_BUTTON_EDITOR_SAVE_GROUP',id:editorSelection.kind==='custom'?editorSelection.id:'',nombre:editorDraft.nombre,plantillas:editorDraft.plantillas});buttonEditorState=r.state;const savedId=editorSelection.kind==='system'?buttonEditorState.sistema.id:r.item?.id;editorSelection={kind:editorSelection.kind==='system'?'system':'custom',id:savedId};const item=selectedEditorItem();editorDraft=cloneEditorData(item);expandedTemplateIndex=0;renderEditorForm();$('editorFormStatus').className='minor-status editor-ok';$('editorFormStatus').textContent='Cambios guardados.';showToast('Cambios guardados correctamente.','success')}catch(err){$('editorFormStatus').className='minor-status editor-error';$('editorFormStatus').textContent=String(err?.message||err);showToast(String(err?.message||err),'error')}finally{btn.disabled=false;btn.textContent=original}});"
if old_save not in home: raise SystemExit("save handler missing")
home=home.replace(old_save,new_save,1)

css=r'''
/* fix66 — editor action hierarchy */
.editor-section-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.editor-section-head .status{margin-left:auto}
.template-add-action{margin-left:2px}
.editor-footer-actions{
  position:sticky;bottom:0;z-index:3;
  display:grid!important;grid-template-columns:auto minmax(120px,1fr) auto!important;
  align-items:center;gap:12px!important;
  margin:16px -16px -15px!important;padding:11px 16px 13px!important;
  background:rgba(255,255,255,.97)!important;
  border-top:1px solid #dce7f1!important;
  box-shadow:0 -8px 20px rgba(13,48,82,.05);
}
.editor-danger-zone{min-width:112px}
.editor-action-hint{font-size:10px;color:#74899d;text-align:center;line-height:1.3}
.editor-main-actions{display:flex;gap:8px;justify-content:flex-end}
.editor-main-actions .btn{min-width:116px}
.editor-main-actions .btn.primary{font-weight:800;box-shadow:0 5px 14px rgba(9,82,153,.12)}
.editor-dirty{color:#9a6500!important;font-weight:700}
@media(max-width:800px){
  .editor-footer-actions{grid-template-columns:1fr!important;margin-left:-16px!important;margin-right:-16px!important}
  .editor-danger-zone{order:3;min-width:0}
  .editor-action-hint{order:1;text-align:left}
  .editor-main-actions{order:2;display:grid;grid-template-columns:1fr 1fr}
  .editor-main-actions .btn{min-width:0;width:100%}
  .editor-danger-zone .btn{width:100%}
  .template-add-action{width:auto!important}
}
@media(max-width:520px){
  .editor-main-actions{grid-template-columns:1fr}
}
'''
css_marker='";\n  const HOME_BODY'
if css_marker not in home: raise SystemExit("CSS marker missing")
home=home.replace(css_marker,enc_css(css)+css_marker,1)

files["js/97-home-ui.js"]=home.encode("utf-8")

for path,const_name in [("background.js","VIENA_BUILD_ID"),("js/80-update-banner.js","CONTENT_BUILD_ID"),("js/90-runtime-status.js","BUILD_ID")]:
    txt=files[path].decode("utf-8")
    txt,n=re.subn(rf"(const\s+{const_name}\s*=\s*['\"])([^'\"]+)(['\"])",rf"\g<1>{NEW_BUILD}\g<3>",txt,count=1)
    if n!=1: raise SystemExit(f"identity missing {path}")
    files[path]=txt.encode("utf-8")

build=json.loads(files["build.json"].decode("utf-8"));build.update({"build":NEW_BUILD,"version":"1.3.26","channel":"DEV"})
files["build.json"]=(json.dumps(build,ensure_ascii=False,indent=2)+"\n").encode()
integrity=json.loads(files["integrity-manifest.json"].decode());integrity["build"]=NEW_BUILD;integrity["files"]={p:sha(b) for p,b in files.items() if p!="integrity-manifest.json"}
files["integrity-manifest.json"]=(json.dumps(integrity,ensure_ascii=False,indent=2)+"\n").encode()

order=[i["path"] for i in pkg["files"]];pkg["build"]=NEW_BUILD;pkg["generated_at"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z");pkg["files"]=[]
for p in order:
    b=files[p];pkg["files"].append({"path":p,"size":len(b),"sha256":sha(b),"content_base64":base64.b64encode(b).decode()})
raw=(json.dumps(pkg,ensure_ascii=False,indent=2)+"\n").encode();DST.write_bytes(raw);package_sha=sha(raw)

ptr=json.loads(PTR.read_text());ptr.update({"schema":1,"version":"1.3.26","build":NEW_BUILD,"channel":"DEV","package_url":f"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/{DST_REL}","package_sha256":package_sha,"notes":["Se ordenan las acciones del editor: Guardar queda como acción primaria, Descartar confirma cambios pendientes y Eliminar permanece separado como acción destructiva.","Agregar plantilla se ubica junto al encabezado de plantillas y deja claro que el cambio queda pendiente hasta Guardar.","Se incorpora estado visible de cambios sin guardar y feedback de Guardando/cambios guardados."]});PTR.write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n")
hist=json.loads(HIST.read_text());hist["current_build"]=NEW_BUILD;hist["current_package"]=DST_REL;hist.setdefault("notes",[]).append("fix66 clarifies editor action hierarchy and adds dirty/discard/save feedback before the final regression pass.");HIST.write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n")

assert len(pkg["files"])==28
assert b"editor-main-actions" in files["js/97-home-ui.js"]
assert b"editorIsDirty" in files["js/97-home-ui.js"]
assert b"Descartar cambios" in files["js/97-home-ui.js"]
print(json.dumps({"build":NEW_BUILD,"package":DST_REL,"files":len(pkg["files"]),"sha256":package_sha},indent=2))
