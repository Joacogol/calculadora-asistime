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

#: Lado largo del PNG que se deja para mirar. La pieza se dibuja siempre a
#: tamaño real —lo que se mide es el render de verdad— y recién después se
#: achica la copia.
#:
#: Existe porque un `story` de 1080×1920 pesa ~600 KB, y en base64 dentro de
#: un mensaje del SDK se pasa del megabyte que aguanta el lector: la corrida
#: se cae justo cuando el agente va a ABRIR lo que dibujó, que es el único
#: momento que importa. Se cae después de escribir los archivos, así que
#: parece que salió bien y sale cualquier cosa.
#:
#: 900 px alcanza de sobra para lo que se mira acá —si el titular entra, si
#: contrasta, si algo quedó pisado— y de paso baja el preview de story de
#: 2.764 a 607 tokens de imagen, que se releen en todos los turnos que siguen.
LADO_LARGO = 900

#: Y un tope de peso, además del de lado. Los píxeles no son el problema: el
#: problema son los bytes, y cuánto pesa un PNG depende del dibujo. Una placa
#: tipográfica sobre negro plano comprime a 60 KB; la misma medida con un
#: degradé ruidoso de fondo pesa siete veces más. Topar sólo el lado deja
#: pasar justo a las que rompen.
MAX_KB = 350


def _achicar(png: pathlib.Path) -> pathlib.Path:
    """Deja el PNG en un tamaño y un peso que se puedan abrir y mirar.

    Achica hasta cumplir las dos cosas. Baja de a poco y con un piso: un
    preview tan chico que no se distinga si el titular entra no sirve para
    nada, y en ese caso es mejor devolver el que hay y que el error se vea.
    """
    try:
        from PIL import Image
    except ImportError:
        return png          # sin Pillow se mira el grande y que sea lo que sea

    lado = LADO_LARGO
    while True:
        with Image.open(png) as im:
            ancho, alto = im.size
            if max(ancho, alto) > lado:
                escala = lado / max(ancho, alto)
                im = im.resize((max(1, round(ancho * escala)),
                                max(1, round(alto * escala))), Image.LANCZOS)
                im.save(png, "PNG", optimize=True)
            elif lado < LADO_LARGO:
                im.save(png, "PNG", optimize=True)
        if png.stat().st_size <= MAX_KB * 1024 or lado <= 450:
            return png
        lado = int(lado * 0.8)


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
                _achicar(destino)
                salidas.append(destino)
                print(f"→ {destino}  ({destino.stat().st_size // 1024} KB)")
        finally:
            navegador.close()
            for tmp in render._tmp:
                tmp.unlink(missing_ok=True)

    print(f"\n{len(salidas)} formato(s). Abrilos con Read y mirá si el titular "
          f"entra, si el texto contrasta con el fondo y si nada queda pisado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
