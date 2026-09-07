#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sube las plantillas del skill a la base del cliente y las publica.

    python3 herramientas/sembrar-plantillas.py boss-padel-disenos
    python3 herramientas/sembrar-plantillas.py boss-padel-disenos --probar
    python3 herramientas/sembrar-plantillas.py boss-padel-disenos --solo torneo,socio

Se corre una vez después de aplicar `plantillas.sql`, para que la base arranque
con lo mismo que trae el despliegue. Después de eso el camino normal es al
revés: se edita y se publica en la base, y el worker las baja al skill en cada
corrida.

Toma las claves del mismo lugar que el worker (`CLIENTES` y las variables de
entorno que ahí se nombran), así que corre con el mismo `.env` y no hay una
segunda copia de nada.

## Es idempotente

Compara contra lo que ya está publicado y sólo sube lo que cambió. Sin eso,
correrlo dos veces dejaría dos versiones idénticas y el historial —que es
justamente para lo que sirve versionar— se volvería ilegible.

## Sube y publica en un solo paso

Es correcto para sembrar: lo que está en el despliegue ya está en producción,
así que publicarlo no cambia ninguna pieza. Para una corrección de verdad el
camino es el estudio, que guarda el borrador, deja verlo y recién ahí publica.
"""
import json
import pathlib
import sys

import requests

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from app import config          # noqa: E402
from app.supa import Cliente    # noqa: E402

TIEMPO = 30


def _cliente(marca: str) -> Cliente:
    for datos in config.clientes():
        if datos["marca"] == marca:
            cli = Cliente(**datos)
            if not cli.configurado:
                raise SystemExit(
                    f"«{marca}» está en CLIENTES pero sin URL o sin clave. "
                    f"Revisá la variable de entorno que nombra su `key_env`.")
            return cli
    conocidos = ", ".join(d["marca"] for d in config.clientes())
    raise SystemExit(f"no encuentro «{marca}» en CLIENTES. Hay: {conocidos}")


def _publicadas(cli) -> dict[str, dict]:
    r = requests.get(cli._url("plantillas"), headers=cli._cab(), timeout=TIEMPO,
                     params={"publicada": "is.true",
                             "select": "plantilla,version,html,contrato"})
    if r.status_code in (400, 404):
        raise SystemExit(
            "esta base todavía no tiene la tabla `plantillas`. "
            "Corré `plantillas.sql` en el SQL Editor de su Supabase primero.")
    if r.status_code != 200:
        raise SystemExit(f"no pude leer las plantillas (HTTP {r.status_code}): "
                         f"{r.text[:300]}")
    return {f["plantilla"]: f for f in r.json()}


def _guardar(cli, slug, html, contrato, quien):
    r = requests.post(
        cli._url("rpc/guardar_plantilla"), headers=cli._cab(), timeout=TIEMPO,
        json={"p_plantilla": slug, "p_html": html, "p_contrato": contrato,
              "p_etiqueta": "sembrada desde el despliegue",
              "p_quien": quien, "p_publicar": True})
    if r.status_code not in (200, 201):
        raise SystemExit(f"no pude guardar «{slug}» (HTTP {r.status_code}): "
                         f"{r.text[:300]}")
    return r.json()


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    marca = argv[1]
    probar = "--probar" in argv
    solo = None
    if "--solo" in argv:
        solo = {s.strip() for s in argv[argv.index("--solo") + 1].split(",")}

    carpeta = RAIZ / ".claude" / "skills" / marca / "plantillas"
    if not carpeta.is_dir():
        raise SystemExit(f"«{marca}» no tiene carpeta `plantillas/`")

    cli = _cliente(marca)
    publicadas = _publicadas(cli)

    nuevas = iguales = 0
    for d in sorted(carpeta.iterdir()):
        slug = d.name
        if not (d / "plantilla.json").exists() or (solo and slug not in solo):
            continue
        html = (d / "plantilla.html").read_text(encoding="utf-8")
        contrato = json.loads((d / "plantilla.json").read_text(encoding="utf-8"))

        actual = publicadas.get(slug)
        if actual and actual["html"] == html and actual["contrato"] == contrato:
            iguales += 1
            continue

        if probar:
            print(f"  subiría  {slug}"
                  + (f" (hoy v{actual['version']})" if actual else " (nueva)"))
            nuevas += 1
            continue

        fila = _guardar(cli, slug, html, contrato, "sembrar-plantillas")
        v = fila.get("version") if isinstance(fila, dict) else "?"
        print(f"  publicada  {slug}  v{v}")
        nuevas += 1

    verbo = "subiría" if probar else "subí"
    print(f"· {verbo} {nuevas} · {iguales} ya estaban al día")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
