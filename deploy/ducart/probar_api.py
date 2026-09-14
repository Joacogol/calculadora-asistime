"""Prueba acotada del alta: autenticación, lectura y una edición de foto."""
from alta_base import req,BASE,config
from pathlib import Path
import json,urllib.request
key=json.loads((config/'ducart-alta.json').read_text())['api_key']
def api(path,body=None):
 r=urllib.request.Request(BASE+'/functions/v1/'+path,data=json.dumps(body).encode() if body else None,headers={'x-api-clave':key,'Content-Type':'application/json'})
 with urllib.request.urlopen(r,timeout=80) as f:return json.loads(f.read())
if __name__=='__main__':
 bank=api('api-disenos/banco');assert bank['total']==17;print('API banco: 17 fotos')
 statepath=Path('/opt/asistime-disenador/ducart-build/pruebas.json')
 state=json.loads(statepath.read_text()) if statepath.exists() else {}
 if not state.get('foto'):
  state['foto']=api('api-fotos',{'verbo':'fondo','foto':BASE+'/storage/v1/object/public/disenos-ducart/banco/botas-bekina.png','quien':'Prueba técnica alta Ducart'})
  statepath.write_text(json.dumps(state))
 print('Prueba foto:',api('api-fotos?id='+state['foto']['id']+'&esperar=no'))
 print('Diseño:',api('api-disenos?id=2c9d1a03-5957-4606-9472-7d1c5c544a34&esperar=no'))
 print('Costos:',req('/rest/v1/movimientos?select=tipo,monto_usd,costo_usd,diseno_id',headers={'Accept-Profile':'ducart'}))
 print('Cuenta Instagram:',req('/rest/v1/instagram_estado?select=usuario,activa',headers={'Accept-Profile':'ducart'}))
