"""Alta acotada de Ducart. Se ejecuta en el servidor, sin imprimir claves."""
import json, urllib.request, urllib.error, os, sys
from pathlib import Path

BASE='https://qxjvtxumkljsroukpkny.supabase.co'
config=Path('/opt/asistime-disenador/config')
secrets=json.loads((config/'credenciales.json').read_text())
H={'apikey':secrets['SUPABASE_KEY'],'Authorization':'Bearer '+secrets['SUPABASE_KEY'],'Content-Type':'application/json'}
def req(path,body=None,method=None,headers=None):
    data=json.dumps(body).encode() if body is not None else None
    r=urllib.request.Request(BASE+path,data=data,headers={**H,**(headers or {})},method=method or ('POST' if data else 'GET'))
    try:
        with urllib.request.urlopen(r,timeout=120) as f:
            b=f.read();return json.loads(b) if b else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(str(e.code)+' '+e.read().decode()[:600]) from None

if __name__=='__main__':
    commit=sys.argv[1]
    marker=config/'ducart-alta.json'
    state=json.loads(marker.read_text()) if marker.exists() else {}
    def save():
        marker.write_text(json.dumps(state,indent=2));os.chmod(marker,0o600)
    if not state.get('schema'):
        result=req('/rest/v1/rpc/alta_desde_repo',{'url':f'https://raw.githubusercontent.com/Joacogol/calculadora-asistime/{commit}/worker/alta/esquemas/ducart-disenos.sql'})
        print('SQL:',result);state['schema']=commit;save()
    found=req('/rest/v1/clientes?marca=eq.ducart-disenos&select=marca,nombre,esquema,bucket,cobra')
    if not found:
        req('/rest/v1/clientes',{'marca':'ducart-disenos','nombre':'Ducart Latin America','esquema':'ducart','bucket':'disenos-ducart','supabase_ref':'qxjvtxumkljsroukpkny','cobra':False,'activo':True,'notas':'Alta 14/9/2026. Tenant 189, agente 625. Costos registrados sin descontar saldo, autorizado por Joaquín.'})
    print('Cliente:',req('/rest/v1/clientes?marca=eq.ducart-disenos&select=marca,nombre,esquema,bucket,cobra'))
    print('Exponer:',req('/rest/v1/rpc/exponer_esquema',{'p_esquema':'ducart'}))
    if not state.get('api_key'):
        state['api_key']=req('/rest/v1/rpc/alta_clave',{'p_marca':'ducart-disenos','p_nota':'Tools Asistime Ducart 625'});save()
    print('Clave emitida y guardada en configuración privada.')
    for table in ['disenos','fotos','plantillas','plantilla_pedidos','fotos_editadas','reels','publicaciones','motor_pedidos']:
        result=req('/rest/v1/'+table+'?select=*&limit=0',headers={'Accept-Profile':'ducart'});print(table,'OK')
