#!/usr/bin/env python3
import base64, json, pathlib, zipfile, hashlib

R = pathlib.Path(__file__).resolve().parents[1]
PKG = R / "dev/builds/1.3.26-dev-update-button-size-fix90.json"
OUT = R / "downloads/VIENA_NOC_Tools_DEV_fix90.zip"

pkg = json.loads(PKG.read_text(encoding="utf-8"))
OUT.parent.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for item in pkg["files"]:
        data = base64.b64decode(item["content_base64"], validate=True)
        assert hashlib.sha256(data).hexdigest() == item["sha256"]
        info = zipfile.ZipInfo(item["path"])
        info.date_time = (1980,1,1,0,0,0)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        zf.writestr(info, data)

print(OUT)
