# -*- coding: utf-8 -*-
"""El libro central: lo que le cuesta a Asistime cada pieza de cada cliente.

── Por qué existe ─────────────────────────────────────────────────────────

Hasta el 7/9/2026 el costo de una pieza quedaba en la base del cliente que la
pidió —`disenos.metricas`, `reels.metricas.costo`, `fotos_editadas`— y en
ningún otro lado. Cuatro clientes, cuatro bases, cuatro unidades distintas.
Saber cuánto se gastó en un mes era abrir las cuatro y sumar a mano, y el
cobro sólo miraba una de las cuatro cosas: las placas. Los reels y las fotos
costaban plata y no se le cobraban a nadie.

Este módulo escribe UNA fila por cosa que costó, en UNA base: el Supabase de
Asistime (la casa). Cada cliente sigue teniendo su `movimientos` —ése es su
estado de cuenta, lo que él ve—; el libro es lo que ve el dueño.

── Tres reglas ────────────────────────────────────────────────────────────

1. **Nunca frena la producción.** Si la casa no contesta, la pieza sale igual
   y el cliente igual recibe su cargo. Queda en el log, y el tablero avisa
   cuando un consumo del cliente no tiene su fila en el libro.
2. **La configuración comercial vive en la tabla `clientes`** de la casa
   —margen, si cobra, precio del crédito— y se lee una vez por corrida. Si
   no se puede leer, `cobro.py` cae a la variable de entorno como hasta
   ahora. Cambiar el margen de un cliente es editar una fila, no redesplegar.
3. **El tablero anota, el worker ejecuta.** Una carga de saldo hecha desde el
   tablero queda en `cargas` de la casa; el worker, que es el único con la
   clave del cliente, la copia a su `movimientos` en el siguiente ciclo.

── Cómo se ubica la casa ──────────────────────────────────────────────────

Asistime ya es un cliente del worker (`asistime-disenos`), con su URL y su
service_role en el registro. La casa es ese mismo cliente: no hace falta
una clave más. `LIBRO_MARCA` cambia cuál es; `LIBRO_URL` + `LIBRO_KEY` la
apuntan a otro proyecto sin pasar por el registro.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone

import requests

from . import config
from .supa import Cliente

log = logging.getLogger(__name__)

TIEMPO = 20
MARCA_CASA = os.environ.get("LIBRO_MARCA", "asistime-disenos")

TIPOS = ("placa", "reel", "video", "foto", "publicacion")

_casa: Cliente | None = None
_casa_buscada = False
_clientes: dict | None = None
_avisado = False


def olvidar():
    """Se llama al arrancar cada corrida: la configuración se relee."""
    global _casa, _casa_buscada, _clientes, _avisado
    _casa = None
    _casa_buscada = False
    _clientes = None
    _avisado = False


def casa() -> Cliente | None:
    """La base donde vive el libro, o None si no hay forma de llegar."""
    global _casa, _casa_buscada
    if _casa_buscada:
        return _casa
    _casa_buscada = True
    url = (os.environ.get("LIBRO_URL") or "").rstrip("/")
    key = os.environ.get("LIBRO_KEY") or ""
    if url and key:
        _casa = Cliente(marca=MARCA_CASA, url=url, key=key, nombre="casa")
        return _casa
    try:
        for c in config.clientes():
            if c.get("marca") == MARCA_CASA and c.get("url") and c.get("key"):
                _casa = Cliente(marca=c["marca"], url=c["url"], key=c["key"],
                                nombre=c.get("nombre") or "casa")
                break
    except Exception:                                   # noqa: BLE001
        log.warning("no pude leer la lista de clientes para ubicar la casa")
    if _casa is None:
        log.warning("sin libro central: «%s» no está en el registro con URL y "
                    "clave. Los costos quedan sólo en cada cliente.", MARCA_CASA)
    return _casa


def _url(c: Cliente, camino: str) -> str:
    return f"{c.url}/rest/v1/{camino}"


def clientes() -> dict:
    """`{marca: fila de public.clientes}`. Vacío si no se pudo leer."""
    global _clientes, _avisado
    if _clientes is not None:
        return _clientes
    c = casa()
    if c is None:
        _clientes = {}
        return _clientes
    try:
        r = requests.get(_url(c, "clientes"), headers=c._cab(),
                         params={"select": "*"}, timeout=TIEMPO)
        r.raise_for_status()
        _clientes = {f["marca"]: f for f in r.json() if f.get("marca")}
    except (requests.RequestException, ValueError, TypeError, KeyError):
        if not _avisado:
            log.warning("no pude leer `clientes` del libro; el margen sale "
                        "del entorno en esta corrida")
            _avisado = True
        _clientes = {}
    return _clientes


def ficha(marca: str) -> dict:
    """La configuración comercial de esta marca, o `{}`."""
    return clientes().get(marca) or {}


def anotar(marca: str, tipo: str, pieza_id: str, **campos) -> bool:
    """Una fila en el libro. Si ya estaba (misma marca, tipo y pieza), la pisa.

    Devuelve si quedó anotada. No levanta: el libro es contabilidad, y la
    contabilidad no puede tirar abajo la pieza que está contando.
    """
    if tipo not in TIPOS:
        log.warning("[%s] tipo de libro desconocido «%s»; anoto como placa",
                    marca, tipo)
        tipo = "placa"
    c = casa()
    if c is None:
        return False
    fila = {"marca": marca, "tipo": tipo, "pieza_id": pieza_id}
    for k, v in campos.items():
        if v is None:
            continue
        fila[k] = v
    try:
        r = requests.post(
            _url(c, "libro"),
            headers=c._cab({"Prefer": "resolution=merge-duplicates,return=minimal"}),
            params={"on_conflict": "marca,tipo,pieza_id"},
            data=json.dumps(fila, default=str),
            timeout=TIEMPO,
        )
        if r.status_code == 409:
            # La marca no está en `clientes`: la FK no deja anotar. Se avisa
            # con nombre para que se dé de alta, y la pieza sigue su camino.
            log.warning("[%s] el libro no acepta la fila: ¿la marca está en "
                        "`clientes` de la casa? %s", marca, r.text[:200])
            return False
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        log.warning("[%s] no pude anotar %s %s en el libro: %s",
                    marca, tipo, pieza_id, e)
        return False


def espejar_cargas(cli: Cliente) -> int:
    """Copia al `movimientos` del cliente las cargas anotadas desde el tablero.

    Devuelve cuántas copió. Va ANTES de atender los pedidos del cliente, para
    que una recarga hecha recién ya cuente cuando `cobro.puede_generar` mire
    el saldo.
    """
    c = casa()
    if c is None:
        return 0
    try:
        r = requests.get(_url(c, "cargas"), headers=c._cab(),
                         params={"marca": f"eq.{cli.marca}",
                                 "espejado_en": "is.null", "error": "is.null",
                                 "order": "creado_en.asc", "limit": "20"},
                         timeout=TIEMPO)
        r.raise_for_status()
        pendientes = r.json()
    except (requests.RequestException, ValueError):
        log.warning("[%s] no pude leer las cargas pendientes del libro", cli.marca)
        return 0

    copiadas = 0
    for carga in pendientes:
        fila = {"tipo": carga["tipo"],
                "monto_usd": round(float(carga["monto_usd"]), 4),
                "detalle": carga.get("detalle") or None}
        try:
            r = requests.post(_url(cli, "movimientos"),
                              headers=cli._cab({"Prefer": "return=representation"}),
                              data=json.dumps(fila), timeout=TIEMPO)
            if r.status_code == 404:
                _marcar_carga(c, carga["id"],
                              error="el cliente no tiene cobro activado "
                                    "(falta correr cobro.sql)")
                continue
            r.raise_for_status()
            devuelto = r.json()
            espejo = (devuelto[0].get("id") if devuelto else None)
        except (requests.RequestException, ValueError, IndexError) as e:
            # Se deja SIN marcar: la próxima corrida lo reintenta. Marcarlo
            # como error por una caída de red sería perderle una recarga al
            # cliente.
            log.warning("[%s] no pude copiar la carga %s: %s",
                        cli.marca, carga["id"], e)
            continue
        _marcar_carga(c, carga["id"],
                      espejado_en=datetime.now(timezone.utc).isoformat(),
                      espejo_id=espejo)
        log.info("[%s] %s de US$%.2f copiada a su cuenta",
                 cli.marca, carga["tipo"], float(carga["monto_usd"]))
        copiadas += 1
    return copiadas


def _marcar_carga(c: Cliente, carga_id: str, **campos):
    try:
        requests.patch(_url(c, "cargas"), headers=c._cab(),
                       params={"id": f"eq.{carga_id}"},
                       data=json.dumps(campos), timeout=TIEMPO).raise_for_status()
    except requests.RequestException as e:
        log.warning("no pude marcar la carga %s en el libro: %s", carga_id, e)


def _contar(cli: Cliente, tabla: str, **filtros) -> int | None:
    """Cuántas filas cumplen los filtros, sin traerlas. None si no se pudo."""
    try:
        r = requests.get(_url(cli, tabla),
                         headers=cli._cab({"Prefer": "count=exact",
                                           "Range": "0-0"}),
                         params={"select": "id", **filtros}, timeout=TIEMPO)
        if r.status_code not in (200, 206):
            return None
        rango = r.headers.get("Content-Range", "")
        return int(rango.rsplit("/", 1)[-1])
    except (requests.RequestException, ValueError):
        return None


def latir(cli: Cliente, **detalle) -> bool:
    """El latido del cliente en la casa: cuándo se lo atendió por última vez,
    cuántos pedidos esperan y cuántos fallaron en el día."""
    c = casa()
    if c is None:
        return False
    hace_un_dia = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    pendientes = _contar(cli, "disenos", estado="eq.pendiente")
    errores = _contar(cli, "disenos", estado="eq.error",
                      actualizado_en=f"gte.{hace_un_dia}")
    # La cuenta de Instagram vive en la base del cliente y el tablero no la
    # puede leer: viaja en el latido. Sin el token, sólo cuándo vence.
    ig = None
    try:
        r = requests.get(_url(cli, "cuentas_ig"), headers=cli._cab(),
                         params={"select": "usuario,expira_en,activa,mensaje",
                                 "order": "creado_en.desc", "limit": "1"},
                         timeout=TIEMPO)
        if r.status_code == 200 and r.json():
            ig = r.json()[0]
    except (requests.RequestException, ValueError):
        ig = None
    fila = {"marca": cli.marca,
            "ultimo_ciclo": datetime.now(timezone.utc).isoformat(),
            "pendientes": pendientes or 0,
            "errores": errores or 0,
            "version": config.VERSION,
            "detalle": {**{k: v for k, v in detalle.items() if v is not None},
                        **({"ig": ig} if ig else {})}}
    try:
        r = requests.post(_url(c, "latidos"),
                          headers=c._cab({"Prefer": "resolution=merge-duplicates,"
                                                    "return=minimal"}),
                          params={"on_conflict": "marca"},
                          data=json.dumps(fila), timeout=TIEMPO)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        log.warning("[%s] no pude dejar el latido: %s", cli.marca, e)
        return False
