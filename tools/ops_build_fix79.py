#!/usr/bin/env python3
import base64,hashlib,json,pathlib
from datetime import datetime,timezone
R=pathlib.Path(__file__).resolve().parents[1]
src=R/"dev/builds/1.3.26-dev-metricas-sync-daily-reset-phase7-fix78.json"
dst_rel="dev/builds/1.3.26-dev-metricas-sync-resilience-phase8-fix79.json"
dst=R/dst_rel
old="1.3.26-dev-metricas-sync-daily-reset-phase7-fix78"
new="1.3.26-dev-metricas-sync-resilience-phase8-fix79"
def h(b): return hashlib.sha256(b).hexdigest()
p=json.loads(src.read_text())
F={}
for x in p["files"]:
 b=base64.b64decode(x["content_base64"]); assert h(b)==x["sha256"]; F[x["path"]]=b
m=F["js/50-metrics.js"].decode()

anchor="""    let metricasSyncEstados = new Map();
    let metricasSyncPendientes = new Map();
    let metricasSyncInFlight = false;"""
rep="""    let metricasSyncEstados = new Map();
    let metricasSyncPendientes = new Map();
    let metricasSyncUltimoWriteMs = new Map();
    let metricasSyncInFlight = false;"""
if anchor not in m: raise SystemExit("state anchor missing")
m=m.replace(anchor,rep,1)

anchor="""            metricasSyncEstados = nuevos;

            if (cambioDeDia) {
                metricasSyncPendientes = new Map();
            }

            metricasSyncPendientes.forEach((pendiente, nodo) => {"""
rep="""            // Evitar que una lectura GET que salió antes de un UPSERT
            // confirmado pise un estado más nuevo del mismo nodo.
            metricasSyncUltimoWriteMs.forEach((writeMs, nodo) => {
                const actual = metricasSyncEstados.get(nodo);
                const entrante = nuevos.get(nodo);

                if (
                    actual &&
                    Number(actual.updated_at_ms || 0) >= Number(writeMs || 0) &&
                    (
                        !entrante ||
                        Number(entrante.updated_at_ms || 0) <
                            Number(actual.updated_at_ms || 0)
                    )
                ) {
                    nuevos.set(
                        nodo,
                        actual
                    );
                }
            });

            metricasSyncEstados = nuevos;

            if (cambioDeDia) {
                metricasSyncPendientes = new Map();
                metricasSyncUltimoWriteMs = new Map();
            }

            metricasSyncPendientes.forEach((pendiente, nodo) => {"""
if anchor not in m: raise SystemExit("GET merge anchor missing")
m=m.replace(anchor,rep,1)

anchor="""            if (estado) {
                metricasSyncEstados.set(estado.nodo, estado);
                metricasSyncPendientes.delete(estado.nodo);
                metricasSyncMeta = {"""
rep="""            if (estado) {
                metricasSyncEstados.set(estado.nodo, estado);
                metricasSyncPendientes.delete(estado.nodo);
                metricasSyncUltimoWriteMs.set(
                    estado.nodo,
                    Number(estado.updated_at_ms || 0)
                );
                metricasSyncMeta = {"""
if anchor not in m: raise SystemExit("UPSERT success anchor missing")
m=m.replace(anchor,rep,1)

anchor="""        } catch (error) {
            metricasSyncMeta = {
                ...metricasSyncMeta,
                ok: false,
                updatedAt: Date.now(),
                lastError: String(error?.message || error || 'upsert_error')
            };
            console.warn('[VIENA][METRICAS_SYNC] no se pudo sincronizar revision', error);
            return false;
        } finally {"""
rep="""        } catch (error) {
            // Si falla el UPSERT, no mantener indefinidamente una referencia
            // optimista que los demás operadores nunca recibieron.
            metricasSyncPendientes.delete(
                nodoSync
            );

            metricasSyncMeta = {
                ...metricasSyncMeta,
                ok: false,
                updatedAt: Date.now(),
                lastError: String(error?.message || error || 'upsert_error')
            };

            console.warn(
                '[VIENA][METRICAS_SYNC] no se pudo sincronizar revision',
                error
            );

            procesarTabla();

            return false;
        } finally {"""
if anchor not in m: raise SystemExit("UPSERT catch anchor missing")
m=m.replace(anchor,rep,1)

anchor="""        metricasSyncEstados = new Map();
        metricasSyncPendientes = new Map();

        document.querySelectorAll("""
rep="""        metricasSyncEstados = new Map();
        metricasSyncPendientes = new Map();
        metricasSyncUltimoWriteMs = new Map();

        document.querySelectorAll("""
if anchor not in m: raise SystemExit("daily reset state anchor missing")
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
ptr=json.loads((R/"dev/self-update.json").read_text());ptr.update({"build":new,"package_url":"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/"+dst_rel,"package_sha256":h(raw),"notes":["Se evita que una lectura remota antigua pise un reconocimiento más nuevo ya confirmado por el backend.","Si falla un UPSERT, la referencia optimista se descarta y la tabla vuelve a la última referencia global/local válida.","El reset diario limpia también los marcadores de escritura reciente para no mezclar estados entre días operativos."]});(R/"dev/self-update.json").write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n")
hist=json.loads((R/"dev/history.json").read_text());hist["current_build"]=new;hist["current_package"]=dst_rel;(R/"dev/history.json").write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n")

assert "metricasSyncUltimoWriteMs = new Map()" in m
assert "metricasSyncUltimoWriteMs.set(" in m
assert "metricasSyncPendientes.delete(" in m
assert "procesarTabla();" in m
print(new,h(raw))
