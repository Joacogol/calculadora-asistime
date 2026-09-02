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

print("\n■ El tenant se reusa cuando ya existe")
#
# Lo normal, no la excepción: Boss, Clínica y Stadium eran tenants de Asistime
# antes de ser clientes de diseño, y Asistime es el tenant 1 desde marzo.
class _Falso(alta.Alta):
    def __init__(self, ficha, paginas):
        self.ficha, self._paginas, self.dicho = ficha, paginas, []
        self.nombre = ficha["nombre"]; self.slug = ficha.get("slug", "x"); self.simular = False
    def _asistime(self, metodo, ruta, **kw):
        return self._paginas.pop(0)
    def decir(self, t): self.dicho.append(t)

f = _Falso({"nombre": "Asistime", "slug": "asistime", "asistime": {"tenant": 1}}, [])
ok(f._tenant_existente() == 1, "el marca.json manda y no se consulta nada")

f = _Falso({"nombre": "Club Demo", "slug": "club-demo"}, [
    {"data": [{"id": 5, "slug": "otro", "name": "Otro"}], "meta": {"totalPages": 2}},
    {"data": [{"id": 42, "slug": "club-demo", "name": "Club Demo"}], "meta": {"totalPages": 2}}])
ok(f._tenant_existente() == 42, "sin marca.json, lo busca por slug y pagina")

f = _Falso({"nombre": "Club Demo", "slug": "club-demo"}, [
    {"data": [{"id": 5, "slug": "otro", "name": "CLUB DEMO"}], "meta": {"totalPages": 1}}])
ok(f._tenant_existente() == 5, "y lo encuentra por nombre aunque el slug no coincida")

f = _Falso({"nombre": "Nadie", "slug": "nadie"}, [{"data": [], "meta": {"totalPages": 1}}])
ok(f._tenant_existente() is None, "si no está, devuelve None y el alta lo crea")

print("\n■ La forma del marca.json, antes de que exista el cliente")
# El caso es real: el 2/9/2026 Asistime tenía `sedes` como lista `["Todas"]`.
# Se lee perfectamente razonable, el alta pasó entera, y el primer diseño de
# verdad murió cuatro minutos después con «'list' object has no attribute
# 'get'» — un mensaje que no nombra ni la marca ni el campo.
malos = alta.revisar_ficha({"sedes": ["Todas"], "sede_por_defecto": "Todas"})
ok(bool(malos) and "sedes" in malos[0] and "list" in malos[0],
   "caza `sedes` escrito como lista", str(malos))
ok(bool(alta.revisar_ficha({"sedes": {"Centro": "099 123 456"}})),
   "caza una sede que no es diccionario")
ok(bool(alta.revisar_ficha({"sedes": {"Centro": {}}, "sede_por_defecto": "Norte"})),
   "caza un sede_por_defecto que no está en sedes")
ok(bool(alta.revisar_ficha({"fotos": []})), "caza `fotos` como lista")

# La otra mitad, y la que importa igual: un chequeo que se queja de lo que está
# bien se apaga a la semana.
sucias = []
for carpeta in sorted((RAIZ / ".claude/skills").iterdir()):
    ficha = carpeta / "marca.json"
    if ficha.exists():
        problemas = alta.revisar_ficha(json.loads(ficha.read_text(encoding="utf-8")))
        if problemas:
            sucias.append(f"{carpeta.name}: {problemas}")
ok(not sucias, "y las marcas de verdad pasan limpias", "; ".join(sucias))

print("\n■ La simulación no toca nada")
r = subprocess.run([sys.executable, "herramientas/alta.py", "stadium-disenos", "--simular"],
                   cwd=RAIZ, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
ok(r.returncode == 0, "termina bien", r.stderr[-300:])
ok("SIMULACIÓN" in r.stdout and all(p in r.stdout for p in alta.PASOS), "muestra los doce pasos", r.stdout[:200])
ok(not (RAIZ / ".claude/skills/stadium-disenos/alta.json").exists(), "y no escribe alta.json")
ok(len(alta.clave_nueva()) == 64, "la clave nueva mide 64")

print(f"\n✗ {fallos} fallo(s)\n" if fallos else "\n✓ todo bien\n")
sys.exit(1 if fallos else 0)
