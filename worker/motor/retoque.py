# -*- coding: utf-8 -*-
"""El pedido a medida que vive en UNA pieza y en ninguna más.

── Qué resuelve ──────────────────────────────────────────────────────────

Hasta acá había dos velocidades y nada en el medio. La plantilla, que es
rápida y segura pero sólo hace lo que ya sabe; y `crear_plantilla`, que funda
un molde nuevo: tarda, hay que publicarlo, y queda para siempre en el
catálogo. Con eso, «poneles un recuadro de chimenea al texto» obliga a fundar
una plantilla «titular con chimenea» que nadie va a volver a pedir.

El retoque es el medio: un bloque de CSS escrito para ESA pieza, que se aplica
encima de la plantilla y no se guarda en ningún lado. La plantilla deja de ser
una jaula y pasa a ser una base — dibuja el esqueleto, los márgenes seguros,
la tipografía y el pie, y el retoque hace lo que ese pedido necesitaba.

Viaja dentro de `data`, así que no hay que tocar el formato del spec ni el
agente que lo escribe: `data["retoque"]` y listo.

── Pintar no es dibujar: `dibujo` ────────────────────────────────────────

El CSS solo llegó hasta donde llega el CSS. El 3/9/2026 se pidió una story de
viernes «con emojis de música y el dibujo de una silueta de consola de DJ», y
el agente escribió en sus notas que probó el retoque y terminó poniendo los
emojis del sistema: 🎵 en la fuente del contenedor es azul marino, así que
sobre un fondo azul y violeta desapareció, y la consola quedó en cuatro
perillas grises. No fue un descuido: **con CSS se cambia el aspecto de lo que
ya está, no se agregan formas nuevas.** Un recuadro de chimenea, una consola,
una guirnalda de notas — los tres piden trazos, no estilos.

Por eso `data["dibujo"]` acepta SVG: una capa, o varias, que se pegan adentro
del lienzo y que el retoque después posiciona y colorea. SVG y no HTML porque
es lo que se necesita —trazos— y porque se puede verificar de verdad: es XML,
así que se parsea antes de entrar y lo que no parsea no entra.

Cada capa cubre el lienzo entero y el SVG se estira a su tamaño, así que
conviene un `viewBox` propio y dibujar en esas coordenadas: eso vale para
cualquier formato, y la misma pieza sale igual en story que en post.

Y un dibujo puede traer una FOTO adentro, con `<image href="assets/subidas/
01-foto.jpg">`. Eso es lo que convierte «poné la captura adentro de un
teléfono» en algo que se puede hacer: la plantilla sabe poner una foto de
fondo y nada más, y una captura de pantalla de fondo es ilegible. Adentro de
un SVG la imagen se ubica, se recorta con `clipPath`, se le pone sombra con
un filtro y se le dibuja el marco alrededor. Las rutas son relativas a la
carpeta de la marca y no se puede salir de ahí.

Va encima de la plantilla salvo que la capa diga `"atras": true`, que la manda
detrás del texto y delante del fondo — que es donde va un marco.

── Qué se valida, y qué no ───────────────────────────────────────────────

Lo que se valida es lo que **rompe el mecanismo**, y son cuatro cosas:

  · `</style>` — se escapa del bloque de estilos y a partir de ahí puede
    escribir HTML. Es la única de las cuatro que no es una molestia sino un
    agujero.
  · `@import` y las `url()` que apuntan a internet — la pieza se dibuja sin
    red y tiene que seguir saliendo igual dentro de un año. Las `data:` sí:
    un SVG embebido es la forma natural de dibujar un marco.
  · `position: fixed` — se sale del lienzo, y lo que se captura es el lienzo.
  · El largo. Cuatro mil caracteres es muchísimo para un retoque; más que eso
    no es un retoque, es una plantilla que no se quiso escribir.

**Lo que NO se valida es que la pieza quede linda o que respete la marca**, y
conviene decirlo en vez de simularlo. Un CSS libre puede tapar el logo, sacar
el pie o desbordar el texto, y ninguna expresión regular lo va a distinguir de
un pedido legítimo: «sacale el pie a esta pieza» es exactamente igual de
válido. Lo que cuida eso es que la pieza a medida SE MIRA antes de entregarse
—el revisor y la persona— y que nada se publica sin que alguien lo pida.
"""
from __future__ import annotations

