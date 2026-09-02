#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba el encuadre por planos sin video y sin OpenCV.

    python3 herramientas/probar-encuadre.py

Las caras entran como listas por cuadro —lo mismo que devuelve el detector—
con el caso real del 2/9/2026: un plano de dos (caras al 20 % y al 60 %), una
reacción de 1,2 s en primer plano (66 %), otra vez el plano de dos, y el
primer plano largo (67 %). Lo que vigila: que los planos se corten donde
cambia el conjunto de caras, que el plano de dos se abra y el primer plano se
centre, que la reacción corta NO se trague, y que sin OpenCV los tramos
salgan como entraron.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

fallos = 0
def ok(c, que, det=None):
    global fallos
    print("  ✓" if c else "  ✗", que, "" if c or det is None else repr(det))
    fallos += 0 if c else 1

from motor import encuadre as e

W, H = 1280, 720
DOS = [(0.20, 0.07), (0.60, 0.075)]        # ella y el de lentes
UNO = [(0.66, 0.11)]                        # el tercero, en primer plano
def cuadros(caras, segundos): return [list(caras)] * int(segundos * e.FPS)

print("\n■ Los planos se cortan donde cambia el conjunto de caras")
caras = cuadros(DOS, 2.0) + cuadros(UNO, 1.2) + cuadros(DOS, 4.4) + cuadros(UNO, 18.0)
p = e.planos(caras)
ok(len(p) == 4, "cuatro planos", p)
ok([round((b - a) / e.FPS, 1) for a, b in p] == [2.0, 1.2, 4.4, 18.0], "con sus largos", p)

print("\n■ Un parpadeo del detector no es un plano")
ruido = cuadros(DOS, 2.0) + cuadros(UNO, 0.2) + cuadros(DOS, 2.0)
ok(len(e.planos(ruido)) == 1, "un cuadro suelto distinto no corta", e.planos(ruido))

print("\n■ Personas de un plano")
ok(len(e.personas(cuadros(DOS, 1))) == 2, "dos caras estables → dos personas")
mezcla = cuadros(DOS, 1) + cuadros([(0.21, 0.07)], 1)
ok(len(e.personas(mezcla)) == 2, "la misma cara corrida 1 % es la misma persona", e.personas(mezcla))

print("\n■ Decidir por plano")
foco, rec, motivo = e.decidir(UNO, W, H)
cw = e._ancho_recorte(rec, W, H)
centro = (1 - cw) * foco + cw / 2
ok(rec == e.RECORTE_BASE and abs(centro - 0.66) < 0.01, "una cara: recorte base centrado en la cara", (rec, centro))
foco, rec, motivo = e.decidir(DOS, W, H)
cw = e._ancho_recorte(rec, W, H); x0 = (1 - cw) * foco
ok(rec > e.RECORTE_BASE and x0 <= 0.20 - 0.07 * e.AIRE + 0.01 and x0 + cw >= 0.60 + 0.075 * e.AIRE - 0.01,
   "dos caras: se abre y entran las dos con aire", (rec, x0, x0 + cw))
ok(rec <= e.RECORTE_MAXIMO, "sin pasarse de 1:1", rec)
lejos = [(0.05, 0.06), (0.95, 0.12)]
foco, rec, motivo = e.decidir(lejos, W, H)
cw = e._ancho_recorte(rec, W, H); x0 = (1 - cw) * foco
ok(rec == e.RECORTE_BASE and "más grande" in motivo and x0 <= 0.95 <= x0 + cw,
   "no entran ni abriendo: va a la más grande (pegada al borde, pero adentro)", (rec, motivo, x0, x0 + cw))
ok(e.decidir([], W, H)[2] == "sin caras", "sin caras: centrado y lo dice")

print("\n■ Sub-tramos del caso real")
subs = e.subtramos(caras, 302.5, 328.0, W, H)
ok(len(subs) == 4, "la reacción de 1,2 s NO se traga: cuatro sub-tramos", [(s["desde"], s["hasta"], s["motivo"]) for s in subs])
ok(subs[0]["desde"] == 302.5 and subs[-1]["hasta"] == 328.0, "empieza y termina donde el tramo original")
ok(all(abs(subs[i]["hasta"] - subs[i + 1]["desde"]) < 1e-6 for i in range(len(subs) - 1)), "sin huecos ni solapes")
ok(subs[1]["recorte"] == e.RECORTE_BASE and subs[0]["recorte"] > e.RECORTE_BASE, "primer plano cerrado, plano de dos abierto")

print("\n■ Un plano corto SÍ se fusiona si el vecino ya lo contiene")
casi = cuadros(DOS, 3.0) + cuadros([(0.22, 0.07), (0.60, 0.075)], 1.0) + cuadros(DOS, 3.0)
subs2 = e.subtramos(casi, 0, 7.0, W, H)
ok(len(subs2) == 1, "la misma gente corrida 2 % no parte el tramo", [(s["desde"], s["hasta"]) for s in subs2])

print("\n■ Aplicar: lo que no se toca")
import motor.encuadre as me
guardado = me.disponible
try:
    me.disponible = lambda: False
    t = [{"archivo": "x.mp4", "desde": 0, "hasta": 5}]
    salida, avisos = me.aplicar(t, pathlib.Path("."))
    ok(salida == t, "sin OpenCV los tramos salen como entraron")
    ok(avisos and "no disponible" in avisos[0], "y avisa", avisos)
finally:
    me.disponible = guardado
me.disponible = lambda: True
try:
    t = [{"archivo": "no-existe.mp4", "desde": 0, "hasta": 5},
         {"archivo": "x.mp4", "desde": 0, "hasta": 5, "foco_x": 0.9},
         {"tipo": "placa", "archivo": "p.png"}]
    salida, _ = me.aplicar(t, pathlib.Path("."))
    ok(salida == t, "archivo inexistente, foco_x a mano y placas: intactos", salida)
finally:
    me.disponible = guardado

print("\n", "todo bien" if not fallos else f"{fallos} fallo(s)")
sys.exit(1 if fallos else 0)
