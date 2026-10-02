#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/"dev/builds/1.3.26-dev-icon-csp-template-viewport-fix71.json"
DST_REL="dev/builds/1.3.26-dev-state-ring-icon-fix72.json"
DST=ROOT/DST_REL
PTR=ROOT/"dev/self-update.json"
HIST=ROOT/"dev/history.json"
NEW_BUILD="1.3.26-dev-state-ring-icon-fix72"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(i):
    b=base64.b64decode(i["content_base64"],validate=True)
    assert len(b)==i["size"] and sha(b)==i["sha256"]
    return b

pkg=json.loads(SRC.read_text(encoding="utf-8"))
files={i["path"]:decode(i) for i in pkg["files"]}
bg=files["background.js"].decode("utf-8")

old_block="""const EXTENSION_ICON_VARIANT_KEY = 'viena_extension_icon_variant_v1';
function normalizeExtensionIconVariant(value){const v=String(value||'1');return globalThis.VIENA_ICON_VARIANTS?.[v]?v:'1'}
async function iconDataUrlToImageData(dataUrl,size){
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
}
async function applyExtensionIconVariant(value,{persist=false}={}){
  const variant=normalizeExtensionIconVariant(value), assets=globalThis.VIENA_ICON_VARIANTS?.[variant];
  if(!assets) throw new Error('Icono no disponible');
  const imageData={};
  for(const size of [16,32,48,128]) imageData[size]=await iconDataUrlToImageData(assets[String(size)],size);
  await chrome.action.setIcon({imageData});
  if(persist) await chrome.storage.local.set({[EXTENSION_ICON_VARIANT_KEY]:variant});
  return variant;
}
async function restoreExtensionIconVariant(){try{const st=await chrome.storage.local.get([EXTENSION_ICON_VARIANT_KEY]);return await applyExtensionIconVariant(st[EXTENSION_ICON_VARIANT_KEY]||'1')}catch(_){return '1'}}"""

new_block="""const EXTENSION_ICON_VARIANT_KEY = 'viena_extension_icon_variant_v1';
const ICON_RING_COLORS = {
  on:'#23833B',
  update:'#D97706',
  reload:'#B42318',
  tabs:'#AD6B00'
};
let currentExtensionIconState='neutral';
const extensionIconBaseCache=new Map();
function normalizeExtensionIconVariant(value){const v=String(value||'1');return globalThis.VIENA_ICON_VARIANTS?.[v]?v:'1'}
async function iconDataUrlToImageData(dataUrl,size){
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
}
async function getBaseExtensionIconData(variant,size,dataUrl){
  const key=`${variant}:${size}`;
  if(extensionIconBaseCache.has(key)) return extensionIconBaseCache.get(key);
  const data=await iconDataUrlToImageData(dataUrl,size);
  extensionIconBaseCache.set(key,data);
  return data;
}
function renderExtensionIconState(base,size,state){
  const color=ICON_RING_COLORS[state]||'';
  if(!color)return base;
  const canvas=new OffscreenCanvas(size,size);
  const ctx=canvas.getContext('2d',{willReadFrequently:true});
  ctx.putImageData(base,0,0);
  const width=Math.max(1,Math.round(size*.09));
  const inset=Math.max(.5,width/2);
  ctx.save();
  ctx.strokeStyle=color;
  ctx.lineWidth=width;
  ctx.globalAlpha=.98;
  if(typeof ctx.roundRect==='function'){
    const radius=Math.max(2,Math.round(size*.18));
    ctx.beginPath();
    ctx.roundRect(inset,inset,size-width,size-width,radius);
    ctx.stroke();
  }else{
    ctx.strokeRect(inset,inset,size-width,size-width);
  }
  ctx.restore();
  return ctx.getImageData(0,0,size,size);
}
async function applyExtensionIconVariant(value,{persist=false,state=currentExtensionIconState}={}){
  const variant=normalizeExtensionIconVariant(value), assets=globalThis.VIENA_ICON_VARIANTS?.[variant];
  if(!assets) throw new Error('Icono no disponible');
  currentExtensionIconState=state||'neutral';
  const imageData={};
  for(const size of [16,32,48,128]){
    const base=await getBaseExtensionIconData(variant,size,assets[String(size)]);
    imageData[size]=renderExtensionIconState(base,size,currentExtensionIconState);
  }
  await chrome.action.setIcon({imageData});
  if(persist) await chrome.storage.local.set({[EXTENSION_ICON_VARIANT_KEY]:variant});
  return variant;
}
async function applyExtensionIconState(state){
  currentExtensionIconState=state||'neutral';
  const st=await chrome.storage.local.get([EXTENSION_ICON_VARIANT_KEY]);
  return applyExtensionIconVariant(st[EXTENSION_ICON_VARIANT_KEY]||'1',{state:currentExtensionIconState});
}
async function restoreExtensionIconVariant(){try{const st=await chrome.storage.local.get([EXTENSION_ICON_VARIANT_KEY]);return await applyExtensionIconVariant(st[EXTENSION_ICON_VARIANT_KEY]||'1',{state:currentExtensionIconState})}catch(_){return '1'}}"""

if old_block not in bg:
    raise SystemExit("icon block not found")
bg=bg.replace(old_block,new_block,1)

