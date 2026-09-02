#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba `publicar-prompt.py` sin tocar la red ni el agente de verdad.

    python3 herramientas/probar-publicar-prompt.py

Lo que se prueba es lo que puede salir caro:

- que **no escriba** cuando el prompt publicado ya es el generado. Sin eso,
  cada despliegue deja una versión idéntica y el historial del agente se
  vuelve ilegible justo cuando hace falta leerlo.
- que **escriba y publique** cuando cambió — las dos cosas: una versión
  creada y sin publicar es peor que ninguna, porque parece hecha y el agente
  sigue leyendo la anterior.
- que **no toque** una marca sin `asistime.agente`. Boss, Clínica y Stadium
  tienen prompts escritos a mano en el panel; publicarles el generado se los
  borraría.

La API se reemplaza por un doble que devuelve lo que devuelve la de verdad:
el agente trae el **id** de la versión publicada, no su texto. Ese detalle es
justamente el que rompía la idempotencia, así que el doble lo respeta.
"""
import contextlib
import importlib
import importlib.util
import io
import json
import os
import pathlib
import sys
import types

RAIZ = pathlib.Path(__file__).resolve().parents[1]
MARCA = "asistime-disenos"
sys.path.insert(0, str(RAIZ / "herramientas"))
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / ".claude/skills" / MARCA))

publicado = {"texto": ""}
posts: list[tuple[str, dict]] = []


class _Respuesta:
    def __init__(self, codigo, datos):
        self.status_code, self._datos = codigo, datos
        self.text = json.dumps(datos)

    def json(self):
        return self._datos


def _get(url, **kw):
    if url.endswith("/agents/594"):
        return _Respuesta(200, {"currentPromptVersionId": 4809})
    if "/prompt-versions/4809" in url:
        return _Respuesta(200, {"systemPrompt": publicado["texto"]})
    raise AssertionError(f"GET inesperado: {url}")


def _post(url, **kw):
    posts.append((url, kw.get("json") or {}))
    return _Respuesta(201, {"id": 5000})


falso = types.ModuleType("requests")
falso.get, falso.post = _get, _post
sys.modules["requests"] = falso

os.environ["ASISTIME_CLAVE_ASISTIME_DISENOS"] = "clave-de-prueba"
_spec = importlib.util.spec_from_file_location(
    "publicar_prompt", RAIZ / "herramientas" / "publicar-prompt.py")
pp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pp)

import alta                                                    # noqa: E402

_marca = importlib.import_module("marca")
_ficha = json.loads((RAIZ / ".claude/skills" / MARCA / "marca.json")
                    .read_text(encoding="utf-8"))
ESPERADO = alta.prompt_para(
    _ficha, {p: f.contrato for p, f in _marca.PLANTILLAS.items()})


def prueba(titulo, fn):
    """Corre una prueba tragándose lo que el script imprime.

    `--probar` escribe el diff entero del prompt —doscientas y pico de
    líneas—, y con eso adentro los ✓ de esta lista dejan de verse. Lo que se
    traga se muestra igual si la prueba falla."""
    posts.clear()
    ruido = io.StringIO()
    try:
        with contextlib.redirect_stdout(ruido):
            fn()
    except BaseException:
        print(ruido.getvalue())
        raise
    print(f"  ✓ {titulo}")


def no_escribe_si_no_cambio():
    publicado["texto"] = ESPERADO
    pp.main(["x", MARCA])
    assert not posts, f"escribió {len(posts)} veces sin motivo"


def escribe_y_publica_si_cambio():
    publicado["texto"] = "un prompt viejo"
    pp.main(["x", MARCA])
    urls = [u for u, _ in posts]
    assert len(urls) == 2, f"esperaba crear y publicar, hizo {urls}"
    assert urls[0].endswith("/prompt-versions"), urls[0]
    assert urls[1].endswith("/5000/publish"), urls[1]
    assert posts[0][1]["systemPrompt"] == ESPERADO, "mandó un prompt que no es el generado"


def probar_no_escribe():
    publicado["texto"] = "un prompt viejo"
    pp.main(["x", MARCA, "--probar"])
    assert not posts, "--probar escribió"


def no_toca_una_marca_sin_agente():
    for otra in ("boss-padel-disenos", "clinica-preventiva-disenos", "stadium-disenos"):
        ficha = json.loads((RAIZ / ".claude/skills" / otra / "marca.json")
                           .read_text(encoding="utf-8"))
        assert "agente" not in (ficha.get("asistime") or {}), (
            f"{otra} declara `agente`: este script le publicaría el prompt "
            f"generado encima del escrito a mano")
        try:
            pp.main(["x", otra])
        except SystemExit as e:
            assert "agente" in str(e), str(e)
        else:
            raise AssertionError(f"{otra} no fue rechazada")
        assert not posts, f"escribió sobre {otra}"


print("publicar-prompt.py")
prueba("no escribe si el prompt no cambió", no_escribe_si_no_cambio)
prueba("escribe la versión Y la publica cuando cambió", escribe_y_publica_si_cambio)
prueba("--probar no escribe", probar_no_escribe)
prueba("no toca a las marcas sin `agente`", no_toca_una_marca_sin_agente)
print("\n✓ todo bien")
