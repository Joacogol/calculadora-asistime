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

print("\n■ Una frase corta no se pega hacia atrás por encima de un punto")
PALABRAS2 = [
    {"texto": "Vi", "desde": 0.0, "hasta": 0.2}, {"texto": "lo", "desde": 0.2, "hasta": 0.3},
    {"texto": "que", "desde": 0.3, "hasta": 0.4}, {"texto": "me", "desde": 0.4, "hasta": 0.5},
    {"texto": "mostraste.", "desde": 0.5, "hasta": 1.0},
    {"texto": "Panchi,", "desde": 1.2, "hasta": 1.6},
    {"texto": "¿viste", "desde": 1.7, "hasta": 2.0}, {"texto": "al", "desde": 2.0, "hasta": 2.1},
    {"texto": "diseñador?", "desde": 2.1, "hasta": 2.8},
]
habla.palabras = lambda ruta, voc="": PALABRAS2
fr3 = habla.para_guion({"tramos": [{"archivo": "probar-subtitulos.py", "desde": 0.0, "hasta": 3.0}]}, base)
textos = [f["texto"] for f in fr3]
ok(not any(t.startswith("Vi lo que me mostraste. Panchi") for t in textos),
   "«Panchi,» no se pega a la frase cerrada", textos)
ok(any(t.startswith("Panchi, ¿viste") for t in textos), "va con la frase siguiente, que es la suya", textos)
print("\n■ Una pausa en medio de una frase no corta después de «la»")
#
# Medido sobre el reel de Bauti el 3/9/2026: el chico duda un segundo y medio
# entre «¡Opa! La» y «pelota», y el subtítulo salía partido ahí — un renglón
# entero terminado en «La», que no dice nada solo.
pals = [{"texto": "¡Opa!", "desde": 14.84, "hasta": 15.6},
        {"texto": "La", "desde": 15.9, "hasta": 16.46},
        {"texto": "pelota,", "desde": 17.98, "hasta": 18.6},
        {"texto": "la", "desde": 18.6, "hasta": 18.9},
        {"texto": "que", "desde": 18.9, "hasta": 19.2},
        {"texto": "la", "desde": 19.2, "hasta": 19.5},
        {"texto": "pegó.", "desde": 19.5, "hasta": 19.76}]
sal = [f["texto"] for f in habla.frases(pals)]
ok(not any(t.rstrip().lower().endswith(" la") or t.strip().lower() == "la" for t in sal),
   "ninguna línea termina en «la»", sal)
ok("La pelota," in " ".join(sal), "«La» viaja con «pelota»", sal)

# Y lo contrario tiene que seguir valiendo: «Sí.» es una frase entera aunque
# «si» esté en la lista de palabras débiles, así que ahí sí se corta.
sal = [f["texto"] for f in habla.frases(
    [{"texto": "Sí.", "desde": 5.7, "hasta": 6.0},
     {"texto": "¿En", "desde": 7.0, "hasta": 7.2},
     {"texto": "serio?", "desde": 7.2, "hasta": 7.6}])]
ok(sal == ["Sí.", "¿En serio?"], "una pausa después de un punto sigue cortando", sal)

print("\n", "todo bien" if not fallos else f"{fallos} fallo(s)")
sys.exit(1 if fallos else 0)
