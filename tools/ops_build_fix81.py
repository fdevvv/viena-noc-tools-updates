#!/usr/bin/env python3
import base64,hashlib,json,pathlib
from datetime import datetime,timezone

R=pathlib.Path(__file__).resolve().parents[1]
SRC=R/"dev/builds/1.3.26-dev-metricas-sync-ui-phase9-fix80.json"
DST_REL="dev/builds/1.3.26-dev-metricas-sync-initial-baseline-fix81.json"
DST=R/DST_REL
OLD="1.3.26-dev-metricas-sync-ui-phase9-fix80"
NEW="1.3.26-dev-metricas-sync-initial-baseline-fix81"

def h(b): return hashlib.sha256(b).hexdigest()

pkg=json.loads(SRC.read_text())
files={}
for item in pkg["files"]:
    b=base64.b64decode(item["content_base64"])
    assert h(b)==item["sha256"]
    files[item["path"]]=b

m=files["js/50-metrics.js"].decode("utf-8")

anchor="""    const METRICAS_SYNC_POLL_MS = 10000;
    const METRICAS_SYNC_TIMEOUT_MS = 6000;
"""
rep="""    const METRICAS_SYNC_POLL_MS = 10000;
    const METRICAS_SYNC_TIMEOUT_MS = 6000;
    const METRICAS_SYNC_INIT_RETRY_MS = 15000;
"""
assert anchor in m
m=m.replace(anchor,rep,1)

anchor="""    let metricasSyncEstados = new Map();
    let metricasSyncPendientes = new Map();
    let metricasSyncUltimoWriteMs = new Map();
    let metricasSyncInFlight = false;
"""
rep="""    let metricasSyncEstados = new Map();
    let metricasSyncPendientes = new Map();
    let metricasSyncUltimoWriteMs = new Map();
    let metricasSyncInitEnCurso = new Set();
    let metricasSyncInitUltimoIntento = new Map();
    let metricasSyncInFlight = false;
"""
assert anchor in m
m=m.replace(anchor,rep,1)

# Reconcile init bookkeeping after GET.
anchor="""            metricasSyncEstados = nuevos;

            if (cambioDeDia) {
                metricasSyncPendientes = new Map();
                metricasSyncUltimoWriteMs = new Map();
            }
"""
rep="""            metricasSyncEstados = nuevos;

            nuevos.forEach((_, nodo) => {
                metricasSyncInitEnCurso.delete(nodo);
                metricasSyncInitUltimoIntento.delete(nodo);
            });

            if (cambioDeDia) {
                metricasSyncPendientes = new Map();
                metricasSyncUltimoWriteMs = new Map();
                metricasSyncInitEnCurso = new Set();
                metricasSyncInitUltimoIntento = new Map();
            }
"""
assert anchor in m
m=m.replace(anchor,rep,1)

# Daily reset also clears INIT trackers even before a GET rebuild.
anchor="""        metricasSyncEstados = new Map();
        metricasSyncPendientes = new Map();
        metricasSyncUltimoWriteMs = new Map();
"""
rep="""        metricasSyncEstados = new Map();
        metricasSyncPendientes = new Map();
        metricasSyncUltimoWriteMs = new Map();
        metricasSyncInitEnCurso = new Set();
        metricasSyncInitUltimoIntento = new Map();
"""
assert anchor in m
m=m.replace(anchor,rep,1)

