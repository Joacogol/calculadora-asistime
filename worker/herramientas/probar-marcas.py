#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Que las CUATRO marcas de esta copia carguen, antes de construir la imagen.

    python3 herramientas/probar-marcas.py

El 4/9/2026 se descubrió que este repo tiene dos generaciones de kit conviviendo:

  · **Marcas de datos** (Asistime, Stadium): la identidad vive en `marca.json`
    y `marca.py` son seis líneas que llaman a `motor.identidad.cargar`. Todo
    lo que necesitan está acá.

  · **Marcas de código** (Boss, Clínica): su `marca.py` importa `brand`,
    `templates`, `diapositivas` y `presentacion` — archivos que viven en el
    REPO DEL WORKER, no en éste. Por eso `DESPLEGAR.md` dice copiar el código
    nuevo ADENTRO del repo del worker y desplegar desde ahí.

Desplegar parado en el clon de `calculadora-asistime` construye una imagen sin
esos archivos. Y no falla: el `Dockerfile` hace `COPY . .` y se lleva lo que
haya. El worker arranca, encuentra `marca.py`, lo intenta importar, revienta
con `ModuleNotFoundError: No module named 'brand'`, y lo atrapa el `except` que
existe para que un cliente caído no frene a los demás. Queda una línea en el
log. El cliente deja de recibir sus piezas y nadie se entera.

Esta prueba carga cada marca por el MISMO camino que el worker
(`motor.cargador.cargar_marca`, que aísla las carpetas entre sí) y falla con el
nombre de lo que falta. Corre en segundos y sin red, y `desplegar-chat.sh` la
usa como condición para construir: **una imagen donde una marca no carga no se
despliega.**
"""
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from motor import contrato                                            # noqa: E402
from motor.cargador import cargar_marca                               # noqa: E402

SKILLS = RAIZ / ".claude/skills"
fallos = []

kits = sorted(k for k in SKILLS.iterdir()
              if (k / "marca.json").exists() and (k / "marca.py").exists())
if not kits:
    print(f"✗ No hay ninguna marca en {SKILLS}")
    raise SystemExit(1)

print(f"\n■ Que cada marca de esta copia cargue ({len(kits)})")
for kit in kits:
    try:
        m = cargar_marca(kit)
    except Exception as e:
        # El mensaje pelado de un ImportError no dice nada al que despliega.
        # Lo que hace falta saber es qué falta y de dónde sacarlo.
        pista = ""
        if isinstance(e, ModuleNotFoundError):
            pista = (f"\n      Le falta el módulo «{e.name}.py» en su carpeta. "
                     f"Las marcas de código lo traen del REPO DEL WORKER: "
                     f"estás desplegando desde el clon de calculadora-asistime "
                     f"en vez de copiar adentro del worker. Ver DESPLEGAR.md, paso 1.")
        print(f"  ✗ {kit.name}: {type(e).__name__}: {e}{pista}")
        fallos.append(kit.name)
        continue

    cuantas = len(getattr(m, "PLANTILLAS", {}) or {})
    try:
        contrato.verificar(m)
        print(f"  ✓ {kit.name}: carga · {cuantas} plantillas · contrato en orden")
    except Exception as e:
        print(f"  ✗ {kit.name}: carga pero no cumple el contrato — {e}")
        fallos.append(kit.name)

print()
if fallos:
    print(f"  ✗ NO se puede desplegar: {', '.join(fallos)}")
    print("    Una marca que no carga deja de recibir sus piezas y no avisa.")
    raise SystemExit(1)
print("  todo bien")
