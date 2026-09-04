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

print("\n■ asistime-disenos: la primera marca que entró entera como datos")
#
# Sin Python, sin SVG —sus logos son PNG en dos versiones— y con las fuentes en
# woff2 más dos TTF fijas para los rótulos del reel. Si esto carga y dibuja,
# el camino del alta está completo de punta a punta.
asi = identidad.cargar(RAIZ / ".claude/skills/asistime-disenos/marca.py")
ok(contrato.verificar(asi), "cumple el contrato")
ok(sorted(asi.PLANTILLAS) == ["cierre", "dato", "producto", "testimonio", "titular"], "sus cinco plantillas", sorted(asi.PLANTILLAS))
asal = renders(asi)
ok(len(asal) == 20, "20 salidas", len(asal))
ok('src="assets/lockup-color.png"' in asal["cierre/post"], "el logo PNG va como imagen")
ok('src="assets/isotipo-blanco.png"' in asal["dato/post"], "y sobre oscuro va la versión blanca")
# La firma tiene que quedar alcanzable desde un retoque: clase para apuntarle
# y el tamaño como RESPALDO de una variable, no declarado en línea. Si alguien
# vuelve a poner `width:60px` a secas, «agrandá el logo» vuelve a ser
# imposible y nadie se entera hasta que sale la pieza.
ok('class="marca-logo"' in asal["cierre/post"]
   and "width:var(--logo-ancho," in asal["cierre/post"],
   "el lockup se puede agrandar desde un retoque")
ok('class="marca-iso"' in asal["dato/post"]
   and "width:var(--iso-ancho," in asal["dato/post"],
   "y el isotipo también")
# La firma no es siempre la misma: las cinco plantillas tienen que respetar el
# campo `firma`. Si alguna vuelve a dibujar el isotipo a mano, «que sea
# dinámico según la pieza» deja de valer para esa plantilla y nadie se entera.
for _pid, _fn in sorted(asi.PLANTILLAS.items()):
    _con = _fn({**datos_de_ejemplo(_fn.contrato), "firma": "lockup"}, "story")
    _sin = _fn({**datos_de_ejemplo(_fn.contrato), "firma": "ninguna"}, "story")
    ok("lockup" in _con, f"«{_pid}» firma con el lockup cuando se lo piden")
    ok("isotipo" not in _sin.split("</style>")[-1],
       f"«{_pid}» no firma arriba con «ninguna»")

ok(asi.TIPO_REEL == ("RedHatDisplay-ExtraBold.ttf", "RedHatDisplay-SemiBold.ttf") and all((RAIZ / ".claude/skills/asistime-disenos/fonts" / f).exists() for f in asi.TIPO_REEL),
   "las TTF del reel existen")
ok("Red Hat Display" in asi.BASE_CSS and "Sora" not in asi.BASE_CSS, "una sola tipografía: Red Hat Display")

print("\n■ asistime-disenos: carruseles sin Python, con sus propias plantillas")
#
# `carrusel.diapos` en el marca.json dice con qué plantilla se dibuja cada tipo
# de diapositiva y el motor arma DIAPOS con eso. Si esto pasa, una marca de
# datos tiene carruseles y secuencias sin escribir una línea.
from motor import carrusel as mcarrusel
ok(hasattr(asi, "DIAPOS") and contrato.verificar(asi, con_carrusel=True), "cumple el contrato CON carrusel")
ok(sorted(asi.DIAPOS) == ["cierre", "cuadro", "dato", "portada", "producto", "testimonio", "texto"], "sus siete tipos de diapositiva", sorted(asi.DIAPOS))
carr = {"slides": [
    {"tipo": "portada", "titulo": "¿Cuántas horas se te van?", "destacado": "horas"},
    {"tipo": "dato", "numero": "11 h", "texto": "por semana", "fuente": "Asistime, 2026"},
    {"tipo": "testimonio", "cita": "Ceno con mis hijos.", "nombre": "Ana"},
    {"tipo": "producto", "titulo": "Así se ve", "chat": "Hola\nTony: ¡Hola!"},
    {"tipo": "cierre", "estilo": "degrade"}]}
pags = mcarrusel.paginas(asi, carr, "vert")
ok(len(pags) == 5 and all("01 / 05" in pags[0] for _ in [0]), "un carrusel de cinco, numerado")
ok("Ceno con mis hijos" in pags[2] and "¡Hola!" in pags[3], "cada diapositiva es su plantilla")
ok('class="cr-idx" style="color:#0A0B14' in pags[0] and 'class="cr-idx" style="color:#FFFFFF' in pags[1] and 'class="cr-idx" style="color:#FFFFFF' in pags[4],
   "el índice va en tinta sobre claro y en blanco sobre el dato y el cierre degradé")
sec = mcarrusel.paginas(asi, {"slides": [{"tipo": "cuadro", "titulo": "¿Atendés a las 23?"}, {"tipo": "cierre", "responder": "Contame"}]}, "story", secuencia=True)
ok(len(sec) == 2 and "Contame" in sec[1] and "height:1920px" in sec[0], "una secuencia de stories, con la caja de respuesta")
try:
    mcarrusel.paginas(asi, {"slides": [{"tipo": "podio"}]}, "vert")
    ok(False, "un tipo que no existe se rechaza")
except ValueError as e:
    ok("podio" in str(e), "un tipo que no existe se rechaza con nombre", e)
ok("### Las diapositivas de esta marca" in asi.CATALOGO() and "`portada` → plantilla `titular`" in asi.CATALOGO(), "el catálogo cuenta las diapositivas")

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
