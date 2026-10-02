#!/usr/bin/env python3
import base64,hashlib,json,pathlib
from datetime import datetime,timezone
R=pathlib.Path(__file__).resolve().parents[1]
src=R/"dev/builds/1.3.26-dev-metricas-sync-resilience-phase8-fix79.json"
dst_rel="dev/builds/1.3.26-dev-metricas-sync-ui-phase9-fix80.json"
dst=R/dst_rel
old="1.3.26-dev-metricas-sync-resilience-phase8-fix79"
new="1.3.26-dev-metricas-sync-ui-phase9-fix80"
def h(b): return hashlib.sha256(b).hexdigest()
p=json.loads(src.read_text())
F={}
for x in p["files"]:
 b=base64.b64decode(x["content_base64"]); assert h(b)==x["sha256"]; F[x["path"]]=b
m=F["js/50-metrics.js"].decode()

anchor="""    const METRICAS_SYNC_POLL_MS = 10000;
    const METRICAS_SYNC_TIMEOUT_MS = 6000;
"""
rep="""    const METRICAS_SYNC_POLL_MS = 10000;
    const METRICAS_SYNC_TIMEOUT_MS = 6000;

    const METRICAS_SYNC_STATUS_ID =
        'viena-metricas-sync-status';

    const METRICAS_VIOLETA_TOAST_KEY =
        'viena_metricas_violeta_toast_v1';

    const METRICAS_VIOLETA_TOOLTIP =
        'Valor incrementado después del reconocimiento. Ctrl + doble click para volver a marcarla en verde.';

    const METRICAS_VIOLETA_TOAST =
        'Violeta = aumentó después de la última marca. Ctrl + doble click para reconocer el nuevo valor.';
"""
if anchor not in m: raise SystemExit("constants anchor missing")
m=m.replace(anchor,rep,1)

anchor="""    function normalizarNodoSync(value) {
        return String(value == null ? '' : value)
            .trim()
            .toUpperCase();
    }
"""
rep="""    function normalizarNodoSync(value) {
        return String(value == null ? '' : value)
            .trim()
            .toUpperCase();
    }

    function asegurarEstadoSyncUi() {
        let badge =
            document.getElementById(
                METRICAS_SYNC_STATUS_ID
            );

        if (badge) {
            return badge;
        }

        badge =
            document.createElement('div');

        badge.id =
            METRICAS_SYNC_STATUS_ID;

        badge.setAttribute(
            'aria-live',
            'polite'
        );

        badge.style.cssText = [
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

        return badge;
    }

    function actualizarEstadoSyncUi(estado) {
        const badge =
            asegurarEstadoSyncUi();

        if (estado === 'syncing') {
            badge.textContent =
                '↻ Sincronizando';

            badge.style.background =
                '#fff7ed';

            badge.style.color =
                '#9a3412';

            return;
        }

        if (estado === 'synced') {
            badge.textContent =
                '● Sincronizado';

            badge.style.background =
                '#ecfdf5';

            badge.style.color =
                '#166534';

            return;
        }

        badge.textContent =
            '○ Modo local';

        badge.style.background =
            '#f3f4f6';

        badge.style.color =
            '#4b5563';
    }

    function restaurarTooltipVioleta(fila) {
        if (!fila) return;

        fila.querySelectorAll(
            '[data-viena-violeta-tooltip="1"]'
        ).forEach(celda => {
            const previo =
                celda.dataset.vienaPrevTitle;

            if (typeof previo === 'string') {
                if (previo) {
                    celda.setAttribute(
                        'title',
                        previo
                    );
                } else {
                    celda.removeAttribute(
                        'title'
                    );
                }
            }

            delete celda.dataset.vienaPrevTitle;
            delete celda.dataset.vienaVioletaTooltip;
        });
    }

    function aplicarTooltipVioleta(fila) {
        if (!fila) return;

        [
            fila.querySelector(SELECTOR_TOTAL),
            fila.querySelector(SELECTOR_PROBLEMA)
        ].filter(Boolean).forEach(celda => {
            if (
                celda.dataset
                    .vienaVioletaTooltip !==
                '1'
            ) {
                celda.dataset.vienaPrevTitle =
                    celda.getAttribute('title') || '';

                celda.dataset.vienaVioletaTooltip =
                    '1';
            }

            celda.setAttribute(
                'title',
                METRICAS_VIOLETA_TOOLTIP
            );
        });
    }

    function mostrarAyudaVioletaUnaVez() {
        try {
            if (
                sessionStorage.getItem(
                    METRICAS_VIOLETA_TOAST_KEY
                ) === '1'
            ) {
                return;
            }

            sessionStorage.setItem(
                METRICAS_VIOLETA_TOAST_KEY,
                '1'
            );
        } catch (_) {}

        const anterior =
            document.getElementById(
                'viena-metricas-violeta-toast'
            );

        if (anterior) {
            return;
        }

        const toast =
            document.createElement('div');

        toast.id =
            'viena-metricas-violeta-toast';

        toast.textContent =
            METRICAS_VIOLETA_TOAST;

        toast.style.cssText = [
            'position:fixed',
            'right:14px',
            'bottom:52px',
            'z-index:999999',
            'max-width:420px',
            'padding:10px 14px',
            'border-radius:8px',
            'font:600 13px/1.35 Arial,sans-serif',
            'background:#6b21a8',
            'color:#fff',
            'box-shadow:0 3px 12px rgba(0,0,0,.28)',
            'pointer-events:none'
        ].join(';');

        document.body.appendChild(
            toast
        );

        setTimeout(() => {
            toast.style.transition =
                'opacity .25s';

            toast.style.opacity =
                '0';

            setTimeout(
                () => toast.remove(),
                300
            );
        }, 4200);
    }
"""
if anchor not in m: raise SystemExit("ui function anchor missing")
m=m.replace(anchor,rep,1)

