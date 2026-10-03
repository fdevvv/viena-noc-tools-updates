#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

R = pathlib.Path(__file__).resolve().parents[1]
SRC = R / "dev/builds/1.3.26-dev-fullview-general-updates-fix92.json"
DST_REL = "dev/builds/1.3.26-dev-update-layout-info-coherence-fix93.json"
DST = R / DST_REL
OLD = "1.3.26-dev-fullview-general-updates-fix92"
NEW = "1.3.26-dev-update-layout-info-coherence-fix93"

def h(b):
    return hashlib.sha256(b).hexdigest()

pkg=json.loads(SRC.read_text(encoding="utf-8"))
files={}
order=[]
for item in pkg["files"]:
    raw=base64.b64decode(item["content_base64"],validate=True)
    assert h(raw)==item["sha256"]
    files[item["path"]]=raw
    order.append(item["path"])

html=files["popup.html"].decode("utf-8")
popup=files["popup.js"].decode("utf-8")

current = '<div class="update-actions-grid"><button id="checkUpdate" type="button" class="btn secondary">Buscar actualización DEV</button><div class="viena-update-actions" aria-label="Acciones de actualización"><button id="openUpdate" type="button" class="btn primary" style="display:none">Actualizar</button><button id="manualReleaseZip" type="button" class="btn secondary manual-zip-action" style="display:none" title="Descarga la RELEASE vigente para instalación manual">Descargar ZIP</button></div></div>'
replacement = '<div class="update-actions-grid viena-update-actions-final" aria-label="Acciones de actualización"><button id="checkUpdate" type="button" class="btn secondary">Buscar actualización DEV</button><button id="manualReleaseZip" type="button" class="btn secondary manual-zip-action" style="display:none" title="Descarga la RELEASE vigente para instalación manual">Descargar ZIP</button><button id="openUpdate" type="button" class="btn primary" style="display:none">Actualizar</button></div>'
assert current in html, "current popup update action markup changed"
html=html.replace(current,replacement,1)

for style_id in ("viena-update-actions-layout-fix88","viena-update-buttons-final-align-fix91"):
    html2,n=re.subn(r'\n?<style id="'+re.escape(style_id)+r'">.*?</style>\n?', '\n', html, count=1, flags=re.S)
    assert n==1, style_id+" not found"
    html=html2

final_css = """
<style id="viena-update-actions-final-fix93">
.update-actions-grid.viena-update-actions-final{display:grid!important;grid-template-columns:minmax(0,1fr) minmax(0,1fr)!important;gap:8px!important;align-items:start!important}
.update-actions-grid.viena-update-actions-final>button{box-sizing:border-box!important;width:100%!important;min-width:0!important;height:52px!important;min-height:52px!important;max-height:52px!important;margin:0!important;padding:8px 10px!important;border-radius:8px!important;align-items:center;justify-content:center;text-align:center!important;line-height:1.15!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}
.update-actions-grid.viena-update-actions-final #manualReleaseZip{background:linear-gradient(180deg,#1684f6 0%,#0b69d1 100%)!important;border:1px solid #0b69d1!important;color:#fff!important;font-weight:700!important}
.update-actions-grid.viena-update-actions-final #openUpdate{grid-column:1/-1!important;background:linear-gradient(180deg,#1684f6 0%,#0b69d1 100%)!important;border:1px solid #0b69d1!important;color:#fff!important;font-weight:700!important}
.update-actions-grid.viena-update-actions-final:has(#manualReleaseZip[style*="display: none"]) #checkUpdate{grid-column:1/-1!important}
.update-actions-grid.viena-update-actions-final #manualReleaseZip[style*="display: none"],.update-actions-grid.viena-update-actions-final #openUpdate[style*="display: none"]{display:none!important}
@media(max-width:340px){.update-actions-grid.viena-update-actions-final{grid-template-columns:1fr!important}.update-actions-grid.viena-update-actions-final #checkUpdate,.update-actions-grid.viena-update-actions-final #manualReleaseZip,.update-actions-grid.viena-update-actions-final #openUpdate{grid-column:1!important}}
</style>
"""
assert "</head>" in html
html=html.replace("</head>",final_css+"\n</head>",1)

