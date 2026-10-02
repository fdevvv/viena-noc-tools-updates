#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

R = pathlib.Path(__file__).resolve().parents[1]
SRC = R / "dev/builds/1.3.26-dev-manual-release-zip-fix85.json"
DST_REL = "dev/builds/1.3.26-dev-registry-device-identity-fix86.json"
DST = R / DST_REL
OLD = "1.3.26-dev-manual-release-zip-fix85"
NEW = "1.3.26-dev-registry-device-identity-fix86"

def h(b):
    return hashlib.sha256(b).hexdigest()

pkg = json.loads(SRC.read_text(encoding="utf-8"))
files = {}
order = []
for item in pkg["files"]:
    b = base64.b64decode(item["content_base64"], validate=True)
    assert h(b) == item["sha256"]
    files[item["path"]] = b
    order.append(item["path"])

# Locate the existing VIENA content script that already answers VIENA_GET_DETECTED_USER.
viena_path = None
for path, raw in files.items():
    if path.endswith(".js") and path not in {"background.js", "popup.js"}:
        s = raw.decode("utf-8", "ignore")
        if "VIENA_GET_DETECTED_USER" in s and "chrome.runtime.onMessage.addListener" in s:
            viena_path = path
            break
assert viena_path, "VIENA user-detection content script not found"

viena = files[viena_path].decode("utf-8")
assert "VIENA_GET_REGISTRY_IDENTITY" not in viena
identity_listener = r'''

// Registry identity persists in the VIENA origin, not in extension storage.
// This survives manual extension reinstalls/replacements in the same browser profile.
(() => {
  const DEVICE_KEY = 'viena_noc_registry_device_id_v1';
  const INSTALLATION_KEY = 'viena_noc_registry_installation_id_v1';

  function safeLocalGet(key) {
    try { return String(window.localStorage.getItem(key) || '').trim(); }
    catch (_) { return ''; }
  }

  function safeLocalSet(key, value) {
    try {
      window.localStorage.setItem(key, String(value || ''));
      return true;
    } catch (_) {
      return false;
    }
  }

  function newDeviceId() {
    try {
      if (globalThis.crypto?.randomUUID) return 'pc-' + globalThis.crypto.randomUUID();
    } catch (_) {}
    return 'pc-' + Date.now() + '-' + Math.random().toString(36).slice(2, 14);
  }

  function ensureDeviceId() {
    let id = safeLocalGet(DEVICE_KEY);
    if (!id) {
      id = newDeviceId();
      safeLocalSet(DEVICE_KEY, id);
    }
    return id;
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.type === 'VIENA_GET_REGISTRY_IDENTITY') {
      sendResponse({
        ok: true,
        deviceId: ensureDeviceId(),
        installationId: safeLocalGet(INSTALLATION_KEY)
      });
      return;
    }
    if (msg?.type === 'VIENA_SET_REGISTRY_INSTALLATION_ID') {
      const installationId = String(msg?.installationId || '').trim();
      if (!installationId) {
        sendResponse({ ok: false, error: 'installation_id_empty' });
        return;
      }
      const ok = safeLocalSet(INSTALLATION_KEY, installationId);
      sendResponse({ ok, installationId: ok ? installationId : '' });
    }
  });
})();
'''
viena += identity_listener
files[viena_path] = viena.encode("utf-8")

bg = files["background.js"].decode("utf-8")
assert "VIENA_GET_REGISTRY_IDENTITY" not in bg
old_block = r'''function stableRegistryInstallationId(usuario,channel){
  const user=String(usuario||'').trim().toLowerCase().replace(/[^a-z0-9._-]+/g,'-').replace(/^-+|-+$/g,'');
  const ch=String(channel||'RELEASE').trim().toUpperCase()==='DEV'?'dev':'release';
  return user && user!=='sin_detectar' ? `operator:${ch}:${user}` : '';
}

async function ensureInstallationId(usuario='',channel='RELEASE'){
  const saved=await chrome.storage.local.get([INSTALLATION_ID_KEY]);
  let id=String(saved[INSTALLATION_ID_KEY]||'').trim();
  if(id) return id;
  id=stableRegistryInstallationId(usuario,channel);
  if(!id) id=(globalThis.crypto?.randomUUID?.() || `viena-${Date.now()}-${Math.random().toString(36).slice(2,12)}`);
  await chrome.storage.local.set({[INSTALLATION_ID_KEY]:id});
  return id;
}
'''
assert old_block in bg, "current installation-id implementation changed"