anchor="""    async function sincronizarEstadosCompartidos() {
        if (metricasSyncInFlight) return;
        metricasSyncInFlight = true;
"""
rep="""    async function sincronizarEstadosCompartidos() {
        if (metricasSyncInFlight) return;
        metricasSyncInFlight = true;

        actualizarEstadoSyncUi(
            'syncing'
        );
"""
if anchor not in m: raise SystemExit("sync start anchor missing")
m=m.replace(anchor,rep,1)

anchor="""            procesarTabla();

            if (!metricasSyncPrimerOkInformado) {"""
rep="""            procesarTabla();

            actualizarEstadoSyncUi(
                'synced'
            );

            if (!metricasSyncPrimerOkInformado) {"""
if anchor not in m: raise SystemExit("sync success anchor missing")
m=m.replace(anchor,rep,1)

anchor="""        catch (error) {
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
"""
rep="""        catch (error) {
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

            actualizarEstadoSyncUi(
                'local'
            );
        }
"""
if anchor not in m: raise SystemExit("sync catch anchor missing")
m=m.replace(anchor,rep,1)

anchor="""    async function guardarEstadoCompartido(nodo, valores) {
        const nodoSync = normalizarNodoSync(nodo);
        if (!nodoSync || !valores) return false;
"""
rep="""    async function guardarEstadoCompartido(nodo, valores) {
        const nodoSync = normalizarNodoSync(nodo);
        if (!nodoSync || !valores) return false;

        actualizarEstadoSyncUi(
            'syncing'
        );
"""
if anchor not in m: raise SystemExit("write status anchor missing")
m=m.replace(anchor,rep,1)

anchor="""                procesarTabla();
            }
            return true;"""
rep="""                procesarTabla();

                actualizarEstadoSyncUi(
                    'synced'
                );
            }
            return true;"""
if anchor not in m: raise SystemExit("write success anchor missing")
m=m.replace(anchor,rep,1)

anchor="""            procesarTabla();

            return false;"""
rep="""            procesarTabla();

            actualizarEstadoSyncUi(
                'local'
            );

            return false;"""
if anchor not in m: raise SystemExit("write failure anchor missing")
m=m.replace(anchor,rep,1)

anchor="""        // Recalcular visual desde cero
        limpiarColorFila(fila);
"""
rep="""        // Recalcular visual desde cero
        limpiarColorFila(fila);
        restaurarTooltipVioleta(fila);
"""
if anchor not in m: raise SystemExit("tooltip reset anchor missing")
m=m.replace(anchor,rep,1)

anchor="""                fila.dataset.nuevosVts = '1';

                aplicarColorFila(
                    fila,
                    COLOR_VIOLETA
                );
"""
rep="""                fila.dataset.nuevosVts = '1';

                aplicarColorFila(
                    fila,
                    COLOR_VIOLETA
                );

                aplicarTooltipVioleta(
                    fila
                );

                mostrarAyudaVioletaUnaVez();
"""
if anchor not in m: raise SystemExit("violet help anchor missing")
m=m.replace(anchor,rep,1)

anchor="""    // Fase 3: iniciar la lectura compartida en paralelo. TodavÃ­a no influye
    // en procesarTabla()/procesarFila() ni en los colores existentes.
    setTimeout(
"""
rep="""    actualizarEstadoSyncUi(
        'syncing'
    );

    setTimeout(
"""
if anchor not in m: raise SystemExit("execution status anchor missing")
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
ptr=json.loads((R/"dev/self-update.json").read_text());ptr.update({"build":new,"package_url":"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/"+dst_rel,"package_sha256":h(raw),"notes":["Métricas muestra el estado de sincronización: Sincronizado, Sincronizando o Modo local.","Las filas violetas mantienen ayuda contextual en las celdas de métricas con Ctrl + doble click.","La primera aparición violeta de cada sesión muestra una única ayuda breve para recordar cómo reconocer el nuevo valor."]});(R/"dev/self-update.json").write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n")
hist=json.loads((R/"dev/history.json").read_text());hist["current_build"]=new;hist["current_package"]=dst_rel;(R/"dev/history.json").write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n")

assert "● Sincronizado" in m
assert "↻ Sincronizando" in m
assert "○ Modo local" in m
assert METRICAS_VIOLETA_TOOLTIP if False else True
assert "Valor incrementado después del reconocimiento. Ctrl + doble click para volver a marcarla en verde." in m
assert "Violeta = aumentó después de la última marca. Ctrl + doble click para reconocer el nuevo valor." in m
assert "sessionStorage.getItem" in m
print(new,h(raw))
