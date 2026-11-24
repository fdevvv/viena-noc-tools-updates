"""Validate the isolated portable feed without changing the historical channel."""
import base64
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path.cwd()
CHANNEL = "release/portable/"
POINTER = CHANNEL + "latest.json"
URL = "https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/" + CHANNEL
EXTENSION_ID = "kncbbeclddielngolalkmlclfljgaoje"
PACKAGE = re.compile(r"release/portable/v(\d+\.\d+\.\d+)-package\.json")
ZIP = re.compile(r"release/portable/VIENA_NOC_Tools_PORTABLE_v(\d+\.\d+\.\d+)\.zip")
ROOT_FILES = set("""build.json cws-migration.html icon128.png installation-transfer.html
macro-transfer.html manifest.json popup.html background.js popup.js integrity-manifest.json
permission.html building-capture-permission.html node-background.html updater.html updater.js
onmsi-viewer.html manual-update.html js/55-mira-fec-analysis.css js/98-native-search-highlight.css
js/70-html2canvas.LICENSE.txt""".split())
REQUIRED = {"manifest.json", "build.json", "background.js", "integrity-manifest.json", "popup.html", "popup.js"}
SELF_INSTALL = {"updater.html", "updater.js", "js/95-local-updater.js", "js/102-portable-updater.js"}
MANUAL_INSTALL = {"manual-update.html", "js/102-portable-download.js", "js/102-portable-download-page.js"}
EXCLUDED = re.compile(rb"VienaLupa|VienaTicketRecording|VienaHfcDegradation|VienaHfcSupervised|66-site-themes")
DESTRUCTIVE = re.compile(rb"chrome\.storage\.local\.clear\s*\(|indexedDB\.deleteDatabase\s*\(")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def package(path):
    match = PACKAGE.fullmatch(path)
    require(match, f"Invalid portable package path: {path}")
    version = match.group(1)
    raw = (ROOT / path).read_bytes()
    data = json.loads(raw)
    require(data["schema"] == 1 and data["app"] == "VIENA NOC Tools", "Invalid package format")
    require(data["version"] == data["build"] == version and data["channel"] == "RELEASE", "Invalid package identity")
    require(data["mode"] == "full" and not data.get("remove") and not data.get("patches"), "Expected a full package")
    inventory = {}
    files = {}
    with tempfile.TemporaryDirectory() as temporary:
        for entry in data["files"]:
            name = entry["path"]
            require(name in ROOT_FILES or re.fullmatch(r"js/[A-Za-z0-9._-]+\.js", name), f"Unexpected path: {name}")
            require(name not in files, f"Duplicate entry: {name}")
            contents = base64.b64decode(entry["content_base64"], validate=True)
            digest = sha(contents)
            require(len(contents) == entry["size"] and digest == entry["sha256"], f"Invalid bytes: {name}")
            require(not EXCLUDED.search(contents), f"DEV-only component: {name}")
            files[name] = contents
            if name != "integrity-manifest.json":
                inventory[name] = digest
            if name.endswith(".js"):
                require(not DESTRUCTIVE.search(contents), f"Destructive storage operation: {name}")
                script = pathlib.Path(temporary) / name.replace("/", "__")
                script.write_bytes(contents)
                subprocess.run(["node", "--check", str(script)], check=True)
    require(REQUIRED <= files.keys(), "Missing portable runtime files")
    manifest = json.loads(files["manifest.json"])
    build = json.loads(files["build.json"])
    declared = json.loads(files["integrity-manifest.json"])
    require(manifest["version"] == version and manifest["name"] == "VIENA NOC Tools", "Invalid manifest")
    key_hash = sha(base64.b64decode(manifest["key"], validate=True))[:32]
    require("".join(chr(97 + int(digit, 16)) for digit in key_hash) == EXTENSION_ID, "Wrong extension ID")
    for identity in (build, declared):
        require(identity["version"] == identity["build"] == version and identity["channel"] == "RELEASE", "Invalid runtime identity")
    require(build["distribution"] == "portable" and declared["files"] == inventory, "Invalid portable inventory")
    manual = "manual-update.html" in files
    if manual:
        require(MANUAL_INSTALL <= files.keys() and not SELF_INSTALL & files.keys(), "Invalid manual runtime")
        require(URL.encode() in files["js/102-portable-download.js"], "Wrong manual feed URL")
    else:
        require(SELF_INSTALL <= files.keys(), "Missing self-install runtime")
        require((URL + "latest.json").encode() in files["js/102-portable-updater.js"], "Wrong feed URL")
    print(f"PASS {path}: {len(files)} entries")
    return version, sha(raw), files, manual


