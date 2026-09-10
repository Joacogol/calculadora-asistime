#!/usr/bin/env python3
"""Carga interactiva de credenciales; no ejecuta pedidos ni llama a APIs."""
import base64
import getpass
import json
import os
from pathlib import Path
import tempfile

DESTINO = Path('/opt/asistime-disenador/config/credenciales.json')


def main():
    os.umask(0o077)
    actual = json.loads(DESTINO.read_text()) if DESTINO.exists() else {}
    print('Configuración del diseñador de Larrique en Hetzner')
    print('Las claves no se muestran al escribir y no van al historial.')
    print('Si ya hay una clave guardada, Enter la conserva. Ctrl+C cancela.')
    anthropic = getpass.getpass('1/2 Clave API de Anthropic: ').strip()
    anthropic = anthropic or actual.get('ANTHROPIC_API_KEY', '')
    if not anthropic.startswith('sk-ant-') or len(anthropic) < 30:
        raise ValueError('La clave de Anthropic no tiene el formato esperado.')
    supabase = getpass.getpass('2/2 Clave service_role de Supabase asistime-disenos: ').strip()
    supabase = supabase or actual.get('SUPABASE_KEY', '')
    try:
        fragmento = supabase.split('.')[1]
        payload = json.loads(base64.urlsafe_b64decode(fragmento + '=' * (-len(fragmento) % 4)))
    except Exception:
        raise ValueError('Se necesita la clave JWT service_role, no la anon ni la contraseña.') from None
    if payload.get('role') != 'service_role' or payload.get('ref') != 'qxjvtxumkljsroukpkny':
        raise ValueError('La clave no corresponde al rol service_role del proyecto asistime-disenos.')
    actual.update(ANTHROPIC_API_KEY=anthropic, SUPABASE_KEY=supabase)
    DESTINO.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporal = tempfile.mkstemp(dir=DESTINO.parent, prefix='.credenciales-')
    try:
        with os.fdopen(fd, 'w') as salida:
            json.dump(actual, salida)
            salida.flush()
            os.fsync(salida.fileno())
        os.replace(temporal, DESTINO)
    finally:
        if os.path.exists(temporal):
            os.unlink(temporal)
    print('Claves guardadas con permisos privados. No se ejecutó ningún pedido.')
    print('Avisale a Codex que terminaste para validar conexiones y probar Larrique.')


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\nCancelado. No se guardaron cambios.')
        raise SystemExit(1)
    except ValueError as error:
        print(f'No se guardaron cambios: {error}')
        raise SystemExit(1)
