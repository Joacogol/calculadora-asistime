"""Recupera sólo el registro de la foto de prueba ya generada; nunca la regenera."""
import runpy,sys,requests
sys.path.insert(0,'/app')
runpy.run_path('/run/ducart.py',run_name='configurar')
from app import config,cobro,libro
from app.supa import Cliente
cli=Cliente(**config.clientes()[0])
assert cli.marca=='ducart-disenos' and not cobro.cobra(cli.marca)
rid='ea30cdb1-b8cd-492d-93d9-063c883f1a3e'
r=requests.get(cli._url('fotos_editadas'),headers=cli._cab(),params={'id':'eq.'+rid,'select':'id,estado,verbo,url,modelo,creditos_gastados'},timeout=30);r.raise_for_status()
fila=r.json()[0];assert fila['estado']=='listo' and fila['creditos_gastados']==3
from app.fotero import _cobrar
_cobrar(cli,{**fila,'creditos_estimados':fila['creditos_gastados']},fila['url'])
casa=libro.casa()
r=requests.get(casa._url('libro'),headers=casa._cab(),params={'marca':'eq.ducart-disenos','pieza_id':'eq.'+rid,'select':'tipo,creditos,precio_usd,cobrado_en'},timeout=30);r.raise_for_status()
rows=r.json();assert len(rows)==1 and rows[0]['creditos']==3 and rows[0]['precio_usd']==0 and rows[0]['cobrado_en'] is None
print('Registro verificado:',rows)
