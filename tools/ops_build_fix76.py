#!/usr/bin/env python3
import base64,hashlib,json,pathlib
from datetime import datetime,timezone
R=pathlib.Path(__file__).resolve().parents[1]
src=R/"dev/builds/1.3.26-dev-metricas-sync-write-phase4-fix75.json"
dst_rel="dev/builds/1.3.26-dev-metricas-sync-apply-phase5-fix76.json"
dst=R/dst_rel
old="1.3.26-dev-metricas-sync-write-phase4-fix75"
new="1.3.26-dev-metricas-sync-apply-phase5-fix76"
def h(b): return hashlib.sha256(b).hexdigest()
p=json.loads(src.read_text())
F={}
for x in p["files"]:
 b=base64.b64decode(x["content_base64"]); assert h(b)==x["sha256"]; F[x["path"]]=b
m=F["js/50-metrics.js"].decode()

anchor = "        if (!historial[nodo]) {"
pos = m.index(anchor, m.index("// CON BANDERA"))
insert = """        // Fase 5: si existe una referencia compartida para este nodo,
        // usarla como fuente de verdad para el historial local.
        const nodoSync =
            normalizarNodoSync(nodo);

        const estadoCompartido =
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
m = m[:pos] + insert + m[pos:]

no_flag = "            delete fila.dataset.nuevosVts;\n\n            const maximo ="
if no_flag not in m: raise SystemExit("no-flag marker missing")
m = m.replace(
    no_flag,
    "            delete fila.dataset.nuevosVts;\n            delete fila.dataset.vienaSyncBase;\n\n            const maximo =",
    1
)

F["js/50-metrics.js"]=m.encode()
for q in ("background.js","js/80-update-banner.js","js/90-runtime-status.js"):
 s=F[q].decode(); assert old in s; F[q]=s.replace(old,new,1).encode()
b=json.loads(F["build.json"]);b["build"]=new;F["build.json"]=(json.dumps(b,ensure_ascii=False,indent=2)+"\n").encode()
im=json.loads(F["integrity-manifest.json"]);im["build"]=new;im["files"]={k:h(v) for k,v in F.items() if k!="integrity-manifest.json"};F["integrity-manifest.json"]=(json.dumps(im,ensure_ascii=False,indent=2)+"\n").encode()
order=[x["path"] for x in p["files"]];p["build"]=new;p["generated_at"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z");p["files"]=[]
for q in order:
 b=F[q];p["files"].append({"path":q,"size":len(b),"sha256":h(b),"content_base64":base64.b64encode(b).decode()})
raw=(json.dumps(p,ensure_ascii=False,indent=2)+"\n").encode();dst.write_bytes(raw)
ptr=json.loads((R/"dev/self-update.json").read_text());ptr.update({"build":new,"package_url":"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/"+dst_rel,"package_sha256":h(raw),"notes":["MÃ©tricas aplica las referencias recibidas desde METRICAS_SYNC al historial local por nodo.","Se sincronizan total/problema de referencia; la lÃ³gica de colores existente sigue decidiendo el estado visual.","Si no existe referencia global, el comportamiento local previo se conserva."]});(R/"dev/self-update.json").write_text(json.dumps(ptr,ensure_ascii=False,indent=2)+"\n")
hist=json.loads((R/"dev/history.json").read_text());hist["current_build"]=new;hist["current_package"]=dst_rel;(R/"dev/history.json").write_text(json.dumps(hist,ensure_ascii=False,indent=2)+"\n")

row=m[m.index("function procesarFila"):m.index("function procesarTabla")]
assert "metricasSyncEstados.get(nodoSync)" in row
assert "referenciaGlobal" in row
assert "estadoCompartido.total_marcado" in row and "estadoCompartido.problema_marcado" in row
assert "aplicarColorFila" in row
print(new,h(raw))
