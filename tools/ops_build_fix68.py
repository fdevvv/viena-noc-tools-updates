#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/"dev/builds/1.3.26-dev-final-ui-cleanup-fix67.json"
DST_REL="dev/builds/1.3.26-dev-ui-detail-polish-fix68.json"
DST=ROOT/DST_REL
PTR=ROOT/"dev/self-update.json"
HIST=ROOT/"dev/history.json"
NEW_BUILD="1.3.26-dev-ui-detail-polish-fix68"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(i):
    b=base64.b64decode(i["content_base64"],validate=True)
    assert len(b)==i["size"] and sha(b)==i["sha256"]
    return b
def enc_css(s): return s.replace("\\","\\\\").replace('"','\\"').replace("\n","\\n")

pkg=json.loads(SRC.read_text(encoding="utf-8"))
files={i["path"]:decode(i) for i in pkg["files"]}

# Popup: improve Operator section proportions/typography and give it a little more width.
popup=files["popup.html"].decode("utf-8")
popup_css=r'''
/* fix68 — popup operator geometry polish */
html,body{width:480px;max-width:480px;min-width:480px}
.operator-grid{
  grid-template-columns:minmax(0,1fr) minmax(0,1.08fr)!important;
  gap:9px!important;
  align-items:stretch!important;
}
.operator-box{
  min-width:0;
  padding:10px 11px!important;
  border-radius:9px!important;
  display:flex;
  flex-direction:column;
  justify-content:flex-start;
}
.operator-label{
  margin:0 0 6px!important;
  font-size:10px!important;
  line-height:1.25!important;
}
.operator-value,.user-auto-value{
  font-size:13px!important;
  line-height:1.25!important;
}
.user-auto-panel{align-items:center!important;min-height:31px}
.input-row{
  display:grid!important;
  grid-template-columns:minmax(0,1fr) auto!important;
  align-items:end!important;
  gap:7px!important;
}
.input-row input{width:100%;min-width:0}
.assign-warning{
  margin-top:7px!important;
  padding:7px 8px!important;
  line-height:1.35!important;
}
.statusline,.hint{margin-top:6px!important;line-height:1.4!important}
@media(max-width:492px){
  html,body{width:100%;min-width:0;max-width:none}
  .operator-grid{grid-template-columns:1fr!important}
}
'''
popup=popup.replace("</style>",popup_css+"\n</style>",1)
files["popup.html"]=popup.encode("utf-8")

home=files["js/97-home-ui.js"].decode("utf-8")

# CSS polish for editor search, reason-count column, update cards and template motion.
home_css=r'''
/* fix68 — editor/update detail polish */
.editor-search{position:relative!important;display:block!important}
.editor-search>span:first-child{
  position:absolute!important;left:11px!important;top:16px!important;
  transform:translateY(-50%)!important;display:grid!important;place-items:center!important;
  width:14px!important;height:14px!important;line-height:1!important;margin:0!important;
  color:#6f879e!important;pointer-events:none!important;z-index:2!important;
}
.editor-search input{
  width:100%!important;padding-left:31px!important;padding-right:10px!important;
  box-sizing:border-box!important;
}
.template-summary{
  display:grid!important;
  grid-template-columns:24px 28px minmax(0,1fr) 76px 26px!important;
  align-items:center!important;
  column-gap:8px!important;
}
.template-reason-count{
  justify-self:end!important;
  min-width:64px!important;
  text-align:center!important;
  white-space:nowrap!important;
}
.template-chevron{justify-self:end!important;margin:0!important}
.update-summary{
  gap:10px!important;
  align-items:stretch!important;
}
.update-summary>div{
  min-width:0!important;
  min-height:68px!important;
  padding:11px 12px!important;
  display:flex!important;
  flex-direction:column!important;
  justify-content:center!important;
  gap:6px!important;
}
.update-label{margin:0!important;line-height:1.2!important}
.update-value{margin:0!important;line-height:1.35!important;overflow-wrap:anywhere}
.update-status{margin-top:9px!important;line-height:1.4!important}
.template-card{will-change:height,transform}
@media(max-width:760px){
  .template-summary{grid-template-columns:22px 26px minmax(0,1fr) 68px 24px!important;column-gap:6px!important}
  .template-reason-count{min-width:58px!important}
}
@media(prefers-reduced-motion:reduce){
  .template-card{will-change:auto}
}
'''
marker='";\n  const HOME_BODY'
if marker not in home:
    raise SystemExit("HOME_CSS marker missing")
