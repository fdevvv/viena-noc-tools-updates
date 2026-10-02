#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/"dev/builds/1.3.26-dev-editor-actions-regression-fix66.json"
DST_REL="dev/builds/1.3.26-dev-final-ui-cleanup-fix67.json"
DST=ROOT/DST_REL
PTR=ROOT/"dev/self-update.json"
HIST=ROOT/"dev/history.json"
NEW_BUILD="1.3.26-dev-final-ui-cleanup-fix67"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(i):
    b=base64.b64decode(i["content_base64"],validate=True)
    assert len(b)==i["size"] and sha(b)==i["sha256"]
    return b

pkg=json.loads(SRC.read_text(encoding="utf-8"))
files={i["path"]:decode(i) for i in pkg["files"]}
home=files["js/97-home-ui.js"].decode("utf-8")

# Final cleanup: remove hidden duplicate sections from the full-view markup.
patterns = [
    r'\\n\\n      <section class=\\\"view\\\" data-view=\\\"tools\\\">.*?</section>',
    r'\\n\\n      <section class=\\\"view\\\" data-view=\\\"diagnostics\\\">.*?</section>',
]
for pat in patterns:
    home2,n=re.subn(pat,'',home,count=1,flags=re.S)
    if n!=1: raise SystemExit(f"section not found: {pat}")
    home=home2

# Remove dead diagnostics writes from refresh functions.
repls = [
    (";$('diagRuntime').textContent=stale?'Activo · revisar pestañas':'Activo'",""),
    (";$('diagRuntime').textContent='Sin datos'",""),
    (";$('diagUser').value=user;$('diagSurname').value=surname;$('diagOperatorStatus').textContent=local.viena_usuario_origen==='auto'?'El usuario VIENA se obtiene de la sesión y no se modifica desde esta pantalla.':'Usuario configurado manualmente.'",""),
    (";$('diagFolder').textContent=text",""),
]
for old,new in repls:
    if old not in home: raise SystemExit(f"dead diagnostic fragment missing: {old[:80]}")
    home=home.replace(old,new,1)

# Remove refreshRegistry and keep refreshAll focused only on visible UI.
old_reg="""async function refreshRegistry(){try{const r=await chrome.runtime.sendMessage({type:'VIENA_GET_INSTALL_REGISTRY_STATUS'});if(!r?.ok)throw new Error();$('diagRegistry').textContent=r.lastOk?'OK':'Pendiente'}catch(_){$('diagRegistry').textContent='Sin datos'}}
    async function refreshAll(){await Promise.allSettled([refreshOperational(),refreshOperator(),refreshFolder(),refreshUpdates(),refreshRegistry()])}"""
new_reg="""async function refreshAll(){await Promise.allSettled([refreshOperational(),refreshOperator(),refreshFolder(),refreshUpdates()])}"""
if old_reg not in home: raise SystemExit("refreshRegistry block missing")
home=home.replace(old_reg,new_reg,1)

# Remove inactive diagnostics actions from listener chain, retain visible actions only.
old_chain="""$('refreshAll').addEventListener('click',refreshAll);$('refreshTools')?.addEventListener('click',refreshOperational);$('checkUpdates').addEventListener('click',refreshUpdates);$('openFolderManager').addEventListener('click',()=>openAdjacentExtensionTab(chrome.runtime.getURL('updater.html')));$('saveSurname').addEventListener('click',async()=>{const v=$('diagSurname').value.trim();if(!/^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]{2,40}$/.test(v)){showToast('Ingresá un apellido válido.','error');return}await chrome.storage.local.set({[ASSIGN_KEY]:v});try{await chrome.storage.sync.set({[ASSIGN_KEY]:v})}catch(_){}showToast('Apellido guardado.','success');await refreshOperator()});$('syncRegistry').addEventListener('click',async e=>{e.currentTarget.disabled=true;try{const r=await chrome.runtime.sendMessage({type:'VIENA_INSTALL_REGISTRY_SYNC_NOW',reason:'full_view'});if(!r?.ok)throw new Error(r?.error||'No se pudo sincronizar');showToast('Registro sincronizado.','success');await refreshRegistry()}catch(err){showToast(String(err?.message||err),'error')}finally{e.currentTarget.disabled=false}});"""
new_chain="""$('refreshAll').addEventListener('click',refreshAll);$('checkUpdates').addEventListener('click',refreshUpdates);$('openFolderManager').addEventListener('click',()=>openAdjacentExtensionTab(chrome.runtime.getURL('updater.html')));"""
if old_chain not in home: raise SystemExit("listener chain missing")
home=home.replace(old_chain,new_chain,1)

