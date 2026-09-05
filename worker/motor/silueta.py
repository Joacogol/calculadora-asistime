# -*- coding: utf-8 -*-
"""Dónde cae, adentro de la pieza, lo que la foto tiene dibujado.

── Qué resuelve ───────────────────────────────────────────────────────────

Que la firma de la marca no se apoye sobre el sujeto.

El 4 y el 5/9/2026, cuatro veces, «ASISTIME.AI» salió escrito encima de la
oreja de Tony. El guardián de contraste lo vio —2,6:1 sobre el pelaje— y eso
está bien: avisa. Pero avisar después de renderizar no es lo mismo que no
hacerlo. Un diseñador no pone la firma sobre la cara del sujeto y después mide
si se lee: mira dónde está el sujeto y firma en otro lado.

Para poder mirar hay que saber DÓNDE quedó el recorte, y eso no es obvio: la
foto entra al lienzo con `object-fit: contain` y `object-position`, así que su
contenido no ocupa el rectángulo entero ni está donde está en el archivo. Acá
se hace esa cuenta —la misma que hace el navegador— y se mide el alfa real en
el pedazo de pieza que se pregunta.

── Por qué el alfa y no la caja ───────────────────────────────────────────

Porque la caja de Tony es toda la pieza de abajo y adentro de esa caja hay
mucho aire: entre las dos orejas no hay nada. Lo que importa es si HAY PELO
donde va a caer la firma, no si el recorte pasa cerca. Con la caja, cualquier
recorte grande bloquearía las cuatro esquinas y no quedaría dónde firmar.

── Qué NO hace ────────────────────────────────────────────────────────────

No mira fotos de fondo. Una foto que ocupa el rectángulo entero está debajo de
TODO, y para eso está el velo de `legibilidad`: oscurecerla es la respuesta
correcta y no hay adónde mover nada. Esto es sólo para objetos recortados, que
son los que dejan lugar libre al lado.
"""
from __future__ import annotations

import logging
import pathlib

log = logging.getLogger(__name__)

#: Debajo de este alfa un píxel es aire. El mismo umbral que usa
#: `legibilidad.transparencia`, para que las dos medidas hablen del mismo
#: recorte: un borde suavizado no es sujeto.
OPACO = 17


def _fraccion(valor: str, cual: int) -> float:
    """La parte `cual` (0=x, 1=y) de un `object-position`, como 0..1.

    Acepta lo que aceptan las plantillas y el banco: `"50% 80%"`,
    `"center bottom"`, `"center 70%"`. Lo que no entiende cae en el centro,
    que es el default del navegador — nunca levanta, porque este módulo no
    tiene por qué romper una pieza.
    """
    palabras = {"left": 0.0, "top": 0.0, "center": 0.5, "centre": 0.5,
                "right": 1.0, "bottom": 1.0}
    partes = (valor or "").strip().lower().split()
    if not partes:
        return 0.5
    p = partes[cual] if len(partes) > cual else partes[0]
    if p in palabras:
        return palabras[p]
    try:
        return max(0.0, min(1.0, float(p.rstrip("%")) / 100.0))
    except ValueError:
        return 0.5


def ocupacion(foto, ancho: int, alto: int, zona,
              foco: str = "50% 50%", ajuste: str = "contain") -> float:
    """Qué parte de `zona` tapa lo dibujado de la foto. 0.0 si no se puede.

    `zona` es un rectángulo de la PIEZA en fracciones `(x0, y0, x1, y1)`, con
    el origen arriba a la izquierda: el pie de abajo a la izquierda de una
    story es `(0, 0.88, 0.5, 1.0)`.

    Devuelve 0.0 —«no hay nada ahí»— también cuando no se puede medir: sin
    PIL, con el archivo roto, o con una foto sin canal alfa. Es la regla 3 de
    `motor/revisar.py`: si no se puede medir, callarse. Un falso «está tapado»
    haría desaparecer la firma de piezas que estaban bien.
    """
    if not foto or not ancho or not alto:
        return 0.0
    try:
        from PIL import Image
    except Exception:                                        # noqa: BLE001
        return 0.0

    ruta = pathlib.Path(foto)
    try:
        with Image.open(ruta) as im:
            if im.mode not in ("RGBA", "LA", "PA") and "transparency" not in im.info:
                return 0.0                      # una foto de fondo, no un recorte
            alfa = im.convert("RGBA").getchannel("A")
            iw, ih = alfa.size
    except Exception as e:                                   # noqa: BLE001
        log.debug("no pude mirar la silueta de %s: %s", foto, e)
        return 0.0
    if not iw or not ih:
        return 0.0

    # La misma cuenta que hace el navegador con `object-fit` + `object-position`.
    escala = (min(ancho / iw, alto / ih) if ajuste == "contain"
              else max(ancho / iw, alto / ih))
    dw, dh = iw * escala, ih * escala
    ox = (ancho - dw) * _fraccion(foco, 0)
    oy = (alto - dh) * _fraccion(foco, 1)

    x0, y0, x1, y1 = zona
    px0, py0, px1, py1 = x0 * ancho, y0 * alto, x1 * ancho, y1 * alto
    area = max(1.0, (px1 - px0) * (py1 - py0))

    # De coordenadas de la pieza a coordenadas del archivo.
    ix0, iy0 = (px0 - ox) / escala, (py0 - oy) / escala
    ix1, iy1 = (px1 - ox) / escala, (py1 - oy) / escala
    # Lo que cae fuera del archivo es aire: se recorta y se cuenta como vacío,
    # porque el área contra la que se divide es la de la ZONA, no la del corte.
    cx0, cy0 = max(0, int(ix0)), max(0, int(iy0))
    cx1, cy1 = min(iw, int(round(ix1))), min(ih, int(round(iy1)))
    if cx1 <= cx0 or cy1 <= cy0:
        return 0.0

    try:
        corte = alfa.crop((cx0, cy0, cx1, cy1))
        h = corte.histogram()
        opacos = sum(h[OPACO:])
    except Exception as e:                                   # noqa: BLE001
        log.debug("no pude contar la silueta de %s: %s", foto, e)
        return 0.0

    # Cada píxel del archivo vale `escala²` píxeles de la pieza.
    return min(1.0, opacos * escala * escala / area)
