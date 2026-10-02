#!/usr/bin/env python3
import base64,hashlib,json,pathlib
from datetime import datetime,timezone
R=pathlib.Path(__file__).resolve().parents[1]
src=R/"dev/builds/1.3.26-dev-metricas-sync-violet-phase6-fix77.json"
dst_rel="dev/builds/1.3.26-dev-metricas-sync-daily-reset-phase7-fix78.json"
dst=R/dst_rel
old="1.3.26-dev-metricas-sync-violet-phase6-fix77"
new="1.3.26-dev-metricas-sync-daily-reset-phase7-fix78"
def h(b): return hashlib.sha256(b).hexdigest()
p=json.loads(src.read_text())
F={}
for x in p["files"]:
 b=base64.b64decode(x["content_base64"]); assert h(b)==x["sha256"]; F[x["path"]]=b
m=F["js/50-metrics.js"].decode()

anchor="""    // Historial local
    const STORAGE_KEY = 'metricas_nodos_vts_v7__dev';
"""
rep="""    // Historial local
    const STORAGE_KEY = 'metricas_nodos_vts_v7__dev';
    const STORAGE_DATE_KEY = 'metricas_nodos_vts_fecha_operativa_v1';
"""
if anchor not in m: raise SystemExit("storage anchor missing")
m=m.replace(anchor,rep,1)

anchor="""    function guardarHistorial(historial) {
        try {
            localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify(historial)
            );
        } catch (e) {
            console.warn('No se pudo guardar historial VTS:', e);
        }
    }
"""
rep="""    function guardarHistorial(historial) {
        try {
            localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify(historial)
            );
        } catch (e) {
            console.warn('No se pudo guardar historial VTS:', e);
        }
    }

    function fechaOperativaLocalGuardada() {
        try {
            return String(
                localStorage.getItem(
                    STORAGE_DATE_KEY
                ) || ''
            ).trim();
        } catch (_) {
            return '';
        }
    }

    function guardarFechaOperativaLocal(fecha) {
        try {
            localStorage.setItem(
                STORAGE_DATE_KEY,
                String(fecha || '')
            );
        } catch (_) {}
    }

    function resetearEstadoDiarioLocal(fechaServidor) {
        try {
            localStorage.removeItem(
                STORAGE_KEY
            );
        } catch (_) {}

        metricasSyncEstados = new Map();
        metricasSyncPendientes = new Map();

        document.querySelectorAll(
            'tr[data-nuevos-vts="1"], tr[data-viena-sync-base]'
        ).forEach(fila => {
            delete fila.dataset.nuevosVts;
            delete fila.dataset.vienaSyncBase;
        });

        guardarFechaOperativaLocal(
            fechaServidor
        );
    }

    function asegurarFechaOperativaLocal(fechaServidor) {
        const fecha =
            String(fechaServidor || '').trim();

        if (!/^\d{4}-\d{2}-\d{2}$/.test(fecha)) {
            return false;
        }

        const guardada =
            fechaOperativaLocalGuardada();

        // Primera instalación de esta fase: preservar el historial actual
        // y empezar a etiquetarlo con la fecha operativa del servidor.
        if (!guardada) {
            guardarFechaOperativaLocal(fecha);
            return false;
        }

        if (guardada === fecha) {
            return false;
        }

        resetearEstadoDiarioLocal(fecha);

        console.info(
            '[VIENA][METRICAS_SYNC] nuevo día operativo',
            {
                anterior: guardada,
                actual: fecha
            }
        );

        return true;
    }
"""
if anchor not in m: raise SystemExit("history function anchor missing")
m=m.replace(anchor,rep,1)

anchor="""            const fechaServidor =
                String(data.date || '').trim();

            const nuevos = new Map();
"""
rep="""            const fechaServidor =
                String(data.date || '').trim();

            const cambioDeDia =
                asegurarFechaOperativaLocal(
                    fechaServidor
                );

            const nuevos = new Map();
"""
if anchor not in m: raise SystemExit("server date anchor missing")
m=m.replace(anchor,rep,1)

anchor="""            metricasSyncEstados = nuevos;

            metricasSyncPendientes.forEach((pendiente, nodo) => {
"""
rep="""            metricasSyncEstados = nuevos;

            if (cambioDeDia) {
                metricasSyncPendientes = new Map();
            }

            metricasSyncPendientes.forEach((pendiente, nodo) => {
"""
if anchor not in m: raise SystemExit("pending reset anchor missing")
m=m.replace(anchor,rep,1)

anchor="""            metricasSyncMeta = {
                ok: true,
                fechaOperativa: fechaServidor,
                updatedAt: Date.now(),
                visibleNodes: visibles.size,
                remoteStates: nuevos.size,
                lastError: ''
            };
"""
rep="""            metricasSyncMeta = {
                ok: true,
                fechaOperativa: fechaServidor,
                updatedAt: Date.now(),
                visibleNodes: visibles.size,
                remoteStates: nuevos.size,
                lastError: '',
                dailyReset:
                    cambioDeDia === true
            };
"""
if anchor not in m: raise SystemExit("meta anchor missing")
m=m.replace(anchor,rep,1)

F["js/50-metrics.js"]=m.encode()
for q in ("background.js","js/80-update-banner.js","js/90-runtime-status.js"):
 s=F[q].decode(); assert old in s; F[q]=s.replace(old,new,1).encode()
b=json.loads(F["build.json"]);b["build"]=new;F["build.json"]=(json.dumps(b,ensure_ascii=False,indent=2)+"\n").encode()
im=json.loads(F["integrity-manifest.json"]);im["build"]=new;im["files"]={k:h(v) for k,v in F.items() if k!="integrity-manifest.json"};F["integrity-manifest.json"]=(json.dumps(im,ensure_ascii=False,indent=2)+"\n").encode()
order=[x["path"] for x in p["files"]];p["build"]=new;p["generated_at"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z");p["files"]=[]
for q in order:
 b=F[q];p["files"].append({"path":q,"size":len(b),"sha256":h(b),"content_base64":base64.b64encode(b).decode()})
raw=(json.dumps(p,ensure_ascii=False,indent=2)+"\n").encode();dst.write_bytes(raw)
ptr=json.loads((R/"dev/self-update.json").read_text());ptr.update({"build":new,"package_url":"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/"+dst_rel,"package_sha256":h(raw),"notes":["Métricas detecta el cambio de fecha operativa informado por METRICAS_SYNC y limpia las referencias del día anterior sin requerir F5.","La primera instalación de esta fase conserva el historial actual y lo etiqueta con la fecha del servidor para no perder el seguimiento en curso.","Al comenzar un nuevo día también se limpian referencias pendientes y marcas visuales de violeta/global antes de reprocesar la tabla."]});(R/"dev/self-update.json").write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n")
hist=json.loads((R/"dev/history.json").read_text());hist["current_build"]=new;hist["current_package"]=dst_rel;(R/"dev/history.json").write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n")

assert "STORAGE_DATE_KEY" in m
assert "asegurarFechaOperativaLocal" in m
assert "resetearEstadoDiarioLocal" in m
assert "localStorage.removeItem(" in m
assert "metricasSyncPendientes = new Map()" in m
assert "dailyReset:" in m
print(new,h(raw))
