# -*- coding: utf-8 -*-
"""Las reglas de marca, leídas de Asistime en cada corrida.

Hasta acá el criterio de cada marca —qué foto usar, si va el teléfono, el tono
del caption, qué no hacer nunca— vivía adentro del `SKILL.md`, o sea adentro
del zip que se despliega. Cambiar una regla era editar un archivo, armar un
zip, subirlo a Cloud Shell y esperar el build: el cliente no podía, y yo era el
cuello de botella de su propia marca.

Ahora ese criterio es un **Documento de Asistime**, y el worker lo lee acá.
El club lo edita desde la plataforma —con versiones, etiqueta de cambio y
vuelta atrás, que Asistime ya trae— y la pieza siguiente sale con el cambio.
Sin despliegue.

Lo que NO se movió: el motor. Las plantillas, cómo se dibuja cada una, los
formatos y el catálogo siguen siendo código. La división es la de siempre —
**el motor dice qué se PUEDE hacer, el manual dice qué HAY que hacer.**

## Por qué un solo GET

`GET /api/tenants/{tenant}/documents/{id}` devuelve el documento con
`currentVersion` adentro, y el texto publicado viene en `currentVersion.content`.
No hace falta pedir después la versión: una llamada y listo.

## Por qué nunca frena un diseño

Si Asistime no contesta, contesta mal, o el documento está vacío, esto devuelve
`None` y el diseño se genera igual con lo que trae el skill. Es deliberado: un
club no puede quedarse sin sus piezas del día porque una API tardó. Lo que sí
hace es dejarlo escrito en el log, para que un manual que dejó de llegar no
pase inadvertido durante una semana.
"""
import logging
import os

import requests

from . import config

log = logging.getLogger(__name__)

#: Corto a propósito. Un diseño tarda entre 2 y 4 minutos, así que esperar
#: medio minuto por el manual no cambiaría nada bueno: si a los 8 segundos no
#: llegó, algo está mal y conviene seguir sin él.
TIEMPO = 8

#: Tope de tamaño, y es el mismo que impone Asistime en el campo de contenido:
#: 30.000 caracteres. Ponerle uno más alto no servía de nada —nadie puede
#: guardar más que eso— y ponerle uno más bajo habría recortado en silencio un
#: manual que la plataforma acepta entero. Son unos 7.500 tokens, y el manual
#: entra al prompt de CADA pieza: el 79% de lo que cuesta un diseño es contexto.
TOPE = 30_000

#: Una lectura por corrida y por marca. Sin esto, diez pedidos en la misma
#: corrida son diez llamadas idénticas.
_cache: dict[str, tuple[str | None, int | None]] = {}


def _ficha(marca: str) -> dict:
    """De qué tenant y qué documento es el manual de esta marca.

    Vive en el `marca.json` del skill y no en una variable de entorno porque no
    es un secreto: es un dato de la marca, y ahí es donde se busca todo lo demás
    de la marca. La clave de API sí es secreto y va aparte.
    """
    from .disenador import _ficha as ficha_de_marca
    return (ficha_de_marca(marca) or {}).get("asistime") or {}


def _nombre_clave(marca: str) -> str:
    """En qué variable de entorno está la clave de Asistime de esta marca.

    Había una sola, `ASISTIME_CLAVE`, para todo el worker. Eso alcanzaba con un
    cliente y se rompe con dos: **la clave de Asistime está atada a un tenant**.
    Se comprobó pidiéndole a la de Boss que escribiera un documento de Clínica
    —contestó 403, que es lo correcto—, y con una sola variable el worker podría
    leer el manual de una marca o el de la otra, nunca los dos.

    Así que cada marca puede nombrar la suya en su `marca.json`, igual que ya
    hacen con la de Supabase en `clientes.json`. La que no la nombre sigue
    usando `ASISTIME_CLAVE` y no se entera del cambio.

    Cuando una marca SÍ la nombra, no se cae de vuelta a la compartida a
    propósito: mandarle a un tenant la clave de otro da 403 —un error que se
    lee como «no tenés permiso» y manda a buscar el problema donde no está—
    en vez de un «falta la clave» que dice la verdad.
    """
    return _ficha(marca).get("clave_env") or "ASISTIME_CLAVE"


def _clave(marca: str) -> str:
    """La clave, sin lo que se cuele alrededor.

    El `.strip()` no es adorno. La clave se pega a mano en una terminal y de ahí
    va a Secret Manager: un Enter de más al pegar, y el header sale con un `\\n`
    adentro. La API contesta 401 «Authentication required», exactamente el mismo
    cuerpo que si no hubiéramos mandado clave — así que desde el log es
    imposible distinguir «la pegaron mal» de «no la reconoce». Una hora se fue
    ahí. Limpiarla acá hace que ese error no pueda volver a pasar.
    """
    return (os.environ.get(_nombre_clave(marca)) or "").strip()


def limpiar() -> None:
    """Olvida lo leído. El ciclo la llama al empezar, así una corrida nunca
    trabaja con el manual que se leyó en la corrida anterior."""
    _cache.clear()


def leer(marca: str) -> tuple[str | None, int | None]:
    """El texto del manual publicado, y qué número de versión es.

    Devuelve `(None, None)` cuando no hay manual configurado o no se pudo
    traer. El número de versión se guarda después en las métricas del diseño:
    es lo que permite mirar una pieza que salió mal y saber con qué versión del
    manual se hizo, en vez de deducirlo.
    """
    if marca in _cache:
        return _cache[marca]

    resultado: tuple[str | None, int | None] = (None, None)
    ficha, clave = _ficha(marca), _clave(marca)
    tenant, documento = ficha.get("tenant"), ficha.get("documento")

    if not (tenant and documento):
        # Normal: una marca que todavía no migró su manual. No es un error y no
        # merece un WARNING que después nadie mira.
        _cache[marca] = resultado
        return resultado

    if not clave:
        log.warning("[%s] hay manual configurado pero falta %s: sigo con "
                    "el skill", marca, _nombre_clave(marca))
        _cache[marca] = resultado
        return resultado

    url = (f"{config.ASISTIME_API}/api/tenants/{tenant}"
           f"/documents/{documento}")
    try:
        r = requests.get(url, headers={"X-API-KEY": clave}, timeout=TIEMPO)
        if r.status_code != 200:
            # El cuerpo del error trae `message` y `correlationId`, que es lo
            # que le sirve a quien tenga que mirarlo del lado de Asistime.
            log.warning("[%s] el manual dio %s: %s", marca, r.status_code,
                        r.text[:300])
            _cache[marca] = resultado
            return resultado

        d = r.json()
        version = d.get("currentVersion") or {}
        texto = (version.get("content") or "").strip()
        numero = version.get("versionNumber")

        if not texto:
            # Un documento sin contenido publicado es un caso real: alguien
            # creó el documento y todavía no publicó ninguna versión. Se avisa
            # porque desde afuera se ve igual que «no hay manual».
            log.warning("[%s] el manual existe pero no tiene texto publicado",
                        marca)
            _cache[marca] = resultado
            return resultado

        if len(texto) > TOPE:
            log.warning("[%s] el manual mide %d caracteres y el tope es %d: "
                        "va recortado", marca, len(texto), TOPE)
            texto = texto[:TOPE] + "\n\n[…recortado por tamaño…]"

        log.info("[%s] manual v%s · %d caracteres", marca, numero, len(texto))
        resultado = (texto, numero)

    except Exception as e:
        log.warning("[%s] no pude leer el manual (%s): sigo con el skill",
                    marca, e)

    _cache[marca] = resultado
    return resultado
