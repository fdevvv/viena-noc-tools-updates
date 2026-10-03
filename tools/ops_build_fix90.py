#!/usr/bin/env python3
import base64, hashlib, json, pathlib
from datetime import datetime, timezone

R = pathlib.Path(__file__).resolve().parents[1]
SRC = R / "dev/builds/1.3.26-dev-manual-zip-label-fix89.json"
DST_REL = "dev/builds/1.3.26-dev-update-button-size-fix90.json"
DST = R / DST_REL
OLD = "1.3.26-dev-manual-zip-label-fix89"
NEW = "1.3.26-dev-update-button-size-fix90"

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

popup = files["popup.js"].decode("utf-8")
assert "VIENA_EQUAL_UPDATE_ACTION_SIZE_FIX90" not in popup

runtime_fix = r'''
// VIENA_EQUAL_UPDATE_ACTION_SIZE_FIX90
(() => {
  const TARGET_RE = /^(Buscar actualización(?: DEV)?|Actualizar DEV\b|Descargar ZIP\b)/i;

  function normalizeUpdateActionButton(btn) {
    if (!(btn instanceof HTMLButtonElement)) return;
    const label = String(btn.textContent || '').replace(/\s+/g, ' ').trim();
    if (!TARGET_RE.test(label)) return;

    btn.style.setProperty('box-sizing', 'border-box', 'important');
    btn.style.setProperty('width', '100%', 'important');
    btn.style.setProperty('min-width', '0', 'important');
    btn.style.setProperty('height', '52px', 'important');
    btn.style.setProperty('min-height', '52px', 'important');
    btn.style.setProperty('max-height', '52px', 'important');
    btn.style.setProperty('padding', '8px 10px', 'important');
    btn.style.setProperty('display', 'flex', 'important');
    btn.style.setProperty('align-items', 'center', 'important');
    btn.style.setProperty('justify-content', 'center', 'important');
    btn.style.setProperty('align-self', 'start', 'important');
    btn.style.setProperty('text-align', 'center', 'important');
    btn.style.setProperty('line-height', '1.15', 'important');
    btn.style.setProperty('overflow', 'hidden', 'important');
  }

  function equalizeUpdateActionButtons() {
    document.querySelectorAll('button').forEach(normalizeUpdateActionButton);
  }

  const observer = new MutationObserver(equalizeUpdateActionButtons);
  const start = () => {
    equalizeUpdateActionButtons();
    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
'''

popup += "\n" + runtime_fix
files["popup.js"] = popup.encode("utf-8")

for path in ("background.js", "js/80-update-banner.js", "js/90-runtime-status.js"):
    s = files[path].decode("utf-8")
    assert OLD in s, f"{OLD} missing in {path}"
    files[path] = s.replace(OLD, NEW, 1).encode("utf-8")

build = json.loads(files["build.json"].decode("utf-8"))
build["build"] = NEW
files["build.json"] = (json.dumps(build, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

integ = json.loads(files["integrity-manifest.json"].decode("utf-8"))
integ["build"] = NEW
integ["files"] = {p:h(b) for p,b in files.items() if p!="integrity-manifest.json"}
files["integrity-manifest.json"] = (json.dumps(integ, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

pkg["build"] = NEW
pkg["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
pkg["files"] = []
for path in order:
    b = files[path]
    pkg["files"].append({
        "path":path,
        "size":len(b),
        "sha256":h(b),
        "content_base64":base64.b64encode(b).decode("ascii")
    })

raw = (json.dumps(pkg, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
DST.write_bytes(raw)

ptr = json.loads((R/"dev/self-update.json").read_text(encoding="utf-8"))
ptr.update({
    "build":NEW,
    "package_url":"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/"+DST_REL,
    "package_sha256":h(raw),
    "notes":[
        "Se iguala a 52 px el alto de Buscar actualización DEV, Actualizar DEV y Descargar ZIP.",
        "El ajuste se aplica también cuando los botones cambian de texto o se renderizan dinámicamente.",
        "No se modifica la lógica de actualización, descarga manual ni elegibilidad por usuario."
    ]
})
(R/"dev/self-update.json").write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist = json.loads((R/"dev/history.json").read_text(encoding="utf-8"))
hist["current_build"] = NEW
hist["current_package"] = DST_REL
(R/"dev/history.json").write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

assert "VIENA_EQUAL_UPDATE_ACTION_SIZE_FIX90" in popup
assert "MutationObserver(equalizeUpdateActionButtons)" in popup
assert "height', '52px'" in popup
assert "new Set(['efoschi'])" in popup
assert "new Set(['mbruno'])" in popup
assert "VIENA_NOC_Tools_RELEASE_v${latest}.zip" in popup
print(json.dumps({"build":NEW,"package":DST_REL,"package_sha256":h(raw)},ensure_ascii=False,indent=2))
