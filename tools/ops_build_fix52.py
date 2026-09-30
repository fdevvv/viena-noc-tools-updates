import base64, hashlib, json, pathlib
from datetime import datetime, timezone

root = pathlib.Path(".")
src_path = root / "dev/builds/1.3.26-dev-release-history-fix51.json"
dst_rel = "dev/builds/1.3.26-dev-registry-v21-fix52.json"
dst_path = root / dst_rel
old_build = "1.3.26-dev-release-history-fix51"
new_build = "1.3.26-dev-registry-v21-fix52"

old_endpoint = "https://script.google.com/macros/s/AKfycbyDDLTQ5H3a2BMxlA_PPCiy958Jm0c5Lvu-QyoA5mUfvE3CdCvaRV8gnZgJ_Z9VItE6/exec"
new_endpoint = "https://script.google.com/macros/s/AKfycbybjd7pdwq4QuqLwdZo1bYV-gkAWcP20dZmb3rsO2vcqRGY8UekSSnDHYPipjOUblY-/exec"

pkg = json.loads(src_path.read_text(encoding="utf-8"))
files, order = {}, []
for item in pkg["files"]:
    raw = base64.b64decode(item["content_base64"], validate=True)
    assert len(raw) == item["size"]
    assert hashlib.sha256(raw).hexdigest() == item["sha256"]
    files[item["path"]] = raw
    order.append(item["path"])

bg_path = "background.js"
src = files[bg_path].decode("utf-8")
assert old_endpoint in src, "old registry endpoint not found in background.js"
assert new_endpoint not in src, "new registry endpoint already present"
src = src.replace(old_endpoint, new_endpoint)
files[bg_path] = src.encode("utf-8")

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
        "Fix52 DEV: migra el registro de instalaciones al backend Apps Script v2.1.",
        "El nuevo backend reutiliza la primera fila libre real y consolida registros repetidos.",
        "No modifica funcionalidades operativas de VIENA, MIRA 5, GPON, MOICA ni Grafana."
    ]
})
pointer_path.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

history_path = root / "dev/history.json"
history = json.loads(history_path.read_text(encoding="utf-8"))
history["current_build"] = new_build
history["current_package"] = dst_rel
note = "fix52 migrates installation registry heartbeats to the Apps Script v2.1 deployment and keeps all operator-facing functionality unchanged."
if note not in history.get("notes", []):
    history.setdefault("notes", []).append(note)
history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"package": dst_rel, "sha256": package_sha, "build": new_build}, indent=2))
