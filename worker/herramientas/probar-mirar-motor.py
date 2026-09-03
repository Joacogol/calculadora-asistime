#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba `motor/mirar.py` sin red y sin clave de Gemini.

    python3 herramientas/probar-mirar-motor.py

Lo que vigila: que los tiempos vuelvan al reloj del archivo original aunque
el material haya ido en pedazos; que un tramo imposible se descarte sin tirar
los demás; que sin clave, con cuota agotada o sin JSON se levante
`NoPudeMirar` y no otra cosa; y el camino entero con un video sintético y
una respuesta enlatada.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

fallos = 0
def ok(c, que, det=None):
    global fallos
    print("  ✓" if c else "  ✗", que, "" if c or det is None else repr(det))
    fallos += 0 if c else 1

import os
from motor import mirar as m

print("\n■ Validar: pedazos, desplazamientos y basura")
pedazos = [
    {"archivo": "charla.mp4", "indice": 1, "parte": 1, "desplazamiento": 0.0, "duracion": 3600.0},
    {"archivo": "charla.mp4", "indice": 1, "parte": 2, "desplazamiento": 1800.0, "duracion": 3600.0},
    {"archivo": "corto.mp4", "indice": 2, "parte": 1, "desplazamiento": 0.0, "duracion": 40.0},
]
crudos = [
    {"archivo": 1, "parte": 1, "desde": "05:04.500", "hasta": "05:28.000", "por_que": "bien"},
    {"archivo": 1, "parte": 2, "desde": "01:10", "hasta": "01:30"},            # → 1870–1890
    {"archivo": 2, "parte": 1, "desde": "00:05", "hasta": "00:20"},
    {"archivo": 2, "parte": 1, "desde": "00:30", "hasta": "00:50"},            # se sale (40 s)
    {"archivo": 3, "parte": 1, "desde": "00:00", "hasta": "00:10"},            # no existe
    {"archivo": 1, "parte": 1, "desde": "00:10", "hasta": "00:10.500"},        # parpadeo
    {"archivo": 1, "parte": 1, "desde": "qué", "hasta": "00:10"},              # ilegible
]
buenos, avisos = m.validar(crudos, pedazos, 60)
ok([(t["archivo"], t["desde"], t["hasta"]) for t in buenos] ==
   [("charla.mp4", 304.5, 328.0), ("charla.mp4", 1870.0, 1890.0), ("corto.mp4", 5.0, 20.0)],
   "tres buenos, en el reloj del original (la parte 2 suma 1800)", buenos)
ok(len(avisos) == 4, "cuatro avisos, uno por cada malo", avisos)
_, av = m.validar([{"archivo": 1, "desde": 0, "hasta": 100}], pedazos, 30)
ok(any("acortar" in a for a in av), "se pasa del objetivo → avisa", av)

print("\n■ La pregunta lista los archivos y las partes")
q = m.pregunta("lo más fuerte sobre IA", 60, pedazos)
ok("lo más fuerte sobre IA" in q and "60 segundos" in q, "instrucción y objetivo")
ok("archivo 1" in q and "en 2 partes" in q and "archivo 2" in q, "archivos numerados con sus partes", q[:400])
ok('"archivo": 1' in q and "SOLAMENTE" in q, "pide JSON y nada más")
ok("ELEGIR" in q and "LIMPIAR" not in q, "material largo → modo elegir")
q_corto = m.pregunta("x", 60, pedazos[2:])          # corto.mp4 dura 40 s
ok("LIMPIAR" in q_corto and "ELEGIR" not in q_corto, "material que entra → modo limpiar", q_corto[:300])
q1 = m.pregunta("x", 30, pedazos[2:])
ok("partes" not in q1.lower().replace("apartes", ""), "sin partes no habla de partes")

print("\n■ Sin clave: NoPudeMirar y nada más")
os.environ.pop("GEMINI_CLAVE", None)
try:
    m.elegir_tramos([pathlib.Path(__file__)], "x", 30); ok(False, "tendría que haber levantado")
except m.NoPudeMirar as e:
    ok("GEMINI_CLAVE" in str(e), "dice qué falta", str(e))

