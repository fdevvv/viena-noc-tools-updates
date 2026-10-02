#!/usr/bin/env python3
import base64,hashlib,json,pathlib
from datetime import datetime,timezone
R=pathlib.Path(__file__).resolve().parents[1]
src=R/"dev/builds/1.3.26-dev-metricas-sync-apply-phase5-fix76.json"
dst_rel="dev/builds/1.3.26-dev-metricas-sync-violet-phase6-fix77.json"
dst=R/dst_rel
old="1.3.26-dev-metricas-sync-apply-phase5-fix76"
new="1.3.26-dev-metricas-sync-violet-phase6-fix77"
def h(b): return hashlib.sha256(b).hexdigest()
p=json.loads(src.read_text())
F={}
for x in p["files"]:
 b=base64.b64decode(x["content_base64"]); assert h(b)==x["sha256"]; F[x["path"]]=b
m=F["js/50-metrics.js"].decode()

# Add optimistic per-node reference so a stale poll cannot undo the local
# Ctrl+double-click before UPSERT completes.
anchor="""    let metricasSyncEstados = new Map();
    let metricasSyncInFlight = false;"""
rep="""    let metricasSyncEstados = new Map();
    let metricasSyncPendientes = new Map();
    let metricasSyncInFlight = false;"""
if anchor not in m: raise SystemExit("pending anchor missing")
m=m.replace(anchor,rep,1)

# After a successful GET, clear pending refs only when server has caught up.
anchor="""            metricasSyncEstados = nuevos;

            const visibles ="""
rep="""            metricasSyncEstados = nuevos;

            metricasSyncPendientes.forEach((pendiente, nodo) => {
                const remoto = nuevos.get(nodo);
                if (
                    remoto &&
                    remoto.total_marcado === pendiente.total &&
                    remoto.problema_marcado === pendiente.problema
                ) {
                    metricasSyncPendientes.delete(nodo);
                }
            });

            const visibles ="""
if anchor not in m: raise SystemExit("GET reconciliation anchor missing")
m=m.replace(anchor,rep,1)

# On successful UPSERT, authoritative server state replaces optimistic ref and
# immediately reprocess visible rows.
anchor="""            if (estado) {
                metricasSyncEstados.set(estado.nodo, estado);
                metricasSyncMeta = {
                    ...metricasSyncMeta,
                    ok: true,
                    fechaOperativa: estado.fecha_operativa,
                    updatedAt: Date.now(),
                    remoteStates: metricasSyncEstados.size,
                    lastError: ''
                };
            }
            return true;"""
rep="""            if (estado) {
                metricasSyncEstados.set(estado.nodo, estado);
                metricasSyncPendientes.delete(estado.nodo);
                metricasSyncMeta = {
                    ...metricasSyncMeta,
                    ok: true,
                    fechaOperativa: estado.fecha_operativa,
                    updatedAt: Date.now(),
                    remoteStates: metricasSyncEstados.size,
                    lastError: ''
                };
                procesarTabla();
            }
            return true;"""
if anchor not in m: raise SystemExit("UPSERT success anchor missing")
m=m.replace(anchor,rep,1)

# Remote polling should update rows immediately instead of waiting up to 1.5s.
anchor="""            if (!metricasSyncPrimerOkInformado) {
                metricasSyncPrimerOkInformado = true;"""
rep="""            procesarTabla();

            if (!metricasSyncPrimerOkInformado) {
                metricasSyncPrimerOkInformado = true;"""
if anchor not in m: raise SystemExit("GET immediate process anchor missing")
m=m.replace(anchor,rep,1)

# Effective reference: optimistic local recognition > shared server ref > local.
anchor="""        const estadoCompartido =
            nodoSync
                ? metricasSyncEstados.get(nodoSync)
                : null;

        if (estadoCompartido) {
            const referenciaGlobal = {
                total:
                    estadoCompartido.total_marcado,
                problema:
                    estadoCompartido.problema_marcado
            };

            const referenciaLocal =
                historial[nodo];

            if (
                !referenciaLocal ||
                referenciaLocal.total !==
                    referenciaGlobal.total ||
                referenciaLocal.problema !==
                    referenciaGlobal.problema
            ) {
                historial[nodo] =
                    referenciaGlobal;

                cambioHistorial = true;
            }

            fila.dataset.vienaSyncBase =
                'global';
        }

        else {
            delete fila.dataset.vienaSyncBase;
        }
"""
rep="""        const referenciaPendiente =
            nodoSync
                ? metricasSyncPendientes.get(nodoSync)
                : null;

        const estadoCompartido =
            nodoSync
                ? metricasSyncEstados.get(nodoSync)
                : null;

        let referenciaSincronizada = null;
        let fuenteSincronizada = '';

        if (referenciaPendiente) {
            referenciaSincronizada = {
                total: referenciaPendiente.total,
                problema: referenciaPendiente.problema
            };
            fuenteSincronizada = 'pending';
        }

        else if (estadoCompartido) {
            referenciaSincronizada = {
                total:
                    estadoCompartido.total_marcado,
                problema:
                    estadoCompartido.problema_marcado
            };
            fuenteSincronizada = 'global';
        }

        if (referenciaSincronizada) {
            const referenciaLocal =
                historial[nodo];

            if (
                !referenciaLocal ||
                referenciaLocal.total !==
                    referenciaSincronizada.total ||
                referenciaLocal.problema !==
                    referenciaSincronizada.problema
            ) {
                historial[nodo] =
                    referenciaSincronizada;

                cambioHistorial = true;
            }

            fila.dataset.vienaSyncBase =
                fuenteSincronizada;
        }

        else {
            delete fila.dataset.vienaSyncBase;
        }
"""
if anchor not in m: raise SystemExit("effective reference block missing")
m=m.replace(anchor,rep,1)

# On Ctrl+double-click, register optimistic reference before async UPSERT.
anchor="""            guardarHistorial(
                historial
            );

            // Local primero; sincronizacion global en segundo plano.
            void guardarEstadoCompartido(
                nodo,
                valores
            );
"""
rep="""            guardarHistorial(
                historial
            );

            const nodoSync =
                normalizarNodoSync(nodo);

            if (nodoSync) {
                metricasSyncPendientes.set(
                    nodoSync,
                    {
                        total: valores.total,
                        problema: valores.problema,
                        createdAt: Date.now()
                    }
                );
            }

            // Local primero; sincronizacion global en segundo plano.
            void guardarEstadoCompartido(
                nodo,
                valores
            );
"""
if anchor not in m: raise SystemExit("dblclick pending hook missing")
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
ptr=json.loads((R/"dev/self-update.json").read_text());ptr.update({"build":new,"package_url":"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/"+dst_rel,"package_sha256":h(raw),"notes":["El estado violeta ya se calcula para todos contra la misma referencia global de total/problema.","Un Ctrl + doble click crea una referencia optimista local para evitar que un estado remoto viejo vuelva a poner la fila violeta mientras se confirma el UPSERT.","Las lecturas y escrituras exitosas reprocesan inmediatamente las filas visibles para reducir la latencia entre operadores."]});(R/"dev/self-update.json").write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n")
hist=json.loads((R/"dev/history.json").read_text());hist["current_build"]=new;hist["current_package"]=dst_rel;(R/"dev/history.json").write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n")

assert "metricasSyncPendientes = new Map()" in m
assert "fuenteSincronizada = 'pending'" in m
assert "estadoCompartido.total_marcado" in m
assert "valores.total > base.total" in m and "valores.problema > base.problema" in m
assert "metricasSyncPendientes.set(" in m
print(new,h(raw))