home=home.replace(marker,enc_css(home_css)+marker,1)

# Wrap editor rendering once. This fixes:
# - the stale loading card remaining visible after the editor loads;
# - the protected system-button name input being visually empty;
# - smooth expand/collapse feedback for templates using FLIP geometry.
insert_before="$('addEditorTemplate').addEventListener('click'"
if insert_before not in home:
    raise SystemExit("editor listener marker missing")
runtime=r'''
const fix68BaseRenderEditorForm=renderEditorForm;
renderEditorForm=function(...args){
  const oldCards=Array.from(document.querySelectorAll('#editorTemplates .template-card')).map(card=>card.getBoundingClientRect());
  const result=fix68BaseRenderEditorForm.apply(this,args);

  const empty=$('buttonEditorEmpty');
  if(empty) empty.style.display=editorDraft?'none':'grid';

  const nameInput=$('editorButtonName');
  if(nameInput&&editorDraft?.nombre){
    nameInput.value=editorDraft.nombre;
  }

  if(oldCards.length&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches){
    const cards=Array.from(document.querySelectorAll('#editorTemplates .template-card'));
    cards.forEach((card,index)=>{
      const before=oldCards[index],after=card.getBoundingClientRect();
      if(!before||!after)return;
      const dy=before.top-after.top;
      const heightChanged=Math.abs(before.height-after.height)>1;
      const moved=Math.abs(dy)>1;
      if(!heightChanged&&!moved)return;
      card.style.overflow='hidden';
      const animation=card.animate([
        {height:heightChanged?before.height+'px':after.height+'px',transform:moved?'translateY('+dy+'px)':'none',opacity:.96},
        {height:after.height+'px',transform:'none',opacity:1}
      ],{duration:190,easing:'cubic-bezier(.2,.7,.2,1)'});
      animation.onfinish=()=>{card.style.height='';card.style.overflow='';card.style.transform='';card.style.opacity=''};
      animation.oncancel=animation.onfinish;
    });
  }
  return result;
};
'''
home=home.replace(insert_before,runtime+"\n    "+insert_before,1)

files["js/97-home-ui.js"]=home.encode("utf-8")

# Runtime identity only.
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
        "Se corrige la geometría y legibilidad de la sección Operador del popup, con cards proporcionadas y mejor espaciado.",
        "El editor oculta correctamente el bloque de carga, alinea la búsqueda y los contadores de motivos, y muestra el nombre actual del botón.",
        "Las plantillas incorporan una transición suave al desplegarse/cerrarse y las cards de versión reciben espaciado y jerarquía visual corregidos."
    ]
})
PTR.write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist=json.loads(HIST.read_text(encoding="utf-8"))
hist["current_build"]=NEW_BUILD
hist["current_package"]=DST_REL
note="fix68 polishes popup Operator geometry, update-card spacing and editor alignment; it hides the stale loading block, keeps the current button name visible and adds FLIP motion to template expand/collapse."
if note not in hist.get("notes",[]): hist.setdefault("notes",[]).append(note)
HIST.write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

assert len(pkg["files"])==28
h=files["js/97-home-ui.js"].decode("utf-8")
ph=files["popup.html"].decode("utf-8")
checks={
  "popup width":"width:480px" in ph,
  "operator grid":"minmax(0,1.08fr)" in ph,
  "search alignment":"editor-search>span:first-child" in h,
  "reason alignment":"grid-template-columns:24px 28px minmax(0,1fr) 76px 26px" in h,
  "loading hidden":"empty.style.display=editorDraft?'none':'grid'" in h,
  "button name":"nameInput.value=editorDraft.nombre" in h,
  "template motion":"fix68BaseRenderEditorForm" in h and "card.animate([" in h,
  "update spacing":"min-height:68px" in h,
}
bad=[k for k,v in checks.items() if not v]
if bad: raise SystemExit("FAILED: "+", ".join(bad))
print(json.dumps({"build":NEW_BUILD,"package":DST_REL,"files":len(pkg["files"]),"sha256":package_sha,"checks":checks},ensure_ascii=False,indent=2))
