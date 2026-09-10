"""Procesa diseños y fotos de Larrique, uno nuevo de cada tipo por ciclo."""
import asyncio
import json
import os
from pathlib import Path
import sys

MARCA = 'larrique-disenos'
d = json.loads(Path('/run/credenciales.json').read_text())
os.environ.update(ANTHROPIC_API_KEY=d['ANTHROPIC_API_KEY'],
                  LIBRO_URL='https://qxjvtxumkljsroukpkny.supabase.co',
                  LIBRO_KEY=d['SUPABASE_KEY'], PUBLICAR='0', MAX_POR_CICLO='1')
os.environ['MAGNIFIC_CLAVE'] = d.get('MAGNIFIC_CLAVE', '')
sys.path.insert(0, '/app')
from app import chat, config, libro, fotero
from app.supa import Cliente
import requests

config.VERSION = 'hetzner-encuadre-v3-20260910'
cli = Cliente(MARCA, os.environ['LIBRO_URL'], d['SUPABASE_KEY'],
              bucket='disenos-larrique', nombre='Larrique', esquema='larrique')

async def main():
    pedidos = cli.leer_pedidos(1)
    cli.leer_pedidos = lambda limite: pedidos
    config.SALIDA.mkdir(parents=True, exist_ok=True)
    await libro_async()
    fotos_movidas = 0
    if os.environ['MAGNIFIC_CLAVE']:
        leer_fotos = fotero._pendientes
        # Un pedido nuevo por ciclo; las tareas ya enviadas se consultan todas.
        def acotadas(cliente, estado):
            filas = leer_fotos(cliente, estado)
            return filas[:1] if estado == 'pendiente' else filas
        fotero._pendientes = acotadas
        try:
            fotos_movidas = await asyncio.to_thread(fotero.atender, cli)
        finally:
            fotero._pendientes = leer_fotos
    else:
        print('Fotos: esperando clave Magnific; diseños siguen habilitados.', flush=True)
    print('Fotos actualizadas:', fotos_movidas, flush=True)
    await chat.atender(cli)
    errores = 0
    for pedido in pedidos:
        r = requests.get(cli._url('disenos'), headers=cli._cab(),
                         params={'id':'eq.'+pedido['id'], 'select':'id,estado'}, timeout=30)
        r.raise_for_status()
        filas=r.json()
        if len(filas)!=1 or filas[0]['estado']!='listo':
            errores += 1
        print('Pedido', pedido['id'], 'estado', filas[0]['estado'] if filas else 'ausente', flush=True)
    if not libro.latir(cli, disenos=len(pedidos)-errores, fotos=fotos_movidas, fotos_habilitadas=bool(os.environ["MAGNIFIC_CLAVE"])):
        raise RuntimeError('No se pudo registrar el latido.')
    if errores:
        raise RuntimeError('Un diseño no terminó listo; consultar su diagnóstico.')

async def libro_async():
    await asyncio.to_thread(libro.espejar_cargas, cli)

if __name__=='__main__':
    asyncio.run(main())
