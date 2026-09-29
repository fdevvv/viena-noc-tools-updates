import base64, hashlib, json, pathlib
# rebuild trigger for validated fix51
from datetime import datetime, timezone

root = pathlib.Path(".")
src_path = root / "dev/builds/1.3.26-dev-completar-exclusive-menus-fix50.json"
dst_rel = "dev/builds/1.3.26-dev-release-history-fix51.json"
dst_path = root / dst_rel
old_build = "1.3.26-dev-completar-exclusive-menus-fix50"
new_build = "1.3.26-dev-release-history-fix51"

pkg = json.loads(src_path.read_text(encoding="utf-8"))
files, order = {}, []
for item in pkg["files"]:
    raw = base64.b64decode(item["content_base64"], validate=True)
    assert len(raw) == item["size"]
    assert hashlib.sha256(raw).hexdigest() == item["sha256"]
    files[item["path"]] = raw
    order.append(item["path"])

popup_path = "popup.js"
popup = files[popup_path].decode("utf-8")

needle = """const OPERATOR_RELEASE_HISTORY = [
  {
    version: '1.3.29',"""

insert = """const OPERATOR_RELEASE_HISTORY = [
  {
    version: '1.3.35',
    title: 'Cuadras: vista previa y fallas rápidas',
    notes: [
      'La vista previa de cuadras incorpora fallas rápidas y templates editables para completar FALLA DETECTADA.',
      'Las cuadras se muestran un rango por línea.',
      'Los templates seleccionados se agregan al final de FALLA DETECTADA sin alterar ESTADO DE FUENTE.'
    ]
  },
  {
    version: '1.3.34',
    title: 'Selección de cuadras en MIRA',
    notes: [
      'Se agregó la selección de direcciones desde el Listado de CMs para armar rangos de cuadras.',
      'La selección se integra al sector de acciones del listado y convive con Copiar datos Edif cuando corresponde.'
    ]
  },
  {
    version: '1.3.33',
    title: 'Avisos de actualización más confiables',
    notes: [
      'Se corrigieron avisos de actualización que podían quedar desactualizados respecto de la RELEASE publicada.',
      'La extensión vuelve a validar la versión publicada antes de actuar sobre un aviso de actualización.'
    ]
  },
  {
    version: '1.3.32',
    title: 'Estado de actualización más claro',
    notes: [
      'Se mejoró el estado mostrado después de una actualización para evitar mensajes ambiguos mientras termina la verificación.',
      'La extensión diferencia mejor entre una actualización aplicada y una confirmación todavía pendiente.'
    ]
  },
  {
    version: '1.3.31',
    title: 'Vinculación y estado más coherentes',
    notes: [
      'Se mejoró la verificación de la carpeta vinculada y la coherencia del estado mostrado en el popup.',
      'Las acciones de prueba destinadas a DEV dejan de mostrarse en RELEASE.'
    ]
  },
  {
    version: '1.3.30',
    title: 'Historial de RELEASES para el operador',
    notes: [
      'Se incorporó al popup un historial de versiones centrado en cambios útiles para el operador.',
      'El historial evita detalles internos de desarrollo y publicación.'
    ]
  },
  {
    version: '1.3.29',"""

assert needle in popup, "Expected operator history anchor not found"
popup = popup.replace(needle, insert, 1)
files[popup_path] = popup.encode("utf-8")

for path, raw in list(files.items()):
    if path == "integrity-manifest.json":
        continue
    try:
        txt = raw.decode("utf-8")
    except UnicodeDecodeError:
        continue
    if old_build in txt:
        files[path] = txt.replace(old_build, new_build).encode("utf-8")

integrity = json.loads(files["integrity-manifest.json"].decode("utf-8"))
integrity["build"] = new_build
integrity["files"] = {
    path: hashlib.sha256(files[path]).hexdigest()
    for path in order
    if path != "integrity-manifest.json"
}
files["integrity-manifest.json"] = (
    json.dumps(integrity, ensure_ascii=False, indent=2) + "\n"
).encode("utf-8")

pkg["build"] = new_build
pkg["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
pkg["files"] = [{
    "path": path,
    "size": len(files[path]),
    "sha256": hashlib.sha256(files[path]).hexdigest(),
    "content_base64": base64.b64encode(files[path]).decode("ascii"),
} for path in order]

raw_pkg = (json.dumps(pkg, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
dst_path.write_bytes(raw_pkg)
package_sha = hashlib.sha256(raw_pkg).hexdigest()

pointer_path = root / "dev/self-update.json"
pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
pointer.update({
    "build": new_build,
    "package_url": f"https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/{dst_rel}",
    "package_sha256": package_sha,
    "notes": [
        "Fix51 DEV: el historial visible del popup se actualiza desde 1.3.29 hasta 1.3.35.",
        "El historial mantiene sólo cambios útiles para el operador y omite detalles internos de desarrollo.",
        "No modifica RELEASE ni el flujo de actualización."
    ]
})
pointer_path.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

history_path = root / "dev/history.json"
history = json.loads(history_path.read_text(encoding="utf-8"))
history["current_build"] = new_build
history["current_package"] = dst_rel
note = "fix51 updates the operator-facing RELEASE history through 1.3.35 without exposing internal implementation or publication details."
if note not in history.get("notes", []):
    history.setdefault("notes", []).append(note)
history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"package": dst_rel, "sha256": package_sha, "build": new_build}, indent=2))
