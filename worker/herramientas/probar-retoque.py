#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""El retoque: que entre donde tiene que entrar y que rebote lo que rompe.

    python3 herramientas/probar-retoque.py
"""
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from motor import cargador, carrusel as mcarrusel, retoque   # noqa: E402

fallos = 0


def ok(c, que, det=None):
    global fallos
    print("  ✓" if c else "  ✗", que, "" if c or det is None else str(det)[:300])
    fallos += 0 if c else 1


print("\n■ Lo que rompe el mecanismo, rebota con el motivo")
for malo, esperado in (
    ("a{}</style><script>alert(1)</script>", "escapa"),
    ("@import url(otra.css)", "afuera"),
    (".a{background:url(https://ejemplo.com/x.png)}", "internet"),
    (".a{background:url(//ejemplo.com/x.png)}", "internet"),
    (".a{position:fixed;top:0}", "lienzo"),
    (".a{color:red}" * 400, "tope"),
):
    try:
        retoque.revisar(malo)
        ok(False, f"rechaza «{malo[:28]}…»")
    except retoque.RetoqueInvalido as e:
        ok(esperado in str(e), f"rechaza «{malo[:28]}…» y dice por qué", e)

print("\n■ Lo que sí es un retoque, pasa")
ok(retoque.revisar("") == "", "vacío es vacío, no un error")
# Un SVG embebido es la forma natural de dibujar un marco, y no sale a la red.
marco = '.disp{border-image:url("data:image/svg+xml,<svg xmlns=\'http://www.w3.org/2000/svg\'/>") 30}'
ok(retoque.revisar(marco) == marco, "un SVG en data: no es internet")
ok("retoque de esta pieza" in retoque.hoja({"retoque": ".a{color:red}"}),
   "la hoja va comentada, para saber qué parte es de la marca")
ok(retoque.hoja({}) == "" and retoque.hoja(None) == "", "sin retoque no agrega nada")

print("\n■ En una pieza de verdad")
m = cargador.cargar_marca(RAIZ / ".claude/skills/asistime-disenos")
d = {"titulo": "Se viene el invierno", "retoque": ".disp{border:14px solid #B45309}"}
html = m.PLANTILLAS["titular"](d, "vert")
ok(".disp{border:14px solid #B45309}" in html, "el retoque entra en la pieza")
# Después de la hoja de la marca: si fuera antes, la plantilla lo pisaría y el
# retoque no serviría para nada.
ok(html.index("border:14px solid #B45309") > html.index("font-family"),
   "y va DESPUÉS de la hoja de la marca, para poder pisarla")
ok("retoque" not in m.PLANTILLAS["titular"]({"titulo": "sin nada"}, "vert"),
   "una pieza sin retoque sale exactamente como antes")

print("\n■ En una diapositiva de carrusel")
carr = {"slides": [
    {"tipo": "portada", "titulo": "Con marco", "retoque": ".disp{outline:9px dotted #B362FF}"},
    {"tipo": "cierre"}]}
pags = mcarrusel.paginas(m, carr, "vert")
ok(".disp{outline:9px dotted #B362FF}" in pags[0], "la diapositiva lleva el suyo")
ok("outline:9px dotted" not in pags[1], "y no se le pega a las demás", pags[1][:0])

print("\n", "todo bien" if not fallos else f"{fallos} fallo(s)")
sys.exit(1 if fallos else 0)