new_block = r'''function stableRegistryInstallationId(usuario,channel,deviceId=''){
  const user=String(usuario||'').trim().toLowerCase().replace(/[^a-z0-9._-]+/g,'-').replace(/^-+|-+$/g,'');
  const ch=String(channel||'RELEASE').trim().toUpperCase()==='DEV'?'dev':'release';
  const device=String(deviceId||'').trim().toLowerCase().replace(/[^a-z0-9._-]+/g,'-').replace(/^-+|-+$/g,'');
  return user && user!=='sin_detectar' && device ? `operator:${ch}:${user}:device:${device}` : '';
}

async function getRegistryIdentityFromViena(){
  try{
    const tabs=await chrome.tabs.query({url:'https://viena.telecentro.net.ar/*'});
    const ordered=[...tabs].filter(t=>t.id).sort((a,b)=>{
      if(Boolean(a.active)!==Boolean(b.active)) return a.active?-1:1;
      return Number(b.lastAccessed||0)-Number(a.lastAccessed||0);
    });
    for(const tab of ordered){
      try{
        const result=await Promise.race([
          chrome.tabs.sendMessage(tab.id,{type:'VIENA_GET_REGISTRY_IDENTITY'}),
          new Promise((_,reject)=>setTimeout(()=>reject(new Error('registry_identity_timeout')),1200))
        ]);
        const deviceId=String(result?.deviceId||'').trim();
        const installationId=String(result?.installationId||'').trim();
        if(deviceId) return {tabId:tab.id,deviceId,installationId};
      }catch(_){}
    }
  }catch(_){}
  return null;
}

async function persistRegistryInstallationIdInViena(identity,installationId){
  const tabId=Number(identity?.tabId||0);
  const id=String(installationId||'').trim();
  if(!tabId || !id) return false;
  try{
    const result=await chrome.tabs.sendMessage(tabId,{
      type:'VIENA_SET_REGISTRY_INSTALLATION_ID',
      installationId:id
    });
    return result?.ok===true;
  }catch(_){
    return false;
  }
}

async function ensureInstallationId(usuario='',channel='RELEASE'){
  const identity=await getRegistryIdentityFromViena();
  const saved=await chrome.storage.local.get([INSTALLATION_ID_KEY]);
  let id=String(saved[INSTALLATION_ID_KEY]||'').trim();

  // Migration path: if this extension instance already owns a registry ID,
  // anchor that exact ID in the VIENA origin before doing anything else.
  // Future manual reinstalls on this PC/profile will recover the same row.
  if(id){
    if(identity && identity.installationId!==id){
      await persistRegistryInstallationIdInViena(identity,id);
    }
    return id;
  }

  // Manual reinstall / different unpacked-extension ID on the same PC/profile:
  // recover the anchored installation ID instead of creating a new row.
  if(identity?.installationId){
    id=String(identity.installationId).trim();
    await chrome.storage.local.set({[INSTALLATION_ID_KEY]:id});
    return id;
  }

  // First real installation for this PC/profile. Do not fall back to a
  // user-only ID, because that would merge different PCs of the same operator.
  id=stableRegistryInstallationId(usuario,channel,identity?.deviceId||'');
  if(!id) return '';

  await chrome.storage.local.set({[INSTALLATION_ID_KEY]:id});
  if(identity) await persistRegistryInstallationIdInViena(identity,id);
  return id;
}
'''
bg = bg.replace(old_block, new_block, 1)

old_send = "      const installationId=await ensureInstallationId(usuario,channel);\n      const runtimeId=String(chrome.runtime.id||'');"
new_send = "      const installationId=await ensureInstallationId(usuario,channel);\n      if(!installationId) return {ok:false,pending:true,reason:'registry_identity_pending'};\n      const runtimeId=String(chrome.runtime.id||'');"
assert old_send in bg
bg = bg.replace(old_send, new_send, 1)
files["background.js"] = bg.encode("utf-8")

for path in ("background.js","js/80-update-banner.js","js/90-runtime-status.js"):
    s=files[path].decode("utf-8")
    assert OLD in s, f"{OLD} missing in {path}"
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
    b=files[path]
    pkg["files"].append({
        "path":path,
        "size":len(b),
        "sha256":h(b),
        "content_base64":base64.b64encode(b).decode("ascii")
    })

raw=(json.dumps(pkg,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
DST.write_bytes(raw)

ptr=json.loads((R/"dev/self-update.json").read_text(encoding="utf-8"))
ptr.update({
    "build":NEW,
    "package_url":"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/"+DST_REL,
    "package_sha256":h(raw),
    "notes":[
        "El registro de instalación conserva el mismo ID al reinstalar manualmente la extensión en la misma PC/perfil.",
        "La identidad se ancla en el almacenamiento del dominio VIENA y se recupera aunque cambie el ID local de la extensión.",
        "Una PC/perfil nuevo genera una identidad distinta, evitando mezclar instalaciones reales del mismo usuario."
    ]
})
(R/"dev/self-update.json").write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist=json.loads((R/"dev/history.json").read_text(encoding="utf-8"))
hist["current_build"]=NEW
hist["current_package"]=DST_REL
(R/"dev/history.json").write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

# Regression assertions
assert "VIENA_GET_REGISTRY_IDENTITY" in files[viena_path].decode("utf-8")
assert "viena_noc_registry_device_id_v1" in files[viena_path].decode("utf-8")
assert "viena_noc_registry_installation_id_v1" in files[viena_path].decode("utf-8")
assert "identity.installationId" in files["background.js"].decode("utf-8")
assert "registry_identity_pending" in files["background.js"].decode("utf-8")
assert "operator:${ch}:${user}:device:${device}" in files["background.js"].decode("utf-8")
print(json.dumps({
    "build":NEW,
    "package":DST_REL,
    "package_sha256":h(raw),
    "viena_content_script":viena_path
},ensure_ascii=False,indent=2))
