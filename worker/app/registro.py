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
       "bucket": "disenos",            ← opcional, es el default
       "esquema": "club_x"}            ← opcional: sólo si comparte proyecto
    ]}

Las claves van ADENTRO, y eso es a propósito: el registro entero es un secreto,
con la misma protección que tenían los secretos sueltos. Lo que cambia es que
son uno en vez de siete, y que no hay que nombrarlos en ningún otro lado.

**Nunca se registra entero.** `resumen()` es lo único que va al log, y no
lleva ninguna clave.

── Los que NO hace falta anotar acá ───────────────────────────────────────

El registro es un secreto por una sola razón: guarda la `service_role` de cada
cliente. Eso era cierto cuando cada uno tenía su propio Supabase.

Un cliente de esquema compartido no tiene ninguna clave propia: su
`service_role` **es la de la casa**, la misma que ya está acá para la marca
casa. Lo suyo son cinco datos que no son secretos —marca, nombre, URL pública,
esquema y bucket— y los cinco ya viven en `public.clientes` del proyecto de la
casa, que es donde se los da de alta.

Así que `compartidos()` los lee de ahí y los suma a la lista, prestándoles la
URL y la clave de la casa. El resultado es que **dar de alta un cliente nuevo
es un `insert` y nada más**: no hay que escribir una versión nueva del secreto,
que era el último paso del alta que exigía `gcloud` y una persona.

Los cuatro que tienen proyecto propio siguen exactamente igual: entran por el
secreto, con su clave, y si están en los dos lados gana el secreto — lo
explícito le gana a lo deducido.

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
        # El esquema donde viven SUS tablas cuando comparte proyecto con otros
        # clientes. Vacío es `public`, que es lo que tienen los que llegaron
        # con su propio Supabase: no hay que tocarles la entrada.
        "esquema": (c.get("esquema") or "").strip(),
        "asistime_clave": (c.get("asistime_clave") or "").strip(),
    }


#: La marca cuyo proyecto de Supabase es «la casa»: el que alojan los clientes
#: de esquema compartido y donde vive `public.clientes`. Es la MISMA variable
#: que usa el libro (`app/libro.py`), y a propósito: son la misma cosa vista
#: desde dos lados, y dos nombres distintos para un solo dato es una forma
#: barata de que un día no coincidan.
MARCA_CASA = os.environ.get("LIBRO_MARCA", "asistime-disenos")

#: Cuánto se espera a la casa. Corto porque esto corre en cada arranque del
#: worker, que es cada minuto: si la base tarda, es mejor una corrida con los
#: clientes del secreto que una corrida que no arranca.
ESPERA = 10

_compartidos_cache: list[dict] | None = None


def compartidos(lista: list[dict]) -> list[dict]:
    """Los clientes que viven en el Supabase de la casa, leídos de su tabla.

    Devuelve sólo los que NO están ya en `lista`: si alguien está en el
    secreto, manda el secreto.

    Nunca levanta. Un problema para leer la casa no puede dejar sin atender a
    los clientes que sí están en el secreto — el worker corre cada minuto y la
    corrida siguiente lo vuelve a intentar. Lo que sí hace es dejarlo escrito
    en el log, porque si no se ve, un cliente nuevo simplemente no existiría y
    nadie sabría por qué.
    """
    global _compartidos_cache
    if _compartidos_cache is not None:
        return _compartidos_cache

    casa = next((c for c in lista if c["marca"] == MARCA_CASA), None)
    if not casa:
        # No es un error: es un despliegue donde la casa no se atiende a sí
        # misma. Sin ella no hay con qué leer la tabla, y no hay nada que leer.
        _compartidos_cache = []
        return _compartidos_cache

    ya = {c["marca"] for c in lista}
    try:
        import requests
        r = requests.get(
            f"{casa['url']}/rest/v1/clientes",
            headers={"apikey": casa["key"], "Authorization": f"Bearer {casa['key']}"},
            params={"select": "marca,nombre,esquema,bucket,activo"},
            timeout=ESPERA)
        r.raise_for_status()
        filas = r.json()
    except Exception as e:                                       # noqa: BLE001
        log.warning("no pude leer los clientes de la casa (%s): sigo con los "
                    "%d del registro", e, len(lista))
        return []

    salida = []
    for f in filas if isinstance(filas, list) else []:
        marca = (f.get("marca") or "").strip()
        esquema = (f.get("esquema") or "").strip()
        # Sin esquema es un cliente con proyecto propio: su fila en esta tabla
        # existe para el tablero, no para atenderlo desde acá.
        if not marca or not esquema or marca in ya or f.get("activo") is False:
            continue
        salida.append({
            "marca": marca,
            "nombre": (f.get("nombre") or marca).strip(),
            "url": casa["url"],
            "key": casa["key"],
            "bucket": (f.get("bucket") or "disenos").strip(),
            "esquema": esquema,
            # La de Asistime NO se deduce: es un secreto de verdad y sigue
            # viniendo por variable de entorno, que es donde `manual.py` la
            # busca cuando el registro no la trae.
            "asistime_clave": "",
        })
    _compartidos_cache = salida
    if salida:
        log.info("de la casa: %s", ", ".join(c["marca"] for c in salida))
    return salida


def olvidar() -> None:
    """Olvida los clientes leídos de la casa. El ciclo la llama al empezar,
    igual que `manual.limpiar()`: una corrida no trabaja con la lista de la
    corrida anterior."""
    global _compartidos_cache
    _compartidos_cache = None


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
