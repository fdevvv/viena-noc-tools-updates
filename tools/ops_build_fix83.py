#!/usr/bin/env python3
import base64,hashlib,json,pathlib
from datetime import datetime,timezone

R=pathlib.Path(__file__).resolve().parents[1]
SRC=R/"dev/builds/1.3.26-dev-metricas-sync-flag-replacement-guard-fix82.json"
DST_REL="dev/builds/1.3.26-dev-metricas-sync-header-status-fix83.json"
DST=R/DST_REL
OLD="1.3.26-dev-metricas-sync-flag-replacement-guard-fix82"
NEW="1.3.26-dev-metricas-sync-header-status-fix83"

def h(b): return hashlib.sha256(b).hexdigest()

pkg=json.loads(SRC.read_text())
files={}
for item in pkg["files"]:
    b=base64.b64decode(item["content_base64"])
    assert h(b)==item["sha256"]
    files[item["path"]]=b

m=files["js/50-metrics.js"].decode("utf-8")

old_style="""        badge.style.cssText = [
            'position:fixed',
            'right:14px',
            'bottom:14px',
            'z-index:999998',
            'padding:6px 10px',
            'border-radius:999px',
            'font:600 12px/1.2 Arial,sans-serif',
            'box-shadow:0 2px 8px rgba(0,0,0,.18)',
            'background:#f3f4f6',
            'color:#374151',
            'pointer-events:none',
            'user-select:none'
        ].join(';');

        document.body.appendChild(
            badge
        );
"""

new_style="""        badge.style.cssText = [
            'position:fixed',
            'left:50%',
            'top:14px',
            'transform:translateX(-50%)',
            'z-index:999998',
            'padding:5px 10px',
            'border-radius:999px',
            'font:600 12px/1.2 Arial,sans-serif',
            'box-shadow:0 1px 4px rgba(0,0,0,.12)',
            'background:#f3f4f6',
            'color:#374151',
            'pointer-events:none',
            'user-select:none',
            'white-space:nowrap',
            'max-width:180px',
            'overflow:hidden',
            'text-overflow:ellipsis'
        ].join(';');

        document.body.appendChild(
            badge
        );
"""

assert old_style in m
m=m.replace(old_style,new_style,1)

files["js/50-metrics.js"]=m.encode()

for path in ("background.js","js/80-update-banner.js","js/90-runtime-status.js"):
    s=files[path].decode("utf-8")
    assert OLD in s
    files[path]=s.replace(OLD,NEW,1).encode()

build=json.loads(files["build.json"].decode())
build["build"]=NEW
files["build.json"]=(json.dumps(build,ensure_ascii=False,indent=2)+"\n").encode()

integ=json.loads(files["integrity-manifest.json"].decode())
integ["build"]=NEW
integ["files"]={p:h(b) for p,b in files.items() if p!="integrity-manifest.json"}
files["integrity-manifest.json"]=(json.dumps(integ,ensure_ascii=False,indent=2)+"\n").encode()

order=[x["path"] for x in pkg["files"]]
pkg["build"]=NEW
pkg["generated_at"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
pkg["files"]=[]
for path in order:
    b=files[path]
    pkg["files"].append({
        "path":path,
        "size":len(b),
        "sha256":h(b),
        "content_base64":base64.b64encode(b).decode()
    })

raw=(json.dumps(pkg,ensure_ascii=False,indent=2)+"\n").encode()
DST.write_bytes(raw)

ptr=json.loads((R/"dev/self-update.json").read_text())
ptr.update({
    "build":NEW,
    "package_url":"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/"+DST_REL,
    "package_sha256":h(raw),
    "notes":[
        "El estado de sincronización de Métricas se muestra ahora centrado en la cabecera superior.",
        "Se elimina su posición flotante inferior para no interferir con los controles operativos.",
        "La lógica de METRICAS_SYNC, colores y reconocimiento de baseline no cambia."
    ]
})
(R/"dev/self-update.json").write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n")

hist=json.loads((R/"dev/history.json").read_text())
hist["current_build"]=NEW
hist["current_package"]=DST_REL
(R/"dev/history.json").write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n")

assert "'left:50%'" in m
assert "'top:14px'" in m
assert "'transform:translateX(-50%)'" in m
assert "'bottom:14px'" not in m
assert "'right:14px'" in m  # violet help toast remains bottom-right
assert "'INIT_STATE'" in m
assert "'UPSERT_STATE'" in m
assert "valores.total > base.total" in m
assert "valores.problema > base.problema" in m
assert "METRICAS_FLAG_REPLACEMENT_GRACE_MS = 12000" in m
print(NEW,h(raw))
