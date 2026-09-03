#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""El tope de buffer del SDK tiene que aguantar una pieza mirada.

    python3 herramientas/probar-buffer-agente.py

El 2 y 3/9/2026 todas las corridas del diseñador que abrían el PNG murieron
con «Failed to decode JSON: JSON message exceeded maximum buffer size of
1048576 bytes». El SDK lee la salida del CLI mensaje por mensaje y descarta
la corrida entera si uno solo pasa el tope. Un `Read` de una pieza terminada
manda el PNG en base64 —un tercio más pesado que el archivo— y nuestras
stories pesan hasta 1,7 MB, o sea 2,3 MB en base64: cinco corridas perdidas.

La prueba no llama al SDK: lee el tope que pone cada agente en su código y lo
compara contra el PNG más pesado que sabe hacer el motor. Si mañana las
piezas engordan o alguien copia un `ClaudeAgentOptions` sin el tope, esto lo
dice antes que un pedido real.
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]

# Los agentes que pueden abrir una pieza con Read.
AGENTES = {
    "app/disenador.py": "el que arma las piezas",
    "app/motorista.py": "el que toca el motor",
    "app/plantillero.py": "el que escribe plantillas",
}

# Cuánto pesa lo más pesado que hace el motor, medido sobre los renders del
# set completo de Boss (56 piezas, 4 formatos): la story de `americano`.
PIEZA_MAS_PESADA = 1.7 * 1024 * 1024
BASE64 = 4 / 3          # lo que engorda un binario al viajar como texto
MARGEN = 2              # para el resto del mensaje y para piezas futuras
MINIMO = PIEZA_MAS_PESADA * BASE64 * MARGEN

fallos = []
print(f"■ Una pieza de {PIEZA_MAS_PESADA/1024/1024:.1f} MB viaja como "
      f"{PIEZA_MAS_PESADA*BASE64/1024/1024:.1f} MB de base64")
print(f"  → cada agente necesita al menos {MINIMO/1024/1024:.1f} MB de buffer\n")

for archivo, quien in AGENTES.items():
    codigo = (RAIZ / archivo).read_text(encoding="utf-8")
    m = re.search(r"max_buffer_size\s*=\s*([0-9]+)\s*\*\s*1024\s*\*\s*1024", codigo)
    tope = int(m.group(1)) * 1024 * 1024 if m else 0
    bien = tope >= MINIMO
    print(f"  {'✓' if bien else '✗'} {archivo} ({quien}): "
          + (f"{tope/1024/1024:.0f} MB" if tope else "SIN TOPE PROPIO → 1 MB por defecto"))
    if not bien:
        fallos.append(archivo)

# El otro lado: los agentes de un solo turno que no leen archivos no lo
# necesitan, y está bien que no lo tengan. Sólo avisamos si alguno empezó a
# permitir Read sin haber subido el tope.
for p in sorted((RAIZ / "app").rglob("*.py")) + sorted((RAIZ / "motor").rglob("*.py")):
    rel = p.relative_to(RAIZ).as_posix()
    if rel in AGENTES:
        continue
    codigo = p.read_text(encoding="utf-8")
    for bloque in re.findall(r"ClaudeAgentOptions\((.*?)\)", codigo, re.S):
        if "Read" in bloque and "max_buffer_size" not in bloque:
            print(f"  ✗ {rel}: deja usar Read y no subió el tope")
            fallos.append(rel)

print("\n  todo bien" if not fallos else f"\n  {len(fallos)} problema(s)")
sys.exit(1 if fallos else 0)
