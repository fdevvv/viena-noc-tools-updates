#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/"dev/builds/1.3.26-dev-state-ring-icon-fix72.json"
DST_REL="dev/builds/1.3.26-dev-page-manifest-icon-fix73.json"
DST=ROOT/DST_REL
PTR=ROOT/"dev/self-update.json"
HIST=ROOT/"dev/history.json"
NEW_BUILD="1.3.26-dev-page-manifest-icon-fix73"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(i):
    b=base64.b64decode(i["content_base64"],validate=True)
    assert len(b)==i["size"] and sha(b)==i["sha256"]
    return b

pkg=json.loads(SRC.read_text(encoding="utf-8"))
files={i["path"]:decode(i) for i in pkg["files"]}

# Extract the selected visual family (variant 1 = VN Clásico) from embedded assets
# and package static PNGs for Manifest V3. Chrome uses these for extension details
# and other browser-owned surfaces where runtime action.setIcon() is not used.
assets_js=files["js/96-ui-assets.js"].decode("utf-8")
m=re.search(r"globalThis\.VIENA_ICON_VARIANTS\s*=\s*Object\.freeze\((\{.*?\})\);", assets_js, re.S)
if not m: raise SystemExit("VIENA_ICON_VARIANTS not found")
variants=json.loads(m.group(1))
data=variants["1"]["128"]
prefix="data:image/png;base64,"
if not data.startswith(prefix): raise SystemExit("invalid icon data 128")
files["icon128.png"]=base64.b64decode(data[len(prefix):])

# Reuse the already-authorized portable root icon path for all manifest sizes.
# Chrome scales the packaged PNG for browser-owned surfaces.
manifest=json.loads(files["manifest.json"].decode("utf-8"))
manifest["icons"]={
  "16":"icon128.png",
  "32":"icon128.png",
  "48":"icon128.png",
  "128":"icon128.png"
}
files["manifest.json"]=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode("utf-8")

# Full-page extension favicon: follow the user's selected icon variant dynamically.
# This affects chrome-extension://.../popup.html when opened in a tab.
ph=files["popup.html"].decode("utf-8")
if 'id="vienaPageFavicon"' not in ph:
    ph=ph.replace("<title>VIENA NOC Tools</title>","<title>VIENA NOC Tools</title>\n<link id=\"vienaPageFavicon\" rel=\"icon\" type=\"image/png\" href=\"icon128.png\">",1)
files["popup.html"]=ph.encode("utf-8")

home=files["js/97-home-ui.js"].decode("utf-8")
needle="""const ICON_VARIANT_KEY='viena_extension_icon_variant_v1';"""
insert="""const ICON_VARIANT_KEY='viena_extension_icon_variant_v1';
    function applyPageFavicon(variant){
      const v=String(variant||'1');
      const data=globalThis.VIENA_ICON_VARIANTS?.[v]?.['32']||globalThis.VIENA_ICON_VARIANTS?.['1']?.['32'];
      const link=document.getElementById('vienaPageFavicon');
      if(link&&data)link.href=data;
    }"""
if needle not in home: raise SystemExit("ICON_VARIANT_KEY marker missing")
home=home.replace(needle,insert,1)

old_paint="""function paintIconSelection(variant){const v=String(variant||'1');document.querySelectorAll('[data-icon-variant]').forEach(btn=>{const selected=btn.dataset.iconVariant===v;btn.classList.toggle('selected',selected);btn.setAttribute('aria-checked',selected?'true':'false')});const status=$('iconSelectionStatus');if(status){status.textContent=`Opción ${v} seleccionada`;status.className='status ok'}}"""
new_paint="""function paintIconSelection(variant){const v=String(variant||'1');document.querySelectorAll('[data-icon-variant]').forEach(btn=>{const selected=btn.dataset.iconVariant===v;btn.classList.toggle('selected',selected);btn.setAttribute('aria-checked',selected?'true':'false')});applyPageFavicon(v);const status=$('iconSelectionStatus');if(status){status.textContent=`Opción ${v} seleccionada`;status.className='status ok'}}"""
if old_paint not in home: raise SystemExit("paintIconSelection block missing")
home=home.replace(old_paint,new_paint,1)
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
      "La extensión incorpora iconos PNG propios en el manifest para reemplazar el icono genérico del navegador en la ficha de la extensión.",
      "Cuando VIENA NOC Tools se abre en una pestaña, el favicon usa la variante de icono seleccionada en Personalización.",
      "El icono de la barra del navegador y su borde de estado continúan funcionando de forma independiente."
    ]
})
PTR.write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist=json.loads(HIST.read_text(encoding="utf-8"))
hist["current_build"]=NEW_BUILD
hist["current_package"]=DST_REL
note="fix73 adds packaged manifest icons and makes the full-tab page favicon follow the selected extension icon variant."
if note not in hist.get("notes",[]): hist.setdefault("notes",[]).append(note)
HIST.write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

checks={
  "manifest icon updated": files["icon128.png"][:8]==b"\x89PNG\r\n\x1a\n",
  "manifest mapping": all(v=="icon128.png" for v in json.loads(files["manifest.json"].decode("utf-8"))["icons"].values()),
  "page favicon": 'id="vienaPageFavicon"' in files["popup.html"].decode("utf-8"),
  "dynamic favicon":"applyPageFavicon(v)" in files["js/97-home-ui.js"].decode("utf-8"),
}
bad=[k for k,v in checks.items() if not v]
if bad: raise SystemExit("FAILED: "+", ".join(bad))
print(json.dumps({"build":NEW_BUILD,"files":len(pkg["files"]),"sha256":package_sha,"checks":checks},ensure_ascii=False,indent=2))
