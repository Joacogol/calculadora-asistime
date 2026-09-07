#!/usr/bin/env python3
"""¿El cobro anota en los dos lados y el libro nunca frena una pieza?

    python3 herramientas/probar-libro.py

No toca ninguna base: `requests` se reemplaza por uno de mentira que anota
qué se pidió y contesta lo que se le dice. Lo que se fija acá es lo que no se
ve en producción hasta que sale mal:

  1. El margen sale de la tabla `clientes` de la casa, y si la casa no
     contesta, del entorno — sin levantar.
  2. Una placa cobrada queda en `movimientos` del cliente Y en `libro` de la
     casa, con el mismo precio y el id del movimiento.
  3. Un reel en dólares (fal) y una foto en créditos (Magnific) se cobran
     como corresponde: los créditos sólo si hay precio por crédito, y nunca
     con `diseno_id` (la columna tiene clave foránea a `disenos`).
  4. Una marca con `cobra = false` anota el costo y no cobra.
  5. Un cliente sin `cobro.sql` (404) no se cobra, pero el libro se entera.
  6. Las cargas del tablero se copian al cliente y se marcan; las que no
     entran se marcan con el error, no se pierden.
"""
import json
import os
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

os.environ["CLIENTES"] = json.dumps([
    {"marca": "asistime-disenos", "url": "https://casa.test", "key": "casa"},
    {"marca": "boss-padel-disenos", "url": "https://boss.test", "key": "boss"},
])
os.environ["MARGEN"] = "2.0"
os.environ.pop("CLIENTES_REGISTRO", None)

from app import cobro, libro  # noqa: E402
from app.supa import Cliente  # noqa: E402


class Respuesta:
    def __init__(self, status=200, datos=None, headers=None, texto=""):
        self.status_code = status
        self._datos = datos
        self.headers = headers or {}
        self.text = texto

    def json(self):
        if self._datos is None:
            raise ValueError("sin json")
        return self._datos

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"{self.status_code}")


class Falso:
    """Un `requests` de mentira. `reglas` es {(metodo, url): respuesta o callable}."""
    RequestException = __import__("requests").RequestException
    HTTPError = __import__("requests").HTTPError

    def __init__(self):
        self.llamadas = []
        self.reglas = {}
        self.caida = False

    def _pedir(self, metodo, url, **kw):
        if self.caida:
            raise self.RequestException("sin red")
        cuerpo = kw.get("data")
        datos = json.loads(cuerpo) if cuerpo else None
        self.llamadas.append((metodo, url, datos, kw.get("params") or {}, kw.get("headers") or {}))
        regla = self.reglas.get((metodo, url))
        if callable(regla):
            return regla(datos, kw)
        return regla or Respuesta(200, [])

    def get(self, url, **kw): return self._pedir("GET", url, **kw)
    def post(self, url, **kw): return self._pedir("POST", url, **kw)
    def patch(self, url, **kw): return self._pedir("PATCH", url, **kw)


falso = Falso()
libro.requests = falso
cobro.requests = falso

CASA = "https://casa.test/rest/v1/"
BOSS = "https://boss.test/rest/v1/"
boss = Cliente(marca="boss-padel-disenos", url="https://boss.test", key="boss")
asistime = Cliente(marca="asistime-disenos", url="https://casa.test", key="casa")

fallas = []


def ok(cond, msg):
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        fallas.append(msg)


def de(metodo, url):
    return [l for l in falso.llamadas if l[0] == metodo and l[1] == url]


def limpiar(tabla_clientes):
    falso.llamadas.clear()
    falso.reglas.clear()
    falso.caida = False
    falso.reglas[("GET", CASA + "clientes")] = Respuesta(200, tabla_clientes)
    libro.olvidar()


CLIENTES = [
    {"marca": "boss-padel-disenos", "margen": "2.5", "cobra": True,
     "cuenta_creditos": "asistime", "precio_credito_usd": None},
    {"marca": "asistime-disenos", "margen": "2.0", "cobra": False,
     "cuenta_creditos": "asistime", "precio_credito_usd": None},
]

# 1. margen desde la casa, y desde el entorno si la casa no contesta
print("1. el margen")
limpiar(CLIENTES)
ok(cobro.margen("boss-padel-disenos") == 2.5, "boss lee 2.5 de la tabla")
ok(cobro.margen("nadie") == 2.0, "una marca que no está cae al entorno (2.0)")
limpiar([])
falso.caida = True
ok(cobro.margen("boss-padel-disenos") == 2.0, "sin red: cae al entorno sin levantar")
ok(libro.anotar("boss-padel-disenos", "placa", "p1", costo_usd=1) is False,
   "sin red: anotar devuelve False y no levanta")

# 2. una placa cobrada, en los dos lados
print("2. una placa")
limpiar(CLIENTES)
falso.reglas[("POST", BOSS + "movimientos")] = Respuesta(201, [{"id": "mov-1"}])
r = cobro.registrar(boss, "d1", 0.5, detalle="post · story", tipo="placa",
                    metricas={"segundos": 61.2, "tokens_entrada": 1000, "modelo": "claude-x"},
                    titulo="Torneo", url="https://x/1.png", plantilla="titular")
ok(r is True, "devuelve True")
mov = de("POST", BOSS + "movimientos")
ok(len(mov) == 1 and mov[0][2]["monto_usd"] == -1.25 and mov[0][2]["diseno_id"] == "d1",
   "movimientos: -1.25 (0.5 × 2.5) con diseno_id")
