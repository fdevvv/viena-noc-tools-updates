"""Validate the isolated portable feed without changing the historical channel."""
import base64
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path.cwd()
CHANNEL = "release/portable/"
POINTER = CHANNEL + "latest.json"
URL = "https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/" + CHANNEL
EXTENSION_ID = "kncbbeclddielngolalkmlclfljgaoje"
PACKAGE = re.compile(r"release/portable/v(\d+\.\d+\.\d+)-package\.json")
ROOT_FILES = set("""build.json cws-migration.html icon128.png installation-transfer.html
macro-transfer.html manifest.json popup.html background.js popup.js integrity-manifest.json
permission.html building-capture-permission.html node-background.html updater.html updater.js
onmsi-viewer.html js/55-mira-fec-analysis.css js/98-native-search-highlight.css
js/70-html2canvas.LICENSE.txt""".split())
REQUIRED = {"manifest.json", "build.json", "background.js", "integrity-manifest.json",
            "popup.html", "popup.js", "updater.html", "updater.js",
            "js/95-local-updater.js", "js/102-portable-updater.js"}
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
    require((URL + "latest.json").encode() in files["js/102-portable-updater.js"], "Wrong feed URL")
    print(f"PASS {path}: {len(files)} entries")
    return version, sha(raw)


def pointer():
    value = json.loads((ROOT / POINTER).read_bytes())
    version = value["latest"]
    require(re.fullmatch(r"\d+\.\d+\.\d+", version), "Invalid pointer version")
    package_path = CHANNEL + f"v{version}-package.json"
    require((value["schema"], value["channel"], value["distribution"], value["extension_id"]) ==
            (2, "RELEASE", "portable", EXTENSION_ID), "Invalid pointer identity")
    require(value["build"] == version and value["package_url"] == URL + f"v{version}-package.json", "Invalid pointer route")
    require(package(package_path) == (version, value["package_sha256"]), "Pointer SHA mismatch")
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
            require(status == "A" and PACKAGE.fullmatch(path), "Portable packages are immutable")
            package(path)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--review"]:
        review(*sys.argv[2:])
    elif sys.argv[1:2] == ["--pointer"]:
        pointer()
    else:
        package(sys.argv[1])
