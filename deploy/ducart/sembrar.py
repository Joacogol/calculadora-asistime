"""Publica las plantillas y las fotos aportadas; verifica cada escritura."""
from alta_base import req, H, BASE
from pathlib import Path
import json, hashlib, urllib.request, sys

root=Path('/opt/asistime-disenador/ducart-build/.claude/skills/ducart-disenos')
profile={'Accept-Profile':'ducart','Content-Profile':'ducart'}
for p in sorted((root/'plantillas').glob('*/plantilla.json')):
    contrato=json.loads(p.read_text());html=(p.parent/'plantilla.html').read_text()
    path='/rest/v1/plantillas?plantilla=eq.'+contrato['id']+'&publicada=is.true&select=*'
    rows=req(path,headers=profile)
    if not rows or rows[0]['html'] != html or rows[0]['contrato'] != contrato:
        req('/rest/v1/rpc/guardar_plantilla',dict(p_plantilla=contrato['id'],p_html=html,p_contrato=contrato,p_etiqueta='Alta Ducart 14/9/2026',p_quien='Codex',p_publicar=True),headers=profile)
    rows=req(path,headers=profile)
    assert len(rows)==1 and rows[0]['html']==html and rows[0]['contrato']==contrato, contrato['id']
    print('Plantilla verificada:',contrato['id'])
if '--plantillas' in sys.argv:
    sys.exit(0)
for clave,f in json.loads((root/'referencias/fotos.json').read_text())['fotos'].items():
    data=(root/f['archivo']).read_bytes();path='banco/'+clave+'.png'
    u=BASE+'/storage/v1/object/disenos-ducart/'+path
    r=urllib.request.Request(u,data=data,method='POST',headers={**H,'Content-Type':'image/png','x-upsert':'true'})
    with urllib.request.urlopen(r,timeout=90) as response: response.read()
    public=BASE+'/storage/v1/object/public/disenos-ducart/'+path
    with urllib.request.urlopen(public,timeout=90) as response:
        assert hashlib.sha256(response.read()).digest()==hashlib.sha256(data).digest()
    row=dict(clave=clave,url=public,descripcion=f['descripcion']+' '+f['origen'],etiquetas=[s.strip() for s in f['usar_para'].split(',')],quien=f['quien'],foco=f['foco'],ancho=f['medidas'][0],alto=f['medidas'][1],activa=True)
    req('/rest/v1/fotos?on_conflict=clave',row,headers={**profile,'Prefer':'resolution=merge-duplicates'})
    check=req('/rest/v1/fotos?clave=eq.'+clave+'&select=clave,url,ancho,alto',headers=profile)
    assert len(check)==1 and check[0]['url']==public
    print('Foto verificada:',clave)
