# -*- coding: utf-8 -*-
"""Las plantillas publicadas de la marca, bajadas al skill en cada corrida.

Es el mismo camino que ya hacen el manual de marca (`manual.py`, desde
Asistime) y el banco de fotos (`banco.py`, desde la base del cliente): lo que
el cliente puede cambiar vive afuera del despliegue y entra al skill antes de
diseñar.

## Por qué escribe archivos en vez de devolver un dict

Porque el diseñador no es una función que reciba parámetros: es un agente que
corre con el sistema de archivos delante. Escribe el spec, corre `render.py`,
mira el PNG que salió y lo corrige. `render.py` levanta las plantillas del
disco a través de `marca.py`, y el catálogo del skill se arma leyendo esas
mismas carpetas.

Si esto devolviera un dict habría que enhebrarlo por el agente, por el
subproceso de render y por el generador de catálogo — tres lugares — y el
preview del estudio dejaría de renderizar exactamente como producción. Bajando
los archivos, no cambia nada de todo eso: para el resto del sistema una
plantilla que vino de la base y una que vino del despliegue son la misma cosa.

## Lo que NO hace: borrar

Una plantilla que está en el disco y no en la base se deja como está. Si
borrara, un cliente que todavía no corrió `plantillas.sql` —o al que se le
vació la tabla por accidente— se quedaría sin ninguna plantilla y sin forma de
diseñar, cuando las del despliegue estaban ahí y andaban.

La base pisa lo que trae; lo que no trae, no lo toca.
"""
import json
import logging
import os
import pathlib

import requests

from . import config

log = logging.getLogger(__name__)

TIEMPO = 10

#: Las plantillas se leen una vez por corrida y por marca.
_cache: dict[str, dict] = {}


def limpiar() -> None:
    """Olvida lo leído, para que una corrida no trabaje con lo de la anterior."""
    _cache.clear()


def carpeta(marca: str) -> pathlib.Path:
    return config.RAIZ / ".claude" / "skills" / marca / "plantillas"


def _escribir(ruta: pathlib.Path, texto: str) -> bool:
    """Escribe sólo si cambió, y de forma atómica. Devuelve si tocó el disco.

    Atómica porque el reloj dispara una corrida por minuto y dos pueden
    solaparse: un lector que agarre el archivo a mitad de escritura vería una
    plantilla cortada, y el error saldría en el render, lejos de acá.
    """
    if ruta.exists() and ruta.read_text(encoding="utf-8") == texto:
        return False
    tmp = ruta.with_suffix(ruta.suffix + ".parcial")
    tmp.write_text(texto, encoding="utf-8")
    os.replace(tmp, ruta)
    return True


def _filas(cli) -> list[dict] | None:
    """Las plantillas publicadas. `None` si esta base todavía no tiene la tabla."""
    try:
        r = requests.get(
            cli._url("plantillas"),
            headers=cli._cab(),
            params={"publicada": "is.true",
                    "select": "plantilla,version,html,contrato",
                    "order": "plantilla.asc"},
            timeout=TIEMPO,
        )
    except requests.RequestException as e:
        log.warning("[%s] no pude leer las plantillas (%s): sigo con las del "
                    "despliegue", cli.marca, e)
        return None

    # Un cliente que todavía no corrió `plantillas.sql` no es un error y no
    # merece un WARNING que después nadie mira: es el estado normal de una
    # marca que aún no migró.
    if r.status_code in (404, 400):
        log.info("[%s] esta base todavía no tiene tabla de plantillas: "
                 "uso las del despliegue", cli.marca)
        return None
    if r.status_code != 200:
        log.warning("[%s] la base contestó %s al pedir las plantillas: sigo "
                    "con las del despliegue", cli.marca, r.status_code)
        return None
    return r.json()


def sincronizar(cli, marca: str) -> dict[str, int]:
    """Baja las plantillas publicadas al skill. Devuelve {plantilla: versión}.

    Lo que devuelve va a `metricas` del diseño: mirar una pieza que salió mal y
    saber con qué versión de qué plantilla se hizo, en vez de deducirlo.
    """
    if marca in _cache:
        return _cache[marca]

    versiones: dict[str, int] = {}
    filas = _filas(cli)
    if not filas:
        _cache[marca] = versiones
        return versiones

    base = carpeta(marca)
    base.mkdir(parents=True, exist_ok=True)
    tocadas = 0

    for f in filas:
        slug = (f.get("plantilla") or "").strip()
        html, contrato = f.get("html"), f.get("contrato")
        # Una fila incompleta se saltea sin tirar abajo la sincronización: el
        # resto de las plantillas de la marca no tienen la culpa.
        if not slug or not html or not contrato:
            log.warning("[%s] la plantilla «%s» vino incompleta: la salteo",
                        marca, slug or "?")
            continue
        if "/" in slug or slug.startswith("."):
            log.warning("[%s] nombre de plantilla inválido: «%s»", marca, slug)
            continue

        destino = base / slug
        destino.mkdir(parents=True, exist_ok=True)
        tocadas += _escribir(destino / "plantilla.html", html)
        tocadas += _escribir(
            destino / "plantilla.json",
            json.dumps(contrato, ensure_ascii=False, indent=2) + "\n")
        versiones[slug] = f.get("version")

    if tocadas:
        log.info("[%s] %d plantillas publicadas, %d archivos actualizados",
                 marca, len(versiones), tocadas)
    _cache[marca] = versiones
    return versiones
