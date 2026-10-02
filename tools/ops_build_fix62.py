#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "dev/builds/1.3.26-dev-ui-foundation-fix61.json"
DST_REL = "dev/builds/1.3.26-dev-ui-motion-toast-fix62.json"
DST = ROOT / DST_REL
PTR = ROOT / "dev/self-update.json"
HIST = ROOT / "dev/history.json"
NEW_BUILD = "1.3.26-dev-ui-motion-toast-fix62"

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def decode_file(item):
    raw = base64.b64decode(item["content_base64"], validate=True)
    assert len(raw) == item["size"]
    assert sha(raw) == item["sha256"]
    return raw

def encode_js_css(css: str) -> str:
    return css.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

pkg = json.loads(SRC.read_text(encoding="utf-8"))
files = {item["path"]: decode_file(item) for item in pkg["files"]}

# 4) Full-view interaction feedback + section transition.
home = files["js/97-home-ui.js"].decode("utf-8")
css_marker = "/* fix62 — motion feedback + compact notifications */"
if css_marker not in home:
    extra_css = r'''
/* fix62 — motion feedback + compact notifications */
:where(.nav-item,.btn,.link-btn,.tool-action,.chip,.editor-button-card,.template-summary,.extension-icon-choice){
  transition:transform .14s ease,background-color .14s ease,border-color .14s ease,color .14s ease,box-shadow .14s ease,filter .14s ease,opacity .14s ease;
  -webkit-tap-highlight-color:transparent;
}
:where(.nav-item,.btn,.link-btn,.tool-action,.chip,.editor-button-card,.template-summary,.extension-icon-choice):hover:not(:disabled){
  transform:translateY(-1px);
}
:where(.nav-item,.btn,.link-btn,.tool-action,.chip,.editor-button-card,.template-summary,.extension-icon-choice):active:not(:disabled){
  transform:translateY(0) scale(.985);
}
:where(.nav-item,.btn,.link-btn,.tool-action,.chip,.editor-button-card,.template-summary,.extension-icon-choice):focus-visible{
  outline:2px solid rgba(11,114,231,.52);
  outline-offset:2px;
}
.nav-item.active:hover{transform:none}
.btn:disabled,.tool-action:disabled{transform:none!important;filter:none!important}
.view.active{animation:viena-view-in .18s ease-out both}
.template-body:not([hidden]){animation:viena-expand-in .16s ease-out both}
@keyframes viena-view-in{from{opacity:.58;transform:translateY(5px)}to{opacity:1;transform:none}}
@keyframes viena-expand-in{from{opacity:.5;transform:translateY(-3px)}to{opacity:1;transform:none}}
.toast{
  top:18px;right:18px;bottom:auto;
  width:max-content;max-width:min(340px,calc(100vw - 28px));
  padding:9px 11px;border-radius:9px;
  background:#fff;color:#1f3d5f;border:1px solid #d7e4f0;border-left:4px solid #0b72e7;
  box-shadow:0 10px 26px rgba(8,38,69,.18);
  font-size:12px;line-height:1.35;
  opacity:0;transform:translate3d(0,-7px,0) scale(.985);
  pointer-events:none;
  transition:opacity .15s ease,transform .15s ease;
}
.toast.show{opacity:1;transform:none}
.toast.success{background:#fff;border-left-color:#16823b;color:#244a32}
.toast.error{background:#fff;border-left-color:#b42318;color:#5f302c}
.toast.warning{background:#fff;border-left-color:#a76500;color:#624915}
@media(max-width:560px){
  .toast{top:12px;right:12px;max-width:calc(100vw - 24px)}
}
@media(prefers-reduced-motion:reduce){
  :where(.nav-item,.btn,.link-btn,.tool-action,.chip,.editor-button-card,.template-summary,.extension-icon-choice),.toast{transition:none!important}
  .view.active,.template-body:not([hidden]){animation:none!important}
}
'''
    marker = '";\n  const HOME_BODY'
    if marker not in home:
        raise SystemExit("HOME_CSS marker not found")
    home = home.replace(marker, encode_js_css(extra_css) + marker, 1)
