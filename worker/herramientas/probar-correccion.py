#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corregir una pieza es corregirla, no volver a hacerla.

    python3 herramientas/probar-correccion.py

El 5/9/2026 salió una story que al cliente le gustó y pidió UN cambio: «que la
jirafa arranque desde abajo sin que haya espacio». Volvió una pieza distinta —
otro fondo, otra tipografía, otro centrado, el logo encima de la cara— y hubo
que empezar de nuevo.

No fue desobediencia. El `spec.json` se escribía en un directorio temporal y
moría con el contenedor, así que **no había nada que corregir**: el pedido de
cambio entraba como un pedido nuevo y el agente rehacía todo desde el mensaje,
tomando decisiones nuevas cada vez.

Es el mismo problema que ya estaba resuelto para los reels —`ver_reel` +
`retocar_reel` sobre el guion guardado, con la regla «NUNCA vuelvas a llamar a
montar_reel para corregir»— y que para los diseños no existía.

Esta prueba cubre las dos mitades del arreglo: que el spec quede guardado, y
que un pedido con `corrige` le llegue al agente con ESE spec y la orden de no
tocar nada más.
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from app import disenador                                             # noqa: E402

fallos = []


def ok(caso, condicion, detalle=""):
    print(f"  {'✓' if condicion else '✗'} {caso}"
          + (f" — {str(detalle)[:200]}" if detalle and not condicion else ""))
    if not condicion:
        fallos.append(caso)


SPEC = {"nombre": "expectativa", "plantilla": "titular", "formato": "story",
        "data": {"titulo": "Algo grande\nse está por venir",
                 "estilo": "degrade", "alineacion": "izquierda",
                 "foto": "assets/banco/tony-asomandose.png",
                 "foco": "50% 100%"}}


class ClienteFalso:
    def __init__(self, previo):
        self.previo = previo

    def leer_diseno(self, _id):
        return self.previo


print("\n■ Un pedido normal no lleva bloque de corrección")
vacio = disenador._correccion(ClienteFalso(None), {"texto": "una placa"})
ok("sin `corrige`, no se agrega nada", vacio == "", vacio[:80])

print("\n■ Con `corrige` y spec guardado")
cli = ClienteFalso({"id": "abc", "mensaje": "Story de expectativa con Tony",
                    "spec": SPEC})
bloque = disenador._correccion(cli, {"corrige": "abc"})
ok("dice que es una corrección y no una pieza nueva",
   "CORRECCIÓN, NO UNA PIEZA NUEVA" in bloque)
ok("trae el spec anterior entero",
   '"plantilla": "titular"' in bloque and '"estilo": "degrade"' in bloque)
ok("y el encuadre medido de la foto", '"foco": "50% 100%"' in bloque)
# Se busca por trozos que no cruzan el corte de línea: el bloque va envuelto
# a 76 columnas y una frase larga se parte donde el texto la parta.
ok("prohíbe cambiar lo que no se pidió",
   "esté en el pedido" in bloque
   and "se copia tal cual" in bloque
   and "No lo rehagas" in bloque)
ok("cuenta de dónde viene la pieza",
   "Story de expectativa con Tony" in bloque)

print("\n■ Con `corrige` pero sin spec (una pieza vieja)")
# Este caso NO puede pasar en silencio: el agente tiene que saber que hay algo
# que respetar aunque no pueda verlo, y avisarle a la persona que puede salir
# distinta. Creer que empieza de cero es lo que rompió la pieza que gustaba.
bloque = disenador._correccion(
    ClienteFalso({"id": "abc", "mensaje": "algo", "spec": None}),
    {"corrige": "abc"})
ok("avisa que es una corrección igual", "CORRECCIÓN" in bloque)
ok("y que la pieza puede salir distinta", "distinta" in bloque, bloque[:120])

print("\n■ El spec cabe en el prompt")
grande = {"trabajos": [SPEC] * 40}
bloque = disenador._correccion(
    ClienteFalso({"id": "abc", "mensaje": "x", "spec": grande}), {"corrige": "abc"})
ok("un spec enorme se recorta y no revienta el prompt", len(bloque) < 14000, len(bloque))

print()
if fallos:
    print(f"  ✗ {len(fallos)} fallo(s)")
    raise SystemExit(1)
print("  todo bien")
