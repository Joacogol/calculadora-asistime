#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""¿Un corte que cae en medio de una frase se corre a la pausa? ¿«Va todo» es todo?

    python3 herramientas/probar-cortes.py

Sale del reel del 7/9/2026: tres videos, «no cortar ninguna frase del final»,
y Gemini devolvió un tramo que terminaba en 5,00 s de un clip donde la última
palabra iba de 4,91 a 6,24. Dos arreglos, dos pruebas:

  1. `analisis.acomodar_al_habla` mide dónde hay voz y corre el corte a la
     pausa más cercana, con tope. El audio se FABRICA con ffmpeg: dos ráfagas
     de tono (1–3 s y 4–6 s) en ocho segundos de silencio.
  2. `mirar.quiere_todo` reconoce el pedido y `mirar.tramos_enteros` deja un
     tramo entero por archivo, en el orden del modelo, sin olvidar ninguno.
"""
import pathlib
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from motor import analisis, mirar  # noqa: E402

fallos = 0


def ok(c, que, det=None):
    global fallos
    print("  ✓" if c else "  ✗", que, "" if c or det is None else repr(det))
    fallos += 0 if c else 1


def fabricar(destino: pathlib.Path, dur: float, rafagas: str):
    """Video de prueba con tono sólo en las `rafagas` (expresión de ffmpeg)."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", f"testsrc2=size=320x240:rate=10:duration={dur}",
         "-f", "lavfi", "-i", f"aevalsrc=exprs='sin(440*2*PI*t)*0.6*({rafagas})':d={dur}:s=16000",
         "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(destino)],
        capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("ffmpeg falló: " + r.stderr[-600:])
    return destino


with tempfile.TemporaryDirectory() as tmp:
    t = pathlib.Path(tmp)
    corto = fabricar(t / "corto.mp4", 8, r"between(t\,1\,3)+between(t\,4\,6)")
    largo = fabricar(t / "largo.mp4", 14, r"between(t\,1\,3)+between(t\,4\,13)")

    print("\n■ Un corte en medio de una frase se corre a la pausa")
    d, h, c = analisis.acomodar_al_habla(corto, 0.0, 5.0)
    ok(5.9 <= h <= 6.5 and c, "final en 5,0 (dentro de la ráfaga 4–6) → va al final de la ráfaga", (d, h, c))
    ok(d == 0.0, "el arranque en 0 no se toca", d)
    d, h, c = analisis.acomodar_al_habla(corto, 0.0, 3.5)
    ok(h == 3.5 and not c, "final en 3,5 (pausa) queda como está", (h, c))
    d, h, c = analisis.acomodar_al_habla(corto, 4.6, 7.5)
    ok(3.4 <= d <= 4.1 and "arranque" in c, "arranque en 4,6 (dentro de la ráfaga) vuelve al principio de la ráfaga", (d, c))
    d, h, c = analisis.acomodar_al_habla(corto, 1.0, 8.0)
    ok(h == 8.0 and d == 1.0, "el final del archivo cuenta como pausa", (d, h, c))

    print("\n■ Con tope: correr cuatro segundos es acomodar, correr nueve es otra decisión")
    d, h, c = analisis.acomodar_al_habla(largo, 0.0, 5.0)
    ok(h == 5.0 and "lo dejé" in c, "final en 5,0 con la frase siguiendo 8 s más: se deja y se avisa", (h, c))
    d, h, c = analisis.acomodar_al_habla(largo, 0.0, 10.0)
    ok(12.9 <= h <= 13.5, "final en 10,0 con la pausa a 3 s: se corre", (h, c))

    print("\n■ Sin una sola pausa no hay frase que proteger")
    seguido = fabricar(t / "seguido.mp4", 6, "1")
    d, h, c = analisis.acomodar_al_habla(seguido, 1.0, 4.0)
    ok((d, h) == (1.0, 4.0) and not c, "un tono continuo deja el corte donde estaba", (d, h, c))

    print("\n■ Sin audio, se calla")
    mudo = t / "mudo.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(corto), "-an", "-c:v", "copy", str(mudo)], check=True)
    d, h, c = analisis.acomodar_al_habla(mudo, 0.0, 5.0)
    ok(h == 5.0 and not c, "un clip sin audio no se toca", (h, c))

print("\n■ «Va todo» se reconoce")
for frase, esp in (
        ("Reel con los tres videos enviados, usando absolutamente todo el contenido de cada video. "
         "No cortar ninguna frase del final, ni sacar nada.", True),
        ("Unir los videos y subtitular todo, sin cortar ninguna frase.", True),
        ("Ponelos enteros, uno atrás del otro", True),
        ("Reel de expectativa con las reacciones del equipo", False),
        ("Elegí lo mejor de estos seis clips, máximo 40 segundos", False),
        ("", False)):
    ok(mirar.quiere_todo(frase) is esp, f"{frase[:50]!r} → {esp}")

print("\n■ Todo es todo: un tramo entero por archivo, en el orden del modelo, sin olvidar ninguno")
pedazos = [{"archivo": "a.mp4", "indice": 1, "parte": 1, "duracion": 13.9, "desplazamiento": 0},
           {"archivo": "b.mp4", "indice": 2, "parte": 1, "duracion": 7.64, "desplazamiento": 0},
           {"archivo": "c.mp4", "indice": 3, "parte": 1, "duracion": 7.74, "desplazamiento": 0}]
elegidos = [{"archivo": "b.mp4", "desde": 0.83, "hasta": 5.0}, {"archivo": "a.mp4", "desde": 0.89, "hasta": 12.62}]
enteros = mirar.tramos_enteros(pedazos, elegidos)
ok([x["archivo"] for x in enteros] == ["b.mp4", "a.mp4", "c.mp4"], "orden del modelo, y el que no nombró al final", enteros)
ok(all(x["desde"] == 0.0 for x in enteros) and [x["hasta"] for x in enteros] == [7.64, 13.9, 7.74], "cada uno de punta a punta")

print("\n■ La pregunta cambia con el modo")
p = mirar.pregunta("no cortar nada", 60, pedazos, "Asistime", modo="todo")
ok("ORDENAR" in p and "ELEGIR" not in p.split("ORDENAR")[0], "con «todo» se le pide ordenar, no elegir")
p = mirar.pregunta("elegí lo mejor", 60, pedazos, "Asistime")
ok("ELEGIR" in p and "ORDENAR" not in p, "sin «todo», tres videos se eligen")

print()
if fallos:
    print(f"✗ {fallos} falla(s)")
    sys.exit(1)
print("✓ todo bien")
