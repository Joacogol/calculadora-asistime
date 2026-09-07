#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Una corrida del agente que se corta tiene que dejar rastro.

    python3 herramientas/probar-corrida-cortada.py

El 3/9/2026 dos pedidos de la story del viernes entregaron una pieza
incompleta —sin copy ni notas— con `metricas = {"manual": 1}`. Eso es
exactamente lo que guarda una pieza cargada a mano, así que el fallo era
invisible desde la plataforma: no había forma de distinguir «el agente
terminó» de «el agente explotó a la mitad».

Esta prueba fuerza las dos situaciones (corrida entera y corrida cortada)
contra `_correr` y verifica que la cortada quede marcada con `corto`, y que
además no se rompa por leer métricas que no existen.
"""
import asyncio
import pathlib
import sys
import types

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

# El SDK del agente no está instalado en todos lados y no hace falta para esto.
sys.modules.setdefault("claude_agent_sdk", types.ModuleType("claude_agent_sdk"))
sdk = sys.modules["claude_agent_sdk"]
for nombre in ("query", "ClaudeAgentOptions", "AssistantMessage", "TextBlock",
               "ResultMessage", "ToolUseBlock"):
    if not hasattr(sdk, nombre):
        setattr(sdk, nombre, type(nombre, (), {"__init__": lambda self, **k: self.__dict__.update(k)}))

from app import disenador  # noqa: E402

fallos = []


def revisar(caso, condicion, detalle=""):
    print(f"  {'✓' if condicion else '✗'} {caso}" + (f" — {detalle}" if detalle and not condicion else ""))
    if not condicion:
        fallos.append(caso)


class ResultMessage:   # el nombre importa: `_correr` lo reconoce por eso
    """Lo mínimo que `_metricas` le pide a un ResultMessage."""
    def __init__(self):
        self.usage = {"input_tokens": 10, "output_tokens": 20}
        self.total_cost_usd = 0.12345
        self.num_turns = 7
        self.duration_ms = 4000
        self.duration_api_ms = 3000
        self.session_id = "s"


def _correr_con(mensajes, explota=None):
    """Corre `_correr` con un `query` de mentira."""
    async def falso(prompt=None, options=None):
        for m in mensajes:
            yield m
        if explota:
            raise explota

    disenador.query = falso
    salida = pathlib.Path("/tmp/probar-corrida-cortada")
    salida.mkdir(parents=True, exist_ok=True)
    return asyncio.run(disenador._correr("prompt", "modelo-x", salida, "asistime"))


# ── 1. La corrida entera se mide como siempre ────────────────────────────────
_ultimo, met = _correr_con([ResultMessage()])
revisar("la corrida entera trae costo", met.get("costo_usd") == 0.12345, str(met))
revisar("la corrida entera trae turnos", met.get("turnos") == 7, str(met))
revisar("la corrida entera no dice 'corto'", "corto" not in met, str(met))

# ── 2. La corrida cortada deja el error escrito ──────────────────────────────
_ultimo, met = _correr_con([], explota=RuntimeError("se cayó el proceso"))
revisar("la cortada queda marcada", "corto" in met, str(met))
revisar("dice qué error fue",
        "RuntimeError" in met.get("corto", "") and "se cayó" in met.get("corto", ""),
        str(met))
revisar("la cortada no se confunde con una pieza a mano", bool(met), str(met))
revisar("la cortada anota el modelo", met.get("modelo") == "modelo-x", str(met))

# ── 3. Cortada después de haber recibido el ResultMessage ────────────────────
# Puede pasar: el error salta al cerrar la sesión, con las métricas ya leídas.
_ultimo, met = _correr_con([ResultMessage()], explota=RuntimeError("cerró feo"))
revisar("conserva las métricas si alcanzó a leerlas", met.get("turnos") == 7, str(met))
revisar("y aun así marca el corte", "corto" in met, str(met))

print("\n  todo bien" if not fallos else f"\n  {len(fallos)} fallo(s): " + ", ".join(fallos))
sys.exit(1 if fallos else 0)
