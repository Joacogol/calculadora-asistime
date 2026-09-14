"""Fotos inmediatas y asíncronas registran crédito una vez al completar."""
import os,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import fotero,cobro
os.environ['MAGNIFIC_CLAVE']='prueba-sin-red'
class Cliente:
    marca='ducart-disenos'
cli=Cliente()
row={'id':'foto-prueba','verbo':'fondo','foto':'https://ejemplo.test/entrada.png'}
def probar(sync,completa=True):
    records=[];marks=[];tomados=set()
    def pendientes(c,estado):
        if sync: return [dict(row)] if estado=='pendiente' and not tomados else []
        return [{**row,'tarea':'task','creditos_estimados':3,'modelo':'modelo-async'}] if estado=='trabajando' and not marks else []
    def tomar(c,rid,*args):tomados.add(rid);return True
    def marcar(c,rid,estado,**kw):marks.append((estado,kw))
    with patch.object(fotero,'_pendientes',side_effect=pendientes),patch.object(fotero,'_tomar',side_effect=tomar),patch.object(fotero,'_marcar',side_effect=marcar),patch.object(fotero,'copiar_entrante',return_value=row['foto']),patch.object(fotero,'pedir',return_value=(None,'https://resultado.test/foto.png')),patch.object(fotero,'estado',return_value=('COMPLETED','https://resultado.test/foto.png') if completa else ('WORKING',None)),patch.object(fotero,'_colgada',return_value=False),patch.object(fotero,'_guardar',return_value='https://propio.test/foto.png'),patch.object(cobro,'registrar',side_effect=lambda *a,**kw:records.append((a,kw))):
        fotero.atender_todos(cli,{},lambda *a:None)
        fotero.atender_todos(cli,{},lambda *a:None)
    if not completa:
        assert not records and not marks
    else:
        assert len(records)==1 and marks[0][0]=='listo'
        args,kw=records[0];assert args[1]==row['id'] and kw['tipo']=='foto' and kw['url']=='https://propio.test/foto.png'
        assert kw['creditos']==(fotero.precio('fondo') if sync else 3)
        assert kw['modelo']==(fotero.VERBOS['fondo']['modelo'] if sync else 'modelo-async')
probar(True);probar(False);probar(False,False)
print('OK: foto inmediata, asíncrona y pendiente; sin duplicar registros ni consumir APIs.')
