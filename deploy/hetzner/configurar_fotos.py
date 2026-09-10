#!/usr/bin/env python3
"""Añade la clave de fotos sin modificar las credenciales existentes."""
import getpass
import json
import os
from pathlib import Path
import tempfile

DESTINO = Path('/opt/asistime-disenador/config/credenciales.json')

def main():
    os.umask(0o077)
    actual = json.loads(DESTINO.read_text())
    print('Edición de fotos de Larrique en Hetzner')
    print('La clave queda oculta. Enter conserva la existente; Ctrl+C cancela.')
    print('Al guardar, el servicio podrá procesar las fotos pendientes de Larrique.')
    clave = getpass.getpass('Clave API de Magnific: ').strip()
    clave = clave or actual.get('MAGNIFIC_CLAVE', '')
    if len(clave) < 16 or any(c.isspace() for c in clave):
        raise ValueError('La clave parece incompleta o contiene espacios. No se guardó.')
    actual['MAGNIFIC_CLAVE'] = clave
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
    print('Clave guardada con permisos privados. Avisale a Codex para verificar el resultado.')

if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\nCancelado. No se guardaron cambios.')
        raise SystemExit(1)
    except ValueError as error:
        print(error)
        raise SystemExit(1)