files["js/97-home-ui.js"] = home.encode("utf-8")

# 4 + 5) Popup micro-interactions and compact toast.
popup = files["popup.html"].decode("utf-8")
popup_marker = "/* fix62 — compact toast + button feedback */"
if popup_marker not in popup:
    popup_css = r'''
/* fix62 — compact toast + button feedback */
:where(.btn,.icon-button,.section-action,.platform-action,.personalization-row,.chip,#toastClose){
  transition:transform .14s ease,background-color .14s ease,border-color .14s ease,color .14s ease,box-shadow .14s ease,opacity .14s ease;
  -webkit-tap-highlight-color:transparent;
}
:where(.btn,.icon-button,.section-action,.platform-action,.personalization-row,.chip,#toastClose):hover:not(:disabled){
  transform:translateY(-1px);
}
:where(.btn,.icon-button,.section-action,.platform-action,.personalization-row,.chip,#toastClose):active:not(:disabled){
  transform:translateY(0) scale(.985);
}
:where(.btn,.icon-button,.section-action,.platform-action,.personalization-row,.chip,#toastClose):focus-visible{
  outline:2px solid rgba(11,114,231,.5);
  outline-offset:2px;
}
#toast{
  top:10px;left:50%;right:auto;
  width:max-content;max-width:min(340px,calc(100% - 24px));
  padding:8px 10px;gap:7px;
  border-radius:9px;font-size:11.5px;line-height:1.35;
  transform:translate(-50%,-7px) scale(.985);
  opacity:0;
  box-shadow:0 10px 26px rgba(15,35,60,.18);
}
#toast.show{display:flex;animation:viena-popup-toast-in .15s ease-out forwards}
#toastIcon{flex:0 0 auto}
#toastClose{font-size:17px;align-self:center}
@keyframes viena-popup-toast-in{to{opacity:1;transform:translate(-50%,0) scale(1)}}
@media(prefers-reduced-motion:reduce){
  :where(.btn,.icon-button,.section-action,.platform-action,.personalization-row,.chip,#toastClose){transition:none!important}
  #toast.show{animation:none;opacity:1;transform:translate(-50%,0)}
}
'''
    popup = popup.replace("</style>", popup_css + "\n</style>", 1)
files["popup.html"] = popup.encode("utf-8")

# 5) Operational VIENA toast: preserve safe dialog host, only make visual footprint compact.
corp = files["js/30-corporate-detail.js"].decode("utf-8")
changes = [
    ("width:'min(430px, calc(100vw - 32px))', background:'#fff', color:'#1f2937',",
     "width:'max-content', maxWidth:'min(360px, calc(100vw - 28px))', minWidth:'0', background:'#fff', color:'#1f2937',"),
    ("border:'1px solid #d7e0ea', borderLeft:`5px solid ${cfg.accent}`, borderRadius:'10px',",
     "border:'1px solid #d7e0ea', borderLeft:`4px solid ${cfg.accent}`, borderRadius:'9px',"),
    ("display:'flex', alignItems:'flex-start', gap:'11px', padding:'13px 14px',",
     "display:'flex', alignItems:'center', gap:'8px', padding:'9px 10px',"),
    ("opacity:'0', transform:'translateY(-8px)', transition:'opacity .16s ease, transform .16s ease'",
     "opacity:'0', transform:'translateY(-6px) scale(.985)', transition:'opacity .14s ease, transform .14s ease'"),
    ("{width:'28px',height:'28px',minWidth:'28px',borderRadius:'50%',background:cfg.accent,color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',fontSize:'17px',fontWeight:'800',lineHeight:'1'}",
     "{width:'22px',height:'22px',minWidth:'22px',borderRadius:'50%',background:cfg.accent,color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',fontSize:'13px',fontWeight:'800',lineHeight:'1'}"),
    ("{fontSize:'13px',fontWeight:'800',color:'#183b63',marginBottom:'2px'}",
     "{fontSize:'11.5px',fontWeight:'800',color:'#183b63',marginBottom:'1px'}"),
    ("{fontSize:'14px',fontWeight:'600',lineHeight:'1.4'}",
     "{fontSize:'12.5px',fontWeight:'600',lineHeight:'1.35',overflowWrap:'anywhere'}"),
    ("{border:'0',background:'transparent',color:'#64748b',fontSize:'21px',lineHeight:'1',padding:'0 2px',cursor:'pointer'}",
     "{border:'0',background:'transparent',color:'#64748b',fontSize:'18px',lineHeight:'1',padding:'1px',cursor:'pointer'}"),
    ("toast.style.opacity = '0'; toast.style.transform = 'translateY(-8px)';",
     "toast.style.opacity = '0'; toast.style.transform = 'translateY(-6px) scale(.985)';"),
]
for old, new in changes:
    if old not in corp:
        raise SystemExit(f"corporate toast fragment not found: {old[:100]!r}")
    corp = corp.replace(old, new, 1)
