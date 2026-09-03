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
