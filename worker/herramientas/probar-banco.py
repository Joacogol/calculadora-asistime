#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""El banco de fotos del cliente llega al disco, tenga carpeta o no.

    python3 herramientas/probar-banco.py

Existe por lo que pasó el 5/9/2026, que es el error más caro de la semana
justamente porque no rompió nada:

`sincronizar()` empezaba con `if not refs.exists(): return 0`. El kit de
Asistime nunca trajo una carpeta `referencias/` —al darse de alta no tenía
fotos propias— así que la sincronía se iba en la primera línea y las cuatro
fotos de Tony cargadas en su tabla **nunca llegaron al disco**.

Del otro lado, el PROMPT le dice al agente «leé `referencias/fotos.json` y
elegí la foto que mejor encaje». El agente leía un archivo que no existía, no
encontraba nada, y resolvía: primero inventó una clave que no existe
(`tony-pose-inferior`), después colocó la foto a mano perdiendo el encuadre
medido, y al final **dibujó la jirafa de la marca en SVG**. Tres piezas
seguidas con `fotos_elegidas` vacío, y el diagnóstico se buscó todo el tiempo
en el agente —que estaba improvisando porque no tenía nada— en vez de en una
carpeta que faltaba.

Un cliente que cargó fotos en su tabla quiere un banco. Que la carpeta exista
es un detalle de cómo se dio de alta la marca, no una decisión de nadie.
"""
import json
import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from app import banco                                                 # noqa: E402

fallos = []


def ok(caso, condicion, detalle=""):
    print(f"  {'✓' if condicion else '✗'} {caso}"
          + (f" — {str(detalle)[:200]}" if detalle and not condicion else ""))
    if not condicion:
        fallos.append(caso)


class ClienteFalso:
    """Devuelve filas de `fotos` y baja los archivos sin salir a la red."""

    def __init__(self, filas):
        self.filas = filas

    def leer_fotos(self, _tope):
        return self.filas


def correr(filas, con_carpeta):
    """Sincroniza una marca de mentira y devuelve el banco que quedó escrito."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    marca = "marca-de-prueba"
    base = tmp / ".claude/skills" / marca
    base.mkdir(parents=True)
    if con_carpeta:
        (base / "referencias").mkdir()

    # `carpeta()` y la bajada se sustituyen: lo que se prueba es la decisión,
    # no la red ni el disco de producción.
    banco.config.RAIZ, viejo = tmp, banco.config.RAIZ
    import app.supa as supa
    bajar_real = supa.bajar
    supa.bajar = lambda url, destino: (destino.parent.mkdir(parents=True, exist_ok=True),
                                       destino.write_bytes(b"x"))[1]
    try:
        cuantas = banco.sincronizar(ClienteFalso(filas), marca)
    finally:
        banco.config.RAIZ = viejo
        supa.bajar = bajar_real
    vivo = base / "referencias/fotos.json"
    leido = json.loads(vivo.read_text()) if vivo.exists() else None
    return cuantas, leido, base


FOTOS = [{"clave": "tony-asomandose", "url": "https://x/y/Tony%20(4).png",
          "descripcion": "Tony asomándose", "etiquetas": ["tony"],
          "foco": {"post": "50% 100%"}, "ancho": 1080, "alto": 1350}]

print("\n■ El cliente tiene fotos y la marca NO trajo carpeta")
cuantas, leido, base = correr(FOTOS, con_carpeta=False)
ok("la carpeta se crea sola", (base / "referencias").exists())
ok("y la foto entra al banco", cuantas == 1, cuantas)
ok("con su ruta en el disco",
   (leido or {}).get("tony-asomandose", {}).get("archivo", "").startswith("assets/banco/"),
   leido)
ok("el archivo existe de verdad",
   (base / (leido or {}).get("tony-asomandose", {}).get("archivo", "no")).exists())
ok("y el foco medido se conserva",
   (leido or {}).get("tony-asomandose", {}).get("foco", {}).get("post") == "50% 100%")

print("\n■ La marca trajo carpeta: sigue funcionando igual")
cuantas, leido, _ = correr(FOTOS, con_carpeta=True)
ok("la foto entra igual", cuantas == 1, cuantas)

print("\n■ Sin fotos en la tabla no se inventa nada")
cuantas, leido, base = correr([], con_carpeta=False)
ok("no se crea una carpeta vacía", not (base / "referencias").exists())
ok("y no rompe", cuantas == 0)

print()
if fallos:
    print(f"  ✗ {len(fallos)} fallo(s)")
    raise SystemExit(1)
print("  todo bien")