files["js/30-corporate-detail.js"] = corp.encode("utf-8")

# Runtime identity only.
for path, const_name in [
    ("background.js", "VIENA_BUILD_ID"),
    ("js/80-update-banner.js", "CONTENT_BUILD_ID"),
    ("js/90-runtime-status.js", "BUILD_ID"),
]:
    text = files[path].decode("utf-8")
    pat = rf"(const\s+{const_name}\s*=\s*['\"])([^'\"]+)(['\"])"
    text2, n = re.subn(pat, rf"\g<1>{NEW_BUILD}\g<3>", text, count=1)
    if n != 1:
        raise SystemExit(f"could not update {const_name} in {path}")
    files[path] = text2.encode("utf-8")

build = json.loads(files["build.json"].decode("utf-8"))
build["build"] = NEW_BUILD
build["version"] = "1.3.26"
build["channel"] = "DEV"
files["build.json"] = (json.dumps(build, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

inventory = {}
for path, raw in files.items():
    if path != "integrity-manifest.json":
        inventory[path] = sha(raw)
integrity = json.loads(files["integrity-manifest.json"].decode("utf-8"))
integrity["build"] = NEW_BUILD
integrity["files"] = inventory
files["integrity-manifest.json"] = (json.dumps(integrity, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

order = [item["path"] for item in pkg["files"]]
pkg["build"] = NEW_BUILD
pkg["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
pkg["files"] = []
for path in order:
    raw = files[path]
    pkg["files"].append({
        "path": path,
        "size": len(raw),
        "sha256": sha(raw),
        "content_base64": base64.b64encode(raw).decode("ascii"),
    })

raw_pkg = (json.dumps(pkg, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
DST.write_bytes(raw_pkg)
package_sha = sha(raw_pkg)

ptr = json.loads(PTR.read_text(encoding="utf-8"))
ptr.update({
    "schema": 1,
    "version": "1.3.26",
    "build": NEW_BUILD,
    "channel": "DEV",
    "package_url": f"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/{DST_REL}",
    "package_sha256": package_sha,
    "notes": [
        "Se agregan transiciones breves y feedback visual consistente al navegar y accionar botones.",
        "La vista completa anima cambios de sección y expansiones sin afectar usuarios con reducción de movimiento.",
        "Los avisos emergentes del popup, vista completa y VIENA pasan a un formato compacto para no cubrir contenido operativo."
    ]
})
PTR.write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

hist = json.loads(HIST.read_text(encoding="utf-8"))
hist["current_build"] = NEW_BUILD
hist["current_package"] = DST_REL
note = "fix62 adds compact interaction motion and standardizes popup/full-view/VIENA toast sizing without changing operational logic."
if note not in hist.get("notes", []):
    hist.setdefault("notes", []).append(note)
HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

assert len(pkg["files"]) == 28
assert css_marker.encode() in files["js/97-home-ui.js"]
assert popup_marker.encode() in files["popup.html"]
assert b"maxWidth:'min(360px, calc(100vw - 28px))'" in files["js/30-corporate-detail.js"]

print(json.dumps({
    "build": NEW_BUILD,
    "package": DST_REL,
    "files": len(pkg["files"]),
    "sha256": package_sha
}, indent=2))
