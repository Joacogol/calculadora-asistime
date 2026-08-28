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
por pieza. Acá el multiplicador vive en una variable de entorno de Cloud Run:
no está en la base del cliente ni en el código que se le entrega.

**3. El corte por saldo tiene que ser del lado del servidor.** Una validación
en la app es una sugerencia: se saltea escribiendo una fila en la tabla desde
otro lado. Y sobre todo, es el WORKER el que gasta la plata — si él no mira el
saldo, la pieza se genera igual y la API ya se cobró.

── El multiplicador ───────────────────────────────────────────────────────

`MARGEN=2.0` significa que el cliente paga el doble de lo que cuesta la API.
Se puede fijar por cliente con `MARGEN_<MARCA>`, en mayúsculas y con guiones
cambiados por guión bajo:

    MARGEN=2.0
    MARGEN_BOSS_PADEL_DISENOS=2.5

Ojo con leerlo como «ganás el 100%»: el margen sobre la API es sólo una parte.
Cloud Run, Supabase, el alta de la marca y tu tiempo no están adentro de este
número. Ver `claude/modelo-de-negocio.md` en el proyecto.
"""
import json
import logging
import os
import re

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
    clave = "MARGEN_" + re.sub(r"[^A-Z0-9]+", "_", marca.upper())
    crudo = os.environ.get(clave) or os.environ.get("MARGEN") or "2.0"
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


def registrar(cli, diseno_id: str, costo_usd: float, detalle: str = "") -> bool:
    """Anota el consumo de una pieza. Devuelve si quedó registrado.

    Va DESPUÉS de entregar la pieza, no antes. Si el registro falla, el cliente
    igual se queda con su diseño: preferimos perder el cobro de una pieza antes
    que perder la pieza. Y queda en el log, así que se puede corregir a mano
    con un movimiento de tipo `ajuste`.
    """
    p = precio(costo_usd, cli.marca)
    if p <= 0:
        return False
    fila = {
        "tipo": "consumo",
        "monto_usd": -p,          # negativo: resta del saldo
        "costo_usd": round(float(costo_usd or 0.0), 6),
        "diseno_id": diseno_id,
        "detalle": detalle or None,
    }
    try:
        r = requests.post(
            _url(cli, "movimientos"),
            headers=cli._cab({"Prefer": "return=minimal"}),
            data=json.dumps(fila),
            timeout=TIEMPO,
        )
        if r.status_code == 404:
            return False          # el cliente no tiene cobro activado
        r.raise_for_status()
        log.info("[%s] consumo %s · costo US$%.4f · cobrado US$%.2f",
                 cli.marca, diseno_id, costo_usd, p)
        return True
    except requests.RequestException:
        log.exception("[%s] NO PUDE REGISTRAR el consumo del diseño %s "
                      "(costo US$%.4f). Corregilo con un movimiento de tipo "
                      "«ajuste».", cli.marca, diseno_id, costo_usd)
        return False


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
    return True
