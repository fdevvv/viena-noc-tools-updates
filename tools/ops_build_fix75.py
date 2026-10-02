#!/usr/bin/env python3
import base64,hashlib,json,pathlib
from datetime import datetime,timezone
R=pathlib.Path(__file__).resolve().parents[1]
src=R/"dev/builds/1.3.26-dev-metricas-sync-read-phase3-fix74.json"
dst_rel="dev/builds/1.3.26-dev-metricas-sync-write-phase4-fix75.json"
dst=R/dst_rel
old="1.3.26-dev-metricas-sync-read-phase3-fix74"
new="1.3.26-dev-metricas-sync-write-phase4-fix75"
def h(b): return hashlib.sha256(b).hexdigest()
p=json.loads(src.read_text())
F={}
for x in p["files"]:
 b=base64.b64decode(x["content_base64"]); assert h(b)==x["sha256"]; F[x["path"]]=b
m=F["js/50-metrics.js"].decode()
anchor="""    // Selectores reales
    const SELECTOR_TOTAL ="""
writer="""    // FASE 4: escritura global, sin bloquear el comportamiento local
    async function guardarEstadoCompartido(nodo, valores) {
        const nodoSync = normalizarNodoSync(nodo);
        if (!nodoSync || !valores) return false;
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), METRICAS_SYNC_TIMEOUT_MS);
        try {
            const response = await fetch(METRICAS_SYNC_ENDPOINT, {
                method: 'POST',
                cache: 'no-store',
                headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
                body: JSON.stringify({
                    op: 'UPSERT_STATE',
                    nodo: nodoSync,
                    total_marcado: Math.max(0, parseInt(valores.total, 10) || 0),
                    problema_marcado: Math.max(0, parseInt(valores.problema, 10) || 0),
                    usuario: String(MI_USUARIO || '').trim().toLowerCase()
                }),
                signal: controller.signal
            });
            if (!response.ok) throw new Error('HTTP ' + response.status);
            const data = await response.json();
            if (!data || data.ok !== true || !data.state) throw new Error('UPSERT_STATE invalido');
            const estado = validarEstadoCompartido(data.state, String(data.state.fecha_operativa || ''));
            if (estado) {
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
            return true;
        } catch (error) {
            metricasSyncMeta = {
                ...metricasSyncMeta,
                ok: false,
                updatedAt: Date.now(),
                lastError: String(error?.message || error || 'upsert_error')
            };
            console.warn('[VIENA][METRICAS_SYNC] no se pudo sincronizar revision', error);
            return false;
        } finally {
            clearTimeout(timer);
        }
    }

"""
if anchor not in m: raise SystemExit("anchor missing")
m=m.replace(anchor,writer+anchor,1)
oldfrag="""            guardarHistorial(
                historial
            );

            delete fila.dataset.nuevosVts;"""
newfrag="""            guardarHistorial(
                historial
            );

            // Local primero; sincronizacion global en segundo plano.
            void guardarEstadoCompartido(
                nodo,
                valores
            );

            delete fila.dataset.nuevosVts;"""
if oldfrag not in m: raise SystemExit("dblclick hook missing")
m=m.replace(oldfrag,newfrag,1)
F["js/50-metrics.js"]=m.encode()
for q in ("background.js","js/80-update-banner.js","js/90-runtime-status.js"):
 s=F[q].decode(); assert old in s; F[q]=s.replace(old,new,1).encode()
b=json.loads(F["build.json"]); b["build"]=new; F["build.json"]=(json.dumps(b,ensure_ascii=False,indent=2)+"\n").encode()
im=json.loads(F["integrity-manifest.json"]); im["build"]=new; im["files"]={k:h(v) for k,v in F.items() if k!="integrity-manifest.json"}; F["integrity-manifest.json"]=(json.dumps(im,ensure_ascii=False,indent=2)+"\n").encode()
order=[x["path"] for x in p["files"]]
p["build"]=new;p["generated_at"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z");p["files"]=[]
for q in order:
 b=F[q];p["files"].append({"path":q,"size":len(b),"sha256":h(b),"content_base64":base64.b64encode(b).decode()})
raw=(json.dumps(p,ensure_ascii=False,indent=2)+"\n").encode();dst.write_bytes(raw)
ptr=json.loads((R/"dev/self-update.json").read_text());ptr.update({"build":new,"package_url":"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/"+dst_rel,"package_sha256":h(raw),"notes":["Ctrl + doble click mantiene la respuesta local inmediata y sincroniza la nueva referencia en METRICAS_SYNC.","La escritura global guarda nodo, total, problema y usuario mediante UPSERT.","Si falla el backend, la logica local sigue funcionando."]});(R/"dev/self-update.json").write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n")
hist=json.loads((R/"dev/history.json").read_text());hist["current_build"]=new;hist["current_package"]=dst_rel;(R/"dev/history.json").write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n")
assert "void guardarEstadoCompartido" in m and "'UPSERT_STATE'" in m
print(new,h(raw))