old_refresh="""async function refreshActionBadge(tabId=null){
  try{
    const diskBuild=await readPackageBuild();
    if(diskBuild && diskBuild!==VIENA_BUILD_ID){
      const b=STATUS_BADGES.reload;
      await chrome.action.setBadgeText({text:b.text}); await chrome.action.setBadgeBackgroundColor({color:b.color}); await chrome.action.setTitle({title:b.title}); return;
    }
    let tab=null;
    if(tabId){ try{tab=await chrome.tabs.get(tabId);}catch(_){} }
    if(!tab){ const arr=await chrome.tabs.query({active:true,currentWindow:true}); tab=arr[0]||null; }
    if(tab && platformForUrl(tab.url)){
      const ping=await pingStatusTab(tab);
      if(!ping.ok||ping.stale){
        const b=STATUS_BADGES.tabs;
        await chrome.action.setBadgeText({text:b.text}); await chrome.action.setBadgeBackgroundColor({color:b.color}); await chrome.action.setTitle({title:b.title}); return;
      }
    }
    const state=await getUpdateState();
    if(state?.available){
      const b=STATUS_BADGES.update;
      await chrome.action.setBadgeText({text:b.text}); await chrome.action.setBadgeBackgroundColor({color:b.color}); await chrome.action.setTitle({title:`${b.title}: v${state.latest}`}); return;
    }
    if(tab && platformForUrl(tab.url)){
      const b=STATUS_BADGES.on;
      await chrome.action.setBadgeText({text:b.text}); await chrome.action.setBadgeBackgroundColor({color:b.color}); await chrome.action.setTitle({title:b.title}); return;
    }
    await chrome.action.setBadgeText({text:''});
    await chrome.action.setTitle({title:'VIENA NOC Tools DEV'});
  }catch(_){ }
}"""

new_refresh="""async function setActionStateVisual(state,badge,title){
  await Promise.all([
    chrome.action.setBadgeText({text:badge?.text||''}),
    badge?.color ? chrome.action.setBadgeBackgroundColor({color:badge.color}) : Promise.resolve(),
    chrome.action.setTitle({title:title||'VIENA NOC Tools DEV'}),
    applyExtensionIconState(state)
  ]);
}
async function refreshActionBadge(tabId=null){
  try{
    const diskBuild=await readPackageBuild();
    if(diskBuild && diskBuild!==VIENA_BUILD_ID){
      const b=STATUS_BADGES.reload;
      await setActionStateVisual('reload',b,b.title); return;
    }
    let tab=null;
    if(tabId){ try{tab=await chrome.tabs.get(tabId);}catch(_){} }
    if(!tab){ const arr=await chrome.tabs.query({active:true,currentWindow:true}); tab=arr[0]||null; }
    if(tab && platformForUrl(tab.url)){
      const ping=await pingStatusTab(tab);
      if(!ping.ok||ping.stale){
        const b=STATUS_BADGES.tabs;
        await setActionStateVisual('tabs',b,b.title); return;
      }
    }
    const state=await getUpdateState();
    if(state?.available){
      const b=STATUS_BADGES.update;
      await setActionStateVisual('update',b,`${b.title}: v${state.latest}`); return;
    }
    if(tab && platformForUrl(tab.url)){
      const b=STATUS_BADGES.on;
      await setActionStateVisual('on',b,b.title); return;
    }
    await setActionStateVisual('neutral',null,'VIENA NOC Tools DEV');
  }catch(_){ }
}"""

if old_refresh not in bg:
    raise SystemExit("refreshActionBadge block not found")
bg=bg.replace(old_refresh,new_refresh,1)

# When a user changes icon variant, render it with current state ring automatically.
# Existing applyExtensionIconVariant() defaults to currentExtensionIconState, so no handler change needed.

files["background.js"]=bg.encode("utf-8")

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
      "El icono de la extensión incorpora un borde/anillo del color del estado actual sin perder la variante de icono elegida.",
      "Activa usa borde verde; actualización disponible naranja; recarga de extensión rojo; recarga de pestaña ámbar.",
      "El estado normal fuera de las páginas operativas mantiene el icono sin borde especial."
    ]
})
PTR.write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist=json.loads(HIST.read_text(encoding="utf-8"))
hist["current_build"]=NEW_BUILD
hist["current_package"]=DST_REL
note="fix72 adds a state-colored ring to the selected toolbar icon while keeping existing badges and icon personalization."
if note not in hist.get("notes",[]): hist.setdefault("notes",[]).append(note)
HIST.write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

bg2=files["background.js"].decode("utf-8")
checks={
  "ring colors":"ICON_RING_COLORS" in bg2 and "on:'#23833B'" in bg2 and "reload:'#B42318'" in bg2,
  "ring renderer":"renderExtensionIconState" in bg2 and "ctx.strokeStyle=color" in bg2,
  "state visual helper":"setActionStateVisual" in bg2,
  "state transitions":"setActionStateVisual('reload'" in bg2 and "setActionStateVisual('tabs'" in bg2 and "setActionStateVisual('update'" in bg2 and "setActionStateVisual('on'" in bg2,
  "variant preserves ring":"state=currentExtensionIconState" in bg2,
  "no csp regression":"fetch(dataUrl)" not in bg2,
}
bad=[k for k,v in checks.items() if not v]
if bad: raise SystemExit("FAILED: "+", ".join(bad))
print(json.dumps({"build":NEW_BUILD,"sha256":package_sha,"checks":checks},ensure_ascii=False,indent=2))
