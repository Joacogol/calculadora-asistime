# -*- coding: utf-8 -*-
"""Stadium, visto desde el motor.

El enchufe: junta lo que esta marca ofrece y lo expone con los nombres que el
motor espera. El contrato completo está en `motor/contrato.py`.

## Ninguna plantilla escrita en Python

Boss y Clínica tienen dos o tres plantillas que quedaron en código porque no
son un diseño con variables sino un programa. Stadium nace **entera como
datos** — sus cuatro plantillas son diseños con campos, y ninguna necesita
decidir su propia estructura.

Eso tiene una consecuencia concreta y buena: **todo lo de Stadium se puede
corregir desde el chat.** No hay ninguna pieza sobre la que haya que contestar
«esa necesita código».

## Lo que todavía no tiene

`DIAPOS` y `PRESENTACION`, o sea carruseles y PDFs. Para una cadena de retail
el carrusel de varios productos es una pieza obvia, así que va a hacer falta.
Se dejó afuera a propósito en vez de armarlo a medias: el contrato del motor
falla fuerte y con nombre y apellido si alguien pide un carrusel, que es mejor
que un carrusel que sale mal.
"""
import pathlib as _pl
import sys as _sys

from brand import (C, FORMATOS, FONT_CSS, BASE_CSS, NARANJA_WEB,   # noqa: F401
                   VOCES, PALETAS,                                 # noqa: F401
                   logo, iso, pastilla, descuento, barra,          # noqa: F401
                   paleta, subrayado, etiqueta_persona, fila_logos)  # noqa: F401

from motor import plantillas as _plantillas

AQUI = _pl.Path(__file__).resolve().parent

#: Todas son datos. El dict arranca vacío y lo llena el cargador.
PLANTILLAS = _plantillas.cargar(AQUI, _sys.modules[__name__])

ESCRITAS_EN_PYTHON = ()


def CATALOGO():
    """El catálogo de plantillas, generado de los contratos.

    Lo lee el diseñador. Una plantilla publicada queda disponible en la pieza
    siguiente sin que nadie actualice un texto a mano en el SKILL.md.
    """
    return _plantillas.catalogo(AQUI, ESCRITAS_EN_PYTHON)


ACENTO_POR_DEFECTO = "naranja"

NOMBRE = "Stadium"

#: Con qué dibuja ffmpeg los rótulos de los reels. TTF de peso fijo: freetype
#: no entiende fuentes variables, así que Archivo —que es variable— saldría
#: siempre en regular. Montserrat es lo más cercano que hay en peso fijo.
TIPO_REEL = ("Montserrat-Black.ttf", "Montserrat-SemiBold.ttf")
ANIMO_MUSICA = "club"   # ver ANIMOS en motor/sonido.py
ACENTO_REEL = C["naranja"]

#: El índice y las flechas del carrusel. Esta marca tiene fondos blancos: en
#: blanco desaparecerían.
COLOR_CROMO = C["tinta"]
FUENTE_CROMO = "'Arch',Helvetica,sans-serif"
FUENTE_TEXTO = "'Arch',Helvetica,sans-serif"
