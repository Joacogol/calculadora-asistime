# -*- coding: utf-8 -*-
"""Chromium convirtiendo HTML en PNG y PDF. No sabe de ninguna marca.

Que sea el mismo navegador el que saca las placas, los carruseles y las
presentaciones es lo que garantiza que la tipografía y el interletrado sean
idénticos entre una placa y un PDF.

La marca entra como parámetro: este módulo sólo sabe que existe un objeto con
`FORMATOS`, `PLANTILLAS` y `DIAPOS`.
"""
import json
import os
import pathlib
import re

from playwright.sync_api import sync_playwright

from . import carrusel as mcarrusel
from . import contrato
from . import efectos


def _inyectar_efecto(html: str, data: dict, w: int, h: int) -> str:
    """Mete el efecto atmosférico en el HTML que ya armó la plantilla.

    Se hace acá y no adentro de cada plantilla a propósito: son nueve plantillas
    por marca y el efecto es el mismo para todas. El CSS entra antes de cerrar
    el `<style>` y el HTML justo después del `<img class="bg">`.

    El anclaje importa: las plantillas no usan z-index, así que manda el orden
    del documento. Ahí el efecto queda encima de la foto y debajo del texto. Si
    fuera el primer hijo del canvas, la foto lo taparía entero.
    """
    ef = data.get("efecto")
    if not ef:
        return html
    css, extra = efectos.aplicar(
        ef, float(data.get("efecto_fuerza", 1.0)),
        data.get("foto", ""), w, h, data.get("foco", "50% 50%"))

    i = html.rfind("</style>")
    if i > 0:
        html = html[:i] + css + html[i:]

    m = re.search(r'<img class="bg"[^>]*>', html)
    if m:
        corte = m.end()
    else:
        # Plantillas sin foto: no hay nada que tapar.
        j = html.find('class="canvas')
        corte = html.find(">", j) + 1 if j > 0 else 0
    return html[:corte] + extra + html[corte:]


class Render:
    """Un Chromium abierto, renderizando piezas de UNA marca.

    `raiz` es la carpeta de la marca: el HTML intermedio tiene que escribirse
    ahí porque las plantillas referencian `assets/` y `fonts/` con rutas
    relativas. Si lo escribiéramos en /tmp, Chromium no encontraría ni las fotos
    ni las tipografías.

    Los temporales llevan el PID en el nombre y se borran en un `finally`: dos
    archivos de depuración quedaron olvidados dentro de una skill y viajaron a la
    imagen de Docker sumando 8.000 tokens de basura que el agente podía leer.
    """

    def __init__(self, marca, raiz: pathlib.Path):
        contrato.verificar(marca)
        self.marca = marca
        self.raiz = pathlib.Path(raiz)
        self._tmp: list[pathlib.Path] = []

    def _temporal(self, sufijo: str) -> pathlib.Path:
        p = self.raiz / f"_tmp-{os.getpid()}{sufijo}"
        self._tmp.append(p)
        return p

    def _captura(self, pg, html, w, h, destino, data=None):
        tmp = self._temporal(f"-{destino.stem}.html")
        tmp.write_text(_inyectar_efecto(html, data or {}, w, h), encoding="utf-8")
        pg.set_viewport_size({"width": w, "height": h})
        pg.goto(f"file://{tmp}")
        pg.wait_for_timeout(320)
        pg.locator(".canvas").screenshot(path=str(destino))
        return destino

    def placa(self, pg, tpl, data, fmt, nombre, salida):
        w, h = self.marca.FORMATOS[fmt]
        html = self.marca.PLANTILLAS[tpl](data, fmt)
        return self._captura(pg, html, w, h, salida / f"{nombre}.png", data)

    def carrusel(self, pg, data, fmt, nombre, salida, secuencia=False):
        """Todas las diapositivas de un carrusel o secuencia.

        Dos cosas se resuelven acá y no en el spec, porque son las dos que se
        rompen solas si dependen de que alguien se acuerde:

        **Un solo formato para todas.** Instagram recorta cada diapositiva a la
        proporción de la primera, así que `fmt` se aplica al carrusel entero.

        **La numeración.** Los archivos salen `nombre-01.png`, `-02.png`. Van a
        aparecer en ese orden en el explorador de quien los suba, que es lo único
        que garantiza que el podio no se publique al revés.
        """
        w, h = (self.marca.FORMATOS["story"] if secuencia
                else self.marca.FORMATOS[fmt])
        paginas = mcarrusel.paginas(self.marca, data, fmt, secuencia)
        rutas = []
        for i, html in enumerate(paginas):
            d = (data.get("slides") or [])[i]
            rutas.append(self._captura(pg, html, w, h,
                                       salida / f"{nombre}-{i+1:02d}.png", d))
        return rutas

    def presentacion(self, pg, data, nombre, salida):
        if not hasattr(self.marca, "PRESENTACION"):
            raise ValueError("esta marca no tiene presentaciones PDF: "
                             "le falta `PRESENTACION`")
        html, ancho, alto = self.marca.PRESENTACION(data)
        tmp = self._temporal(f"-{nombre}-deck.html")
        tmp.write_text(html, encoding="utf-8")
        pg.set_viewport_size({"width": ancho, "height": alto})
        pg.goto(f"file://{tmp}")
        # Las fuentes tienen que estar cargadas antes de imprimir: si no, la
        # primera página sale con la tipografía de respaldo.
        pg.wait_for_function("document.fonts.ready.then(() => true)")
        pg.wait_for_timeout(450)
        destino = salida / f"{nombre}.pdf"
        pg.pdf(path=str(destino), width=f"{ancho}px", height=f"{alto}px",
               print_background=True,
               margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        return destino

    def correr(self, spec, salida):
        salida = pathlib.Path(salida)
        salida.mkdir(parents=True, exist_ok=True)
        hechas = []
        try:
            with sync_playwright() as p:
                b = p.chromium.launch()
                pg = b.new_page(viewport={"width": 1080, "height": 1080},
                                device_scale_factor=1)
                for j in spec:
                    tpl = j["plantilla"]
                    if tpl == "presentacion":
                        hechas.append(self.presentacion(
                            pg, j["data"], j["nombre"], salida))
                    elif tpl in ("carrusel", "secuencia"):
                        hechas += self.carrusel(
                            pg, j["data"], j.get("formato", "vert"),
                            j["nombre"], salida, secuencia=(tpl == "secuencia"))
                    else:
                        hechas.append(self.placa(
                            pg, tpl, j["data"], j.get("formato", "post"),
                            j["nombre"], salida))
                b.close()
        finally:
            for t in self._tmp:
                t.unlink(missing_ok=True)
        return hechas


def desde_linea_de_comandos(marca, raiz, argv):
    """El lanzador que cada marca expone como `render.py spec.json [salida]`."""
    spec = json.loads(pathlib.Path(argv[1]).read_text(encoding="utf-8"))
    destino = argv[2] if len(argv) > 2 else pathlib.Path(raiz) / "out"
    for p in Render(marca, raiz).correr(spec, destino):
        print("→", p)
