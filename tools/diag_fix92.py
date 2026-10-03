#!/usr/bin/env python3
import base64,json,pathlib,re
R=pathlib.Path(__file__).resolve().parents[1]
P=R/'dev/builds/1.3.26-dev-update-buttons-final-align-fix91.json'
pkg=json.loads(P.read_text(encoding='utf-8'))
files={f['path']:base64.b64decode(f['content_base64']).decode('utf-8','replace') for f in pkg['files']}
h=files['js/97-home-ui.js']
for term in ['data-section=\\\"updates\\\"','data-view=\\\"updates\\\"','Actualizaciones','update-summary','Carpeta de instalación','Vincular / cambiar carpeta','Buscar actualización']:
    print('\n###',term)
    i=h.find(term)
    print('INDEX',i)
    if i>=0: print(h[max(0,i-1800):i+3500])