def archive(path, validated=None):
    match = ZIP.fullmatch(path)
    require(match, f"Invalid portable ZIP path: {path}")
    version = match.group(1)
    checked = validated or package(CHANNEL + f"v{version}-package.json")
    require(checked[0] == version and checked[3], "ZIP must match a manual runtime")
    raw = ROOT / path
    with zipfile.ZipFile(raw) as zipped:
        names = [entry.filename.replace("\\", "/") for entry in zipped.infolist() if not entry.is_dir()]
        require(len(names) == len(set(names)) and set(names) == set(checked[2]), "ZIP inventory differs")
        for entry, name in ((e, e.filename.replace("\\", "/")) for e in zipped.infolist() if not e.is_dir()):
            expected = checked[2][name]
            require(entry.file_size == len(expected) and zipped.read(entry) == expected, f"ZIP bytes differ: {name}")
    print(f"PASS {path}: {len(names)} files match the package")
    return sha(raw.read_bytes())


def pointer():
    value = json.loads((ROOT / POINTER).read_bytes())
    version = value["latest"]
    require(re.fullmatch(r"\d+\.\d+\.\d+", version), "Invalid pointer version")
    package_path = CHANNEL + f"v{version}-package.json"
    require((value["schema"], value["channel"], value["distribution"], value["extension_id"]) ==
            (2, "RELEASE", "portable", EXTENSION_ID), "Invalid pointer identity")
    require(value["build"] == version, "Invalid pointer build")
    checked = package(package_path)
    if checked[3]:
        name = f"VIENA_NOC_Tools_PORTABLE_v{version}.zip"
        require(value["zip_url"] == URL + name, "Invalid ZIP route")
        require("package_url" not in value and "package_sha256" not in value, "Manual feed cannot request self-install")
        require(archive(CHANNEL + name, checked) == value["zip_sha256"], "ZIP pointer SHA mismatch")
    else:
        require(value["package_url"] == URL + f"v{version}-package.json", "Invalid pointer route")
        require(checked[:2] == (version, value["package_sha256"]), "Pointer SHA mismatch")
    print(f"PASS {POINTER}: {version}")
    return tuple(map(int, version.split(".")))


def git(*args):
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8")


def review(base, head, branch):
    changes = [line.split("\t") for line in git("diff", "--no-renames", "--name-status", base, head).splitlines()]
    portable = [(status, path) for status, path in changes if path.startswith(CHANNEL)]
    for status, path in portable:
        if path == POINTER:
            require(len(changes) == 1 and branch.startswith("release/portable-promote-"),
                    "Portable promotion must be a dedicated pointer-only PR")
            current = pointer()
            previous = subprocess.run(["git", "show", f"{base}:{POINTER}"], capture_output=True, check=False)
            if previous.returncode == 0:
                before = tuple(map(int, json.loads(previous.stdout)["latest"].split(".")))
                require(current > before, "Portable version must advance")
            require(status in {"A", "M"}, "Portable pointer cannot be removed")
        else:
            require(status == "A", "Portable files are immutable")
            if ZIP.fullmatch(path):
                archive(path)
            else:
                package(path)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--review"]:
        review(*sys.argv[2:])
    elif sys.argv[1:2] == ["--pointer"]:
        pointer()
    else:
        if ZIP.fullmatch(sys.argv[1]):
            archive(sys.argv[1])
        else:
            package(sys.argv[1])
