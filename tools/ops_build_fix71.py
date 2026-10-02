#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/"dev/builds/1.3.26-dev-status-operator-stability-fix70.json"
DST_REL="dev/builds/1.3.26-dev-icon-csp-template-viewport-fix71.json"
DST=ROOT/DST_REL
PTR=ROOT/"dev/self-update.json"
HIST=ROOT/"dev/history.json"
NEW_BUILD="1.3.26-dev-icon-csp-template-viewport-fix71"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(i):
    b=base64.b64decode(i["content_base64"],validate=True)
    assert len(b)==i["size"] and sha(b)==i["sha256"]
    return b

pkg=json.loads(SRC.read_text(encoding="utf-8"))
files={i["path"]:decode(i) for i in pkg["files"]}

# Fix icon CSP error: never fetch(data:...). Decode the embedded data URL locally.
bg=files["background.js"].decode("utf-8")
old_icon="""async function iconDataUrlToImageData(dataUrl,size){
  const blob=await fetch(dataUrl).then(r=>r.blob());
  const bitmap=await createImageBitmap(blob);
  const canvas=new OffscreenCanvas(size,size);
  const ctx=canvas.getContext('2d',{willReadFrequently:true});
  ctx.clearRect(0,0,size,size); ctx.drawImage(bitmap,0,0,size,size); try{bitmap.close()}catch(_){}
  return ctx.getImageData(0,0,size,size);
}"""
new_icon="""async function iconDataUrlToImageData(dataUrl,size){
  const raw=String(dataUrl||'');
  const match=/^data:([^;,]+)?(;base64)?,(.*)$/s.exec(raw);
  if(!match) throw new Error('Icono embebido inválido');
  const mime=match[1]||'image/png';
  const payload=match[3]||'';
  let bytes;
  if(match[2]){
    const binary=atob(payload);
    bytes=new Uint8Array(binary.length);
    for(let i=0;i<binary.length;i++) bytes[i]=binary.charCodeAt(i);
  }else{
    const text=decodeURIComponent(payload);
    bytes=new TextEncoder().encode(text);
  }
  const bitmap=await createImageBitmap(new Blob([bytes],{type:mime}));
  const canvas=new OffscreenCanvas(size,size);
  const ctx=canvas.getContext('2d',{willReadFrequently:true});
  ctx.clearRect(0,0,size,size); ctx.drawImage(bitmap,0,0,size,size); try{bitmap.close()}catch(_){}
  return ctx.getImageData(0,0,size,size);
}"""
if old_icon not in bg: raise SystemExit("iconDataUrlToImageData block not found")
bg=bg.replace(old_icon,new_icon,1)
files["background.js"]=bg.encode("utf-8")

# Fix accordion viewport behavior: preserve clicked header position first, then
# minimally scroll only as much as needed to show the whole expanded card.
home=files["js/97-home-ui.js"].decode("utf-8")
old_toggle="""const toggle=()=>{const anchorTop=card.getBoundingClientRect().top;expandedTemplateIndex=expandedTemplateIndex===index?-1:index;renderEditorForm();const keepAnchor=()=>{const next=document.querySelector(`#editorTemplates .template-card[data-template-index="${index}"]`);if(next){const delta=next.getBoundingClientRect().top-anchorTop;if(Math.abs(delta)>.5)window.scrollBy(0,delta)}};keepAnchor();requestAnimationFrame(()=>{keepAnchor();requestAnimationFrame(keepAnchor)})};"""
new_toggle="""const toggle=()=>{const opening=expandedTemplateIndex!==index;const anchorTop=card.getBoundingClientRect().top;expandedTemplateIndex=opening?index:-1;renderEditorForm();const keepAnchor=()=>{const next=document.querySelector(`#editorTemplates .template-card[data-template-index="${index}"]`);if(!next)return;const delta=next.getBoundingClientRect().top-anchorTop;if(Math.abs(delta)>.5)window.scrollBy(0,delta)};const ensureExpandedVisible=()=>{if(!opening)return;const next=document.querySelector(`#editorTemplates .template-card[data-template-index="${index}"]`);if(!next)return;const rect=next.getBoundingClientRect(),topSafe=12,bottomSafe=window.innerHeight-16,available=bottomSafe-topSafe;let dy=0;if(rect.height<=available){if(rect.top<topSafe)dy=rect.top-topSafe;else if(rect.bottom>bottomSafe)dy=rect.bottom-bottomSafe}else if(rect.top!==topSafe){dy=rect.top-topSafe}if(Math.abs(dy)>.5)window.scrollBy({top:dy,left:0,behavior:'smooth'})};keepAnchor();requestAnimationFrame(()=>{keepAnchor();requestAnimationFrame(ensureExpandedVisible)})};"""
if old_toggle not in home: raise SystemExit("fix70 template toggle not found")
home=home.replace(old_toggle,new_toggle,1)

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
      "Se elimina el error CSP al cambiar/restaurar el icono de la extensión: los iconos embebidos ya no usan fetch sobre data: URLs.",
      "Al desplegar una plantilla se conserva primero la posición de la fila elegida y luego se ajusta automáticamente el scroll mínimo para mostrar la plantilla completa dentro del viewport.",
      "El cierre de una plantilla mantiene estable la posición de su encabezado y no fuerza scroll adicional."
    ]
})
PTR.write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist=json.loads(HIST.read_text(encoding="utf-8"))
hist["current_build"]=NEW_BUILD
hist["current_package"]=DST_REL
note="fix71 removes data-URL fetch from icon decoding to satisfy extension CSP and makes template accordion expansion viewport-aware with minimal automatic scrolling."
if note not in hist.get("notes",[]): hist.setdefault("notes",[]).append(note)
HIST.write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

bg2=files["background.js"].decode("utf-8")
h=files["js/97-home-ui.js"].decode("utf-8")
checks={
  "no data fetch":"fetch(dataUrl)" not in bg2,
  "local base64 decode":"atob(payload)" in bg2 and "new Blob([bytes]" in bg2,
  "viewport aware":"ensureExpandedVisible" in h and "window.innerHeight-16" in h,
  "minimal scroll":"rect.bottom>bottomSafe" in h and "behavior:'smooth'" in h,
  "anchor first":"keepAnchor();requestAnimationFrame" in h,
}
bad=[k for k,v in checks.items() if not v]
if bad: raise SystemExit("FAILED: "+", ".join(bad))
print(json.dumps({"build":NEW_BUILD,"sha256":package_sha,"checks":checks},ensure_ascii=False,indent=2))
