#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Carga al libro de la casa lo que ya se hizo antes de que el libro existiera.

    python3 herramientas/cargar-libro.py               # los cuatro, desde el registro
    python3 herramientas/cargar-libro.py boss-padel-disenos
    python3 herramientas/cargar-libro.py --simular     # cuenta y no escribe

Corre en Cloud Shell: lee las claves del registro (`clientes-registro`) con
`gcloud`, igual que `registro.py`. Con `LIBRO_URL` + `LIBRO_KEY` en el
entorno, la casa se apunta a otro proyecto sin pasar por el registro.

── La regla ───────────────────────────────────────────────────────────────

**Lo que pasó, pasó** (decisión del 7/9/2026). Las placas que ya se cobraron
entran con el precio que se cobró —está en el `movimientos` del cliente, y
la fila del libro apunta a ese movimiento—. Los reels, videos y fotos entran
con precio 0: costaron, no se cobraron, y no se van a cobrar para atrás. El
libro igual los tiene, porque el costo fue real y el tablero lo muestra.

Las cargas de saldo de cada cliente (`carga`, `abono`, `ajuste`) entran a
`cargas` de la casa ya marcadas como espejadas: ya están en el cliente.

── Se puede correr de nuevo ───────────────────────────────────────────────

El libro hace upsert por (marca, tipo, pieza) y las cargas se saltean si su
`espejo_id` ya está. Correrlo dos veces deja lo mismo que una.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import sys
from datetime import datetime, timezone

import requests

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

TIEMPO = 60
MARCA_CASA = os.environ.get("LIBRO_MARCA", "asistime-disenos")
TANDA = 100
RELLENO = {"creditos": 0, "costo_usd": 0.0, "precio_usd": 0.0, "extra": {}}


def _registro() -> list[dict]:
    spec = importlib.util.spec_from_file_location(
        "registro_cli", pathlib.Path(__file__).with_name("registro.py"))
    reg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reg)
    return reg.bajar()


def _clave(c: dict) -> str:
    return (c.get("service_role") or c.get("key") or "").strip()


class Base:
    def __init__(self, marca: str, url: str, key: str):
        self.marca, self.url, self.key = marca, url.rstrip("/"), key

    def _cab(self, extra=None):
        c = {"apikey": self.key, "Authorization": f"Bearer {self.key}",
             "Content-Type": "application/json"}
        if extra:
            c.update(extra)
        return c

    def leer(self, tabla: str, **params) -> list[dict] | None:
        """Toda la tabla (de a 1000). None si la tabla no existe."""
        filas, desde = [], 0
        while True:
            r = requests.get(f"{self.url}/rest/v1/{tabla}",
                             headers=self._cab({"Range": f"{desde}-{desde + 999}"}),
                             params=params, timeout=TIEMPO)
            if r.status_code == 404:
                return None
            if r.status_code == 416:          # más allá del final
                break
            r.raise_for_status()
            tanda = r.json()
            filas.extend(tanda)
            if len(tanda) < 1000:
                break
            desde += 1000
        return filas

    def escribir(self, tabla: str, filas: list[dict], on_conflict: str | None = None):
        # PostgREST exige que todas las filas de una tanda tengan las MISMAS
        # claves («All object keys must match»): una placa trae tokens y un
        # reel no. Se completa con null lo que falte en cada una.
        # Y lo que falta no puede ser null en las columnas obligatorias
        # (`creditos`, `costo_usd`, `precio_usd`, `extra`): un null explícito
        # NO usa el default de la tabla, lo rechaza con 23502.
        claves = sorted({k for f in filas for k in f})
        filas = [{k: f.get(k, RELLENO.get(k)) for k in claves} for f in filas]
        for i in range(0, len(filas), TANDA):
            r = requests.post(
                f"{self.url}/rest/v1/{tabla}",
                headers=self._cab({"Prefer": "resolution=merge-duplicates,return=minimal"
                                   if on_conflict else "return=minimal"}),
                params={"on_conflict": on_conflict} if on_conflict else None,
                data=json.dumps(filas[i:i + TANDA], default=str), timeout=TIEMPO)
            if r.status_code >= 400:
                raise SystemExit(f"{tabla}: {r.status_code} {r.text[:400]}")


