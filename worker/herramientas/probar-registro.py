#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba el registro de clientes sin gcloud y sin red.

    python3 herramientas/probar-registro.py

Lo que vigila: que el worker lea el registro nuevo, que siga leyendo el
formato viejo tal cual, que un registro mal escrito frene con un mensaje que
diga qué falta —y no arranque con la mitad de los clientes—, que ninguna clave
se filtre en lo que va al log, y que los clientes de esquema compartido se
sumen desde la tabla de la casa sin que la casa deje de andar cuando esa
lectura falla.
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

fallos = 0
def ok(c, que, det=None):
    global fallos
    print("  ✓" if c else "  ✗", que, "" if c or det is None else repr(det))
    fallos += 0 if c else 1

def limpio():
    for k in ("CLIENTES_REGISTRO", "CLIENTES", "SUPABASE_URL", "SUPABASE_KEY",
              "SUPABASE_KEY_BOSS", "ASISTIME_CLAVE", "ASISTIME_CLAVE_BOSS"):
        os.environ.pop(k, None)

from app import config, registro
import importlib

REG = '''{"clientes":[
  {"marca":"boss-padel-disenos","nombre":"Boss Padel","url":"https://boss.supabase.co/",
   "service_role":"sr-boss-1234 ","asistime_clave":" as-boss-9999\\n"},
  {"marca":"stadium-disenos","nombre":"Stadium","url":"https://stad.supabase.co",
   "service_role":"sr-stad-5678"}
]}'''

print("\n■ El registro nuevo")
limpio(); os.environ["CLIENTES_REGISTRO"] = REG
lista = config.clientes()
ok(len(lista) == 2, "dos clientes", len(lista))
b = lista[0]
ok(b["url"] == "https://boss.supabase.co", "la URL sin la barra final", b["url"])
ok(b["key"] == "sr-boss-1234", "la service_role limpia de espacios", b["key"])
ok(b["asistime_clave"] == "as-boss-9999", "la clave de Asistime limpia del Enter", b["asistime_clave"])
ok(lista[1]["asistime_clave"] == "" and lista[1]["bucket"] == "disenos",
   "sin clave de Asistime y bucket por defecto", lista[1])

print("\n■ manual.py toma la clave del registro, no del entorno")
from app import manual
os.environ["ASISTIME_CLAVE"] = "la-compartida-vieja"
ok(manual._clave("boss-padel-disenos") == "as-boss-9999", "Boss: la del registro")
# Una marca sin clave en el registro cae a LA VARIABLE QUE ELLA NOMBRA en su
# marca.json, nunca a la compartida: mandarle a un tenant la clave de otro da
# 403. Ese es un diseño anterior y esto lo respeta.
suya = manual._nombre_clave("stadium-disenos")
os.environ[suya] = "la-de-stadium"
ok(manual._clave("stadium-disenos") == "la-de-stadium",
   f"Stadium sin clave en el registro: cae a {suya}, la que nombra su marca.json")

print("\n■ El formato viejo sigue andando igual")
limpio()
os.environ["CLIENTES"] = '[{"marca":"boss-padel-disenos","nombre":"Boss","url":"https://b.supabase.co","key_env":"SUPABASE_KEY_BOSS"}]'
os.environ["SUPABASE_KEY_BOSS"] = "vieja"
lista = config.clientes()
ok(lista[0]["key"] == "vieja" and lista[0]["marca"] == "boss-padel-disenos", "CLIENTES + secreto por cliente", lista)

print("\n■ Un registro mal escrito frena y dice qué falta")
limpio(); os.environ["CLIENTES_REGISTRO"] = '{"clientes":[{"marca":"x","nombre":"X","url":"https://x"}]}'
try:
    config.clientes(); ok(False, "tendría que haber levantado")
except registro.RegistroInvalido as e:
    ok("service_role" in str(e) and "x" in str(e), "nombra la marca y el campo", str(e))
limpio(); os.environ["CLIENTES_REGISTRO"] = "{esto no es json"
try:
    config.clientes(); ok(False, "tendría que haber levantado")
except registro.RegistroInvalido as e:
    ok("JSON" in str(e), "y si no es JSON, lo dice", str(e))

print("\n■ Nada de esto muestra una clave")
limpio(); os.environ["CLIENTES_REGISTRO"] = REG
res = registro.resumen(config.clientes())
ok("sr-boss" not in res and "as-boss" not in res, "el resumen para el log", res)
ok("+asistime" in res, "pero sí dice quién tiene manual", res)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import importlib.util
spec = importlib.util.spec_from_file_location("reg_cli", pathlib.Path(__file__).with_name("registro.py"))
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
t = cli.tabla([{"marca": "boss-padel-disenos", "nombre": "Boss Padel", "url": "u",
                "service_role": "sr-boss-1234", "asistime_clave": "as-boss-9999"}])
ok("sr-boss" not in t and "…1234" in t, "la tabla enmascara", t)
ok(cli.enmascarar("") == "—", "y una clave vacía se ve como ausente")

print("\n■ Sumar y quitar")
base = [{"marca": "a", "nombre": "A", "url": "https://a", "service_role": "1"}]
s = cli.sumar(base, {"marca": "a", "nombre": "A2", "url": "https://a", "service_role": "2"})
ok(len(s) == 1 and s[0]["nombre"] == "A2", "repetir una marca la reemplaza, no la duplica")
ok(len(cli.sacar(s + [{"marca": "b", "nombre": "B", "url": "https://b", "service_role": "3"}], "a")) == 1, "quitar saca una")
try:
    cli.armar([{"marca": "c", "nombre": "C", "url": "https://c"}]); ok(False, "armar tendría que validar")
