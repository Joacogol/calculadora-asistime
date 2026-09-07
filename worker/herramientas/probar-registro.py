#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba el registro de clientes sin gcloud y sin red.

    python3 herramientas/probar-registro.py

Lo que vigila: que el worker lea el registro nuevo, que siga leyendo el
formato viejo tal cual, que un registro mal escrito frene con un mensaje que
diga qué falta —y no arranque con la mitad de los clientes—, y que ninguna
clave se filtre en lo que va al log.
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

print(f"\n✗ {fallos} fallo(s)\n" if fallos else "\n✓ todo bien\n")
sys.exit(1 if fallos else 0)