def _num(x, default=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _plantilla(spec) -> str | None:
    if isinstance(spec, list) and spec:
        spec = spec[0]
    if isinstance(spec, dict) and spec.get("plantilla"):
        return str(spec["plantilla"])[:80]
    return None


def placas(cli: Base, cobrados: dict) -> list[dict]:
    filas = cli.leer("disenos", estado="eq.listo",
                     select="id,creado_en,titulo,urls,metricas,formatos,spec,notas") or []
    salida = []
    for d in filas:
        met = d.get("metricas") or {}
        mov = cobrados.get(d["id"])
        salida.append({
            "marca": cli.marca, "tipo": "placa", "pieza_id": d["id"],
            "creado_en": d["creado_en"],
            "proveedor": "anthropic", "modelo": met.get("modelo"),
            "costo_usd": round(_num(met.get("costo_usd")), 6),
            "segundos": met.get("segundos"),
            "tokens_entrada": met.get("tokens_entrada"),
            "tokens_salida": met.get("tokens_salida"),
            "cache_lectura": met.get("cache_lectura"),
            "cache_escritura": met.get("cache_escritura"),
            "precio_usd": round(-_num(mov["monto_usd"]), 2) if mov else 0.0,
            "margen_aplicado": (round(-_num(mov["monto_usd"]) / _num(met.get("costo_usd")), 3)
                                if mov and _num(met.get("costo_usd")) > 0 else None),
            "cobrado_en": mov["id"] if mov else None,
            "titulo": (d.get("titulo") or "")[:200] or None,
            "detalle": " · ".join(d.get("formatos") or []) or None,
            "url": (d.get("urls") or [None])[0],
            "plantilla": _plantilla(d.get("spec")),
            "avisos": [d["notas"]] if d.get("notas") else None,
            "extra": {"turnos": met.get("turnos"), "version": met.get("version"),
                      "cargado": "historial"},
        })
    return salida


def reels(cli: Base) -> list[dict]:
    filas = cli.leer("reels", estado="eq.listo",
                     select="id,creado_en,titulo,mensaje,modelo,resolucion,duracion,"
                            "url,clip_url,creditos_gastados,creditos_estimados,metricas,notas,origen")
    if filas is None:
        return []
    salida = []
    for f in filas:
        met = f.get("metricas") or {}
        costo = met.get("costo") or {}
        monto, moneda = _num(costo.get("monto")), costo.get("moneda")
        cred = int(f.get("creditos_gastados") or f.get("creditos_estimados") or 0)
        if moneda == "creditos" and not cred:
            cred = int(monto)
        modelo = f.get("modelo") or None
        prov = met.get("proveedor") or ("magnific" if modelo else "motor")
        salida.append({
            "marca": cli.marca,
            "tipo": "video" if met.get("pieza") == "video" else "reel",
            "pieza_id": f["id"], "creado_en": f["creado_en"],
            "proveedor": prov, "modelo": modelo,
            "costo_usd": round(monto, 6) if moneda == "usd" else 0.0,
            "creditos": cred, "cuenta_creditos": "asistime" if cred else None,
            "precio_usd": 0.0,
            "titulo": ((f.get("titulo") or f.get("mensaje") or "")[:120]) or None,
            "detalle": " · ".join(x for x in (modelo, f.get("resolucion"),
                                              f"{f['duracion']}s" if f.get("duracion") else None) if x) or None,
            "url": f.get("url") or f.get("clip_url"),
            "avisos": [f["notas"]] if f.get("notas") else None,
            "extra": {"duracion": f.get("duracion"), "resolucion": f.get("resolucion"),
                      "origen": f.get("origen"), "cargado": "historial"},
        })
    return salida


def fotos(cli: Base) -> list[dict]:
    filas = cli.leer("fotos_editadas", estado="eq.listo",
                     select="id,creado_en,verbo,instruccion,formato,modelo,url,"
                            "creditos_estimados,creditos_gastados")
    if filas is None:
        return []
    return [{
        "marca": cli.marca, "tipo": "foto", "pieza_id": f["id"], "creado_en": f["creado_en"],
        "proveedor": "magnific", "modelo": f.get("modelo"),
        "costo_usd": 0.0,
        "creditos": int(f.get("creditos_gastados") or f.get("creditos_estimados") or 0),
        "cuenta_creditos": "asistime",
        "precio_usd": 0.0,
        "titulo": ((f.get("instruccion") or f.get("verbo") or "")[:120]) or None,
        "detalle": f.get("verbo"), "url": f.get("url"),
        "extra": {"verbo": f.get("verbo"), "formato": f.get("formato"), "cargado": "historial"},
    } for f in filas]


def movimientos(cli: Base) -> tuple[dict, list[dict]]:
    """(consumos por diseno_id, cargas). Vacío si el cliente no tiene cobro."""
    filas = cli.leer("movimientos", select="id,creado_en,tipo,monto_usd,costo_usd,diseno_id,detalle")
    if filas is None:
        return {}, []
    consumos = {m["diseno_id"]: m for m in filas if m["tipo"] == "consumo" and m.get("diseno_id")}
    cargas = [{
        "marca": cli.marca, "creado_en": m["creado_en"], "tipo": m["tipo"],
        "monto_usd": round(_num(m["monto_usd"]), 2), "detalle": m.get("detalle"),
        "quien": "historial", "espejado_en": m["creado_en"], "espejo_id": m["id"],
    } for m in filas if m["tipo"] in ("carga", "abono", "ajuste")]
    return consumos, cargas


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    simular = "--simular" in sys.argv
    registro = _registro()
    if not registro:
        raise SystemExit("el registro está vacío o no se pudo leer: ¿estás en Cloud Shell?")

    url, key = os.environ.get("LIBRO_URL", "").rstrip("/"), os.environ.get("LIBRO_KEY", "")
    if not (url and key):
        casa_reg = next((c for c in registro if c["marca"] == MARCA_CASA), None)
        if not casa_reg:
            raise SystemExit(f"«{MARCA_CASA}» no está en el registro; no sé dónde está el libro")
        url, key = casa_reg["url"], _clave(casa_reg)
    casa = Base(MARCA_CASA, url, key)

    conocidas = {c["marca"] for c in (casa.leer("clientes", select="marca") or [])}
    ya_espejadas = {c["espejo_id"] for c in (casa.leer("cargas", select="espejo_id") or [])
                    if c.get("espejo_id")}

    for c in registro:
        marca = c["marca"]
        if args and marca not in args:
            continue
        if marca not in conocidas:
            print(f"· {marca}: no está en `clientes` de la casa, lo salteo (dalo de alta en el tablero)")
            continue
        cli = Base(marca, c["url"], _clave(c))
        consumos, cargas = movimientos(cli)
        filas = placas(cli, consumos) + reels(cli) + fotos(cli)
        cargas = [k for k in cargas if k["espejo_id"] not in ya_espejadas]
        por_tipo = {}
        for f in filas:
            por_tipo[f["tipo"]] = por_tipo.get(f["tipo"], 0) + 1
        costo = sum(f["costo_usd"] for f in filas)
        precio = sum(f["precio_usd"] for f in filas)
        cred = sum(f.get("creditos", 0) for f in filas)
        print(f"· {marca}: {len(filas)} filas ({', '.join(f'{v} {k}' for k, v in sorted(por_tipo.items()))}) · "
              f"costo US$ {costo:.2f} · cobrado US$ {precio:.2f} · {cred} créditos · "
              f"{len(cargas)} carga(s) nueva(s)")
        if simular:
            continue
        if filas:
            casa.escribir("libro", filas, on_conflict="marca,tipo,pieza_id")
        if cargas:
            casa.escribir("cargas", cargas)
    print("✓ simulado, no escribí nada" if simular else "✓ libro cargado")


if __name__ == "__main__":
    main()
