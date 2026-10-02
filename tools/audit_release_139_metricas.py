#!/usr/bin/env python3
import base64,hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parents[1]
REL=R/"release/v1.3.38-release-status-history-fix54-candidate1-package.json"
PRE=R/"dev/builds/1.3.26-dev-page-manifest-icon-fix73.json"
DEV=R/"dev/builds/1.3.26-dev-metricas-sync-header-status-fix83.json"

def files(path):
    p=json.loads(path.read_text())
    return p,{x["path"]:base64.b64decode(x["content_base64"]) for x in p["files"]}
def h(b): return hashlib.sha256(b).hexdigest()

rp,rf=files(REL)
pp,pf=files(PRE)
dp,df=files(DEV)

print("release_metrics_sha",h(rf["js/50-metrics.js"]))
print("premetrics_metrics_sha",h(pf["js/50-metrics.js"]))
print("metrics_base_identical",rf["js/50-metrics.js"]==pf["js/50-metrics.js"])
print("release_updater_sha",h(rf["js/95-local-updater.js"]))
print("dev_updater_sha",h(df["js/95-local-updater.js"]))
print("updater_identical",rf["js/95-local-updater.js"]==df["js/95-local-updater.js"])

manifest=json.loads(rf["manifest.json"].decode())
print("host_permissions",json.dumps(manifest.get("host_permissions",[]),ensure_ascii=False))

popup=rf["popup.js"].decode("utf-8")
start=popup.find("const OPERATOR_RELEASE_HISTORY = [")
end=popup.find("function renderOperatorReleaseHistory",start)
print("history_marker_found",start>=0 and end>start)
if start>=0 and end>start:
    print("HISTORY_SNIPPET_START")
    print(popup[start:min(end,start+2200)])
    print("HISTORY_SNIPPET_END")
