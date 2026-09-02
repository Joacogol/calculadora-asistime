#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Que una marca hecha sólo de datos dibuje exactamente lo mismo.

    python3 herramientas/probar-identidad.py                    # contra los hashes guardados
    python3 herramientas/probar-identidad.py --grabar           # guarda los hashes de hoy
    python3 herramientas/probar-identidad.py --contra-python    # contra el brand.py viejo, si está

El 2/9/2026 Stadium pasó de 466 líneas de Python propio a `marca.json` +
`estilo.css`. Antes de borrar el Python se renderizaron sus 5 plantillas en
los 4 formatos por los dos caminos y se compararon **byte a byte**: 20 / 20
idénticas. Ese es el modo `--contra-python`, y sólo corre mientras exista el
`brand.py`.

Después, lo que queda es el hash de cada una de esas 20 salidas. Si una
plantilla cambia a propósito, se vuelve a grabar; si cambia sin querer —un
ayudante del motor que alguien tocó—, esto lo dice con nombre de plantilla y
formato.
"""
import hashlib
import importlib
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from motor import contrato, identidad                                   # noqa: E402

MARCA = "stadium-disenos"
CARPETA = RAIZ / ".claude/skills" / MARCA
FIXTURE = pathlib.Path(__file__).with_name("fixtures") / f"identidad-{MARCA}.json"
FOTO = "assets/producto-championes.jpg"

fallos = 0
def ok(c, que, det=None):
    global fallos
    print("  ✓" if c else "  ✗", que, "" if c or det is None else str(det)[:300])
    fallos += 0 if c else 1


def datos_de_ejemplo(c):
    """Cada campo con su ejemplo; las fotos apuntan a una real de la marca."""
    d = {}
    for campo in c["campos"]:
        tipo = campo.get("tipo", "")
        if tipo in ("foto", "imagen") or "foto" in campo["id"]:
            d[campo["id"]] = FOTO
        elif "ejemplo" in campo:
            d[campo["id"]] = campo["ejemplo"]
        elif "default" in campo:
            d[campo["id"]] = campo["default"]
        elif tipo == "lista":
            d[campo["id"]] = []
        elif campo.get("requerido"):
            d[campo["id"]] = f"Ejemplo de {campo['id']}"
    return d


def renders(m):
    salida = {}
    for pid, fn in sorted(m.PLANTILLAS.items()):
        for fmt in fn.contrato["medidas"]:
            salida[f"{pid}/{fmt}"] = fn(datos_de_ejemplo(fn.contrato), fmt)
    return salida


print(f"\n■ {MARCA} como datos")
nuevo = identidad.cargar(CARPETA / "marca.py")
ok(contrato.verificar(nuevo), "cumple el contrato del motor")
ok(len(nuevo.PLANTILLAS) == 5, "las cinco plantillas cargan", list(nuevo.PLANTILLAS))
sal = renders(nuevo)
ok(len(sal) == 20, "20 salidas: 5 plantillas × 4 formatos", len(sal))
ok(all("<html>" in h and 'class="canvas"' in h for h in sal.values()), "todas son una página entera")
ok(nuevo.sombra_texto().endswith(";"), "sombra_texto cierra con punto y coma")
ok(nuevo.pad_seguro("reel", 72) == "250px 144px 420px 72px", "pad_seguro respeta lo que tapa Instagram y nunca achica", nuevo.pad_seguro("reel", 72))
ok("stadium.com.uy" in nuevo.barra(), "la barra dice lo que la identidad dice")
ok(nuevo.paleta("papa")["voz"] == "cond" and nuevo.paleta("madre", fondo="#000")["fondo"] == "#000",
   "las paletas se leen y se pisan")

modo = sys.argv[1] if len(sys.argv) > 1 else ""
if modo == "--contra-python":
    print("\n■ Contra el brand.py viejo, byte a byte")
    if not (CARPETA / "brand.py").exists():
        ok(False, "no está brand.py: este modo sólo corre antes de borrarlo")
    else:
        sys.path.insert(0, str(CARPETA)); sys.path.insert(0, str(RAIZ))
        for mod in ("brand", "marca"):
            sys.modules.pop(mod, None)
        viejo = importlib.import_module("marca")
        vsal = renders(viejo)
        iguales = [k for k in sal if sal[k] == vsal.get(k)]
        distintas = [k for k in sal if sal[k] != vsal.get(k)]
        ok(not distintas, f"{len(iguales)} / {len(sal)} idénticas", distintas)
        for k in distintas[:3]:
            a, b = sal[k], vsal[k]
            i = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
            print(f"    {k}: difiere en el byte {i}: …{a[max(0,i-60):i+40]!r}\n"
                  f"      vs …{b[max(0,i-60):i+40]!r}")
        ok(viejo.BASE_CSS == nuevo.BASE_CSS, "la hoja de estilo es la misma")
        ok(viejo.C == nuevo.C and viejo.FORMATOS == nuevo.FORMATOS, "colores y formatos iguales")
        ok(viejo.PALETAS == nuevo.PALETAS and viejo.VOCES == nuevo.VOCES, "paletas y voces iguales")
        for n in ("TIPO_REEL", "ANIMO_MUSICA", "ACENTO_REEL", "COLOR_CROMO", "FUENTE_CROMO", "FUENTE_TEXTO", "ACENTO_POR_DEFECTO", "NOMBRE", "VOCABULARIO"):
            ok(getattr(viejo, n) == getattr(nuevo, n), f"{n} igual", (getattr(viejo, n), getattr(nuevo, n)))

hashes = {k: hashlib.sha256(v.encode("utf-8")).hexdigest() for k, v in sal.items()}
if modo == "--grabar":
    FIXTURE.parent.mkdir(exist_ok=True)
    FIXTURE.write_text(json.dumps(hashes, indent=1) + "\n")
    print(f"\n  grabados {len(hashes)} hashes en {FIXTURE.name}")
elif FIXTURE.exists():
    print("\n■ Contra lo grabado")
    guardado = json.loads(FIXTURE.read_text())
    cambiadas = [k for k in hashes if guardado.get(k) != hashes[k]]
    ok(not cambiadas, f"{len(hashes) - len(cambiadas)} / {len(hashes)} iguales a lo grabado", cambiadas)
    if cambiadas:
        print("    Si el cambio es a propósito: python3 herramientas/probar-identidad.py --grabar")

print(f"\n✗ {fallos} fallo(s)\n" if fallos else "\n✓ todo bien\n")
sys.exit(1 if fallos else 0)
