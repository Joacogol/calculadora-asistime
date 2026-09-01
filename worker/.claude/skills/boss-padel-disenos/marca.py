# -*- coding: utf-8 -*-
"""Boss Padel, visto desde el motor.

Este archivo es el enchufe: junta todo lo que esta marca tiene para ofrecer y
lo expone con los nombres que el motor espera. El motor no importa `brand`,
`templates` ni `diapositivas` — importa esto.

Para dar de alta una marca nueva alcanza con escribir un archivo así, y los
cuatro o cinco que lo alimentan. Todo lo demás —Chromium, ffmpeg, la síntesis
de sonido, los efectos de clima, la estructura del carrusel, la numeración, las
zonas seguras de story— ya está hecho y no se toca.

El contrato completo está en `motor/contrato.py`, y `motor.contrato.verificar()`
avisa con nombre y apellido si falta algo.
"""
import pathlib as _pl
import sys as _sys

from brand import C, FORMATOS, FONT_CSS, LOGO_CSS, logo, aros, blob   # noqa: F401
from templates import PLANTILLAS, BASE_CSS                            # noqa: F401
from diapositivas import DIAPOS                                       # noqa: F401
import presentacion

from motor import plantillas as _plantillas

# Las plantillas que son datos pisan a las que quedaron escritas en Python.
# Conviven a propósito: `horarios` y `duelo` no son un diseño con variables
# sino un programa —eligen cuerpo tipográfico y estructura según lo que entra—
# y forzarlas sería inventar un lenguaje de programación adentro del HTML.
AQUI = _pl.Path(__file__).resolve().parent
PLANTILLAS = {**PLANTILLAS,
              **_plantillas.cargar(AQUI, _sys.modules[__name__])}

ESCRITAS_EN_PYTHON = ("duelo", "horarios")


def CATALOGO():
    """El catálogo de plantillas, generado de los contratos.

    Lo lee el diseñador. Una plantilla publicada queda disponible en la pieza
    siguiente sin que nadie actualice un texto a mano en el SKILL.md.
    """
    return _plantillas.catalogo(AQUI, ESCRITAS_EN_PYTHON)


ACENTO_POR_DEFECTO = "lima"

NOMBRE = "Boss Padel"

#: Lo que el motor le dice al modelo de transcripción ANTES de escuchar un
#: video de este cliente. **Va en prosa y con sus signos, no como una lista**:
#: `initial_prompt` es «el texto que venía antes» y el modelo copia su estilo,
#: puntuación incluida. Con una lista separada por comas empieza a escribir
#: «cual elegirías?» sin abrir el signo. Ver `motor/habla.py`.
#:
#: Van los términos del deporte y del club, NO nombres de jugadores: una lista
#: de nombres sesga al modelo a escribirlos donde no se dijeron.
VOCABULARIO = (
    "Hablamos de pádel en Boss Padel, con canchas en Carrasco, Hípico y "
    "Punta del Este. ¿Jugamos un americano? Buena pala, lindo revés."
)


# Con qué tipografías dibuja ffmpeg los rótulos de los reels. Tienen que ser
# TTF de peso fijo: freetype no entiende fuentes variables y Archivo lo es, así
# que saldría siempre en regular.
TIPO_REEL = ("Barlow-Black.ttf", "BarlowCondensed-Medium.ttf")

# El acento que usan los reels cuando el pedido no dice otra cosa.
ANIMO_MUSICA = "club"   # ver ANIMOS en motor/sonido.py
ACENTO_REEL = C["lima"]

# Tipografía y color del índice del carrusel.
FUENTE_CROMO = "'BarlowC',sans-serif"
COLOR_CROMO = "#FAFAFA"
FUENTE_TEXTO = "'Barlow',sans-serif"


def PRESENTACION(data):
    """HTML de una presentación PDF, más su tamaño de página."""
    return presentacion.deck(data), presentacion.ANCHO, presentacion.ALTO
