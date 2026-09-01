#!/usr/bin/env python3
"""Saca del Dockerfile la basura que quedó arriba del `FROM`.

    python3 herramientas/limpiar-dockerfile.py

## Por qué existe

El 1/9/2026 un despliegue falló con:

    dockerfile parse error line 1: unknown instruction: ≈≈

La primera línea del Dockerfile decía `≈≈`. Nadie escribió eso a propósito: en
un Mac `Option+X` produce `≈`, y buscando el `Ctrl+X` que cierra nano se
escribieron dos dentro del archivo, que después se guardó.

Es un error de dos caracteres y costó un build entero de cinco minutos para
enterarse, con un mensaje que no dice de dónde salieron. Esto lo saca en un
segundo, y `desplegar-chat.sh` lo revisa antes de construir nada.

Sólo toca lo que hay ANTES del primer `FROM`, y sólo si no es un comentario,
un `ARG` o una línea en blanco — que es lo único que Docker permite ahí.
"""
import pathlib
import shutil
import sys

#: Lo único que Docker acepta antes del primer `FROM`.
def _legitima(linea: str) -> bool:
    s = linea.strip()
    return not s or s.startswith("#") or s.upper().startswith("ARG ")


def main() -> int:
    ruta = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                        else pathlib.Path.home() / "worker" / "Dockerfile")
    if not ruta.exists():
        print(f"✗ No encuentro {ruta}")
        return 1

    lineas = ruta.read_text().splitlines(keepends=True)
    corte = next((i for i, l in enumerate(lineas)
                  if l.strip().upper().startswith("FROM ")), None)
    if corte is None:
        print("✗ Este Dockerfile no tiene ninguna línea `FROM`. No lo toco.")
        return 1

    basura = [(i, l) for i, l in enumerate(lineas[:corte]) if not _legitima(l)]
    if not basura:
        print("✓ El Dockerfile arranca bien. No hay nada que limpiar.")
        return 0

    shutil.copy(ruta, str(ruta) + ".sucio")
    for i, l in basura:
        print(f"  saco la línea {i+1}: {l.rstrip()!r}")
    quedan = [l for i, l in enumerate(lineas) if i >= corte or _legitima(l)]
    ruta.write_text("".join(quedan))
    print(f"✓ Listo: saqué {len(basura)} "
          f"{'línea' if len(basura) == 1 else 'líneas'} de arriba del `FROM`.")
    print(f"  El archivo de antes quedó en {ruta}.sucio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
