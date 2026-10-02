#!/usr/bin/env python3
import base64, hashlib, json, pathlib, re
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/"dev/builds/1.3.26-dev-page-manifest-icon-fix73.json"
DST_REL="dev/builds/1.3.26-dev-metricas-sync-read-phase3-fix74.json"
DST=ROOT/DST_REL
PTR=ROOT/"dev/self-update.json"
HIST=ROOT/"dev/history.json"
NEW_BUILD="1.3.26-dev-metricas-sync-read-phase3-fix74"

def sha(b): return hashlib.sha256(b).hexdigest()
def decode(i):
    b=base64.b64decode(i["content_base64"],validate=True)
    assert len(b)==i["size"] and sha(b)==i["sha256"]
    return b

pkg=json.loads(SRC.read_text(encoding="utf-8"))
files={i["path"]:decode(i) for i in pkg["files"]}

metrics=files["js/50-metrics.js"].decode("utf-8")

old="""    // Historial local
    const STORAGE_KEY = 'metricas_nodos_vts_v7__dev';
"""
new="""    // Historial local
    const STORAGE_KEY = 'metricas_nodos_vts_v7__dev';

    // =========================================================
    // METRICAS_SYNC — FASE 3 (LECTURA SOLAMENTE)
    // =========================================================

    const METRICAS_SYNC_ENDPOINT =
        'https://script.google.com/macros/s/AKfycbxLKOhNj2nW8IQUVbxJK_i9j2xnIMYZQpDaecGpqhxWdB3Zld5Vi_ERWKqLsnFKdkVCFw/exec';

    const METRICAS_SYNC_POLL_MS = 10000;
    const METRICAS_SYNC_TIMEOUT_MS = 6000;

    // En Fase 3 estos datos se cargan y validan, pero todavía NO participan
    // de procesarFila() ni modifican ningún color/estado visual.
    let metricasSyncEstados = new Map();
    let metricasSyncInFlight = false;
    let metricasSyncPrimerOkInformado = false;
    let metricasSyncMeta = {
        ok: false,
        fechaOperativa: '',
        updatedAt: 0,
        visibleNodes: 0,
        remoteStates: 0,
        lastError: ''
    };

    function normalizarNodoSync(value) {
        return String(value == null ? '' : value)
            .trim()
            .toUpperCase();
    }

    function nodosVisiblesNormalizados() {
        const nodos = new Set();

        document.querySelectorAll(SELECTOR_TOTAL).forEach(celda => {
            const fila = celda.closest('tr');
            if (!fila) return;

            const nodo = normalizarNodoSync(obtenerNodo(fila));
            if (nodo) nodos.add(nodo);
        });

        return nodos;
    }

    function validarEstadoCompartido(raw, fechaServidor) {
        if (!raw || typeof raw !== 'object') return null;

        const nodo = normalizarNodoSync(raw.nodo);
        if (!nodo) return null;

        const total = parseInt(raw.total_marcado, 10);
        const problema = parseInt(raw.problema_marcado, 10);
        const fecha = String(raw.fecha_operativa || '').trim();
        const updatedMs = Number(raw.updated_at_ms || 0);

        if (!Number.isFinite(total) || total < 0) return null;
        if (!Number.isFinite(problema) || problema < 0) return null;
        if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(fecha)) return null;
        if (fechaServidor && fecha !== fechaServidor) return null;

        return {
            nodo,
            total_marcado: total,
            problema_marcado: problema,
            usuario: String(raw.usuario || '').trim().toLowerCase(),
            fecha_operativa: fecha,
            updated_at: String(raw.updated_at || ''),
            updated_at_ms: Number.isFinite(updatedMs) ? updatedMs : 0
        };
    }

    async function sincronizarEstadosCompartidos() {
        if (metricasSyncInFlight) return;
        metricasSyncInFlight = true;

        const controller = new AbortController();
        const timer = setTimeout(
            () => controller.abort(),
            METRICAS_SYNC_TIMEOUT_MS
        );

        try {
            const url =
                METRICAS_SYNC_ENDPOINT +
                '?op=GET_TODAY_STATES&_=' +
                Date.now();

            const response = await fetch(url, {
                method: 'GET',
                cache: 'no-store',
                signal: controller.signal
            });

            if (!response.ok) {
                throw new Error('HTTP ' + response.status);
            }

            const data = await response.json();

            if (!data || data.ok !== true || !Array.isArray(data.states)) {
                throw new Error('Respuesta METRICAS_SYNC inválida');
            }

            const fechaServidor =
                String(data.date || '').trim();

            const nuevos = new Map();

            data.states.forEach(raw => {
                const estado =
                    validarEstadoCompartido(
                        raw,
                        fechaServidor
                    );

                if (!estado) return;

                const previo =
                    nuevos.get(estado.nodo);

                if (
                    !previo ||
                    estado.updated_at_ms >=
                        previo.updated_at_ms
                ) {
                    nuevos.set(
                        estado.nodo,
                        estado
                    );
                }
            });

            metricasSyncEstados = nuevos;

            const visibles =
                nodosVisiblesNormalizados();

            metricasSyncMeta = {
                ok: true,
                fechaOperativa: fechaServidor,
                updatedAt: Date.now(),
                visibleNodes: visibles.size,
                remoteStates: nuevos.size,
                lastError: ''
            };

            if (!metricasSyncPrimerOkInformado) {
                metricasSyncPrimerOkInformado = true;
                console.info(
                    '[VIENA][METRICAS_SYNC] lectura activa',
                    {
                        fechaOperativa:
                            metricasSyncMeta.fechaOperativa,
                        estados:
                            metricasSyncMeta.remoteStates,
                        nodosVisibles:
                            metricasSyncMeta.visibleNodes
                    }
                );
            }
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
                        'sync_error'
                    )
            };
        }

        finally {
            clearTimeout(timer);
            metricasSyncInFlight = false;
        }
    }

    // Diagnóstico interno de Fase 3. No modifica la página ni expone datos
    // fuera del contexto aislado de la extensión.
    function obtenerDiagnosticoMetricasSync() {
        return {
            ...metricasSyncMeta,
            estados:
                Array.from(
                    metricasSyncEstados.values()
                )
        };
    }
"""
if old not in metrics:
    raise SystemExit("STORAGE_KEY insertion point not found")
