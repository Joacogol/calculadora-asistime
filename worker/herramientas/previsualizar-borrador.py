#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dibuja una plantilla que todavía es borrador, para poder mirarla.

    python3 herramientas/previsualizar-borrador.py <marca> <carpeta> [formatos…]
    python3 herramientas/previsualizar-borrador.py boss-padel-disenos _borrador
    python3 herramientas/previsualizar-borrador.py boss-padel-disenos _borrador post story

Deja los PNG dentro de la propia carpeta del borrador, como `preview-post.png`.

## Por qué existe

Una carpeta que empieza con guión bajo es invisible para el motor —así un
borrador no puede salir en una pieza mientras se está escribiendo— y por lo
tanto `render.py` tampoco la encuentra. Esto la dibuja igual, por el mismo
camino: `motor.plantillas.compilar()` es literalmente la función que arma la
pieza final.

Es la herramienta que hace que quien escribe una plantilla pueda **ver lo que
dibujó**. Sin eso está escribiendo HTML a ciegas, y una plantilla escrita a
ciegas se nota: el titular desborda, el acento no contrasta con la foto, el pie
queda pisado. Ninguna de esas tres cosas se ve leyendo el código.

## Los datos con los que dibuja

Salen del propio contrato: el `ejemplo` de cada campo, o su valor por defecto,
o algo del tipo que corresponda. Un campo cuyo defecto es vacío se dibuja
vacío, aunque quede un hueco — si el preview lo rellena, enseña lo contrario de
lo que hay que aprender.

Se puede pasar un `ejemplo.json` en la carpeta del borrador para probar casos
límite: el titular largo, la lista de ocho ítems, la sede con nombre de tres
palabras. Esos son los que rompen una plantilla, no los del ejemplo.
"""
import importlib
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def _marca(nombre: str):
    carpeta = RAIZ / ".claude" / "skills" / nombre
    if not carpeta.is_dir():
        raise SystemExit(f"no existe la marca «{nombre}» en .claude/skills/")
    sys.path.insert(0, str(carpeta))
    return importlib.import_module("marca"), carpeta


def ejemplo(contrato: dict, carpeta_marca: pathlib.Path) -> dict:
    """Datos con los que la plantilla se ve, sacados del contrato."""
    muestra = {
        "texto": "Texto de ejemplo",
        "texto_largo": ("Un párrafo de ejemplo, lo bastante largo como para "
                        "que se vea cómo cae el texto cuando el contenido no "
                        "es corto."),
        "si_no": True,
    }
    fotos = sorted((carpeta_marca / "assets").glob("*.jpg"))
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
            d[cid] = [[c.get("etiqueta", c["id"]) for c in cols] for _ in range(3)]
        elif "default" in campo:
            d[cid] = campo["default"]
        elif campo.get("requerido"):
            d[cid] = muestra.get(tipo, "Texto de ejemplo")
        else:
            d[cid] = ""
    return d


def main(argv):
    if len(argv) < 3:
        raise SystemExit(__doc__)
    nombre_marca, borrador = argv[1], argv[2]
    pedidos = argv[3:]

    from playwright.sync_api import sync_playwright
    from motor import plantillas as mp
    from motor.render import Render

    marca, carpeta_marca = _marca(nombre_marca)
    d = carpeta_marca / "plantillas" / borrador
    if not (d / "plantilla.json").exists():
        raise SystemExit(f"no encuentro {d}/plantilla.json")

    contrato = json.loads((d / "plantilla.json").read_text(encoding="utf-8"))
    html = (d / "plantilla.html").read_text(encoding="utf-8")

    propio = d / "ejemplo.json"
    datos = (json.loads(propio.read_text(encoding="utf-8")) if propio.exists()
             else ejemplo(contrato, carpeta_marca))

    formatos = pedidos or list(contrato.get("medidas", {}))
    if not formatos:
        raise SystemExit("el contrato no declara ningún formato en `medidas`")

    render = Render(marca, carpeta_marca)
    salidas = []
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": 1080, "height": 1080},
                                    device_scale_factor=1)
        try:
            for fmt in formatos:
                # Se compila ANTES de tocar el navegador: un error de plantilla
                # sale con su mensaje y su número de línea, sin haber levantado
                # un render para nada.
                cuerpo = mp.compilar(marca, carpeta_marca, contrato, html,
                                     datos, fmt)
                w, h = marca.FORMATOS[fmt]
                destino = d / f"preview-{fmt}.png"
                render._captura(pagina, cuerpo, w, h, destino, datos)
                salidas.append(destino)
                print(f"→ {destino}")
        finally:
            navegador.close()
            for tmp in render._tmp:
                tmp.unlink(missing_ok=True)

    print(f"\n{len(salidas)} formato(s). Abrilos con Read y mirá si el titular "
          f"entra, si el texto contrasta con el fondo y si nada queda pisado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
