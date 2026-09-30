import base64, hashlib, json, pathlib
from datetime import datetime, timezone

root = pathlib.Path(".")
src_path = root / "dev/builds/1.3.26-dev-release-history-137-fix53.json"
dst_rel = "dev/builds/1.3.26-dev-release-status-history-fix54.json"
dst_path = root / dst_rel
old_build = "1.3.26-dev-release-history-137-fix53"
new_build = "1.3.26-dev-release-status-history-fix54"

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
start = "const OPERATOR_RELEASE_HISTORY = ["
end = "\n\nfunction renderOperatorReleaseHistory()"
a = src.find(start)
b = src.find(end, a)
assert a >= 0 and b > a
history = """const OPERATOR_RELEASE_HISTORY = [
  {
    version: '1.3.38',
    title: 'Estado de actualización más preciso',
    notes: [
      'Se corrigió la detección de la RELEASE vigente para que el estado mostrado coincida con la versión publicada.',
      'Se ordenó el historial visible para mantener únicamente información útil para el operador.'
    ]
  },
  {
    version: '1.3.37',
    title: 'Mejoras de estabilidad',
    notes: [
      'Se mejoró la estabilidad general de la extensión y la actualización de actividad.',
      'El historial visible incorpora las RELEASES recientes con información operativa.'
    ]
  },
  {
    version: '1.3.36',
    title: 'Menús de Completar Tarea más ordenados',
    notes: [
      'Completar Tarea y los botones personales mantienen un solo menú desplegable abierto a la vez.',
      'El historial de versiones visible en el popup se actualizó con las RELEASES recientes.'
    ]
  }
];
"""
src = src[:a] + history + src[b:]
for forbidden in ("registro de instalaciones", "installation registry"):
    assert forbidden.lower() not in src[a:b+len(history)].lower()
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
        "Fix54 DEV: corrige el historial visible y prepara la siguiente RELEASE.",
        "El estado de actualización se alinea con la RELEASE vigente.",
        "El historial visible queda limitado a información útil para el operador."
    ]
})
pointer_path.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

history_path = root / "dev/history.json"
history_json = json.loads(history_path.read_text(encoding="utf-8"))
history_json["current_build"] = new_build
history_json["current_package"] = dst_rel
note = "fix54 sanitizes operator-facing release history and aligns the next release with the current published version state."
if note not in history_json.get("notes", []):
    history_json.setdefault("notes", []).append(note)
history_path.write_text(json.dumps(history_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"package": dst_rel, "sha256": package_sha, "build": new_build}, indent=2))
