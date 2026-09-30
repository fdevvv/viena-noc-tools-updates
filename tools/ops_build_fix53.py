import base64, hashlib, json, pathlib
from datetime import datetime, timezone

root = pathlib.Path(".")
src_path = root / "dev/builds/1.3.26-dev-registry-v21-fix52.json"
dst_rel = "dev/builds/1.3.26-dev-release-history-137-fix53.json"
dst_path = root / dst_rel
old_build = "1.3.26-dev-registry-v21-fix52"
new_build = "1.3.26-dev-release-history-137-fix53"

pkg = json.loads(src_path.read_text(encoding="utf-8"))
files, order = {}, []
for item in pkg["files"]:
    raw = base64.b64decode(item["content_base64"], validate=True)
    assert len(raw) == item["size"]
    assert hashlib.sha256(raw).hexdigest() == item["sha256"]
    files[item["path"]] = raw
    order.append(item["path"])

popup_path = "popup.js"
src = files[popup_path].decode("utf-8")
marker = "const OPERATOR_RELEASE_HISTORY = [\n"
assert marker in src
entries = """const OPERATOR_RELEASE_HISTORY = [
  {
    version: '1.3.37',
    title: 'Registro de instalaciones más confiable',
    notes: [
      'Se mejoró el registro de instalaciones para reutilizar correctamente filas disponibles y evitar registros duplicados.',
      'La actualización del estado de cada instalación mantiene el historial y la actividad del operador de forma más consistente.'
    ]
  },
  {
    version: '1.3.36',
    title: 'Menús de Completar Tarea más ordenados',
    notes: [
      'Completar Tarea y los botones personales mantienen un solo menú desplegable abierto a la vez.',
      'El historial de versiones visible en el popup se actualizó con las RELEASES recientes.'
    ]
  },
"""
src = src.replace(marker, entries, 1)
files[popup_path] = src.encode("utf-8")

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
    for path in order if path != "integrity-manifest.json"
}
files["integrity-manifest.json"] = (
    json.dumps(integrity, ensure_ascii=False, indent=2) + "\n"
).encode("utf-8")

pkg["build"] = new_build
pkg["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
pkg["files"] = [{
    "path": path,
    "size": len(files[path]),
    "sha256": hashlib.sha256(files[path]).hexdigest(),
    "content_base64": base64.b64encode(files[path]).decode("ascii")
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
        "Fix53 DEV: prepara el historial visible para la RELEASE 1.3.37.",
        "Agrega 1.3.36 y 1.3.37 al historial del popup.",
        "Mantiene el backend de registro v2.1 validado en fix52."
    ]
})
pointer_path.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

history_path = root / "dev/history.json"
history = json.loads(history_path.read_text(encoding="utf-8"))
history["current_build"] = new_build
history["current_package"] = dst_rel
note = "fix53 adds operator-visible RELEASE history entries for 1.3.36 and the current 1.3.37 before promotion."
if note not in history.get("notes", []):
    history.setdefault("notes", []).append(note)
history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"package": dst_rel, "sha256": package_sha, "build": new_build}, indent=2))
\n# trigger\n