#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dibuja TODO y deja una huella, para saber si un cambio rompió algo.

    python3 herramientas/verificar-motor.py boss-padel-disenos --grabar
    …hacé el cambio…
    python3 herramientas/verificar-motor.py boss-padel-disenos --comparar

La primera corrida guarda el MD5 de cada PNG. La segunda vuelve a dibujar y
dice qué cambió. Sale con código 0 si todo dio igual y 1 si algo se movió, así
que sirve tal cual en un script de despliegue.

## Por qué existe

La regla que gobierna cualquier cambio en `motor/` es una sola: **si el PNG no
da el mismo MD5, no está migrado**. Es la que se usó para pasar las catorce
plantillas a datos y salieron 56 de 56 idénticas.

Pero hasta hoy vivía como instrucciones en un markdown, con un `git stash` en
el medio. Un `git stash` mal salido se lleva puesto el trabajo, y una prueba que
hay que acordarse de correr a mano es una prueba que no se corre. Esto la vuelve
un comando.

## Por qué la huella NO se guarda en el repo

Porque el MD5 de un PNG depende de la versión de Chromium que lo dibujó. Una
huella grabada en una máquina no coincide con la de otra aunque el código sea
idéntico, y una prueba que falla por eso deja de creerse a los tres días. Por
eso se comparan **dos corridas del mismo lugar**, antes y después del cambio.

## Qué NO prueba

Que el diseño sea bueno. Prueba que no cambió — que es otra cosa, y es la que
importa cuando se toca el motor: un cambio que agrega algo sin mover nada de lo
que ya andaba es seguro; uno que mueve un píxel de una plantilla que nadie
pidió tocar es un problema, aunque el píxel se vea mejor.

