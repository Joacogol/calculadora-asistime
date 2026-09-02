#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba que un fallo del proveedor llegue con el motivo puesto.

    python3 herramientas/probar-motivo.py

Sin red. Hasta el 2/9/2026 un reel fallado se guardaba como «Magnific devolvió
FAILED» y ahí se terminaba la historia: había que adivinar entre una foto fuera
de los límites, una duración que el modelo no hace, el moderador de contenido y
una caída del proveedor. Cuatro causas, cuatro arreglos distintos, cero datos.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

fallos = 0
def ok(c, que, det=None):
    global fallos
    print("  ✓" if c else "  ✗", que, "" if c or det is None else repr(det))
    fallos += 0 if c else 1

from app.reelero import motivo_de

print("\n■ Los nombres que usan los proveedores")
for campo in ("reason", "error", "message", "detail", "failure_reason",
              "moderation_reason"):
    ok(motivo_de({"status": "FAILED", campo: "la foto es muy chica"})
       == "la foto es muy chica", f"lo lee de `{campo}`")

print("\n■ Anidado, que es como lo manda media internet")
ok(motivo_de({"status": "FAILED", "error": {"message": "duración no soportada"}})
   == "duración no soportada", "entra a `error.message`")

print("\n■ Sin ningún nombre conocido: no se pierde igual")
m = motivo_de({"status": "FAILED", "codigo_raro": 77, "pista": "content policy"})
ok("content policy" in m and "codigo_raro" in m,
   "vuelca lo que haya en vez de callarse", m)
ok("status" not in m, "y no repite lo que ya sabíamos", m)

print("\n■ Cuando de verdad no dijo nada")
ok(motivo_de({"status": "FAILED"}) == "", "devuelve vacío, no inventa")
ok(motivo_de({"status": "FAILED", "generated": [], "error": None}) == "",
   "los campos vacíos no cuentan como motivo")

print("\n■ Cosas que no son diccionarios")
ok(motivo_de("se cayó todo") == "se cayó todo", "un texto pelado pasa igual")
ok(motivo_de(None) == "None", "y un None no revienta")

print("\n■ No se desborda")
largo = motivo_de({"status": "FAILED", "reason": "x" * 5000})
ok(len(largo) <= 300, "el motivo se recorta", len(largo))
vuelco = motivo_de({"status": "FAILED", "raro": "y" * 5000})
ok(len(vuelco) <= 300, "el volcado también", len(vuelco))

print("\n■ El contrato de estado_clip: tres cosas, siempre")
import app.reelero as reelero
casos = [
    ({"status": "FAILED", "reason": "content policy"}, "FAILED", None, "content policy"),
    ({"status": "PROCESSING"},                        "PROCESSING", None, ""),
    ({"status": "COMPLETED", "generated": ["u"]},     "COMPLETED", "u", ""),
]
guardado = reelero._pedir
try:
    for payload, e_esp, u_esp, m_esp in casos:
        reelero._pedir = lambda ruta, metodo=None, _p=payload: {"data": _p}
        est, url, mot = reelero.estado_clip("t", "seedance-2-mini", "720p")
        ok((est, url, mot) == (e_esp, u_esp, m_esp),
           f"{e_esp} -> ({e_esp}, {u_esp!r}, {m_esp!r})", (est, url, mot))
finally:
    reelero._pedir = guardado

print("\n■ Un COMPLETED no arrastra motivo aunque venga basura")
try:
    reelero._pedir = lambda r, metodo=None: {"data": {"status": "COMPLETED",
                                                      "generated": ["u"],
                                                      "message": "todo bien"}}
    ok(reelero.estado_clip("t", "seedance-2-mini", "720p")[2] == "",
       "el motivo es sólo para los fallos")
finally:
    reelero._pedir = guardado

print("\n", "todo bien" if not fallos else f"{fallos} fallo(s)")
sys.exit(1 if fallos else 0)
