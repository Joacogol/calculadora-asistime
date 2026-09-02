#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publica el catálogo de plantillas de una marca como Documento de Asistime.

    ASISTIME_CLAVE=… python3 herramientas/publicar-catalogo.py boss-padel-disenos
    ASISTIME_CLAVE_CLINICA=… python3 herramientas/publicar-catalogo.py clinica-preventiva-disenos

La variable la nombra cada marca en su `marca.json` (`asistime.clave_env`),
porque la clave de Asistime está atada a un tenant y con dos clientes una
sola no alcanza. La marca que no la nombre usa `ASISTIME_CLAVE`.

El catálogo se genera de los contratos de cada plantilla —`plantillas/<id>/
plantilla.json`— y queda como un documento que el agente lee. Es la otra mitad
de la plantilla-como-dato: el mismo archivo que dibuja el formulario para una
persona le describe la plantilla al agente.

## Por qué un documento y no una herramienta

Una herramienta necesitaría un endpoint nuevo, con su clave, escrita en el
código de la tool a la vista de cualquiera que abra esa pantalla. Un documento
no necesita nada de eso: ya está versionado, ya tiene vuelta atrás, ya lo lee
el agente, y el club lo ve. La regla del proyecto sigue en pie — cuando un
secreto tendría que vivir en un lugar que no controlás, mejor no tener el
secreto.

## Se corre después de cada despliegue

Y es idempotente: si el catálogo no cambió, no escribe una versión nueva. Sin
eso, cada despliegue dejaría una versión idéntica a la anterior y el historial
del documento se volvería ilegible justo cuando hace falta leerlo.
"""
import importlib
import json
import os
import pathlib
import sys

import requests

RAIZ = pathlib.Path(__file__).resolve().parents[1]
API = os.environ.get("ASISTIME_API", "https://api.asistime.ai").rstrip("/")
TIEMPO = 20
TOPE = 30_000          # el máximo que acepta el campo de contenido de Asistime


def _cargar_marca(nombre: str):
    """Importa el módulo de marca con su carpeta en el path, como hace render.py."""
    carpeta = RAIZ / ".claude" / "skills" / nombre
    if not carpeta.is_dir():
        raise SystemExit(f"no existe la marca «{nombre}» en .claude/skills/")
    sys.path.insert(0, str(carpeta))
    sys.path.insert(0, str(RAIZ))
    return importlib.import_module("marca"), carpeta


def _ficha(carpeta: pathlib.Path) -> dict:
    datos = json.loads((carpeta / "marca.json").read_text(encoding="utf-8"))
    return datos.get("asistime") or {}


def _del_registro(marca: str) -> str:
    """La clave de Asistime del registro, si `gcloud` puede leerlo.

    Existe para que estos scripts vean los MISMOS clientes que el worker. Ver
    la nota larga en `registro.clave_de`.
    """
    import importlib.util
    ruta = RAIZ / "herramientas" / "registro.py"
    spec = importlib.util.spec_from_file_location("registro_cli", ruta)
    cli = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(cli)
        return cli.clave_de(marca)
    except Exception:                                        # noqa: BLE001
        return ""


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    nombre = argv[1]
    probar = "--probar" in argv

    marca, carpeta = _cargar_marca(nombre)
    ficha = _ficha(carpeta)
    tenant, documento = ficha.get("tenant"), ficha.get("catalogo")
    if not (tenant and documento):
        raise SystemExit(
            f"«{nombre}» no tiene catálogo configurado. Agregá\n"
            f'  "asistime": {{"tenant": …, "documento": …, "catalogo": …}}\n'
            f"a su marca.json con el id del documento.")

    # La clave de Asistime está atada a un tenant, así que con más de un cliente
    # no puede ser una sola: cada marca nombra la suya en su `marca.json` y la
    # que no la nombre sigue con `ASISTIME_CLAVE`. Mismo criterio que en
    # `app/manual.py`, donde está la explicación larga.
    variable = ficha.get("clave_env") or "ASISTIME_CLAVE"
    clave = (os.environ.get(variable) or "").strip() or _del_registro(nombre)
    if not clave:
        raise SystemExit(
            f"no encontré la clave de Asistime de «{nombre}»: no está en "
            f"{variable} ni en el registro de clientes.\n"
            f"Correlo con la variable puesta, o desde Cloud Shell con sesión "
            f"de gcloud para que pueda leer el registro.")

    if not hasattr(marca, "CATALOGO"):
        raise SystemExit(f"«{nombre}» todavía no expone CATALOGO() en marca.py")

    texto = marca.CATALOGO()
    if len(texto) > TOPE:
        raise SystemExit(
            f"el catálogo mide {len(texto)} caracteres y el tope es {TOPE}. "
            f"Acortá las notas de las plantillas más largas.")

    url = f"{API}/api/tenants/{tenant}/documents/{documento}"
    cab = {"X-API-KEY": clave, "Content-Type": "application/json"}

    r = requests.get(url, headers=cab, timeout=TIEMPO)
    if r.status_code != 200:
        # La API contesta lo mismo sin clave, con una inventada y con una mal
        # pegada. El mensaje no distingue: el largo sí.
        raise SystemExit(
            f"no pude leer el documento {documento} (HTTP {r.status_code}). "
            f"La clave que mandé mide {len(clave)} caracteres y empieza en "
            f"«{clave[:6]}…».")

    actual = ((r.json().get("currentVersion") or {}).get("content") or "")
    if actual.strip() == texto.strip():
        print(f"· el catálogo de {nombre} no cambió — no escribo nada")
        return 0

    plantillas = sorted(p.name for p in (carpeta / "plantillas").iterdir()
                        if (p / "plantilla.json").exists())
    etiqueta = f"{len(plantillas)} plantillas: {', '.join(plantillas)}"[:120]

    if probar:
        print(f"· escribiría una versión nueva del catálogo de {nombre}")
        print(f"  etiqueta: {etiqueta}")
        print(f"  {len(texto)} caracteres (antes: {len(actual)})")
        return 0

    r = requests.post(f"{url}/versions", headers=cab, timeout=TIEMPO,
                      json={"content": texto, "versionLabel": etiqueta,
                            "metadata": {"generado_por": "motor.plantillas.catalogo"}})
    if r.status_code not in (200, 201):
        raise SystemExit(f"no pude crear la versión (HTTP {r.status_code}): {r.text[:300]}")
    version = r.json()["id"]

    r = requests.post(f"{url}/versions/{version}/publish", headers=cab, timeout=TIEMPO)
    if r.status_code not in (200, 201):
        raise SystemExit(
            f"la versión {version} quedó creada pero SIN publicar "
            f"(HTTP {r.status_code}). El agente sigue leyendo la anterior.")

    print(f"· catálogo de {nombre} publicado — versión {version} · {etiqueta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
