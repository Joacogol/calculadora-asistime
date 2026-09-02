# -*- coding: utf-8 -*-
"""El registro de clientes: un solo lugar, leído en cada corrida.

── Por qué existe ─────────────────────────────────────────────────────────

Hasta el 2/9/2026 sumar un cliente exigía **redesplegar el worker**: la lista
de clientes viajaba como una variable de entorno fija, y la clave de cada uno
era un secreto aparte que había que montar a mano en el despliegue. Catorce
pasos para un alta, y dos de ellos —el secreto y el redespliegue— sólo los
podía hacer una persona con `gcloud` a mano.

Ahora la lista entera vive en UN secreto de Secret Manager, `clientes-registro`,
que Cloud Run monta como `CLIENTES_REGISTRO` desde su versión `latest`. Un Job
de Cloud Run resuelve `latest` **cada vez que arranca**, y arranca cada minuto:
así que subir una versión nueva del secreto es todo lo que hace falta para que
un cliente nuevo exista. Sin tocar el despliegue.

── Qué tiene adentro ──────────────────────────────────────────────────────

    {"clientes": [
      {"marca": "boss-padel-disenos",
       "nombre": "Boss Padel",
       "url": "https://xxx.supabase.co",
       "service_role": "eyJ…",
       "asistime_clave": "…",          ← opcional: para leer su manual de marca
       "bucket": "disenos"}            ← opcional, es el default
    ]}

Las claves van ADENTRO, y eso es a propósito: el registro entero es un secreto,
con la misma protección que tenían los secretos sueltos. Lo que cambia es que
son uno en vez de siete, y que no hay que nombrarlos en ningún otro lado.

**Nunca se registra entero.** `resumen()` es lo único que va al log, y no
lleva ninguna clave.

── Qué pasa con la marca que todavía no está en la imagen ────────────────

El registro dice qué clientes atender; el código de la marca —su `marca.py`,
sus plantillas— tiene que estar en la imagen del worker. Hasta que la marca sea
puramente datos (el paso B de la etapa 4), un cliente nuevo en el registro cuya
carpeta no esté en la imagen se **saltea con un aviso**, no rompe la corrida de
los demás. Ver `chat.py`.
"""
from __future__ import annotations

import json
import logging
import os

log = logging.getLogger(__name__)

VARIABLE = "CLIENTES_REGISTRO"
SECRETO = "clientes-registro"

CAMPOS_OBLIGATORIOS = ("marca", "nombre", "url", "service_role")


class RegistroInvalido(ValueError):
    """El registro está, pero no se puede usar. Dice exactamente por qué."""


def leer(crudo: str | None = None) -> list[dict] | None:
    """La lista de clientes del registro, o None si no hay registro.

    `None` y «lista vacía» son cosas distintas: sin la variable, el worker cae
    al modo anterior (`CLIENTES` + un secreto por cliente) y nadie se entera del
    cambio. Con la variable puesta y mal escrita, se levanta un error que dice
    cuál es el campo que falta — mejor que arrancar con la mitad de los
    clientes y que el otro medio se entere al mediodía.
    """
    if crudo is None:
        crudo = os.environ.get(VARIABLE, "")
    crudo = (crudo or "").strip()
    if not crudo:
        return None
    try:
        datos = json.loads(crudo)
    except json.JSONDecodeError as e:
        raise RegistroInvalido(f"{VARIABLE} no es JSON válido: {e}") from e
    lista = datos.get("clientes") if isinstance(datos, dict) else datos
    if not isinstance(lista, list):
        raise RegistroInvalido(
            f"{VARIABLE} tiene que ser {{\"clientes\": [...]}}; llegó "
            f"{type(datos).__name__}")
    return [_normalizar(c, i) for i, c in enumerate(lista)]


def _normalizar(c: dict, i: int) -> dict:
    if not isinstance(c, dict):
        raise RegistroInvalido(f"el cliente #{i + 1} no es un objeto")
    faltan = [k for k in CAMPOS_OBLIGATORIOS if not str(c.get(k) or "").strip()]
    if faltan:
        quien = c.get("marca") or c.get("nombre") or f"#{i + 1}"
        raise RegistroInvalido(
            f"al cliente «{quien}» le falta: {', '.join(faltan)}")
    return {
        "marca": c["marca"].strip(),
        "nombre": c["nombre"].strip(),
        "url": c["url"].strip().rstrip("/"),
        # `key` es el nombre que el resto del worker ya usa. El `.strip()` es
        # por lo mismo que en `manual._clave`: una clave pegada a mano con un
        # Enter de más da un 401 idéntico al de una clave equivocada.
        "key": c["service_role"].strip(),
        "bucket": (c.get("bucket") or "disenos").strip(),
        "asistime_clave": (c.get("asistime_clave") or "").strip(),
    }


def asistime_clave(marca: str) -> str:
    """La clave de Asistime de esta marca según el registro, o «» si no está."""
    try:
        lista = leer()
    except RegistroInvalido:
        return ""
    for c in lista or []:
        if c["marca"] == marca:
            return c["asistime_clave"]
    return ""


def resumen(lista: list[dict]) -> str:
    """Lo único del registro que puede ir a un log: marcas y qué tienen."""
    partes = []
    for c in lista:
        extra = " +asistime" if c.get("asistime_clave") else ""
        partes.append(f"{c['marca']}{extra}")
    return ", ".join(partes)
