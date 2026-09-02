#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba el alta sin red: la sustitución de tools, el prompt y la simulación.

    python3 herramientas/probar-alta.py
"""
import importlib.util
import json
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
spec = importlib.util.spec_from_file_location("alta", pathlib.Path(__file__).with_name("alta.py"))
alta = importlib.util.module_from_spec(spec); spec.loader.exec_module(alta)

fallos = 0
def ok(c, que, det=None):
    global fallos
    print("  ✓" if c else "  ✗", que, "" if c or det is None else str(det)[:300])
    fallos += 0 if c else 1

print("\n■ Sustituir una tool de la marca de referencia")
ORIGEN = alta.REFERENCIA
DESTINO = {"ref": "abcdefghijklmnopqrst", "clave": "f" * 64, "nombre": "Club Demo"}
tool = {"id": 2075, "tenantId": 176, "name": "crear_reel", "type": "custom_code",
        "description": "Encarga un REEL para Stadium. Cuesta plata.",
        "config": {"timeout": 30000,
                   "code": f'const API = "https://{ORIGEN["ref"]}.supabase.co/functions/v1/api-reels";\n'
                           f'const CLAVE = "{ORIGEN["clave"]}";\n// Stadium vende zapatillas',
                   "parameters": {"type": "object", "properties": {"foto": {"type": "string",
                                  "description": "La foto del producto de Stadium"}}}},
        "behaviors": {}, "createdAt": "x", "updatedAt": "y"}
nueva = alta.sustituir_tool(tool, ORIGEN, DESTINO)
ok("id" not in nueva and "createdAt" not in nueva, "sin ids ni fechas", list(nueva))
ok(DESTINO["ref"] in nueva["config"]["code"] and DESTINO["clave"] in nueva["config"]["code"],
   "la dirección y la clave son las nuevas")
ok("Club Demo" in nueva["description"] and "Club Demo" in json.dumps(nueva["config"]["parameters"]),
   "el nombre cambió en la descripción y en los parámetros")
ok(alta.rastro(json.dumps(nueva, ensure_ascii=False), ORIGEN) == [], "no queda rastro de la marca de origen")
ok(alta.rastro("hola Stadium", ORIGEN) == ["nombre"], "y rastro() lo detecta cuando queda")

print("\n■ El prompt del agente")
from motor import identidad
m = identidad.cargar(RAIZ / ".claude/skills/stadium-disenos/marca.py")
contratos = {p: f.contrato for p, f in m.PLANTILLAS.items()}
ficha = {"nombre": "Club Demo", "quien_es": "Un club de barrio.", "cuidados": "**No inventes precios.**"}
p = alta.prompt_para(ficha, contratos)
ok("{{" not in p, "sin marcadores sin llenar")
ok("Sos el diseñador de Club Demo. Un club de barrio." in p, "abre con el nombre y quién es")
ok("## Cuidados propios de esta cuenta" in p and "No inventes precios" in p, "los cuidados entran cuando hay")
ok("`precio`" in p and "`producto`" in p, "la tabla de plantillas sale del catálogo real")
ok("crear_video" in p and "elegir" in p, "menciona crear_video y la elección del sistema")
sin = alta.prompt_para({"nombre": "Otra"}, {})
ok("Cuidados propios" not in sin and "Las que diga el catálogo." in sin, "sin cuidados ni plantillas, no inventa")

print("\n■ La simulación no toca nada")
r = subprocess.run([sys.executable, "herramientas/alta.py", "stadium-disenos", "--simular"],
                   cwd=RAIZ, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
ok(r.returncode == 0, "termina bien", r.stderr[-300:])
ok("SIMULACIÓN" in r.stdout and all(p in r.stdout for p in alta.PASOS), "muestra los doce pasos", r.stdout[:200])
ok(not (RAIZ / ".claude/skills/stadium-disenos/alta.json").exists(), "y no escribe alta.json")
ok(len(alta.clave_nueva()) == 64, "la clave nueva mide 64")

print(f"\n✗ {fallos} fallo(s)\n" if fallos else "\n✓ todo bien\n")
sys.exit(1 if fallos else 0)
