#!/usr/bin/env python3
import base64,hashlib,json,pathlib
from datetime import datetime,timezone

R=pathlib.Path(__file__).resolve().parents[1]
SRC=R/"dev/builds/1.3.26-dev-metricas-sync-initial-baseline-fix81.json"
DST_REL="dev/builds/1.3.26-dev-metricas-sync-flag-replacement-guard-fix82.json"
DST=R/DST_REL
OLD="1.3.26-dev-metricas-sync-initial-baseline-fix81"
NEW="1.3.26-dev-metricas-sync-flag-replacement-guard-fix82"

def h(b): return hashlib.sha256(b).hexdigest()

pkg=json.loads(SRC.read_text())
files={}
for item in pkg["files"]:
    b=base64.b64decode(item["content_base64"])
    assert h(b)==item["sha256"]
    files[item["path"]]=b

m=files["js/50-metrics.js"].decode("utf-8")

anchor="""    const METRICAS_SYNC_INIT_RETRY_MS = 15000;
"""
rep="""    const METRICAS_SYNC_INIT_RETRY_MS = 15000;
    const METRICAS_FLAG_REPLACEMENT_GRACE_MS = 12000;
"""
assert anchor in m
m=m.replace(anchor,rep,1)

anchor="""    let metricasSyncInitEnCurso = new Set();
    let metricasSyncInitUltimoIntento = new Map();
    let metricasSyncInFlight = false;
"""
rep="""    let metricasSyncInitEnCurso = new Set();
    let metricasSyncInitUltimoIntento = new Map();
    let metricasFlagAusenteDesde = new Map();
    let metricasSyncInFlight = false;
"""
assert anchor in m
m=m.replace(anchor,rep,1)

# Reset transient replacement state with daily reset.
anchor="""        metricasSyncInitEnCurso = new Set();
        metricasSyncInitUltimoIntento = new Map();

        document.querySelectorAll(
"""
rep="""        metricasSyncInitEnCurso = new Set();
        metricasSyncInitUltimoIntento = new Map();
        metricasFlagAusenteDesde = new Map();

        document.querySelectorAll(
"""
assert anchor in m
m=m.replace(anchor,rep,1)

# Also clear on server day rollover path.
anchor="""                metricasSyncInitEnCurso = new Set();
                metricasSyncInitUltimoIntento = new Map();
            }
"""
rep="""                metricasSyncInitEnCurso = new Set();
                metricasSyncInitUltimoIntento = new Map();
                metricasFlagAusenteDesde = new Map();
            }
"""
assert anchor in m
m=m.replace(anchor,rep,1)

old_block="""            // Si antes tenÃ­a bandera y ahora no, borrar referencia
            if (
                nodo &&
                historial[nodo]
            ) {
                delete historial[nodo];
                cambioHistorial = true;
            }

            delete fila.dataset.nuevosVts;
"""
new_block="""            // Una bandera puede desaparecer unos segundos cuando otro
            // operador vuelve a iniciar/reasignar la misma mÃ©trica.
            // No borrar inmediatamente el baseline local: eso generarÃ­a
            // una falsa nueva referencia con los valores actuales.
            if (
                nodo &&
                historial[nodo]
            ) {
                const nodoSync =
                    normalizarNodoSync(nodo);

                const tieneBaselineGlobal =
                    nodoSync &&
                    metricasSyncEstados.has(
                        nodoSync
                    );

                if (tieneBaselineGlobal) {
                    metricasFlagAusenteDesde.delete(
                        nodoSync
                    );
                }

                else {
                    const ahora =
                        Date.now();

                    const ausenteDesde =
                        Number(
                            metricasFlagAusenteDesde.get(
                                nodoSync
                            ) || 0
                        );

                    if (!ausenteDesde) {
                        metricasFlagAusenteDesde.set(
                            nodoSync,
                            ahora
                        );
                    }

                    else if (
                        ahora - ausenteDesde >=
                            METRICAS_FLAG_REPLACEMENT_GRACE_MS
                    ) {
                        delete historial[nodo];

                        metricasFlagAusenteDesde.delete(
                            nodoSync
                        );

                        cambioHistorial = true;
                    }
                }
            }

            delete fila.dataset.nuevosVts;
"""
assert old_block in m
m=m.replace(old_block,new_block,1)

# When flag is present again, cancel any transient missing timer.
anchor="""        const nodoSync =
            normalizarNodoSync(nodo);

        const referenciaPendiente =
"""
rep="""        const nodoSync =
            normalizarNodoSync(nodo);

        if (nodoSync) {
            metricasFlagAusenteDesde.delete(
                nodoSync
            );
        }

        const referenciaPendiente =
"""
assert anchor in m
m=m.replace(anchor,rep,1)

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
        "Se protege el baseline cuando la bandera desaparece temporalmente durante una reasignación entre operadores.",
        "Si ya existe baseline global, un reemplazo visual de bandera no borra ni reinicializa la referencia.",
        "Sin baseline global, se conserva el comportamiento anterior pero con una ventana de gracia de 12 segundos para evitar falsos reinicios por cambios transitorios del DOM."
    ]
})
(R/"dev/self-update.json").write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n")

hist=json.loads((R/"dev/history.json").read_text())
hist["current_build"]=NEW
hist["current_package"]=DST_REL
(R/"dev/history.json").write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n")

assert "METRICAS_FLAG_REPLACEMENT_GRACE_MS = 12000" in m
assert "metricasFlagAusenteDesde = new Map()" in m
assert "metricasSyncEstados.has(" in m
assert "ahora - ausenteDesde >=" in m
print(NEW,h(raw))