marker="// VIENA_EQUAL_UPDATE_ACTION_SIZE_FIX90"
assert marker in popup
popup=popup[:popup.index(marker)].rstrip()+"\n"

label_fix = """
// VIENA_UPDATE_BUTTON_LABEL_FIX93
(() => {
  const normalize = () => {
    const btn = document.getElementById('openUpdate');
    if (!btn) return;
    const text = String(btn.textContent || '').replace(/\\s+/g,' ').trim();
    if (!/^Actualizar DEV\\b/i.test(text)) return;
    const match = text.match(/\\b(\\d+\\.\\d+\\.\\d+)\\b/);
    btn.textContent = match ? 'Actualizar DEV · ' + match[1] : 'Actualizar DEV';
  };
  const target = document.getElementById('openUpdate');
  if (target) {
    new MutationObserver(normalize).observe(target,{childList:true,subtree:true,characterData:true});
    normalize();
  }
})();
"""
popup += "\n"+label_fix
files["popup.html"]=html.encode("utf-8")
files["popup.js"]=popup.encode("utf-8")

home=files["js/97-home-ui.js"].decode("utf-8")

old_badge='<div class=\\\"panel-head\\\"><h2>Actualizaciones</h2><span class=\\\"status ok\\\">Resumen</span></div>'
new_badge='<div class=\\\"panel-head\\\"><h2>Actualizaciones</h2><span id=\\\"summaryUpdateBadge\\\" class=\\\"status\\\">Comprobando…</span></div>'
assert old_badge in home
home=home.replace(old_badge,new_badge,1)

old_inst="$('summaryInstalled').textContent=labelVersion();$('updatesInstalled').textContent=labelVersion()"
new_inst="$('summaryInstalled').textContent=manifest.version;$('updatesInstalled').textContent=labelVersion()"
assert old_inst in home
home=home.replace(old_inst,new_inst,1)

tick=chr(96)
placeholder="v$"+"{availableVersion}"
old_label="label=isDev()?("+ "availableBuild||"+tick+placeholder+tick+"):"+tick+placeholder+tick+";"
new_label="label=isDev()?(availableVersion+' DEV'):availableVersion;"
assert old_label in home, old_label
home=home.replace(old_label,new_label,1)

old_available="$('summaryAvailable').textContent=label;$('updatesAvailable').textContent=label;$('updateStateBadge').textContent=newer?'Disponible':'Actualizada';"
new_available="$('summaryAvailable').textContent=label;$('updatesAvailable').textContent=label;const summaryBadge=$('summaryUpdateBadge');if(summaryBadge){summaryBadge.textContent=newer?'Disponible':'Actualizada';summaryBadge.className='status '+(newer?'warn':'ok')}$('updateStateBadge').textContent=newer?'Disponible':'Actualizada';"
assert old_available in home
home=home.replace(old_available,new_available,1)

old_error="$('summaryAvailable').textContent='Sin datos';$('updatesAvailable').textContent='Sin datos';$('updateStateBadge').textContent='Error';"
new_error="$('summaryAvailable').textContent='Sin datos';$('updatesAvailable').textContent='Sin datos';const summaryBadge=$('summaryUpdateBadge');if(summaryBadge){summaryBadge.textContent='Error';summaryBadge.className='status error'}$('updateStateBadge').textContent='Error';"
assert old_error in home
home=home.replace(old_error,new_error,1)

