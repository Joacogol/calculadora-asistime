#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ningún nombre sin definir en el motor ni en el worker.

    python3 herramientas/probar-nombres.py

Es la prueba más barata que existe y encontró dos bugs reales el 2/9/2026:
una foto con texto moría con NameError (`marco_png` copiado de otra función)
y un montaje con correcciones aprendidas moría con UnboundLocalError
(`_habla` usado antes del import local). Ninguno de los dos se veía hasta
que se daba el caso, y el caso era raro pero real.
"""
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
archivos = sorted(str(p) for d in ("motor", "app") for p in (RAIZ / d).rglob("*.py"))
r = subprocess.run([sys.executable, "-m", "pyflakes", *archivos], capture_output=True, text=True)
malos = [l for l in r.stdout.splitlines() if "undefined name" in l or "used before assignment" in l]
for l in malos:
    print("  ✗", l)
print("  ✓ sin nombres indefinidos" if not malos else f"\n {len(malos)} nombre(s) sin definir")
sys.exit(1 if malos else 0)
