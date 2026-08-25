# -*- coding: utf-8 -*-
"""Clínica Preventiva, vista desde el motor.

El enchufe: junta lo que esta marca ofrece y lo expone con los nombres que el
motor espera. El contrato completo está en `motor/contrato.py`.
"""
import pathlib as _pl
import sys as _sys

from brand import (C, FORMATOS, FONT_CSS, LOGO_CSS,                         # noqa: F401
                   logo, puntos, pastilla, sello)
from templates import PLANTILLAS as _EN_PYTHON, BASE_CSS, TEL, WEB          # noqa: F401
from diapositivas import DIAPOS                                             # noqa: F401
import presentacion                                                          # noqa: F401

# ── El vocabulario que una plantilla-dato puede usar ──────────────────────
#
# El motor le pasa a cada plantilla las funciones en minúscula que encuentra
# acá. `logo`, `puntos`, `pastilla` y `sello` ya venían de `brand`; las cuatro
# de abajo vivían como privadas dentro de `templates.py` —`_pie`, `_sedes`,
# `_titular`, `_cuerpo`— y son tan de la marca como el logo: el pie de
# contacto, el bloque de las dos sedes, el titular en dos colores y el ajuste
# de cuerpo cuando el título es largo. Escritas a mano en cada HTML se
# duplicarían cinco veces y la sexta saldría distinta.
#
# Se re-exportan acá y NO se renombran en `templates.py` a propósito: mientras
# dure la migración las dos versiones de cada plantilla tienen que dibujar
# exactamente lo mismo para poder compararlas por MD5, y eso exige que el lado
# Python quede intacto.
from templates import _pie as pie, _sedes as sedes                          # noqa: F401
from templates import _titular as titular                                   # noqa: F401
from templates import _titular_sobre_foto as titular_sobre_foto             # noqa: F401
#: Cuánto cuerpo tipográfico le entra al titular. Se llama así y no `cuerpo`
#: porque `d.cuerpo` es un campo de texto en varias plantillas y dentro del
#: HTML los dos nombres se confundirían.
from templates import _cuerpo as achicar_titular                            # noqa: F401

from motor import plantillas as _plantillas

# Las plantillas que son datos pisan a las que quedaron escritas en Python.
AQUI = _pl.Path(__file__).resolve().parent
_COMO_DATO = _plantillas.cargar(AQUI, _sys.modules[__name__])
PLANTILLAS = {**_EN_PYTHON, **_COMO_DATO}

#: Las que todavía son un programa y no un diseño con variables. Se calcula en
#: vez de escribirse a mano: durante la migración cambia con cada plantilla que
#: pasa, y una lista escrita queda vieja sin que nadie se entere — y lo que se
#: rompe es el catálogo, que es justo lo que el agente lee para saber qué
#: existe.
ESCRITAS_EN_PYTHON = tuple(sorted(set(_EN_PYTHON) - set(_COMO_DATO)))


def CATALOGO():
    """El catálogo de plantillas, generado de los contratos."""
    return _plantillas.catalogo(AQUI, ESCRITAS_EN_PYTHON)


ACENTO_POR_DEFECTO = "rojo"

NOMBRE = "Clínica Preventiva"

# Con qué dibuja ffmpeg los rótulos de los reels. TTF de peso fijo: freetype no
# entiende fuentes variables. Los seis pesos se instanciaron desde la
# Montserrat variable de Google Fonts.
TIPO_REEL = ("Montserrat-Black.ttf", "Montserrat-SemiBold.ttf")
ANIMO_MUSICA = "calmo"   # ver ANIMOS en motor/sonido.py
ACENTO_REEL = C["rojo"]

# El índice y las flechas del carrusel. Esta marca tiene fondos claros: en
# blanco desaparecían en la mitad de las diapositivas.
COLOR_CROMO = C["gris"]
FUENTE_CROMO = "'Mont',sans-serif"
FUENTE_TEXTO = "'Mont',sans-serif"


def PRESENTACION(data):
    """HTML de una presentación PDF, más su tamaño de página."""
    return presentacion.deck(data), presentacion.ANCHO, presentacion.ALTO
