# -*- coding: utf-8 -*-
"""Lanzador: renderiza las piezas de Boss Padel.

    python3 render.py spec.json [carpeta-de-salida]

El comando es el mismo de siempre a propósito. El código de verdad vive en
`motor/`, compartido con las demás marcas: acá sólo se le dice al motor qué
marca usar y dónde están sus materiales.
"""
import pathlib
import sys

AQUI = pathlib.Path(__file__).resolve().parent
# .../worker/.claude/skills/boss-padel-disenos → .../worker
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parents[2]))

import marca                                    # noqa: E402
from motor import render as motor_render        # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    motor_render.desde_linea_de_comandos(marca, AQUI, sys.argv)