import re

#: Más que esto no es un retoque.
LARGO_MAXIMO = 4000

#: Lo que nunca es legítimo, con el porqué que se le devuelve a quien lo
#: escribió. El mensaje importa: quien lo lee es un modelo que tiene que
#: corregirlo, no un humano que puede preguntar.
PROHIBIDO = (
    (re.compile(r"</\s*style", re.I),
     "cierra la etiqueta <style> y se escapa del bloque de estilos"),
    (re.compile(r"@import", re.I),
     "trae una hoja de estilo de afuera, y la pieza se dibuja sin internet"),
    (re.compile(r"url\(\s*['\"]?\s*(?:https?:)?//", re.I),
     "trae un archivo de internet; para dibujar usá un SVG embebido en data:"),
    (re.compile(r"position\s*:\s*fixed", re.I),
     "se sale del lienzo, y lo que se captura es el lienzo"),
)


class RetoqueInvalido(Exception):
    pass


def revisar(css: str) -> str:
    """El CSS del retoque, o `RetoqueInvalido` con el motivo en castellano."""
    css = (css or "").strip()
    if not css:
        return ""
    if len(css) > LARGO_MAXIMO:
        raise RetoqueInvalido(
            f"el retoque tiene {len(css)} caracteres y el tope son "
            f"{LARGO_MAXIMO}. Si necesita más que eso, lo que hace falta es "
            f"una plantilla y no un retoque.")
    for patron, porque in PROHIBIDO:
        if patron.search(css):
            raise RetoqueInvalido(f"el retoque {porque}: «{patron.pattern}»")
    return css


def hoja(data: dict) -> str:
    """El bloque de estilo del retoque, listo para pegar en el `<style>`.

    Va DESPUÉS de la hoja de la marca a propósito: el retoque tiene que poder
    pisar lo que la plantilla decidió, que es todo el punto. Y va comentado,
    para que quien mire el HTML de una pieza sepa qué parte es de la marca y
    qué parte se escribió para ese pedido.
    """
    css = revisar(str((data or {}).get("retoque") or ""))
    return f"\n/* ── retoque de esta pieza ── */\n{css}\n" if css else ""


# ── El dibujo ──────────────────────────────────────────────────────────────

#: Un SVG dibujado a mano por un modelo son dos o tres mil caracteres. Diez
#: mil es holgado; mucho más que eso es una ilustración que convendría
#: guardar como archivo, no escribir adentro del pedido.
LARGO_MAXIMO_DIBUJO = 12000

#: Más de esto no es una pieza a medida, es una escena.
MAXIMO_CAPAS = 4

#: Lo que se puede dibujar. Es una lista blanca y no una negra a propósito:
#: la lista negra hay que adivinarla entera y la blanca sólo hay que
#: ampliarla cuando falte algo, que es un problema que se ve y se arregla.
ETIQUETAS = frozenset("""
    svg g defs symbol use title desc
    path circle ellipse rect line polyline polygon
    text tspan textPath
    linearGradient radialGradient stop pattern clipPath mask marker image
    filter feBlend feColorMatrix feComponentTransfer feComposite
    feConvolveMatrix feDiffuseLighting feDisplacementMap feDistantLight
    feDropShadow feFlood feFuncA feFuncB feFuncG feFuncR feGaussianBlur
    feImage feMerge feMergeNode feMorphology feOffset fePointLight
    feSpecularLighting feSpotLight feTile feTurbulence
""".split())


class DibujoInvalido(Exception):
    pass


