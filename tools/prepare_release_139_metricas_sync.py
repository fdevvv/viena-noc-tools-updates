#!/usr/bin/env python3
import base64,hashlib,json,pathlib,re,zipfile
from datetime import datetime,timezone

R=pathlib.Path(__file__).resolve().parents[1]
BASE=R/"release/v1.3.38-release-status-history-fix54-candidate1-package.json"
PRE=R/"dev/builds/1.3.26-dev-page-manifest-icon-fix73.json"
METRICS=R/"dev/builds/1.3.26-dev-metricas-sync-header-status-fix83.json"
OUT_REL="release/v1.3.39-metricas-sync-global-candidate1-package.json"
OUT=R/OUT_REL
ZIP_REL="downloads/VIENA_NOC_Tools_RELEASE_v1.3.39_candidate1.zip"
ZIP=R/ZIP_REL
VERSION="1.3.39"
BUILD="1.3.39"

def h(b): return hashlib.sha256(b).hexdigest()
def load(path):
    p=json.loads(path.read_text(encoding="utf-8"))
    f={i["path"]:base64.b64decode(i["content_base64"],validate=True) for i in p["files"]}
    for i in p["files"]:
        b=f[i["path"]]
        assert len(b)==i["size"]
        assert h(b)==i["sha256"]
    return p,f,[i["path"] for i in p["files"]]

base,bf,order=load(BASE)
pre,pf,_=load(PRE)
met,mf,_=load(METRICS)

# Isolation gates: RELEASE 1.3.38 metrics base and updater must be byte-identical
# to the corresponding pre-METRICAS/current validated DEV sources.
assert bf["js/50-metrics.js"] == pf["js/50-metrics.js"], "1.3.38 metrics base drifted from pre-METRICAS fix73"
assert bf["js/95-local-updater.js"] == mf["js/95-local-updater.js"], "updater drift: isolated RELEASE cannot be built safely"

manifest=json.loads(bf["manifest.json"].decode("utf-8"))
hosts=set(manifest.get("host_permissions",[]))
assert "https://script.google.com/*" in hosts
assert "https://script.googleusercontent.com/*" in hosts

files=dict(bf)

# The only functional source transplant: the fully validated METRICAS_SYNC module.
files["js/50-metrics.js"]=mf["js/50-metrics.js"]

# RELEASE identity only.
manifest["name"]="VIENA NOC Tools"
manifest["version"]=VERSION
if isinstance(manifest.get("action"),dict):
    manifest["action"]["default_title"]="VIENA NOC Tools"
files["manifest.json"]=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()

build=json.loads(files["build.json"].decode("utf-8"))
build["version"]=VERSION
build["build"]=BUILD
build["channel"]="RELEASE"
build["generated_at"]=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
build["update_channel"]="release/latest.json"
files["build.json"]=(json.dumps(build,ensure_ascii=False,indent=2)+"\n").encode()

for path,const_name in (
    ("background.js","VIENA_BUILD_ID"),
    ("js/80-update-banner.js","CONTENT_BUILD_ID"),
    ("js/90-runtime-status.js","BUILD_ID"),
):
    s=files[path].decode("utf-8")
    pattern=r"(const\s+"+re.escape(const_name)+r"\s*=\s*['\"])([^'\"]+)(['\"])"
    s,n=re.subn(pattern,lambda m:m.group(1)+BUILD+m.group(3),s,count=1)
    assert n==1, f"identity constant missing in {path}"
    files[path]=s.encode()

popup_html=files["popup.html"].decode("utf-8")
popup_html,n=re.subn(r"v1\.3\.38\s+·\s+Manifest V3",f"v{VERSION} · Manifest V3",popup_html,count=1)
assert n==1, "popup version marker missing"
files["popup.html"]=popup_html.encode()

popup=files["popup.js"].decode("utf-8")
marker="const OPERATOR_RELEASE_HISTORY = [\n"
assert marker in popup
entry="""  {
    version: '1.3.39',
    title: 'Métricas compartidas entre operadores',
    notes: [
      'Las referencias de Métricas se sincronizan entre operadores para comparar contra el mismo punto de partida.',
      'Si los valores aumentan después de la marca, el nodo se muestra violeta y Ctrl + doble click reconoce los nuevos valores.',
      'El estado de sincronización se muestra en la cabecera y, si no está disponible, Métricas continúa en modo local.'
    ]
  },
"""
popup=popup.replace(marker,marker+entry,1)
files["popup.js"]=popup.encode()

# Rebuild integrity after the strictly-scoped changes.
integ={
    "schema":1,
    "version":VERSION,
    "channel":"RELEASE",
    "build":BUILD,
    "files":{p:h(files[p]) for p in order if p!="integrity-manifest.json"}
}
files["integrity-manifest.json"]=(json.dumps(integ,ensure_ascii=False,indent=2)+"\n").encode()

pkg={
    "schema":1,
    "app":"VIENA NOC Tools",
    "version":VERSION,
    "build":BUILD,
    "channel":"RELEASE",
    "generated_at":build["generated_at"],
    "files":[
        {
            "path":p,
            "size":len(files[p]),
            "sha256":h(files[p]),
            "content_base64":base64.b64encode(files[p]).decode("ascii")
        }
        for p in order
    ],
    "remove":[],
    "mode":"full"
}
raw=(json.dumps(pkg,ensure_ascii=False,indent=2)+"\n").encode()
assert not OUT.exists(), f"refusing to overwrite immutable candidate {OUT_REL}"
OUT.write_bytes(raw)

# Deterministic operator ZIP.
assert not ZIP.exists(), f"refusing to overwrite {ZIP_REL}"
with zipfile.ZipFile(ZIP,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
    for name in order:
        info=zipfile.ZipInfo(name)
        info.date_time=(1980,1,1,0,0,0)
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=0o100644 << 16
        zf.writestr(info,files[name])

# Exact scope audit against RELEASE 1.3.38.
allowed={
    "js/50-metrics.js",
    "manifest.json",
    "build.json",
    "background.js",
    "js/80-update-banner.js",
    "js/90-runtime-status.js",
    "popup.html",
    "popup.js",
    "integrity-manifest.json",
}
changed={p for p in order if files[p] != bf[p]}
assert changed <= allowed, f"unexpected RELEASE drift: {sorted(changed-allowed)}"
assert "js/50-metrics.js" in changed
assert files["js/50-metrics.js"] == mf["js/50-metrics.js"]

m=files["js/50-metrics.js"].decode("utf-8")
checks={
    "GET_TODAY_STATES":"GET_TODAY_STATES" in m,
    "INIT_STATE":"'INIT_STATE'" in m,
    "UPSERT_STATE":"'UPSERT_STATE'" in m,
    "violet":"valores.total > base.total" in m and "valores.problema > base.problema" in m,
    "flag_guard":"METRICAS_FLAG_REPLACEMENT_GRACE_MS = 12000" in m,
    "header_status":"'left:50%'" in m and "'top:14px'" in m and "'bottom:14px'" not in m,
    "fallback_local":"'local'" in m and "Modo local" in m,
}
assert all(checks.values()), checks
assert "registro de instalaciones" not in entry.lower()
assert "apps script" not in entry.lower()
assert "sheet" not in entry.lower()

print(json.dumps({
    "candidate":OUT_REL,
    "candidate_sha256":h(raw),
    "zip":ZIP_REL,
    "zip_sha256":h(ZIP.read_bytes()),
    "changed_paths":sorted(changed),
    "checks":checks,
},ensure_ascii=False,indent=2))
