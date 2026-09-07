#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba el cliente de `probar-gemini-video.py` sin llamar a Google.

    python3 herramientas/probar-gemini-cliente.py

No mide nada de Gemini: mide que el pedido salga bien armado y que la
respuesta se lea. Existe porque el script se rompió tres veces seguidas en
cosas que no tienen que ver con el video:

1. leyó el registro por la variable de entorno, que en Cloud Shell no está;
2. trató un 429 —cuota agotada— como un 503, e insistió gastando cupo;
3. **le pasó el timeout como CUERPO del pedido**, porque el segundo argumento
   posicional de `urlopen` es `data` y no `timeout`.

El tercero es el que explica por qué esto existe: la sonda pasaba el timeout
por nombre y andaba, así que el camino probado funcionaba y el que gastaba
plata no. Se descubrió con las cuatro llamadas ya pagas.
"""
import importlib.util
import json
import pathlib
import sys
import types

RAIZ = pathlib.Path(__file__).resolve().parents[1]
fallos = 0


def ok(condicion, titulo, detalle=""):
    global fallos
    print(f"  {'✓' if condicion else '✗'} {titulo} {detalle if not condicion else ''}")
    if not condicion:
        fallos += 1


enviados = []


class _R:
    def __init__(self, datos):
        self._d, self.status_code, self.text = datos, 200, json.dumps(datos)

    def json(self):
        return self._d

    def read(self):
        return json.dumps(self._d).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _urlopen(pedido, *args, **kw):
    enviados.append({"url": pedido.full_url, "data": pedido.data,
                     "headers": dict(pedido.headers), "args": args, "kw": kw})
    return _R({"candidates": [{"content": {"parts": [{"text": "listo"}]}}]})


falso = types.ModuleType("urllib.request")
falso.urlopen = _urlopen
falso.Request = __import__("urllib.request").request.Request

_spec = importlib.util.spec_from_file_location(
    "gem", RAIZ / "herramientas" / "probar-gemini-video.py")
gem = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gem)
gem.urllib.request.urlopen = _urlopen

print("El pedido con video")
r = gem.preguntar("clave-x", b"\x00\x01BYTES", "video/mp4", "¿qué se ve?",
                  "agentic", "gemini-3.7-flash")
p = enviados[-1]
cuerpo = json.loads(p["data"])

ok(isinstance(p["data"], (bytes, bytearray)),
   "el cuerpo son bytes, no un número",
   f"mandó {type(p['data']).__name__}")
ok(not p["args"], "el timeout NO va como argumento posicional",
   f"posicionales: {p['args']}")
ok(p["kw"].get("timeout") == gem.TIMEOUT, "va por nombre, y es el nuestro",
   str(p["kw"]))
ok(p["headers"].get("X-goog-api-key") == "clave-x", "la clave va en su cabecera",
   str(p["headers"]))
ok(cuerpo["model"] == "gemini-3.7-flash", "el modelo es el que se pidió")
ok(cuerpo["input"][1]["processing"] == "agentic",
   "y el modo agéntico viaja al lado del video", str(cuerpo["input"][1].keys()))
ok(cuerpo["input"][1]["mime_type"] == "video/mp4", "con su mime")
ok(r.get("segundos") is not None and "error" not in r, "y la respuesta vuelve limpia",
   str(r)[:120])

print("\nLa respuesta se lee, venga como venga")
ok(gem.texto_de({"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}) == "ok",
   "la forma clásica")
ok("los momentos" in gem.texto_de(
    {"id": "v1_x", "output": [{"content": [{"type": "text",
                                            "text": "los momentos son…"}]}]}),
   "y la nueva, que devuelve un id arriba de todo")
ok("esqueleto" in gem.texto_de({"id": "v1_x", "status": "queued"}),
   "y si no hay texto, muestra las claves en vez del JSON entero")

print("\nLos errores de Google se distinguen")
detalle = gem.detallar(json.dumps({"error": {"code": 429, "message": "sin cupo",
    "details": [{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
                 "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
                                 "quotaValue": "20"}]}]}}))
ok(any("FreeTier" in x for x in detalle),
   "un 429 dice QUÉ cuota se agotó, que es lo que decide qué hacer", str(detalle))

print(f"\n✗ {fallos} fallo(s)\n" if fallos else "\n✓ todo bien\n")
sys.exit(1 if fallos else 0)