# Add safe create-if-absent client function before UPSERT.
anchor="""    // FASE 4: escritura global, sin bloquear el comportamiento local
    async function guardarEstadoCompartido(nodo, valores) {
"""
fn="""    async function asegurarBaselineInicialCompartido(nodo, valores) {
        const nodoSync =
            normalizarNodoSync(nodo);

        if (!nodoSync || !valores) {
            return false;
        }

        if (metricasSyncEstados.has(nodoSync)) {
            return true;
        }

        if (metricasSyncInitEnCurso.has(nodoSync)) {
            return false;
        }

        const ahora =
            Date.now();

        const ultimoIntento =
            Number(
                metricasSyncInitUltimoIntento.get(nodoSync) ||
                0
            );

        if (
            ultimoIntento &&
            ahora - ultimoIntento <
                METRICAS_SYNC_INIT_RETRY_MS
        ) {
            return false;
        }

        const total =
            Math.max(
                0,
                parseInt(valores.total, 10) || 0
            );

        const problema =
            Math.max(
                0,
                parseInt(valores.problema, 10) || 0
            );

        metricasSyncInitEnCurso.add(
            nodoSync
        );

        metricasSyncInitUltimoIntento.set(
            nodoSync,
            ahora
        );

        actualizarEstadoSyncUi(
            'syncing'
        );

        const controller =
            new AbortController();

        const timer =
            setTimeout(
                () => controller.abort(),
                METRICAS_SYNC_TIMEOUT_MS
            );

        try {
            const response =
                await fetch(
                    METRICAS_SYNC_ENDPOINT,
                    {
                        method: 'POST',
                        cache: 'no-store',
                        headers: {
                            'Content-Type':
                                'text/plain;charset=UTF-8'
                        },
                        body: JSON.stringify({
                            op: 'INIT_STATE',
                            nodo: nodoSync,
                            total_marcado: total,
                            problema_marcado: problema,
                            usuario:
                                String(MI_USUARIO || '')
                                    .trim()
                                    .toLowerCase()
                        }),
                        signal: controller.signal
                    }
                );

            if (!response.ok) {
                throw new Error(
                    'HTTP ' + response.status
                );
            }

            const data =
                await response.json();

            if (
                !data ||
                data.ok !== true ||
                !data.state
            ) {
                throw new Error(
                    'INIT_STATE invalido'
                );
            }

            const estado =
                validarEstadoCompartido(
                    data.state,
                    String(
                        data.state.fecha_operativa ||
                        ''
                    )
                );

            if (!estado) {
                throw new Error(
                    'INIT_STATE sin estado valido'
                );
            }

            metricasSyncEstados.set(
                estado.nodo,
                estado
            );

            metricasSyncInitUltimoIntento.delete(
                estado.nodo
            );

            if (data.created === true) {
                metricasSyncUltimoWriteMs.set(
                    estado.nodo,
                    Number(
                        estado.updated_at_ms ||
                        0
                    )
                );
            }

            metricasSyncMeta = {
                ...metricasSyncMeta,
                ok: true,
                fechaOperativa:
                    estado.fecha_operativa,
                updatedAt: Date.now(),
                remoteStates:
                    metricasSyncEstados.size,
                lastError: ''
            };

            procesarTabla();

            actualizarEstadoSyncUi(
                'synced'
            );

            return true;
        }

        catch (error) {
            metricasSyncMeta = {
                ...metricasSyncMeta,
                ok: false,
                updatedAt: Date.now(),
                lastError:
                    String(
                        error?.message ||
                        error ||
                        'init_state_error'
                    )
            };

            actualizarEstadoSyncUi(
                'local'
            );

            return false;
        }

        finally {
            clearTimeout(timer);

            metricasSyncInitEnCurso.delete(
                nodoSync
            );
        }
    }

    // FASE 4: escritura global, sin bloquear el comportamiento local
    async function guardarEstadoCompartido(nodo, valores) {
"""
assert anchor in m
m=m.replace(anchor,fn,1)

# Trigger INIT for every flagged node with no authoritative global state.
# If local history already exists, preserve its original baseline during migration.
anchor="""        else {
            delete fila.dataset.vienaSyncBase;
        }

        if (!historial[nodo]) {
"""
rep="""        else {
            delete fila.dataset.vienaSyncBase;
        }

        if (
            !estadoCompartido &&
            !referenciaPendiente
        ) {
            const baselineInicial =
                historial[nodo]
                    ? {
                        total:
                            historial[nodo].total,
                        problema:
                            historial[nodo].problema
                    }
                    : valores;

            void asegurarBaselineInicialCompartido(
                nodo,
                baselineInicial
            );
        }

        if (!historial[nodo]) {
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
        "La primera bandera de un nodo crea automáticamente una referencia global sólo si todavía no existe.",
        "Si dos operadores detectan la bandera al mismo tiempo, el backend serializa la creación y conserva una única referencia inicial.",
        "Los operadores que abren Métricas más tarde reciben esa misma referencia y verán violeta si los valores aumentaron desde la marca inicial."
    ]
})
(R/"dev/self-update.json").write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n")

hist=json.loads((R/"dev/history.json").read_text())
hist["current_build"]=NEW
hist["current_package"]=DST_REL
(R/"dev/history.json").write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n")

assert "'INIT_STATE'" in m
assert "asegurarBaselineInicialCompartido" in m
assert "METRICAS_SYNC_INIT_RETRY_MS = 15000" in m
assert "historial[nodo]" in m
assert "metricasSyncInitEnCurso" in m
print(NEW,h(raw))