except registro.RegistroInvalido:
    ok(True, "armar valida con el mismo código que lee el worker")



# ══════════════════════════════════════════════════════════════════════════
#  Los clientes que se leen de la casa
# ══════════════════════════════════════════════════════════════════════════
#
# Sin red: se reemplaza `requests` por uno de mentira. Lo que se prueba es la
# decisión —a quién sumar, a quién no, y qué hacer cuando la casa no contesta—
# que es lo único que puede estar mal acá.

class _Respuesta:
    def __init__(self, filas, status=200):
        self._filas, self.status_code = filas, status
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")
    def json(self):
        return self._filas

class _Requests:
    def __init__(self, filas, revienta=False):
        self.filas, self.revienta, self.visto = filas, revienta, []
    def get(self, url, **kw):
        self.visto.append((url, kw))
        if self.revienta:
            raise ConnectionError("la casa no contesta")
        return _Respuesta(self.filas)

CASA = {"marca": "asistime-disenos", "nombre": "Asistime",
        "url": "https://casa.supabase.co", "key": "sr-casa", "bucket": "disenos",
        "esquema": "", "asistime_clave": ""}
PROPIO = {"marca": "boss-padel-disenos", "nombre": "Boss Padel",
          "url": "https://boss.supabase.co", "key": "sr-boss", "bucket": "disenos",
          "esquema": "", "asistime_clave": ""}

FILAS = [
    {"marca": "asistime-disenos", "nombre": "Asistime", "esquema": "",
     "bucket": "disenos", "activo": True},
    {"marca": "boss-padel-disenos", "nombre": "Boss Padel", "esquema": "",
     "bucket": "disenos", "activo": True},
    {"marca": "life-montevideo-disenos", "nombre": "Life Montevideo",
     "esquema": "life_montevideo", "bucket": "disenos-life-montevideo",
     "activo": True},
    {"marca": "club-viejo-disenos", "nombre": "Club Viejo", "esquema": "club_viejo",
     "bucket": "disenos-club-viejo", "activo": False},
]

def _con(filas, revienta=False):
    """Corre `compartidos` con un `requests` de mentira y la cache limpia."""
    import sys as _sys
    falso = _Requests(filas, revienta)
    anterior = _sys.modules.get("requests")
    _sys.modules["requests"] = falso
    try:
        registro.olvidar()
        return registro.compartidos([CASA, PROPIO]), falso
    finally:
        if anterior is None:
            _sys.modules.pop("requests", None)
        else:
            _sys.modules["requests"] = anterior
        registro.olvidar()

print("\n■ Los clientes de esquema compartido salen de la casa")
salida, falso = _con(FILAS)
marcas = [c["marca"] for c in salida]
ok(marcas == ["life-montevideo-disenos"],
   "sólo el que tiene esquema, activo y no está ya en el secreto", marcas)
uno = salida[0]
ok(uno["url"] == CASA["url"] and uno["key"] == CASA["key"],
   "le presta la URL y la clave de la casa")
ok(uno["esquema"] == "life_montevideo" and uno["bucket"] == "disenos-life-montevideo",
   "con su esquema y su bucket", uno)
ok(uno["asistime_clave"] == "",
   "y SIN clave de Asistime: ésa es un secreto de verdad y va por variable")
ok(falso.visto and falso.visto[0][0].startswith(CASA["url"]),
   "le pregunta a la casa y no a otro", falso.visto[:1])

print("\n■ Lo explícito le gana a lo deducido")
salida, _ = _con(FILAS + [{"marca": "boss-padel-disenos", "nombre": "Otro",
                           "esquema": "boss", "bucket": "x", "activo": True}])
ok("boss-padel-disenos" not in [c["marca"] for c in salida],
   "un cliente que ya está en el secreto no se duplica desde la tabla")

print("\n■ Si la casa no contesta, el worker igual atiende")
salida, _ = _con(FILAS, revienta=True)
ok(salida == [], "devuelve vacío en vez de levantar", salida)

print("\n■ Sin la casa en el registro no hay a quién preguntarle")
registro.olvidar()
ok(registro.compartidos([PROPIO]) == [],
   "no rompe: simplemente no hay clientes compartidos")
registro.olvidar()

print("\n■ La lista completa que ve el worker")
# El registro de arriba trae Boss y Stadium; la casa, Life. Lo que se mira es
# que `config.clientes()` devuelva las DOS fuentes juntas, que es lo único que
# el resto del worker consume.
limpio()
os.environ["CLIENTES_REGISTRO"] = (
    '{"clientes":[{"marca":"asistime-disenos","nombre":"Asistime",'
    '"url":"https://casa.supabase.co","service_role":"sr-casa"}]}')
importlib.reload(config)
import sys as _sys
_falso = _Requests(FILAS)
_antes = _sys.modules.get("requests")
_sys.modules["requests"] = _falso
try:
    registro.olvidar()
    todos = [c["marca"] for c in config.clientes()]
finally:
    if _antes is None:
        _sys.modules.pop("requests", None)
    else:
        _sys.modules["requests"] = _antes
    registro.olvidar()
ok(todos == ["asistime-disenos", "life-montevideo-disenos"],
   "config.clientes() suma el secreto y la tabla de la casa", todos)

print(f"\n✗ {fallos} fallo(s)\n" if fallos else "\n✓ todo bien\n")
sys.exit(1 if fallos else 0)
