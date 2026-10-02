#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re, zipfile
from datetime import datetime, timezone

R = pathlib.Path(__file__).resolve().parents[1]
SRC = R / "dev/builds/1.3.26-dev-assign-start-selected-row-fix84.json"
DST_REL = "dev/builds/1.3.26-dev-manual-release-zip-fix85.json"
DST = R / DST_REL
OLD = "1.3.26-dev-assign-start-selected-row-fix84"
NEW = "1.3.26-dev-manual-release-zip-fix85"
RELEASE_PACKAGE = R / "release/v1.3.40-metricas-sync-assign-start-candidate1-package.json"
RELEASE_ZIP = R / "downloads/VIENA_NOC_Tools_RELEASE_v1.3.40.zip"

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

html = files["popup.html"].decode("utf-8")
assert 'id="manualReleaseZip"' not in html
m = re.search(r'(<button\b[^>]*\bid=["\']openUpdate["\'][^>]*>.*?</button>)', html, re.S)
assert m, "openUpdate button not found"
manual_button = (
    '<button id="manualReleaseZip" type="button" style="display:none" '
    'title="Descarga la RELEASE vigente para instalación manual">Descargar ZIP manual</button>'
)
html = html[:m.end()] + manual_button + html[m.end():]
files["popup.html"] = html.encode("utf-8")

popup = files["popup.js"].decode("utf-8")
assert "manualReleaseZipBtn" not in popup
anchor = "const openUpdateBtn = document.getElementById('openUpdate');"
assert anchor in popup
popup = popup.replace(anchor, anchor + "\nconst manualReleaseZipBtn = document.getElementById('manualReleaseZip');", 1)
insert_anchor = "async function fetchDevChannelState() {"
assert insert_anchor in popup
manual_logic = r"""
const MANUAL_RELEASE_ZIP_USERS = Object.freeze({
  DEV: new Set(['efoschi']),
  RELEASE: new Set(['mbruno'])
});
const MANUAL_RELEASE_ZIP_BASE_URL = 'https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/downloads';

function normalizeManualUpdateUser(value) {
  const raw = typeof value === 'string' ? value : (value?.usuario ?? value?.username ?? value?.user ?? '');
  return String(raw || '').trim().toLowerCase();
}

async function getRecognizedVienaUserForManualUpdate() {
  try {
    const data = await chrome.storage.local.get(['viena_usuario']);
    return normalizeManualUpdateUser(data?.viena_usuario);
  } catch (_) {
    return '';
  }
}

async function resolveManualReleaseZipTarget() {
  const channel = isDevRuntime() ? 'DEV' : 'RELEASE';
  const user = await getRecognizedVienaUserForManualUpdate();
  if (!MANUAL_RELEASE_ZIP_USERS[channel]?.has(user)) return null;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 6000);
  try {
    const url = `${VIENA_UPDATE_MANIFEST_URL}${VIENA_UPDATE_MANIFEST_URL.includes('?') ? '&' : '?'}_manual_zip=${Date.now()}`;
    const response = await fetch(url, { cache: 'no-store', signal: controller.signal, headers: { 'Cache-Control': 'no-cache' } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const latest = String(data?.latest || '').trim();
    if (!/^\d+\.\d+\.\d+$/.test(latest)) throw new Error('RELEASE latest inválida');
    return { user, latest, url: `${MANUAL_RELEASE_ZIP_BASE_URL}/VIENA_NOC_Tools_RELEASE_v${latest}.zip` };
  } finally {
    clearTimeout(timer);
  }
}

async function refreshManualReleaseZipButton() {
  if (!manualReleaseZipBtn) return;
  manualReleaseZipBtn.style.display = 'none';
  manualReleaseZipBtn.dataset.url = '';
  manualReleaseZipBtn.dataset.version = '';
  try {
    const target = await resolveManualReleaseZipTarget();
    if (!target) return;
    manualReleaseZipBtn.dataset.url = target.url;
    manualReleaseZipBtn.dataset.version = target.latest;
    manualReleaseZipBtn.textContent = `Descargar ZIP manual · v${target.latest}`;
    manualReleaseZipBtn.style.display = '';
  } catch (_) {}
}

manualReleaseZipBtn?.addEventListener('click', async () => {
  const previous = manualReleaseZipBtn.textContent;
  manualReleaseZipBtn.disabled = true;
  try {
    const target = await resolveManualReleaseZipTarget();
    if (!target) {
      manualReleaseZipBtn.style.display = 'none';
      return;
    }
    const result = await chrome.runtime.sendMessage({ type: 'VIENA_UPDATE_OPEN_DOWNLOAD', url: target.url });
    if (result && result.ok === false) throw new Error(result.error || 'No se pudo abrir la descarga.');
    showToast(`Abriendo ZIP manual de la RELEASE ${target.latest}.`, 'success');
  } catch (error) {
    showToast(`No se pudo abrir el ZIP manual: ${String(error?.message || error)}`, 'error');
  } finally {
    manualReleaseZipBtn.disabled = false;
    manualReleaseZipBtn.textContent = previous;
  }
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes?.viena_usuario) void refreshManualReleaseZipButton();
});
void refreshManualReleaseZipButton();

"""
popup = popup.replace(insert_anchor, manual_logic + insert_anchor, 1)
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
integ["files"] = {p: h(b) for p, b in files.items() if p != "integrity-manifest.json"}
files["integrity-manifest.json"] = (json.dumps(integ, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

pkg["build"] = NEW
pkg["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
pkg["files"] = []
for path in order:
    b = files[path]
    pkg["files"].append({"path": path, "size": len(b), "sha256": h(b), "content_base64": base64.b64encode(b).decode("ascii")})
raw = (json.dumps(pkg, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
DST.write_bytes(raw)

ptr = json.loads((R / "dev/self-update.json").read_text(encoding="utf-8"))
ptr.update({
    "build": NEW,
    "package_url": "https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/" + DST_REL,
    "package_sha256": h(raw),
    "notes": [
        "En DEV, efoschi puede descargar desde el popup el ZIP manual de la última RELEASE publicada.",
        "La lógica queda preparada para que en RELEASE esta opción sea visible únicamente para mbruno.",
        "La descarga manual es auxiliar y no modifica ni reemplaza el mecanismo normal de actualización."
    ]
})
(R / "dev/self-update.json").write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
hist = json.loads((R / "dev/history.json").read_text(encoding="utf-8"))
hist["current_build"] = NEW
hist["current_package"] = DST_REL
(R / "dev/history.json").write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

rpkg = json.loads(RELEASE_PACKAGE.read_text(encoding="utf-8"))
RELEASE_ZIP.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(RELEASE_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for item in rpkg["files"]:
        name = item["path"]
        data = base64.b64decode(item["content_base64"], validate=True)
        assert h(data) == item["sha256"]
        info = zipfile.ZipInfo(name)
        info.date_time = (1980, 1, 1, 0, 0, 0)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        zf.writestr(info, data)

assert "new Set(['efoschi'])" in popup
assert "new Set(['mbruno'])" in popup
assert "VIENA_NOC_Tools_RELEASE_v${latest}.zip" in popup
assert 'id="manualReleaseZip"' in html
assert RELEASE_ZIP.exists() and RELEASE_ZIP.stat().st_size > 0
print(json.dumps({"build": NEW, "package": DST_REL, "package_sha256": h(raw), "release_zip": str(RELEASE_ZIP.relative_to(R)), "release_zip_sha256": h(RELEASE_ZIP.read_bytes())}, ensure_ascii=False, indent=2))