tmp = pathlib.Path(tempfile.mkdtemp(prefix="mirar-prueba-"))
try:
    print("\n■ Partir un archivo por peso")
    src = tmp / "sint.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=10",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", "6", "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", "-shortest", str(src)], check=True, capture_output=True)
    peso = src.stat().st_size
    partes = m.partir(src, 6.0, tmp, tope=peso // 2 + 1)
    ok(len(partes) == 2 and partes[0][1] == 0.0 and abs(partes[1][1] - 3.0) < 0.01,
       "dos pedazos, el segundo desplazado 3 s", partes)
    ok(m.partir(src, 6.0, tmp, tope=peso * 2) == [(src, 0.0)], "si entra, no se parte")

    print("\n■ El camino entero con una respuesta enlatada")
    os.environ["GEMINI_CLAVE"] = "prueba"
    respuesta = {"output_text": json.dumps({"tramos": [
        {"archivo": 1, "parte": 1, "desde": "00:01.000", "hasta": "00:04.000", "por_que": "ok"}],
        "gancho": "Un gancho de prueba",
        "palabras": ["pádel", "Paleta", "paleta", "", "Yayo", "x" * 40]}),
        "usage": {"total_tokens": 123}}
    visto = {}
    def _pedir_falso(k, entrada, modelo):
        visto["modelo"] = modelo; visto["videos"] = sum(1 for e in entrada if e.get("type") == "video")
        visto["agentico"] = all(e.get("processing") == "agentic" for e in entrada if e.get("type") == "video")
        return {"datos": respuesta, "segundos": 1.0}
    guardado = m._pedir; m._pedir = _pedir_falso
    try:
        r = m.elegir_tramos([src], "lo que sea", 30, carpeta=tmp / "trabajo")
    finally:
        m._pedir = guardado
    ok(r["tramos"] == [{"archivo": "sint.mp4", "desde": 1.0, "hasta": 4.0, "por_que": "ok"}],
       "los tramos salen con el nombre del archivo y en su reloj", r["tramos"])
    ok(r["gancho"] == "Un gancho de prueba" and r["uso"].get("total_tokens") == 123, "gancho y tokens")
    ok(visto["videos"] == 1 and visto["agentico"], "un video, en modo agéntico", visto)
    ok(visto["modelo"] == m.MODELOS[0], "empieza por el mejor modelo", visto)
    # Las palabras del video: sin vacías, sin repetidas y sin la larguísima.
    # Van al vocabulario que el transcriptor lee antes de escuchar — es lo que
    # arregla «para el padre» donde se decía «para el pádel».
    ok(r["palabras"] == ["pádel", "Paleta", "Yayo"], "las palabras del video, limpias", r["palabras"])

    print("\n■ Cuota agotada: no se insiste con otro modelo")
    llamadas = []
    m._pedir = lambda k, e, modelo: (llamadas.append(modelo) or {"error": "HTTP 429: quota", "codigo": 429})
    try:
        m.elegir_tramos([src], "x", 30, carpeta=tmp / "t2"); ok(False, "tendría que haber levantado")
    except m.NoPudeMirar as e:
        ok("429" in str(e), "levanta con el motivo", str(e))
    finally:
        m._pedir = guardado
    ok(llamadas == [m.MODELOS[0]], "una sola llamada: cambiar de modelo no arregla la cuota", llamadas)

    print("\n■ Saturado: prueba el siguiente modelo")
    llamadas = []
    def _saturado(k, e, modelo):
        llamadas.append(modelo)
        return {"error": "HTTP 503", "codigo": 503} if len(llamadas) == 1 else {"datos": respuesta, "segundos": 1}
    m._pedir = _saturado
    try:
        r = m.elegir_tramos([src], "x", 30, carpeta=tmp / "t3")
        ok(len(llamadas) == 2 and r["modelo"] == m.MODELOS[1], "el segundo modelo contesta", (llamadas, r["modelo"]))
    finally:
        m._pedir = guardado

    print("\n■ Sin JSON: NoPudeMirar")
    m._pedir = lambda k, e, modelo: {"datos": {"output_text": "no sé qué decirte"}, "segundos": 1}
    try:
        m.elegir_tramos([src], "x", 30, carpeta=tmp / "t4"); ok(False, "tendría que haber levantado")
    except m.NoPudeMirar as e:
        ok("JSON" in str(e), "lo dice", str(e))
    finally:
        m._pedir = guardado
finally:
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("GEMINI_CLAVE", None)

print("\n", "todo bien" if not fallos else f"{fallos} fallo(s)")
sys.exit(1 if fallos else 0)
