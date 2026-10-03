#!/usr/bin/env python3
import base64,json,pathlib
R=pathlib.Path(__file__).resolve().parents[1]
P=R/'dev/builds/1.3.26-dev-fullview-general-updates-fix92.json'
pkg=json.loads(P.read_text(encoding='utf-8'))
files={f['path']:base64.b64decode(f['content_base64']).decode('utf-8','replace') for f in pkg['files']}
for path in ['popup.html','popup.js','js/97-home-ui.js']:
    print('\nFILE',path)
    s=files[path]
    for term in ['openUpdate','manualReleaseZip','Buscar actualización DEV','Buscar actualización','summaryAvailable','updatesAvailable','summaryInstalled','updatesInstalled','refreshUpdates','checkUpdate']:
        i=s.find(term)
        if i>=0:
            print('\n###',term,'INDEX',i)
            print(s[max(0,i-1300):i+2600])
