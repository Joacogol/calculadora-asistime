# -*- coding: utf-8 -*-
"""El saldo del cliente: cuánto le queda y cuánto se le cobra por cada pieza.

── Por qué esto vive en el worker y no en la app ──────────────────────────

Son tres razones y ninguna es de comodidad:

**1. El costo sólo lo conoce el worker.** Lo devuelve el SDK al terminar de
generar, en el mismo objeto que trae los tokens. La app nunca lo ve y no lo
podría calcular: tendría que replicar la tabla de precios de cada modelo y
mantenerla al día cada vez que Anthropic cambia una tarifa.

**2. El multiplicador no puede estar en el navegador.** Si la app hiciera
`precio = costo * 2`, ese `2` viaja al navegador del cliente en el JavaScript.
Cualquiera que abra las herramientas de desarrollo ve exactamente cuánto ganás
por pieza. Acá el multiplicador vive en la tabla `clientes` de la casa —el Supabase de
Asistime, ver `libro.py`— con la variable de entorno de Cloud Run como
respaldo: no está en la base del cliente ni en el código que se le entrega.

**3. El corte por saldo tiene que ser del lado del servidor.** Una validación
en la app es una sugerencia: se saltea escribiendo una fila en la tabla desde
otro lado. Y sobre todo, es el WORKER el que gasta la plata — si él no mira el
saldo, la pieza se genera igual y la API ya se cobró.

── El multiplicador ───────────────────────────────────────────────────────

`MARGEN=2.0` significa que el cliente paga el doble de lo que cuesta la API.
Desde el 7/9/2026 el primer lugar donde se mira es la fila de la marca en
`clientes` (columna `margen`), que se edita desde el tablero sin redesplegar.
Si la casa no contesta, se cae al entorno: `MARGEN_<MARCA>` —en mayúsculas y
con guiones cambiados por guión bajo— y después `MARGEN`:

    MARGEN=2.0
    MARGEN_BOSS_PADEL_DISENOS=2.5

── Qué se cobra ───────────────────────────────────────────────────────────

Todo lo que le cuesta plata a Asistime: las placas (Anthropic), los videos
generados (fal en dólares, Magnific en créditos) y las fotos editadas
(Magnific). Los créditos se convierten a dólares con `precio_credito_usd` de
la fila del cliente; si no está cargado, se anotan en el libro como créditos y
no se cobran —mejor no cobrar que cobrar un número inventado—. Una marca con
`cobra = false` (la casa misma) anota el costo y no cobra nada.

Cada consumo queda en DOS lados: el `movimientos` del cliente —su estado de
cuenta— y el `libro` de la casa —el del dueño—. Ver `libro.py`.

Ojo con leerlo como «ganás el 100%»: el margen sobre la API es sólo una parte.
Cloud Run, Supabase, el alta de la marca y tu tiempo no están adentro de este
número. Ver `claude/modelo-de-negocio.md` en el proyecto.
"""
import json
import logging
import os
import re
from datetime import datetime, timezone

import requests

from . import config

log = logging.getLogger(__name__)

TIEMPO = 30

# Cuánto saldo hace falta para arrancar una pieza. No es cero a propósito: una
# pieza cuesta entre 0,30 y 1,40 dólares y recién se sabe cuánto al terminarla,
# así que arrancar con 0,05 de saldo garantiza terminar en rojo. Con este piso
# el cliente puede quedar levemente negativo —lo que cueste la última pieza— y
# nunca mucho más.
PISO_USD = 1.50

# El redondeo del precio. A dos decimales el cliente ve «US$ 1,22» y no
# «US$ 1,2247», que parece un error de programación más que un precio.
DECIMALES = 2


def margen(marca: str) -> float:
    """El multiplicador de este cliente. Por defecto, el general."""
    from . import libro
    de_la_casa = libro.ficha(marca).get("margen")
    clave = "MARGEN_" + re.sub(r"[^A-Z0-9]+", "_", marca.upper())
    crudo = (str(de_la_casa) if de_la_casa is not None else None) \
        or os.environ.get(clave) or os.environ.get("MARGEN") or "2.0"
    try:
        v = float(crudo)
    except ValueError:
        log.warning("MARGEN «%s» no es un número; uso 2.0", crudo)
        return 2.0
    # Un margen menor a 1 sería vender a pérdida. Casi seguro es un typo
    # —poner 0.2 queriendo 2.0— y sale caro en silencio.
    if v < 1.0:
        log.warning("MARGEN %.2f es menor que 1: estarías vendiendo bajo "
                    "costo. Uso 1.0.", v)
        return 1.0
    return v