def _local(tag) -> str:
    """`{http://www.w3.org/2000/svg}path` → `path`."""
    tag = str(tag)
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


#: Lo que puede ir adentro de un `<image>`: fotos que subió el cliente y
#: material del kit. Nada de SVG —un SVG anidado traería su propio árbol sin
#: revisar— y nada que no sea una imagen.
EXTENSIONES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")


def _archivo_de_la_marca(ruta: str) -> bool:
    """¿Es una imagen de la carpeta de la marca, y sólo de ahí?

    La pieza se dibuja con Chromium parado en la carpeta de la marca, así que
    una ruta relativa es exactamente lo que ya usan las plantillas para sus
    fotos. Lo que hay que impedir es salirse: nada de rutas absolutas, nada de
    `..`, nada con esquema. Con eso, lo que se puede dibujar es lo mismo que
    la marca ya tiene en disco, ni un archivo más.
    """
    v = (ruta or "").strip()
    if not v:
        return False
    if v.startswith("#") or v.lower().startswith("data:"):
        return True
    if v.startswith("/") or v.startswith("\\") or ":" in v:
        return False
    partes = v.replace("\\", "/").split("/")
    if any(p in ("", "..", ".") for p in partes):
        return False
    return v.lower().endswith(EXTENSIONES)


def _revisar_atributos(elem, donde: str) -> None:
    for nombre, valor in elem.attrib.items():
        corto = _local(nombre)
        if corto.lower().startswith("on"):
            raise DibujoInvalido(
                f"«{donde}» trae el atributo «{corto}», que es un manejador de "
                f"eventos; un dibujo no ejecuta nada")
        if corto in ("href", "src"):
            if not _archivo_de_la_marca(valor):
                raise DibujoInvalido(
                    f"«{donde}» apunta a «{valor[:50]}»; valen «#algo», un "
                    f"«data:», o un archivo de la carpeta de la marca como "
                    f"«assets/subidas/01-foto.jpg» — nada de internet ni de "
                    f"fuera de la carpeta")
        if corto == "style" and re.search(r"url\(\s*['\"]?\s*(?:https?:)?//",
                                          valor, re.I):
            raise DibujoInvalido(
                f"«{donde}» trae un `url()` de internet en su `style`")


def revisar_dibujo(svg: str) -> str:
    """Un SVG que se puede pegar en la pieza, o `DibujoInvalido` con el motivo.

    Se parsea de verdad, con el parser de XML, y ese es el punto: un SVG que
    no cierra sus etiquetas no se cuela con medio dibujo, y algo como
    `</svg><script>` no es «una etiqueta prohibida» sino directamente un XML
    con dos raíces, que no parsea. Lo que entra es un árbol, no un texto.
    """
    import xml.etree.ElementTree as ET

    svg = (svg or "").strip()
    if not svg:
        return ""
    if len(svg) > LARGO_MAXIMO_DIBUJO:
        raise DibujoInvalido(
            f"el dibujo tiene {len(svg)} caracteres y el tope son "
            f"{LARGO_MAXIMO_DIBUJO}. Si necesita más, lo que hace falta es una "
            f"ilustración guardada como archivo, no escrita adentro del pedido.")
    try:
        raiz = ET.fromstring(svg)
    except ET.ParseError as e:
        raise DibujoInvalido(
            f"el dibujo no es XML válido ({e}). Un SVG tiene que abrir y "
            f"cerrar todas sus etiquetas y tener UNA sola raíz `<svg>`.")
    if _local(raiz.tag) != "svg":
        raise DibujoInvalido(
            f"el dibujo empieza con «{_local(raiz.tag)}» y tiene que empezar "
            f"con «svg»")
    for elem in raiz.iter():
        etiqueta = _local(elem.tag)
        if etiqueta not in ETIQUETAS:
            raise DibujoInvalido(
                f"«{etiqueta}» no se puede dibujar. Lo que vale son formas, "
                f"gradientes y filtros de SVG; no `script`, `style` ni "
                f"`foreignObject`.")
        _revisar_atributos(elem, etiqueta)
    return svg


