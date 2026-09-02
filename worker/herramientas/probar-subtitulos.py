#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba que ningún subtítulo termine después de que el reel terminó.

    python3 herramientas/probar-subtitulos.py

Sin Whisper: se le dan a `para_guion` las palabras ya transcritas. El caso es
una frase CORTA al final del último tramo. `frases()` la estira hacia adelante
para que se pueda leer (MIN_SEGUNDOS), y cuando es la última no tiene una
frase siguiente que la frene: se pasa del final del reel. El validador lo
rechaza y el reel entero muere —pasó el 2/9/2026 con el clip de YouTube:
«termina en 26.1s pero el reel dura 25.6s»—.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

fallos = 0
def ok(c, que, det=None):
    global fallos
    print("  ✓" if c else "  ✗", que, "" if c or det is None else repr(det))
    fallos += 0 if c else 1

from motor import habla

PALABRAS = [
    {"texto": "Claramente", "desde": 10.0, "hasta": 10.6},
    {"texto": "ellos", "desde": 10.6, "hasta": 10.9},
    {"texto": "están", "desde": 10.9, "hasta": 11.3},
    {"texto": "en", "desde": 11.3, "hasta": 11.4},
    {"texto": "modelos", "desde": 11.4, "hasta": 11.9},
    {"texto": "más", "desde": 11.9, "hasta": 12.1},
    {"texto": "adelantados.", "desde": 12.1, "hasta": 12.9},
    # una pausa y una frase de dos palabras justo al final del tramo
    {"texto": "Este", "desde": 14.5, "hasta": 14.7},
    {"texto": "pitch.", "desde": 14.7, "hasta": 14.9},
]
habla.palabras = lambda ruta, voc="": PALABRAS
base = pathlib.Path(__file__).resolve().parent          # existe: alcanza para que `ruta.exists()` dé True
guion = {"tramos": [{"archivo": "probar-subtitulos.py", "desde": 10.0, "hasta": 15.0}]}

print("\n■ Una frase corta al final del reel")
fr = habla.para_guion(guion, base)
dura = 5.0
ultima = max(f["hasta"] for f in fr)
ok(fr, "salen subtítulos", fr)
ok(ultima <= dura + 1e-6, f"el último termina a los {ultima:.2f}s, dentro de los {dura:.0f}s del reel", ultima)
ok(all(f["desde"] < dura for f in fr), "ninguno empieza después del final")
ok(all(f["hasta"] > f["desde"] for f in fr), "y todos duran algo")

print("\n■ Con dos tramos, el reloj es el del reel montado")
guion2 = {"tramos": [{"archivo": "probar-subtitulos.py", "desde": 10.0, "hasta": 12.0},
                     {"archivo": "probar-subtitulos.py", "desde": 14.0, "hasta": 15.0}]}
fr2 = habla.para_guion(guion2, base)
ok(max(f["hasta"] for f in fr2) <= 3.0 + 1e-6, "termina dentro de los 3s del reel", max(f["hasta"] for f in fr2))

print("\n", "todo bien" if not fallos else f"{fallos} fallo(s)")
sys.exit(1 if fallos else 0)
