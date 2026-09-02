#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publica el prompt del agente diseñador de una marca, generado del repo.

    ASISTIME_CLAVE_ASISTIME_DISENOS=… python3 herramientas/publicar-prompt.py asistime-disenos

Es el gemelo de `publicar-catalogo.py`, y por la misma razón: hay dos textos
que el agente lee y que este repo genera —el catálogo de plantillas y el
prompt—, y los dos envejecen igual si nadie los republica.

## Sólo para las marcas que declaran `agente`

`alta.py` sabe CREAR un agente con su prompt, pero nada sabía ACTUALIZARLO.
Eso alcanzaba mientras el prompt se escribía una vez; deja de alcanzar en
cuanto `alta/prompt-disenador.md` cambia, que es lo que pasó el 2/9/2026: la
tabla de rutas prometía carruseles a marcas que no los saben hacer.

El resguardo es el campo `asistime.agente` del `marca.json`. **Sólo lo tiene
la marca cuyo prompt salió de la plantilla genérica.** Boss, Clínica y Stadium
tienen prompts escritos a mano en el panel de Asistime, con cosas que este
repo no sabe; publicarles el prompt generado les borraría eso. Sin `agente` en
su ficha, este script no los toca ni por error.

Si algún día uno de esos tres pasa a usar el prompt generado, el paso es
agregarle `agente` a su `marca.json` — y antes, mirar con `--probar` qué
perdería.

## Idempotente

Si el prompt no cambió, no escribe una versión nueva. Sin eso, cada despliegue
dejaría una versión idéntica a la anterior y el historial del agente se
volvería ilegible justo cuando hace falta leerlo.
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

sys.path.insert(0, str(RAIZ / "herramientas"))
sys.path.insert(0, str(RAIZ))


def _carpeta(nombre: str) -> pathlib.Path:
    carpeta = RAIZ / ".claude" / "skills" / nombre
    if not carpeta.is_dir():
        raise SystemExit(f"no existe la marca «{nombre}» en .claude/skills/")
    return carpeta


def _cargar_marca(carpeta: pathlib.Path):
    sys.path.insert(0, str(carpeta))
    return importlib.import_module("marca")


def _del_registro(marca: str) -> str:
    """La clave de Asistime del registro, si `gcloud` puede leerlo.

    Existe para que este script vea los MISMOS clientes que el worker. La nota
    larga está en `registro.clave_de`.
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

    # La ficha se lee ANTES de importar el código de la marca, a propósito: el
    # «esta marca no la toco» tiene que salir aunque su `marca.py` no cargue.
    # Si el guardián dependiera de importarla, una marca rota daría un
    # ModuleNotFoundError en vez de la negativa, y eso se lee como un bug.
    carpeta = _carpeta(nombre)
    ficha_entera = json.loads((carpeta / "marca.json").read_text(encoding="utf-8"))
    ficha = ficha_entera.get("asistime") or {}
    tenant, agente = ficha.get("tenant"), ficha.get("agente")
    if not (tenant and agente):
        raise SystemExit(
            f"«{nombre}» no declara `asistime.agente`, así que su prompt NO lo "
            f"genera este repo: está escrito a mano en el panel de Asistime.\n"
            f"Leé el encabezado de este archivo antes de agregárselo.")

    marca = _cargar_marca(carpeta)
    variable = ficha.get("clave_env") or "ASISTIME_CLAVE"
    clave = (os.environ.get(variable) or "").strip() or _del_registro(nombre)
    if not clave:
        raise SystemExit(
            f"no encontré la clave de Asistime de «{nombre}»: no está en "
            f"{variable} ni en el registro de clientes.")

    # Se importa acá y no arriba: `alta.py` trae `requests` y lee el entorno al
    # construirse, y este script tiene que poder fallar con un mensaje claro
    # antes de eso.
    import importlib.util
    ruta = RAIZ / "herramientas" / "alta.py"
    spec = importlib.util.spec_from_file_location("alta", ruta)
    alta = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(alta)

    contratos = {pid: fn.contrato for pid, fn in marca.PLANTILLAS.items()}
    texto = alta.prompt_para(ficha_entera, contratos)

    url = f"{API}/api/tenants/{tenant}/agents/{agente}"
    cab = {"X-API-KEY": clave, "Content-Type": "application/json"}

    r = requests.get(url, headers=cab, timeout=TIEMPO)
    if r.status_code != 200:
        raise SystemExit(
            f"no pude leer el agente {agente} (HTTP {r.status_code}). "
            f"La clave que mandé mide {len(clave)} caracteres y empieza en "
            f"«{clave[:6]}…».")

    # El agente NO trae el prompt: trae el id de la versión publicada. Son dos
    # viajes, y el segundo es el que importa — sin él `actual` queda vacío,
    # todo prompt parece distinto y el script deja de ser idempotente: una
    # versión nueva e idéntica en cada despliegue.
    version_actual = r.json().get("currentPromptVersionId")
    actual = ""
    if version_actual:
        rv = requests.get(f"{url}/prompt-versions/{version_actual}",
                          headers=cab, timeout=TIEMPO)
        if rv.status_code != 200:
            raise SystemExit(
                f"no pude leer la versión {version_actual} del prompt "
                f"(HTTP {rv.status_code}). Sin poder compararla no escribo: "
                f"publicaría una versión nueva sin saber qué reemplaza.")
        actual = rv.json().get("systemPrompt") or ""
    if actual.strip() == texto.strip():
        print(f"· el prompt de {nombre} no cambió — no escribo nada")
        return 0

    etiqueta = f"{len(contratos)} plantillas · generado del repo"[:120]
    if probar:
        print(f"· escribiría una versión nueva del prompt de {nombre}")
        print(f"  {len(texto)} caracteres (antes: {len(actual)})")
        # Lo que se PIERDE es lo que más importa mirar: si el prompt de allá
        # tenía párrafos escritos a mano, acá se ven desaparecer.
        import difflib
        for linea in list(difflib.unified_diff(
                actual.splitlines(), texto.splitlines(),
                "publicado", "generado", lineterm="", n=1))[:60]:
            print("  " + linea)
        return 0

    r = requests.post(f"{url}/prompt-versions", headers=cab, timeout=TIEMPO,
                      json={"systemPrompt": texto, "versionLabel": etiqueta})
    if r.status_code not in (200, 201):
        raise SystemExit(f"no pude crear la versión (HTTP {r.status_code}): {r.text[:300]}")
    version = r.json()["id"]

    r = requests.post(f"{url}/prompt-versions/{version}/publish", headers=cab, timeout=TIEMPO)
    if r.status_code not in (200, 201):
        raise SystemExit(
            f"la versión {version} quedó creada pero SIN publicar "
            f"(HTTP {r.status_code}). El agente sigue leyendo la anterior.")

    print(f"· prompt de {nombre} publicado — versión {version} · {len(texto)} caracteres")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
