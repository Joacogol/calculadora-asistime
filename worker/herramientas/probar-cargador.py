#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba que dos marcas cargadas en el mismo proceso no se pisen.

    python3 herramientas/probar-cargador.py

Sin red, sin gcloud y sin tocar las marcas de verdad: arma dos carpetas de
mentira que se llaman igual por dentro (`marca.py` + `brand.py`, como Boss y
Clínica) y comprueba que cada una devuelve LO SUYO.

Contra el código del 2/9/2026 —`sys.path.insert` + `import_module("marca")`—
la segunda marca devolvía la primera, y así fue como el reel de Asistime salió
rechazado por no tener una plantilla `campana` que nunca fue suya.
"""
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

fallos = 0
def ok(c, que, det=None):
    global fallos
    print("  ✓" if c else "  ✗", que, "" if c or det is None else repr(det))
    fallos += 0 if c else 1


def marca_falsa(raiz: pathlib.Path, nombre: str, color: str, rotulo: str):
    """Una carpeta de marca mínima, con un hermano de nombre pelado."""
    d = raiz / nombre
    d.mkdir(parents=True)
    (d / "brand.py").write_text(f'C = {{"acento": "{color}"}}\n', "utf-8")
    (d / "marca.py").write_text(
        "from brand import C  # noqa: F401\n"
        f'PLANTILLA_ROTULO = "{rotulo}"\n'
        f'QUIEN = "{nombre}"\n', "utf-8")
    return d


tmp = pathlib.Path(tempfile.mkdtemp(prefix="cargador-"))
try:
    skills = tmp / ".claude" / "skills"
    una = marca_falsa(skills, "una-disenos", "#ff0000", "campana")
    otra = marca_falsa(skills, "otra-disenos", "#0000ff", "titular")

    print("\n■ El camino viejo: import_module('marca')")
    import importlib
    sys.path.insert(0, str(una)); m1 = importlib.import_module("marca")
    sys.path.insert(0, str(otra)); m2 = importlib.import_module("marca")
    # Acá se EXIGE que el camino viejo esté roto. Si algún día Python dejara
    # de cachear por nombre, este ✗ avisaría que la comprobación ya no prueba
    # nada —que es distinto de que el bug haya vuelto.
    ok(m1.QUIEN == "una-disenos", "la primera marca carga bien", m1.QUIEN)
    ok(m2 is m1 and m2.QUIEN == "una-disenos",
       "la segunda recibe la PRIMERA — el bug que estamos arreglando", m2.QUIEN)
    for n in ("marca", "brand"):
        sys.modules.pop(n, None)
    sys.path.remove(str(una)); sys.path.remove(str(otra))

    print("\n■ El cargador nuevo")
    from motor.cargador import cargar_marca, olvidar
    olvidar()
    a = cargar_marca(una)
    b = cargar_marca(otra)
    ok(a.QUIEN == "una-disenos", "la primera es la primera", a.QUIEN)
    ok(b.QUIEN == "otra-disenos", "la segunda es la segunda", b.QUIEN)
    ok(a.PLANTILLA_ROTULO == "campana", "cada una con su rótulo", a.PLANTILLA_ROTULO)
    ok(b.PLANTILLA_ROTULO == "titular", "cada una con su rótulo", b.PLANTILLA_ROTULO)
    ok(a.C["acento"] == "#ff0000", "y con su color", a.C)
    ok(b.C["acento"] == "#0000ff", "y con el color del hermano correcto", b.C)

    print("\n■ Volver a la primera después de la segunda")
    a2 = cargar_marca(una)
    ok(a2 is a, "el mismo módulo, no uno nuevo")
    ok(a2.QUIEN == "una-disenos", "y sigue siendo el suyo", a2.QUIEN)
    ok(a2.C["acento"] == "#ff0000", "el hermano tampoco se dio vuelta", a2.C)

    print("\n■ En orden inverso, desde cero")
    olvidar()
    b3 = cargar_marca(otra)
    a3 = cargar_marca(una)
    ok(b3.QUIEN == "otra-disenos" and a3.QUIEN == "una-disenos",
       "el orden no cambia nada", (b3.QUIEN, a3.QUIEN))

    print("\n■ No deja basura")
    ok("marca" not in sys.modules, "no queda un `marca` global en el caché")
    ok("brand" not in sys.modules, "ni un `brand` global")
    ok(not any(str(skills / n) in sys.path for n in ("una-disenos", "otra-disenos")),
       "ni carpetas de marca colgadas del sys.path")

    print("\n■ Una carpeta sin marca.py")
    vacia = skills / "vacia-disenos"; vacia.mkdir()
    try:
        cargar_marca(vacia)
        ok(False, "tendría que haber fallado")
    except Exception as e:                                   # noqa: BLE001
        ok(isinstance(e, (ImportError, FileNotFoundError)),
           "falla con un error claro", f"{type(e).__name__}: {e}")
    ok("marca__vacia_disenos" not in sys.modules,
       "y no deja el módulo a medio hacer en el caché")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n", "todo bien" if not fallos else f"{fallos} fallo(s)")
sys.exit(1 if fallos else 0)
