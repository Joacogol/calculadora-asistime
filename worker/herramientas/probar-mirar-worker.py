#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba cuándo el worker le pide a Gemini que mire, y qué hace con la respuesta.

    python3 herramientas/probar-mirar-worker.py

Sin red. Lo que vigila: que sin instrucción o sin clave no se llame a nadie;
que material que ya entra entero en el reel tampoco; que con material largo
los tramos elegidos entren al guion con el gancho y una nota que explique
qué se hizo; y que si Gemini falla el guion quede como estaba y la nota
diga por qué.
"""
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

fallos = 0
def ok(c, que, det=None):
    global fallos
    print("  ✓" if c else "  ✗", que, "" if c or det is None else repr(det))
    fallos += 0 if c else 1

from app import reelero
from motor import mirar as mmirar, analisis as man

tmp = pathlib.Path(tempfile.mkdtemp(prefix="mirar-worker-"))
(tmp / "charla.mp4").write_bytes(b"x")
(tmp / "corto.mp4").write_bytes(b"x")
CLIPS = [{"url": "https://x/charla.mp4"}, {"url": "https://x/corto.mp4"}]
NOMBRES = {"https://x/charla.mp4": "charla.mp4", "https://x/corto.mp4": "corto.mp4"}
DURACIONES = {"charla.mp4": 3600.0, "corto.mp4": 20.0}
g_sondear = man.sondear
man.sondear = lambda ruta: {"duracion": DURACIONES[pathlib.Path(ruta).name], "ancho": 1920, "alto": 1080}
llamadas = []
def _elegir_ok(archivos, instruccion, objetivo, carpeta=None, modelo=None, marca=""):
    llamadas.append((sorted(a.name for a in archivos), instruccion, objetivo))
    return {"tramos": [{"archivo": "charla.mp4", "desde": 304.5, "hasta": 328.0, "por_que": "x"}],
            "gancho": "Están viendo cosas que nosotros hoy no",
            "palabras": ["pádel", "Yayo"], "avisos": [], "uso": {"total_tokens": 28721},
            "segundos": 48.0, "modelo": "gemini-3.7-flash"}
g_elegir, g_disp = mmirar.elegir_tramos, mmirar.disponible
try:
    mmirar.elegir_tramos = _elegir_ok
    mmirar.disponible = lambda: True

    print("\n■ Sin instrucción ni mensaje: se mira igual, con el encargo estándar")
    g, nota = reelero._mirar_si_hace_falta({}, {"mensaje": ""}, CLIPS, NOMBRES, tmp)
    ok(llamadas and "mejor reel" in llamadas[-1][1] and "Pedido" not in llamadas[-1][1],
       "se llama con la instrucción estándar, sin un «Pedido» vacío", llamadas[-1][1] if llamadas else None)
    llamadas.clear()

    print("\n■ Sin clave no se llama a nadie, y no es un error")
    mmirar.disponible = lambda: False
    g, nota = reelero._mirar_si_hace_falta({"instruccion": "lo más fuerte"}, {}, CLIPS, NOMBRES, tmp)
    ok(g == {"instruccion": "lo más fuerte"} and nota == "" and not llamadas, "sigue como hasta hoy, callado")
    mmirar.disponible = lambda: True

    print("\n■ Material que entra entero: se mira igual, para LIMPIAR")
    g, nota = reelero._mirar_si_hace_falta({"instruccion": "x", "duracion_objetivo": 30},
                                          {}, CLIPS[1:], NOMBRES, tmp)
    ok(llamadas and llamadas[-1][0] == ["corto.mp4"], "20 s para un reel de 30: se llama igual", llamadas)
    llamadas.clear()

    print("\n■ Sin instrucción: se arma una con el mensaje del pedido")
    g, nota = reelero._mirar_si_hace_falta({}, {"mensaje": "reel del webinar"}, CLIPS[1:], NOMBRES, tmp)
    ok(llamadas and "reel del webinar" in llamadas[-1][1] and "mejor reel" in llamadas[-1][1],
       "instrucción estándar + el mensaje", llamadas[-1][1] if llamadas else None)
    llamadas.clear()

    print("\n■ Unos segundos de material: no hay nada que cortar")
    DURACIONES["corto.mp4"] = 5.0
    g, nota = reelero._mirar_si_hace_falta({"instruccion": "x"}, {}, CLIPS[1:], NOMBRES, tmp)
    ok(nota == "" and not llamadas, "5 s: no se llama", (nota, llamadas))
    DURACIONES["corto.mp4"] = 20.0

    print("\n■ Material largo con instrucción: Gemini elige")
    g, nota = reelero._mirar_si_hace_falta({"instruccion": "lo más fuerte sobre IA", "hook": ""},
                                          {"mensaje": "otra cosa"}, CLIPS, NOMBRES, tmp)
    ok(llamadas and llamadas[-1] == (["charla.mp4", "corto.mp4"], "lo más fuerte sobre IA", 60.0),
       "se llama con los dos archivos, la instrucción del guion y 60 s por defecto", llamadas)
    ok(g["tramos"] == [{"archivo": "charla.mp4", "desde": 304.5, "hasta": 328.0, "por_que": "x"}], "los tramos entran al guion")
    ok(g["hook"] == "Están viendo cosas que nosotros hoy no", "el gancho llena el hook vacío")
    ok(g["duracion_objetivo"] == 60.0, "y el objetivo queda escrito para que el motor acorte si hace falta")
    # Las palabras que Gemini oyó viajan en el guion hasta el transcriptor, y
    # quedan guardadas ahí para que un retoque posterior las tenga sin volver
    # a pagar una mirada.
    ok(g["vocabulario"] == ["pádel", "Yayo"], "las palabras del video quedan en el guion", g.get("vocabulario"))
    ok("28721" in nota and "1 tramo" in nota and "60 min" in nota, "la nota cuenta qué pasó", nota)

    print("\n■ La instrucción sale del mensaje si el guion no la trae; el hook escrito manda")
    g, nota = reelero._mirar_si_hace_falta({"hook": "Mi frase", "duracion_objetivo": 45},
                                          {"mensaje": "un reel sobre IA"}, CLIPS, NOMBRES, tmp)
    ok("«un reel sobre IA»" in llamadas[-1][1] and llamadas[-1][2] == 45.0, "el mensaje entra en la instrucción, 45 s", llamadas[-1])
    ok(g["hook"] == "Mi frase", "no pisa un hook escrito a mano")

    print("\n■ Gemini falla: el guion queda como estaba y la nota lo dice")
    def _falla(*a, **k): raise mmirar.NoPudeMirar("HTTP 429: cuota")
    mmirar.elegir_tramos = _falla
    antes = {"instruccion": "x"}
    g, nota = reelero._mirar_si_hace_falta(dict(antes), {}, CLIPS, NOMBRES, tmp)
    ok(g == antes, "guion intacto")
    ok("429" in nota and "corté por audio" in nota, "la nota explica", nota)
finally:
    mmirar.elegir_tramos, mmirar.disponible = g_elegir, g_disp
    man.sondear = g_sondear
    import shutil; shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("GEMINI_CLAVE", None)

print("\n", "todo bien" if not fallos else f"{fallos} fallo(s)")
sys.exit(1 if fallos else 0)