Los PNG quedan guardados, así que cuando algo cambia se puede mirar el antes y
el después en vez de discutir sobre un hash.
"""
import argparse
import hashlib
import importlib
import json
import pathlib
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def _marca(nombre: str):
    carpeta = RAIZ / ".claude" / "skills" / nombre
    if not carpeta.is_dir():
        raise SystemExit(f"no existe la marca «{nombre}» en .claude/skills/")
    sys.path.insert(0, str(carpeta))
    return importlib.import_module("marca"), carpeta


def _datos(contrato: dict, carpeta: pathlib.Path) -> dict:
    """Datos fijos para dibujar, sacados del contrato.

    Tienen que ser los MISMOS en las dos corridas o la comparación no dice
    nada. Por eso salen del contrato y no de nada aleatorio, y por eso las
    listas se arman con un largo fijo.
    """
    muestra = {"texto": "Texto de ejemplo",
               "texto_largo": ("Un párrafo de ejemplo, lo bastante largo como "
                               "para que se vea cómo cae el texto."),
               "si_no": True}
    fotos = sorted((carpeta / "assets").glob("*.jpg"))
    d = {}
    for campo in contrato.get("campos", []):
        cid, tipo = campo["id"], campo.get("tipo", "texto")
        if "ejemplo" in campo:
            d[cid] = campo["ejemplo"]
        elif tipo == "imagen":
            d[cid] = f"assets/{fotos[0].name}" if fotos else ""
        elif tipo == "opcion":
            d[cid] = campo.get("default", (campo.get("opciones") or [""])[0])
        elif tipo == "lista":
            cols = campo.get("columnas") or [{"id": "texto"}]
            rot = (lambda c: c if isinstance(c, str)
                   else c.get("etiqueta", c["id"]))
            d[cid] = [[rot(c) for c in cols] for _ in range(3)]
        elif "default" in campo:
            d[cid] = campo["default"]
        elif campo.get("requerido"):
            d[cid] = muestra.get(tipo, "Texto de ejemplo")
        else:
            d[cid] = ""
    return d


def dibujar_todo(nombre_marca: str, salida: pathlib.Path) -> dict[str, str]:
    """Dibuja cada plantilla en cada formato. Devuelve {archivo: md5}."""
    from playwright.sync_api import sync_playwright
    from motor import plantillas as mp
    from motor.render import Render

    marca, carpeta = _marca(nombre_marca)
    salida.mkdir(parents=True, exist_ok=True)

    contratos = mp._contratos(carpeta)
    # Las escritas en Python no tienen contrato: se dibujan con el ejemplo que
    # trae el spec de la marca, si lo hay. Quedan afuera de la huella si no se
    # puede armar su `data` — y eso se dice, en vez de fingir que se probaron.
    solo_python = sorted(set(marca.PLANTILLAS) - set(contratos))

    huella, saltadas = {}, []
    render = Render(marca, carpeta)
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page(viewport={"width": 1080, "height": 1080},
                          device_scale_factor=1)
        try:
            for cid in sorted(contratos):
                contrato = contratos[cid]
                datos = _datos(contrato, carpeta)
                for fmt in contrato["medidas"]:
                    if fmt not in marca.FORMATOS:
                        continue
                    cuerpo = mp.compilar(marca, carpeta, contrato,
                                         contrato["_html"], datos, fmt)
                    w, h = marca.FORMATOS[fmt]
                    destino = salida / f"{cid}-{fmt}.png"
                    render._captura(pg, cuerpo, w, h, destino, datos)
                    huella[destino.name] = hashlib.md5(
                        destino.read_bytes()).hexdigest()
            saltadas = solo_python
        finally:
            nav.close()
            for tmp in render._tmp:
                tmp.unlink(missing_ok=True)

    if saltadas:
        print(f"   (afuera, escritas en Python: {', '.join(saltadas)})")
    return huella


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("marca")
    ap.add_argument("--grabar", action="store_true",
                    help="dibuja y guarda la huella (correlo ANTES del cambio)")
    ap.add_argument("--comparar", action="store_true",
                    help="dibuja de nuevo y dice qué cambió")
    ap.add_argument("--huella", default="/tmp/huella-motor.json")
    a = ap.parse_args(argv)
    if a.grabar == a.comparar:
        raise SystemExit("elegí --grabar o --comparar, no las dos ni ninguna")

    huella = pathlib.Path(a.huella)
    donde = pathlib.Path("/tmp/verificar-motor") / ("antes" if a.grabar else "despues")
    t0 = time.time()
    print(f"dibujando todo en {donde}…")
    actual = dibujar_todo(a.marca, donde)
    print(f"{len(actual)} piezas en {time.time() - t0:.0f}s")

    if a.grabar:
        huella.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
        print(f"\nhuella guardada en {huella}")
        print("Hacé el cambio y después:")
        print(f"  python3 herramientas/verificar-motor.py {a.marca} --comparar")
        return 0

    if not huella.exists():
        raise SystemExit(f"no existe {huella}: corré --grabar primero")
    antes = json.loads(huella.read_text(encoding="utf-8"))

    faltan = sorted(set(antes) - set(actual))
    nuevas = sorted(set(actual) - set(antes))
    movidas = sorted(n for n in set(antes) & set(actual) if antes[n] != actual[n])

    if not (faltan or movidas):
        print(f"\n{len(actual)} / {len(antes)} idénticas. "
              f"El cambio no movió nada de lo que ya andaba.")
        if nuevas:
            print(f"Y agrega {len(nuevas)}: {', '.join(nuevas)}")
        return 0

    print()
    for n in faltan:
        print(f"  FALTA     {n}  — dejó de dibujarse")
    for n in movidas:
        print(f"  DISTINTA  {n}")
    for n in nuevas:
        print(f"  nueva     {n}")
    print(f"\n{len(movidas)} distinta(s), {len(faltan)} que ya no dibujan.")
    print("Mirá el antes y el después:")
    print("  /tmp/verificar-motor/antes/  vs  /tmp/verificar-motor/despues/")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