def cobra(marca: str) -> bool:
    """¿A esta marca se le cobra? La casa (Asistime) anota y no cobra."""
    from . import libro
    valor = libro.ficha(marca).get("cobra")
    return True if valor is None else bool(valor)


def precio_credito(marca: str) -> float | None:
    """Cuánto le cuesta a Asistime un crédito de Magnific, o None si no se
    cargó todavía en la fila del cliente."""
    from . import libro
    crudo = libro.ficha(marca).get("precio_credito_usd")
    if crudo is None:
        return None
    try:
        return max(0.0, float(crudo))
    except (TypeError, ValueError):
        return None


def precio(costo_usd: float, marca: str) -> float:
    """Lo que se le cobra al cliente por una pieza que nos costó `costo_usd`."""
    return round(max(0.0, float(costo_usd or 0.0)) * margen(marca), DECIMALES)


# ── La base ───────────────────────────────────────────────────────────────

def _url(cli, camino):
    return f"{cli.url}/rest/v1/{camino}"


def saldo(cli) -> float | None:
    """Cuánto le queda. `None` si el cliente todavía no tiene cobro activado.

    La diferencia entre `None` y `0.0` importa: `None` es «este cliente no
    corrió `cobro.sql`» y significa seguir trabajando como siempre. `0.0` es
    «se le acabó» y significa frenar. Confundirlos dejaría sin servicio a todos
    los clientes viejos el día que se despliegue esto.
    """
    try:
        r = requests.get(
            _url(cli, "mi_cuenta"),
            headers=cli._cab(),
            params={"select": "saldo_usd", "limit": "1"},
            timeout=TIEMPO,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        filas = r.json()
        if not filas:
            return 0.0
        return float(filas[0].get("saldo_usd") or 0.0)
    except (requests.RequestException, ValueError, TypeError):
        # Un error de red NO puede frenar la producción del día. Ante la duda
        # se atiende: perder un dólar es mucho mejor que dejar a un cliente sin
        # sus piezas por un problema nuestro.
        log.warning("[%s] no pude leer el saldo; sigo sin cobrar", cli.marca)
        return None


def puede_generar(cli) -> tuple[bool, str]:
    """¿Alcanza el saldo para arrancar una pieza?

    Devuelve (sí/no, mensaje para la persona). El mensaje se escribe pensando
    en que lo va a leer alguien que pidió un diseño y no le salió: tiene que
    decir qué pasó y qué hacer, sin jerga.
    """
    s = saldo(cli)
    if s is None:
        return True, ""
    if s >= PISO_USD:
        return True, ""
    return False, (
        "Se agotó el saldo de la cuenta. El pedido quedó guardado: apenas "
        "recargues, pedilo de nuevo y sale en minutos."
    )


def registrar(cli, pieza_id: str, costo_usd: float, detalle: str = "", *,
              tipo: str = "placa", creditos: int = 0,
              proveedor: str | None = "anthropic", modelo: str | None = None,
              metricas: dict | None = None, titulo: str | None = None,
              url: str | None = None, plantilla: str | None = None,
              avisos: list | None = None, extra: dict | None = None) -> bool:
    """Anota lo que costó una pieza: en la cuenta del cliente y en el libro.

    Devuelve si quedó registrado el CARGO al cliente. Que el libro haya
    quedado o no se ve en el log y en el tablero.

    Va DESPUÉS de entregar la pieza, no antes. Si el registro falla, el cliente
    igual se queda con su diseño: preferimos perder el cobro de una pieza antes
    que perder la pieza. Y queda en el log, así que se puede corregir a mano
    con un movimiento de tipo `ajuste`.

    `pieza_id` es el id en la tabla que corresponda: `disenos`, `reels` o
    `fotos_editadas`. Sólo las placas van en `movimientos.diseno_id` —la
    columna tiene clave foránea a `disenos`—; el resto lleva el id en el
    detalle.
    """
    from . import libro

    costo_usd = max(0.0, float(costo_usd or 0.0))
    creditos = max(0, int(creditos or 0))
    por_credito = precio_credito(cli.marca)
    costo_creditos = round(creditos * por_credito, 6) if por_credito else 0.0
    costo_total = round(costo_usd + costo_creditos, 6)

    p = precio(costo_total, cli.marca) if cobra(cli.marca) else 0.0
    cobrado_en = None
    registrado = False
    if p > 0:
        fila = {
            "tipo": "consumo",
            "monto_usd": -p,          # negativo: resta del saldo
            "costo_usd": costo_total,
            "diseno_id": pieza_id if tipo == "placa" else None,
            "detalle": (f"{tipo} {pieza_id} · {detalle}".strip(" ·")
                        if tipo != "placa" else (detalle or None)),
        }
        try:
            r = requests.post(
                _url(cli, "movimientos"),
                headers=cli._cab({"Prefer": "return=representation"}),
                data=json.dumps(fila),
                timeout=TIEMPO,
            )
            if r.status_code == 404:
                # El cliente no tiene cobro activado: no se le cobra, pero el
                # libro igual se entera de lo que costó.
                p = 0.0
            else:
                r.raise_for_status()
                try:
                    cobrado_en = (r.json() or [{}])[0].get("id")
                except ValueError:
                    cobrado_en = None
                registrado = True
                log.info("[%s] consumo %s %s · costo US$%.4f · cobrado US$%.2f",
                         cli.marca, tipo, pieza_id, costo_total, p)
        except requests.RequestException:
            log.exception("[%s] NO PUDE REGISTRAR el consumo de %s %s "
                          "(costo US$%.4f). Corregilo con un movimiento de "
                          "tipo «ajuste».", cli.marca, tipo, pieza_id, costo_total)
            p = 0.0

    met = metricas or {}
    ficha = libro.ficha(cli.marca)
    libro.anotar(
        cli.marca, tipo, pieza_id,
        proveedor=proveedor,
        modelo=modelo or met.get("modelo"),
        costo_usd=costo_total,
        creditos=creditos,
        cuenta_creditos=(ficha.get("cuenta_creditos") or "asistime") if creditos else None,
        segundos=met.get("segundos"),
        tokens_entrada=met.get("tokens_entrada"),
        tokens_salida=met.get("tokens_salida"),
        cache_lectura=met.get("cache_lectura"),
        cache_escritura=met.get("cache_escritura"),
        precio_usd=p,
        margen_aplicado=margen(cli.marca) if p > 0 else None,
        cobrado_en=cobrado_en,
        titulo=(titulo or None) and str(titulo)[:200],
        detalle=detalle or None,
        url=url,
        plantilla=plantilla,
        avisos=avisos or None,
        extra=extra or None,
    )
    return registrado


def cargar(cli, monto_usd: float, tipo: str = "carga", detalle: str = "") -> bool:
    """Suma saldo: una recarga que pagó el cliente o el incluido del abono.

    No la llama el worker — la corrés vos cuando facturás o cuando el cliente
    paga. Está acá para que el movimiento se arme siempre igual y con el mismo
    signo.
    """
    if tipo not in ("carga", "abono", "ajuste"):
        raise ValueError("tipo tiene que ser carga, abono o ajuste")
    r = requests.post(
        _url(cli, "movimientos"),
        headers=cli._cab({"Prefer": "return=minimal"}),
        data=json.dumps({"tipo": tipo, "monto_usd": round(float(monto_usd), 4),
                         "detalle": detalle or None}),
        timeout=TIEMPO,
    )
    r.raise_for_status()
    log.info("[%s] %s de US$%.2f", cli.marca, tipo, monto_usd)
    # Y en la casa, ya espejada: si no, el saldo del tablero y el del
    # cliente dicen cosas distintas desde el primer día.
    from . import libro
    c = libro.casa()
    if c is not None:
        try:
            requests.post(
                libro._url(c, "cargas"),
                headers=c._cab({"Prefer": "return=minimal"}),
                data=json.dumps({"marca": cli.marca, "tipo": tipo,
                                 "monto_usd": round(float(monto_usd), 2),
                                 "detalle": detalle or None,
                                 "quien": "cobro.cargar",
                                 "espejado_en": datetime.now(timezone.utc).isoformat()}),
                timeout=TIEMPO,
            ).raise_for_status()
        except requests.RequestException as e:
            log.warning("[%s] la carga quedó en el cliente pero no en el "
                        "libro: %s", cli.marca, e)
    return True
