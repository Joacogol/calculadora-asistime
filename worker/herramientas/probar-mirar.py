#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba `mirar-video.py` sin red y sin clave.

    python3 herramientas/probar-mirar.py

Lo que vigila: que los tiempos se lean vengan como vengan, que el JSON se
saque aunque venga envuelto en prosa, que un tramo imposible se descarte sin
tirar los demás, y que con el video en partes los tiempos vuelvan al reloj del
original.
"""
import importlib.util
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

fallos = 0
def ok(c, que, det=None):
    global fallos
    print("  ✓" if c else "  ✗", que, "" if c or det is None else repr(det))
    fallos += 0 if c else 1

_s = importlib.util.spec_from_file_location("mirar", RAIZ / "herramientas" / "mirar-video.py")
m = importlib.util.module_from_spec(_s); _s.loader.exec_module(m)

print("\n■ Los tiempos, como los escriba el modelo")
for v, esp in (("01:15", 75), ("01:15.500", 75.5), ("1:02:03", 3723), ("75", 75),
               (75.5, 75.5), ("00:00.000", 0)):
    try:
        ok(abs(m.a_segundos(v) - esp) < 1e-6, f"{v!r} → {esp}", m.a_segundos(v))
    except Exception as e:                                   # noqa: BLE001
        ok(False, f"{v!r} → {esp}", e)
for malo in ("un rato", "1:2:3:4", "", "MM:SS"):
    try:
        m.a_segundos(malo); ok(False, f"{malo!r} tendría que fallar")
    except ValueError:
        ok(True, f"{malo!r} falla con ValueError")

print("\n■ El JSON, venga como venga")
ok(m.extraer_json('{"tramos": []}') == {"tramos": []}, "pelado")
ok(m.extraer_json('Acá va:\n```json\n{"tramos": [1]}\n```\ngracias') == {"tramos": [1]}, "envuelto en ``` y prosa")
try:
    m.extraer_json("no hay nada"); ok(False, "sin JSON tendría que fallar")
except ValueError:
    ok(True, "sin JSON falla claro")

print("\n■ Validar: se descarta lo malo, se conserva lo bueno")
crudos = [
    {"desde": "00:10", "hasta": "00:18", "por_que": "bien"},
    {"desde": "00:30", "hasta": "00:29", "por_que": "al revés"},
    {"desde": "59:00", "hasta": "59:30", "por_que": "fuera del video"},
    {"desde": "01:00", "hasta": "01:00.900", "por_que": "parpadeo"},
    {"desde": "qué", "hasta": "02:00", "por_que": "ilegible"},
    {"desde": "02:00", "hasta": "02:12", "por_que": "bien también"},
]
buenos, avisos = m.validar_tramos(crudos, duracion=600, objetivo=30)
ok([ (t["desde"], t["hasta"]) for t in buenos ] == [(10.0, 18.0), (120.0, 132.0)], "quedan los dos buenos", buenos)
ok(len(avisos) == 4, "cuatro avisos, uno por cada malo", avisos)
ok(all(isinstance(a, str) for a in avisos), "los avisos son texto legible")

print("\n■ Validar: el largo total")
largo = [{"desde": 0, "hasta": 25}, {"desde": 30, "hasta": 55}]
_, av = m.validar_tramos(largo, 600, objetivo=30)
ok(any("acortar" in a for a in av), "se pasa del objetivo → avisa", av)
corto = [{"desde": 0, "hasta": 5}]
_, av = m.validar_tramos(corto, 600, objetivo=30)
ok(any("corto" in a for a in av), "muy corto → avisa", av)
_, av = m.validar_tramos([{"desde": 0, "hasta": 28}], 600, objetivo=30)
ok(not av, "en el objetivo → sin avisos", av)
_, av = m.validar_tramos([{"desde": 0, "hasta": 28}], duracion=0, objetivo=30)
ok(not av, "sin ffprobe (duración 0) no inventa un límite", av)

print("\n■ En partes: los tiempos vuelven al reloj del original")
partes = [{"duracion": 1800.0}, {"duracion": 1870.0}]
t = m.con_desplazamiento([{"parte": 1, "desde": 10.0, "hasta": 20.0},
                          {"parte": 2, "desde": 5.0, "hasta": 15.0},
                          {"desde": 30.0, "hasta": 40.0}], partes)
ok((t[0]["desde"], t[0]["hasta"]) == (10.0, 20.0), "parte 1 no se mueve")
ok((t[1]["desde"], t[1]["hasta"]) == (1805.0, 1815.0), "parte 2 suma lo que duró la 1", t[1])
ok((t[2]["desde"], t[2]["hasta"]) == (30.0, 40.0), "sin `parte` se asume la primera")
ok(m.con_desplazamiento([{"desde": 1, "hasta": 2}], [{"duracion": 9}]) == [{"desde": 1, "hasta": 2}],
   "con una sola parte no toca nada")

print("\n■ La pregunta")
q = m.pregunta("IA en real estate", 30, 1, 3670)
ok("IA en real estate" in q and "30 segundos" in q, "lleva la instrucción y el objetivo")
ok("61 minutos" in q, "y cuánto dura el video")
ok("parte" not in q.lower().replace("aparecer", ""), "con una parte no habla de partes")
q2 = m.pregunta("x", 30, 2, 0)
ok("2 partes" in q2 and "`parte`" in q2, "con dos partes pide el número de parte")
ok("SOLAMENTE" in q and '"tramos"' in q, "pide JSON y nada más")

print("\n■ YouTube y rango: la forma exacta del pedido")
e = m.entrada_video("static", youtube="https://www.youtube.com/watch?v=x", desde=300, hasta=600)
ok(e["uri"] == "https://www.youtube.com/watch?v=x" and "data" not in e, "YouTube va por `uri`, sin bytes")
ok(e["processing"] == {"type": "static", "start_offset": 300, "end_offset": 600},
   "estático con rango: objeto con offsets en segundos", e["processing"])
e = m.entrada_video("agentic", youtube="https://www.youtube.com/watch?v=x", desde=300, hasta=600)
ok(e["processing"] == "agentic", "agéntico: cadena, aunque haya rango (la API no lo tiene)", e["processing"])
e = m.entrada_video("static", youtube="https://youtu.be/x")
ok(e["processing"] == "static", "estático sin rango: cadena simple", e["processing"])
e = m.entrada_video("static", datos=b"abc")
ok(e.get("mime_type") == "video/mp4" and e["data"] == "YWJj", "archivo: base64 + mime")
e = m.entrada_video("static", datos=b"abc", desde=10)
ok(e["processing"] == {"type": "static", "start_offset": 10}, "sólo desde → sólo start_offset", e["processing"])

print("\n■ El rango en la pregunta")
ok(m.mmss(300) == "05:00" and m.mmss(3670) == "61:10" and m.mmss(0) == "00:00", "MM:SS")
q = m.pregunta("IA", 60, 1, 2679, 300, 600)
ok("entre 05:00 y 10:00" in q, "dice el rango en MM:SS", q[:300])
ok("del video entero" in q, "y aclara que los tiempos son del video entero")
q = m.pregunta("IA", 60, 1, 2679)
ok("MIRÁ SOLAMENTE" not in q, "sin rango no lo menciona")

print("\n", "todo bien" if not fallos else f"{fallos} fallo(s)")
sys.exit(1 if fallos else 0)
