# -*- coding: utf-8 -*-
"""Lanzador: renderiza las piezas de Clínica Preventiva.

    python3 render.py spec.json [carpeta-de-salida]
"""
import pathlib, sys
AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI)); sys.path.insert(0, str(AQUI.parents[2]))
import marca                                 # noqa: E402
from motor import render as motor_render     # noqa: E402
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); raise SystemExit(1)
    motor_render.desde_linea_de_comandos(marca, AQUI, sys.argv)
