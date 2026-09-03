# -*- coding: utf-8 -*-
"""Lo que una marca tiene que proveerle al motor, y su verificación.

Existe para que dar de alta una marca nueva falle temprano y con un mensaje
entendible. Sin esto, una marca a la que le falta `PLANTILLAS` no explota al
cargarse: explota veinte minutos después, adentro de un render, con un
`AttributeError` que no le dice nada a nadie.
"""

OBLIGATORIO = {
    "C": "dict de colores, por ejemplo {'lima': '#E4FF02'}",
    "FORMATOS": "dict formato → (ancho, alto), por ejemplo {'post': (1080, 1080)}",
    "BASE_CSS": "str con la hoja de estilo base (tipografías, clases de texto)",
    "PLANTILLAS": "dict nombre → función(data, formato) que devuelve el HTML",
    "logo": "función(size, color, align) que devuelve el HTML del logo",
}

# Sólo hace falta si la marca quiere carruseles o secuencias de stories.
OPCIONAL = {
    "DIAPOS": ("dict tipo → función(data, ancho, alto, acento) con el cuerpo de "
               "cada diapositiva. Tipos esperados: portada, cierre, y los que "
               "la marca use (puesto, punto, texto)"),
    "PRESENTACION": "función(data) que devuelve el HTML de un PDF de varias páginas",
    "FUENTE_CROMO": ("familia tipográfica del índice del carrusel, por ejemplo "
                     "\"'Mont',sans-serif\". Sin esto sale en la de sistema"),
    "FUENTE_TEXTO": ("familia tipográfica de cuerpo, para la caja de respuesta "
                     "de las secuencias de stories"),
    "COLOR_CROMO": ("color del índice y las flechas del carrusel. Blanco por "
                    "defecto: si la marca tiene fondos claros hay que ponerlo "
                    "oscuro o el índice no se ve"),
    "CROMO_DIAPO": ("función(tipo, data) → color del índice sobre ESA "
                    "diapositiva, o None para usar COLOR_CROMO. Para marcas "
                    "que alternan fondos claros y oscuros"),
}

# Toda marca necesita al menos estos dos tipos de diapositiva: el carrusel
# abre y cierra siempre igual, sin importar qué haya en el medio.
DIAPOS_MINIMAS = ("portada", "cierre")


class MarcaIncompleta(Exception):
    pass


def verificar(marca, con_carrusel: bool = False):
    """Revisa que el módulo de marca cumpla el contrato. Falla fuerte si no."""
    faltan = [f"  · {n}: {d}" for n, d in OBLIGATORIO.items()
              if not hasattr(marca, n)]
    if faltan:
        raise MarcaIncompleta(
            f"a la marca «{getattr(marca, '__name__', marca)}» le falta:\n"
            + "\n".join(faltan))

    for fmt, medida in marca.FORMATOS.items():
        if not (isinstance(medida, (tuple, list)) and len(medida) == 2):
            raise MarcaIncompleta(
                f"FORMATOS['{fmt}'] tiene que ser (ancho, alto), llegó {medida!r}")

    if con_carrusel:
        if not hasattr(marca, "DIAPOS"):
            raise MarcaIncompleta(
                "esta marca no tiene carruseles: le falta `DIAPOS`.\n" +
                f"  · DIAPOS: {OPCIONAL['DIAPOS']}")
        faltantes = [t for t in DIAPOS_MINIMAS if t not in marca.DIAPOS]
        if faltantes:
            raise MarcaIncompleta(
                "un carrusel siempre abre y cierra igual, y a esta marca le "
                f"falta: {', '.join(faltantes)}")
    return True