# Remove now-unused secondary grid population logic; keep general grid only.
old_tools="""function renderToolScaffolds(){const html=Object.keys(PLATFORM_LABELS).map(toolMarkup).join('');$('toolGridGeneral').innerHTML=html;if($('toolGridFull'))$('toolGridFull').innerHTML=html;const quick=$('quickTabs');if(quick){quick.innerHTML=Object.entries(PLATFORM_LABELS).filter(([k])=>k!=='viena').map(([k,v])=>`<button class=\\"chip\\" data-quick=\\"${k}\\">${v}</button>`).join('');document.querySelectorAll('[data-quick]').forEach(b=>b.addEventListener('click',()=>runPlatformAction(b.dataset.quick,'open',b)))}document.querySelectorAll('.tool-row').forEach(row=>row.querySelector('[data-action]').addEventListener('click',e=>runPlatformAction(row.dataset.tool,e.currentTarget.dataset.action,e.currentTarget)))}"""
new_tools="""function renderToolScaffolds(){const html=Object.keys(PLATFORM_LABELS).map(toolMarkup).join('');$('toolGridGeneral').innerHTML=html;document.querySelectorAll('.tool-row').forEach(row=>row.querySelector('[data-action]').addEventListener('click',e=>runPlatformAction(row.dataset.tool,e.currentTarget.dataset.action,e.currentTarget)))}"""
if old_tools not in home: raise SystemExit("renderToolScaffolds block missing")
home=home.replace(old_tools,new_tools,1)

# Remove legacy redirects now that old sections no longer exist.
old_section="""function setSection(name){if(name==='tools'||name==='diagnostics')name='general';document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.dataset.view===name));document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.section===name));history.replaceState(null,'',`#${name}`)}"""
new_section="""function setSection(name){if(!['general','personalization','updates'].includes(name))name='general';document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.dataset.view===name));document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.section===name));history.replaceState(null,'',`#${name}`)}"""
if old_section not in home: raise SystemExit("setSection block missing")
home=home.replace(old_section,new_section,1)

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
        "Se elimina definitivamente de la vista completa el contenido duplicado de Herramientas y Configuración/Diagnóstico.",
        "La pestaña queda consolidada en General, Personalización y Actualizaciones, sin secciones ocultas duplicadas.",
        "Se realiza la validación final de sintaxis, compatibilidad histórica y regresiones de la ronda UX/UI."
    ]
})
PTR.write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist=json.loads(HIST.read_text(encoding="utf-8"))
hist["current_build"]=NEW_BUILD
hist["current_package"]=DST_REL
note="fix67 removes dead duplicate full-view Tools/Diagnostics sections and associated code, leaving only General, Personalización and Actualizaciones before final acceptance."
if note not in hist.get("notes",[]): hist.setdefault("notes",[]).append(note)
HIST.write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

assert len(pkg["files"])==28
h=files["js/97-home-ui.js"].decode("utf-8")
for forbidden in ['data-view=\\\"tools\\\"','data-view=\\\"diagnostics\\\"','diagUser','diagSurname','diagRuntime','diagRegistry','diagFolder','syncRegistry','toolGridFull','quickTabs']:
    assert forbidden not in h, forbidden
print(json.dumps({"build":NEW_BUILD,"package":DST_REL,"files":len(pkg["files"]),"sha256":package_sha},indent=2))
