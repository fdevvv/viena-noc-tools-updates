#!/usr/bin/env python3
import base64,json,pathlib
R=pathlib.Path(__file__).resolve().parents[1]
P=R/'dev/builds/1.3.26-dev-update-buttons-final-align-fix91.json'
pkg=json.loads(P.read_text(encoding='utf-8'))
files={f['path']:base64.b64decode(f['content_base64']).decode('utf-8','replace') for f in pkg['files']}
h=files['js/97-home-ui.js']
for term in ["checkUpdates","runUpdateNow","manualReleaseZipFull","openFolderManager","summaryInstalled","summaryAvailable","summaryFolder","setSection(name)","data-section=\\\"updates\\\""]:
    print("\n###",term)
    start=0
    while True:
      i=h.find(term,start)
      if i<0: break
      print("INDEX",i)
      print(h[max(0,i-900):i+1800])
      start=i+len(term)