lib = de("POST", CASA + "libro")
ok(len(lib) == 1, "una fila en el libro")
f = lib[0][2] if lib else {}
ok(f.get("precio_usd") == 1.25 and f.get("costo_usd") == 0.5 and f.get("margen_aplicado") == 2.5,
   "libro: costo 0.5, precio 1.25, margen 2.5")
ok(f.get("cobrado_en") == "mov-1" and f.get("segundos") == 61.2 and f.get("plantilla") == "titular"
   and f.get("modelo") == "claude-x", "libro: id del movimiento, segundos, plantilla y modelo")
ok(lib and lib[0][3].get("on_conflict") == "marca,tipo,pieza_id"
   and "merge-duplicates" in lib[0][4].get("Prefer", ""), "libro: upsert por (marca, tipo, pieza)")

# 3. un reel en dólares y una foto en créditos
print("3. reel y foto")
limpiar(CLIENTES)
falso.reglas[("POST", BOSS + "movimientos")] = Respuesta(201, [{"id": "mov-2"}])
cobro.registrar(boss, "r1", 0.40, detalle="h3-max · 768p · 5s", tipo="video",
                proveedor="fal", modelo="h3-max")
mov = de("POST", BOSS + "movimientos")
ok(len(mov) == 1 and mov[0][2]["monto_usd"] == -1.0 and mov[0][2]["diseno_id"] is None
   and "video r1" in (mov[0][2]["detalle"] or ""),
   "video de fal: cobrado 1.00, sin diseno_id, con el id en el detalle")

falso.llamadas.clear()
cobro.registrar(boss, "f1", 0.0, detalle="fondo", tipo="foto", creditos=100,
                proveedor="magnific", modelo="seedream")
ok(not de("POST", BOSS + "movimientos"), "foto sin precio por crédito: no se cobra")
f = de("POST", CASA + "libro")[0][2]
ok(f["creditos"] == 100 and f["precio_usd"] == 0 and f["costo_usd"] == 0
   and f["cuenta_creditos"] == "asistime", "…pero el libro tiene los 100 créditos")

limpiar([{**CLIENTES[0], "precio_credito_usd": "0.01"}, CLIENTES[1]])
falso.reglas[("POST", BOSS + "movimientos")] = Respuesta(201, [{"id": "mov-3"}])
cobro.registrar(boss, "f2", 0.0, tipo="foto", creditos=100, proveedor="magnific")
mov = de("POST", BOSS + "movimientos")
ok(len(mov) == 1 and mov[0][2]["monto_usd"] == -2.5 and mov[0][2]["costo_usd"] == 1.0,
   "con precio por crédito 0.01: costo 1.00, cobrado 2.50")

# 4. la casa no cobra
print("4. cobra = false")
limpiar(CLIENTES)
r = cobro.registrar(asistime, "d9", 0.7, tipo="placa")
ok(r is False and not de("POST", CASA + "movimientos"), "asistime no se cobra a sí misma")
f = de("POST", CASA + "libro")[0][2]
ok(f["costo_usd"] == 0.7 and f["precio_usd"] == 0 and "margen_aplicado" not in f,
   "…pero el costo queda anotado")

# 5. cliente sin cobro.sql
print("5. cliente sin cobro activado")
limpiar(CLIENTES)
falso.reglas[("POST", BOSS + "movimientos")] = Respuesta(404)
r = cobro.registrar(boss, "d2", 0.3, tipo="placa")
f = de("POST", CASA + "libro")[0][2]
ok(r is False and f["precio_usd"] == 0 and f["costo_usd"] == 0.3,
   "404: no se cobra, el libro dice costo 0.3 y precio 0")

# 6. cargas del tablero
print("6. espejar cargas")
limpiar(CLIENTES)
falso.reglas[("GET", CASA + "cargas")] = Respuesta(200, [
    {"id": "c1", "tipo": "carga", "monto_usd": "50", "detalle": "transferencia"},
    {"id": "c2", "tipo": "abono", "monto_usd": "20", "detalle": None},
])
respuestas = iter([Respuesta(201, [{"id": "m-c1"}]), Respuesta(404)])
falso.reglas[("POST", BOSS + "movimientos")] = lambda d, kw: next(respuestas)
n = libro.espejar_cargas(boss)
parches = de("PATCH", CASA + "cargas")
ok(n == 1, "una copiada")
ok(any(p[3].get("id") == "eq.c1" and p[2].get("espejo_id") == "m-c1" and p[2].get("espejado_en")
       for p in parches), "c1 marcada como espejada con el id del cliente")
ok(any(p[3].get("id") == "eq.c2" and "cobro" in (p[2].get("error") or "") for p in parches),
   "c2 marcada con el error (el cliente no tiene cobro)")

# 7. latido
print("7. latido")
limpiar(CLIENTES)
falso.reglas[("GET", BOSS + "disenos")] = Respuesta(206, [], {"Content-Range": "0-0/3"})
ok(libro.latir(boss, disenos=2) is True, "se deja el latido")
lat = de("POST", CASA + "latidos")
ok(lat and lat[0][2]["pendientes"] == 3 and lat[0][2]["detalle"] == {"disenos": 2}
   and lat[0][3].get("on_conflict") == "marca", "con pendientes contados y upsert por marca")

print()
if fallas:
    print(f"✗ {len(fallas)} falla(s)")
    sys.exit(1)
print("✓ todo bien")