def _capas(data: dict) -> list[dict]:
    """`data["dibujo"]` normalizado a una lista de capas.

    Se acepta un SVG suelto, una capa con opciones, o una lista de las dos
    cosas. Quien escribe el spec no tiene por qué saber cuál de las tres
    formas es «la» forma.
    """
    crudo = (data or {}).get("dibujo")
    if not crudo:
        return []
    if isinstance(crudo, (str, dict)):
        crudo = [crudo]
    if not isinstance(crudo, list):
        raise DibujoInvalido(
            "`dibujo` tiene que ser un SVG, una capa `{svg, atras, clase}` o "
            "una lista de esas dos cosas")
    if len(crudo) > MAXIMO_CAPAS:
        raise DibujoInvalido(
            f"son {len(crudo)} capas de dibujo y el tope son {MAXIMO_CAPAS}")

    capas = []
    for i, item in enumerate(crudo, 1):
        capa = {"svg": item} if isinstance(item, str) else dict(item or {})
        svg = revisar_dibujo(str(capa.get("svg") or ""))
        if not svg:
            continue
        clase = str(capa.get("clase") or "").strip()
        if clase and not re.fullmatch(r"[a-zA-Z][\w-]*", clase):
            raise DibujoInvalido(
                f"la clase «{clase}» de la capa {i} tiene que ser una palabra "
                f"que empiece con letra, para poder apuntarle desde el retoque")
        capas.append({"svg": svg, "atras": bool(capa.get("atras")),
                      "clase": clase})
    return capas


#: Lo mínimo para que una capa exista y se pueda mover desde el retoque. El
#: `inset:0` la hace del tamaño del lienzo y el `viewBox` del SVG hace el
#: resto: se dibuja en coordenadas propias y sale igual en cualquier formato.
#: `pointer-events` no cambia nada en una captura, pero la pieza también se
#: mira en el estudio y ahí una capa encima se come los clicks.
#:
#: El `atras` costó una prueba: el primer intento fue `z-index:-1`, que en
#: teoría deja la capa detrás del contenido y delante del fondo. En la práctica
#: desapareció, porque el fondo de estas plantillas no es el fondo de `.canvas`
#: sino un `.scrim` puesto adentro, y un `z-index` negativo queda detrás de eso
#: también. Lo que funciona es al revés: la capa en 0 —arriba del scrim, que
#: está antes en el documento— y el contenido de la plantilla en 1. Se apoya en
#: que el contenido va en `.pad`, que es la convención de todas las plantillas
#: del motor; una plantilla que no la siga va a mostrar la capa encima del
#: texto, y eso se ve mirando el PNG.
#:
#: Y subir `.pad` obliga a subir también la capa de encima, que si no queda
#: debajo del texto sin que nadie lo haya pedido. Son tres pisos y ninguno
#: sobra: 0 la capa de atrás, 1 el contenido de la plantilla, 2 la de encima.
CSS_CAPAS = """
.dibujo{position:absolute;inset:0;pointer-events:none;z-index:2}
.dibujo>svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.dibujo.atras{z-index:0}
.canvas{position:relative}
.canvas>.pad{z-index:1}
"""


def dibujos(data: dict) -> tuple[str, str]:
    """(css, html) de las capas dibujadas de esta pieza.

    El HTML va al final del lienzo —después del cuerpo de la plantilla— y el
    CSS antes del retoque, para que el retoque pueda pisarlo: mover una capa,
    recolorearla o mandarla atrás es exactamente el trabajo del retoque.
    """
    capas = _capas(data)
    if not capas:
        return "", ""
    partes = []
    for c in capas:
        clases = " ".join(x for x in ("dibujo", "atras" if c["atras"] else "",
                                      c["clase"]) if x)
        partes.append(f'<div class="{clases}">{c["svg"]}</div>')
    return CSS_CAPAS, "\n" + "\n".join(partes)
