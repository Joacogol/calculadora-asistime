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

print("\n■ Reconocer que lo bloqueado fue el audio y no el video")
from app.reelero import bloquearon_el_audio
REAL = ("422 - Task failed. Error: Invalid request to service seedance-2-0-mini. "
        "Status: 422. Error: {\"moderation\": {\"block_reasons\": [{\"label\": "
        "\"Copyright\", \"detail\": \"Potential copyright restriction.\"}]}, "
        "\"error\": {\"message\": \"The request failed because the output audio "
        "may be related to copyright restrictions.\"}, \"code\": "
        "\"OutputAudioSensitiveContentDetected.PolicyViolation\"}")
ok(bloquearon_el_audio(REAL), "el fallo real del 2/9/2026 se reconoce")
ok(bloquearon_el_audio("code: outputaudiosensitivecontentdetected.policyviolation"),
   "no le importan las mayúsculas")
for otro in ("la foto es muy chica", "duration 3 not supported", "", None,
             "NSFW content detected in the output video"):
    ok(not bloquearon_el_audio(otro), f"no confunde {otro!r} con esto")

print("\n■ El pedido callado")
import app.reelero as reelero
enviado = {}
def _espia(ruta, cuerpo=None, metodo="POST"):
    enviado.clear(); enviado.update({"ruta": ruta, **(cuerpo or {})})
    return {"data": {"task_id": "t-nueva"}}
FILA = {"foto": "https://f/1.jpg", "mensaje": "x", "titulo": "t"}
PLAN = {"modelo": "seedance-2-mini", "duracion": 10, "resolucion": "720p"}
guardado = reelero._pedir
try:
    reelero._pedir = _espia
    reelero.pedir_clip(FILA, PLAN, [{"duration": 10, "prompt": "un plano"}])
    ok(enviado.get("sound_effects") is True, "el pedido normal pide audio", enviado.get("sound_effects"))
    ok("no_music" not in enviado, "y a Mini no le manda `no_music`")

    reelero.pedir_clip({**FILA, "metricas": {"sin_audio": True}}, PLAN, [{"duration": 10, "prompt": "un plano"}])
    ok(enviado.get("sound_effects") is False, "el reintento lo pide callado", enviado.get("sound_effects"))
    ok(enviado.get("no_music") is True, "y le manda `no_music` por si lo entiende")
finally:
    reelero._pedir = guardado

print("\n■ Un solo reintento, nunca un bucle")
from app.reelero import que_hacer_con_fallo
BASE = {"id": "r1", "tarea": "t-1", "modelo": "seedance-2-mini", "resolucion": "720p"}

e, c = que_hacer_con_fallo(dict(BASE), "FAILED", REAL)
ok(e == "pendiente", "el primer bloqueo de audio vuelve a la cola", e)
ok(c["metricas"].get("sin_audio") is True, "marcado para pedirse callado", c["metricas"])
ok(c["tarea"] is None, "y sin la tarea vieja colgada")
ok("bloqueó la música" in c["notas"], "la nota explica qué pasó", c["notas"])

e, c = que_hacer_con_fallo({**BASE, "metricas": {"sin_audio": True}}, "FAILED", REAL)
ok(e == "error", "el segundo ya es error, no otro reintento", e)

e, c = que_hacer_con_fallo({**BASE, "metricas": {"guion": {"calidad": "normal"}}},
                           "FAILED", REAL)
ok(c["metricas"].get("guion") == {"calidad": "normal"},
   "el reintento conserva el guión: no se vuelve a pagar el texto", c["metricas"])

e, c = que_hacer_con_fallo(dict(BASE), "FAILED", "la foto es muy chica")
ok(e == "error", "otro motivo no reintenta", e)
ok("muy chica" in c["notas"], "y el motivo llega a las notas", c["notas"])

e, c = que_hacer_con_fallo(dict(BASE), "FAILED", "")
ok(e == "error" and "no dijo por qué" in c["notas"],
   "sin motivo, la nota lo dice en vez de mentir", c["notas"])

e, c = que_hacer_con_fallo({**BASE, "modelo": "h3-max"}, "ERROR", "se cayó")
ok("fal devolvió ERROR" in c["notas"],
   "nombra al proveedor que falló, no siempre a Magnific", c["notas"])

print("\n", "todo bien" if not fallos else f"{fallos} fallo(s)")
sys.exit(1 if fallos else 0)
