import base64, hashlib, json, pathlib
from datetime import datetime, timezone

root = pathlib.Path(".")
src_path = root / "dev/builds/1.3.26-dev-mira-cuadras-modal-transitions-fix49.json"
dst_rel = "dev/builds/1.3.26-dev-completar-exclusive-menus-fix50.json"
dst_path = root / dst_rel
old_build = "1.3.26-dev-mira-cuadras-modal-transitions-fix49"
new_build = "1.3.26-dev-completar-exclusive-menus-fix50"

pkg = json.loads(src_path.read_text(encoding="utf-8"))
files, order = {}, []
for item in pkg["files"]:
    raw = base64.b64decode(item["content_base64"], validate=True)
    assert len(raw) == item["size"]
    assert hashlib.sha256(raw).hexdigest() == item["sha256"]
    files[item["path"]] = raw
    order.append(item["path"])

js_path = "js/40-templates.js"
src = files[js_path].decode("utf-8")

marker = """    function limpiarMenusGruposPersonalizados() {
        document.querySelectorAll('.viena-custom-template-group-menu').forEach(el => el.remove());
    }

    function crearMenuGrupoPersonalizado(grupo, boton) {"""
replacement = """    function limpiarMenusGruposPersonalizados() {
        document.querySelectorAll('.viena-custom-template-group-menu').forEach(el => el.remove());
    }

    // Sólo puede haber un menú de Completar Tarea abierto a la vez.
    function cerrarMenusCompletarExcepto(excepto = null) {
        const principal = document.getElementById('viena-completar-menu-principal');
        if (principal && principal !== excepto) principal.style.display = 'none';
        document.querySelectorAll('.viena-custom-template-group-menu').forEach(menu => {
            if (menu !== excepto) menu.style.display = 'none';
        });
        if (ocultarEditorPlantillaGlobal) ocultarEditorPlantillaGlobal();
    }

    function crearMenuGrupoPersonalizado(grupo, boton) {"""
assert marker in src
src = src.replace(marker, replacement, 1)

old_custom = """        boton.addEventListener('click', e => {
            e.stopPropagation();
            const abrir = menu.style.display === 'none';
            document.querySelectorAll('.viena-custom-template-group-menu').forEach(m => { if (m !== menu) m.style.display='none'; });
            if (abrir) { posicionar(); menu.style.display='block'; }
            else { menu.style.display='none'; if (ocultarEditorPlantillaGlobal) ocultarEditorPlantillaGlobal(); }
            setTimeout(()=>{try{boton.blur();}catch(_){}},0);
        });"""
new_custom = """        boton.addEventListener('click', e => {
            e.stopPropagation();
            const abrir = menu.style.display === 'none';
            cerrarMenusCompletarExcepto(menu);
            if (abrir) { posicionar(); menu.style.display='block'; }
            else { menu.style.display='none'; }
            setTimeout(()=>{try{boton.blur();}catch(_){}},0);
        });"""
assert old_custom in src
src = src.replace(old_custom, new_custom, 1)

old_main = """        boton.onclick = (e) => {

            e.stopPropagation();

            const abrir = menu.style.display === 'none';
            if (abrir) {
                const r = boton.getBoundingClientRect();
                menu.style.left = `${Math.max(8, Math.round(r.left))}px`;
                menu.style.top = `${Math.round(r.bottom + 6)}px`;
                menu.style.display = 'block';
            } else {
                menu.style.display = 'none';
                ocultarEditor();
            }
            setTimeout(() => { try { boton.blur(); } catch (_) {} }, 0);
        };"""
new_main = """        boton.onclick = (e) => {

            e.stopPropagation();

            const abrir = menu.style.display === 'none';
            cerrarMenusCompletarExcepto(menu);
            if (abrir) {
                const r = boton.getBoundingClientRect();
                menu.style.left = `${Math.max(8, Math.round(r.left))}px`;
                menu.style.top = `${Math.round(r.bottom + 6)}px`;
                menu.style.display = 'block';
            } else {
                menu.style.display = 'none';
            }
            setTimeout(() => { try { boton.blur(); } catch (_) {} }, 0);
        };"""
assert old_main in src
src = src.replace(old_main, new_main, 1)
files[js_path] = src.encode("utf-8")

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
integrity["files"] = {path: hashlib.sha256(files[path]).hexdigest() for path in order if path != "integrity-manifest.json"}
files["integrity-manifest.json"] = (json.dumps(integrity, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

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
        "Fix50 DEV: sólo puede quedar abierto un menú de Completar Tarea a la vez.",
        "Al abrir Completar Tarea se cierran los botones personales abiertos, y al abrir un botón personal se cierra Completar Tarea.",
        "Volver a tocar el mismo botón sigue cerrando su propio menú."
    ]
})
pointer_path.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

history_path = root / "dev/history.json"
history = json.loads(history_path.read_text(encoding="utf-8"))
history["current_build"] = new_build
history["current_package"] = dst_rel
note = "fix50 makes the Completar Tarea menu and all personal-button menus mutually exclusive, so opening one always closes any other currently open completion menu."
if note not in history.get("notes", []):
    history.setdefault("notes", []).append(note)
history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"package": dst_rel, "sha256": package_sha, "build": new_build}, indent=2))