metrics=metrics.replace(old,new,1)

old_exec="""    setTimeout(
        procesarTabla,
        300
    );
"""
new_exec="""    // Fase 3: iniciar la lectura compartida en paralelo. Todavía no influye
    // en procesarTabla()/procesarFila() ni en los colores existentes.
    setTimeout(
        sincronizarEstadosCompartidos,
        500
    );

    setInterval(
        sincronizarEstadosCompartidos,
        METRICAS_SYNC_POLL_MS
    );

    setTimeout(
        procesarTabla,
        300
    );
"""
if old_exec not in metrics:
    raise SystemExit("execution insertion point not found")
metrics=metrics.replace(old_exec,new_exec,1)

files["js/50-metrics.js"]=metrics.encode("utf-8")

# Runtime identity
for path,const_name in [("background.js","VIENA_BUILD_ID"),("js/80-update-banner.js","CONTENT_BUILD_ID"),("js/90-runtime-status.js","BUILD_ID")]:
    txt=files[path].decode("utf-8")
    txt,n=re.subn(rf"(const\\s+{const_name}\\s*=\\s*['\\"])([^'\\"]+)(['\\"])",rf"\\g<1>{NEW_BUILD}\\g<3>",txt,count=1)
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
    "schema":1,
    "version":"1.3.26",
    "build":NEW_BUILD,
    "channel":"DEV",
    "package_url":f"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/{DST_REL}",
    "package_sha256":package_sha,
    "notes":[
      "Métricas incorpora lectura de METRICAS_SYNC cada 10 segundos en modo observación.",
      "Los estados remotos se normalizan por el valor literal del nodo y se validan contra la fecha operativa informada por el servidor.",
      "Esta fase no modifica colores, banderas ni la lógica actual de Métricas."
    ]
})
PTR.write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

hist=json.loads(HIST.read_text(encoding="utf-8"))
hist["current_build"]=NEW_BUILD
hist["current_package"]=DST_REL
note="fix74 / phase3: metrics shared backend polling is active in read-only observation mode; existing row colors and local flag logic are untouched."
if note not in hist.get("notes",[]):
    hist.setdefault("notes",[]).append(note)
HIST.write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

m=files["js/50-metrics.js"].decode("utf-8")
manifest=json.loads(files["manifest.json"].decode("utf-8"))
hosts=set(manifest.get("host_permissions",[]))
checks={
  "endpoint": "AKfycbxLKOhNj2nW8IQUVbxJK_i9j2xnIMYZQpDaecGpqhxWdB3Zld5Vi_ERWKqLsnFKdkVCFw" in m,
  "poll 10s": "METRICAS_SYNC_POLL_MS = 10000" in m,
  "read only": "UPSERT_STATE" not in m and "DELETE_STATE" not in m,
  "not applied to colors": "metricasSyncEstados" not in m[m.index("function procesarFila"):m.index("function procesarTabla")],
  "literal node normalize": ".trim()\n            .toUpperCase()" in m,
  "server date validation": "fecha !== fechaServidor" in m,
  "script host permission": "https://script.google.com/*" in hosts and "https://script.googleusercontent.com/*" in hosts,
}
bad=[k for k,v in checks.items() if not v]
if bad: raise SystemExit("FAILED: "+", ".join(bad))

print(json.dumps({
  "build":NEW_BUILD,
  "sha256":package_sha,
  "checks":checks
},ensure_ascii=False,indent=2))
