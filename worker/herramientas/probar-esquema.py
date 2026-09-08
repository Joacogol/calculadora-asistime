#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Que un cliente en un esquema compartido no se mezcle con otro.

    python3 herramientas/probar-esquema.py

Sin red: se mira lo que el worker MANDA, que es donde estaría el error. Un
cliente que comparte proyecto con otros se distingue por una cabecera; si esa
cabecera no sale, PostgREST contesta con las tablas de `public` —las de otro
cliente— y nadie se entera hasta que una pieza aparece en la cuenta equivocada.

Y se revisa el SQL generado: que no queden tablas en `public`, que el bucket
sea propio, que las políticas de `storage` lleven el nombre del cliente y que
cada política exija la membresía.
"""
import importlib.util
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from app.supa import Cliente                                          # noqa: E402

_s = importlib.util.spec_from_file_location(
    "esq", RAIZ / "herramientas" / "esquema-de-cliente.py")
esq = importlib.util.module_from_spec(_s); _s.loader.exec_module(esq)

fallos = 0


def ok(c, que, det=None):
    global fallos
    print("  ✓" if c else "  ✗", que, "" if c or det is None else repr(det))
    fallos += 0 if c else 1


print("\n■ La cabecera que separa a un cliente de otro")
propio = Cliente("boss-padel-disenos", "https://boss.test", "k")
compartido = Cliente("club-x-disenos", "https://casa.test", "k", esquema="club_x")
ok("Accept-Profile" not in propio._cab(), "el que tiene proyecto propio no manda esquema")
c = compartido._cab()
ok(c.get("Accept-Profile") == "club_x", "al leer, Accept-Profile con su esquema", c.get("Accept-Profile"))
ok(c.get("Content-Profile") == "club_x", "al escribir, Content-Profile con su esquema", c.get("Content-Profile"))
ok(compartido._cab({"Prefer": "x"}).get("Accept-Profile") == "club_x",
   "la cabecera sobrevive cuando se agregan otras")

print("\n■ El nombre del esquema sale de la marca")
for marca, esperado in (("boss-padel-disenos", "boss_padel"),
                        ("clinica-preventiva-disenos", "clinica_preventiva"),
                        ("club-x", "club_x"), ("Stadium-Disenos", "stadium")):
    ok(esq.esquema_de(marca) == esperado, f"{marca} → {esperado}", esq.esquema_de(marca))

print("\n■ El SQL generado")
sql = esq.render("club-x-disenos", "club_x", "disenos-club-x")
ok("create schema if not exists club_x;" in sql, "crea el esquema")
ok("public.disenos" not in sql and "public.plantillas" not in sql,
   "ninguna tabla queda en public")
ok(sql.count("public.es_de") >= 5, "las políticas piden la membresía", sql.count("public.es_de"))
ok("'disenos-club-x'" in sql and "'disenos'," not in sql, "el bucket es propio")
ok("search_path = public" not in sql, "las funciones apuntan a su esquema")
ok(sql.count("· club_x\" on storage.objects") >= 3,
   "las políticas de storage llevan el nombre del cliente",
   sql.count("· club_x\" on storage.objects"))
ok("auth.users" in sql and "storage.objects" in sql,
   "auth y storage NO se renombraron: son del proyecto")

print("\n■ Dos clientes no comparten un solo nombre")
otro = esq.render("club-y-disenos", "club_y", "disenos-club-y")
nombres_x = {l for l in sql.splitlines() if "on storage.objects" in l}
nombres_y = {l for l in otro.splitlines() if "on storage.objects" in l}
ok(not (nombres_x & nombres_y), "sus políticas de storage no colisionan")

print()
if fallos:
    print(f"✗ {fallos} falla(s)"); sys.exit(1)
print("✓ todo bien")