start=home.find("async function refreshFolder(){")
end=home.find("\n\nasync function refreshUpdates()",start)
assert start>=0 and end>=0
new_folder = """async function refreshFolder(){const updater=window.VienaLocalUpdater;let label='No disponible',linked=false,ready=false,name='';fullFolderStatus=null;fullFolderHandle=null;try{if(updater?.supported()){const st=await updater.getLinkStatus();fullFolderStatus=st;try{fullFolderHandle=await updater.getStoredHandleForUi?.()}catch(_){}linked=Boolean(st?.linked);ready=Boolean(st?.linked&&st?.valid);name=String(st?.name||'').trim();label=linked?(name||'Vinculada'):'Sin vincular'}}catch(_){label='Error al comprobar'}const linkedLabel=name?(name+' · Vinculada'):'Vinculada';const summary=linked?('Carpeta vinculada: '+linkedLabel+(ready?'':' · acceso guardado · se verificará al actualizar')):('Carpeta vinculada: '+label);$('summaryFolder').textContent=summary;$('folderDetail').textContent=linked?(ready?label:(label+' · acceso guardado')):label;$('folderBadge').textContent=linked?'Vinculada':'Sin vincular';$('folderBadge').className='status '+(linked?'ok':'warn')}"""
home=home[:start]+new_folder+home[end:]

files["js/97-home-ui.js"]=home.encode("utf-8")

for path in ("background.js","js/80-update-banner.js","js/90-runtime-status.js"):
    s=files[path].decode("utf-8")
    assert OLD in s, OLD+" missing in "+path
    files[path]=s.replace(OLD,NEW,1).encode("utf-8")

build=json.loads(files["build.json"].decode("utf-8"))
build["build"]=NEW
files["build.json"]=(json.dumps(build,ensure_ascii=False,indent=2)+"\n").encode("utf-8")

integ=json.loads(files["integrity-manifest.json"].decode("utf-8"))
integ["build"]=NEW
integ["files"]={p:h(b) for p,b in files.items() if p!="integrity-manifest.json"}
files["integrity-manifest.json"]=(json.dumps(integ,ensure_ascii=False,indent=2)+"\n").encode("utf-8")

pkg["build"]=NEW
pkg["generated_at"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
pkg["files"]=[]
for path in order:
    raw=files[path]
    pkg["files"].append({"path":path,"size":len(raw),"sha256":h(raw),"content_base64":base64.b64encode(raw).decode("ascii")})
raw_pkg=(json.dumps(pkg,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
DST.write_bytes(raw_pkg)

ptr=json.loads((R/"dev/self-update.json").read_text(encoding="utf-8"))
ptr.update({
    "build":NEW,
    "package_url":"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/"+DST_REL,
    "package_sha256":h(raw_pkg),
    "notes":[
        "En el popup, Buscar actualización DEV y Descargar ZIP quedan juntos arriba; Actualizar DEV aparece debajo a todo el ancho sólo cuando hay una actualización.",
        "La vista General y el popup muestran la misma versión instalada, versión disponible y estado de carpeta vinculada.",
        "El build interno continúa visible en Estado general para diagnóstico, pero deja de usarse como etiqueta de versión disponible."
    ]
})
(R/"dev/self-update.json").write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist=json.loads((R/"dev/history.json").read_text(encoding="utf-8"))
hist["current_build"]=NEW
hist["current_package"]=DST_REL
(R/"dev/history.json").write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hout=files["popup.html"].decode("utf-8")
jout=files["popup.js"].decode("utf-8")
homeout=files["js/97-home-ui.js"].decode("utf-8")
assert 'viena-update-actions-final-fix93' in hout
assert '<div class="viena-update-actions"' not in hout
assert hout.index('id="checkUpdate"') < hout.index('id="manualReleaseZip"') < hout.index('id="openUpdate"')
assert "VIENA_EQUAL_UPDATE_ACTION_SIZE_FIX90" not in jout
assert "VIENA_UPDATE_BUTTON_LABEL_FIX93" in jout
assert 'id=\\\"summaryUpdateBadge\\\"' in homeout
assert "$('summaryInstalled').textContent=manifest.version" in homeout
assert "label=isDev()?(availableVersion+' DEV'):availableVersion;" in homeout
assert "acceso guardado · se verificará al actualizar" in homeout
print(json.dumps({"build":NEW,"package":DST_REL,"sha256":h(raw_pkg)},ensure_ascii=False,indent=2))
