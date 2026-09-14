"""Ejecuta las colas compartidas exclusivamente para Ducart."""
import asyncio
import json
import os
import sys
from pathlib import Path

secrets = json.loads(Path('/run/credenciales.json').read_text())
propios = json.loads(Path('/run/ducart.json').read_text())
os.environ.update(ANTHROPIC_API_KEY=secrets['ANTHROPIC_API_KEY'],
                  LIBRO_URL='https://qxjvtxumkljsroukpkny.supabase.co',
                  LIBRO_KEY=secrets['SUPABASE_KEY'],
                  ASISTIME_CLAVE_DUCART=propios['ASISTIME_CLAVE_DUCART'],
                  MAGNIFIC_CLAVE=secrets.get('MAGNIFIC_CLAVE', ''),
                  MAX_POR_CICLO='1', MAX_PUBLICACIONES='1',
                  MODELO_PLANTILLERO='claude-sonnet-4-5',
                  MODELO_CORRECTOR='claude-sonnet-4-5',
                  MODELO_MOTORISTA='claude-sonnet-4-5',
                  PUBLICAR='1', MOTORISTA='1', SALIDA='/tmp/piezas')
sys.path.insert(0, '/app')
from app import config, chat

config.VERSION = 'ducart-20260914-v5-flujo-v5'
config.clientes = lambda: [{
    'marca':'ducart-disenos', 'nombre':'Ducart Latin America',
    'url':os.environ['LIBRO_URL'], 'key':secrets['SUPABASE_KEY'],
    'bucket':'disenos-ducart', 'esquema':'ducart',
}]
config.SALIDA.mkdir(parents=True, exist_ok=True)
if __name__ == '__main__':
    asyncio.run(chat.ciclo())
