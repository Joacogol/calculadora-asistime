#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Que una pieza pueda traer un dibujo propio, y que se vea donde va.

    python3 herramientas/probar-dibujo.py

El retoque dejaba pintar lo que la plantilla ya dibujaba, y nada más. El
3/9/2026 se pidió una story de viernes «con emojis de música y el dibujo de
una silueta de consola de DJ»: el agente probó el retoque, no le alcanzó, y
terminó poniendo los emojis del sistema —🎵 es azul marino sobre un fondo
azul, o sea invisible— con una consola de cuatro perillas grises.

`data["dibujo"]` es la respuesta: SVG que se pega adentro del lienzo. Esta
prueba cubre las dos mitades:

  · **Lo que entra y lo que no.** El SVG se parsea con el parser de XML antes
    de tocar la pieza, así que un dibujo a medio cerrar o un `<script>` no
    llegan nunca al HTML.

  · **Dónde queda.** Esto se mide renderizando de verdad, porque la primera
    versión de `atras` usaba `z-index:-1` y la capa DESAPARECÍA: el fondo de
    las plantillas no es el de `.canvas` sino un `.scrim` puesto adentro. En
    el HTML se veía perfecto. Sólo se vio abriendo el PNG.
"""
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from motor import identidad, retoque                                    # noqa: E402

MARCA = RAIZ / ".claude/skills/asistime-disenos"
fallos = []


def ok(caso, condicion, detalle=""):
    print(f"  {'✓' if condicion else '✗'} {caso}"
          + (f" — {str(detalle)[:160]}" if detalle and not condicion else ""))
    if not condicion:
        fallos.append(caso)


def rechaza(caso, svg, esperado=""):
    try:
        retoque.revisar_dibujo(svg)
        ok(caso, False, "lo aceptó")
    except retoque.DibujoInvalido as e:
        ok(caso, (esperado in str(e)) if esperado else True, e)


CIRCULO = "<svg viewBox='0 0 10 10'><circle cx='5' cy='5' r='4'/></svg>"

print("\n■ Lo que se puede dibujar")
ok("un SVG simple entra", retoque.revisar_dibujo(CIRCULO) == CIRCULO)
ok("vacío no es un error", retoque.revisar_dibujo("") == "")
ok("un degradé con filtro entra", bool(retoque.revisar_dibujo(
    "<svg viewBox='0 0 10 10'><defs><linearGradient id='g'>"
    "<stop offset='0' stop-color='#fff'/></linearGradient>"
    "<filter id='f'><feGaussianBlur stdDeviation='2'/></filter></defs>"
    "<rect width='10' height='10' fill='url(#g)' filter='url(#f)'/></svg>")))

print("\n■ Lo que no")
rechaza("un script no entra", "<svg><script>alert(1)</script></svg>", "script")
rechaza("un foreignObject tampoco",
        "<svg><foreignObject><b>hola</b></foreignObject></svg>", "foreignObject")
rechaza("una etiqueta sin cerrar no se cuela a medias",
        "<svg><circle></svg>", "XML válido")
rechaza("dos raíces no son un dibujo",
        "<svg></svg><svg></svg>", "XML válido")
rechaza("no empieza por svg", "<g><circle r='1'/></g>", "empieza con «g»")
rechaza("un manejador de eventos no entra",
        "<svg onload='x()'><circle r='1'/></svg>", "onload")
rechaza("una imagen de internet no entra",
        "<svg><image href='https://x.com/y.png'/></svg>", "sin internet")
rechaza("un url() de internet en el style tampoco",
        "<svg><rect style=\"fill:url(https://x/y)\"/></svg>", "internet")
rechaza("un dibujo enorme no es un dibujo",
        "<svg>" + "<circle r='1'/>" * 2000 + "</svg>", "tope")
ok("una imagen embebida en data: SÍ entra", bool(retoque.revisar_dibujo(
    "<svg><image href='data:image/png;base64,iVBOR'/></svg>")))

print("\n■ Las capas")
uno = retoque.dibujos({"dibujo": CIRCULO})
ok("un SVG suelto es una capa", uno[1].count("<div class=") == 1, uno[1][:80])
varias = retoque.dibujos({"dibujo": [CIRCULO, {"svg": CIRCULO, "atras": True,
                                               "clase": "marco"}]})
ok("dos capas son dos divs", varias[1].count("<div class=") == 2)
ok("la que va atrás lo dice", 'class="dibujo atras marco"' in varias[1], varias[1])
ok("sin dibujo no se inyecta nada", retoque.dibujos({}) == ("", ""))
rechaza_capas = lambda d: retoque.dibujos({"dibujo": d})
for caso, data, esperado in (
        ("cinco capas son demasiadas", [CIRCULO] * 5, "tope"),
        ("una clase rara no pasa", [{"svg": CIRCULO, "clase": "a b"}], "clase"),
        ("un número no es un dibujo", 42, "tiene que ser")):
    try:
        rechaza_capas(data)
        ok(caso, False, "lo aceptó")
    except retoque.DibujoInvalido as e:
        ok(caso, esperado in str(e), e)

print("\n■ Dónde queda, mirando el PNG")
# Un rectángulo de un color que no existe en la marca: si aparece en la
# imagen, la capa se dibujó; si además el texto sigue blanco encima, quedó
# donde tiene que quedar.
VERDE = (0, 200, 0)
capa = ("<svg viewBox='0 0 1080 1920'><rect x='0' y='700' width='1080' "
        "height='500' fill='rgb(0,200,0)'/></svg>")
m = identidad.cargar(MARCA / "marca.py")
titular = m.PLANTILLAS["titular"]


def pintado(atras):
    from motor import render
    import tempfile
    data = {"titulo": "Mañana es\nVIERNES", "estilo": "degrade",
            "alineacion": "centro",
            "dibujo": {"svg": capa, "atras": atras}}
    with tempfile.TemporaryDirectory() as tmp:
        r = render.Render(m, MARCA)
        hechas = r.correr([{"nombre": "d", "plantilla": "titular",
                            "formato": "story", "data": data}], tmp)
        from PIL import Image
        im = Image.open(hechas[0]).convert("RGB")
        franja = im.crop((0, 700, 1080, 1200))
        colores = franja.getcolors(500000) or []
        verde = sum(n for n, c in colores if c == VERDE)
        blanco = sum(n for n, c in colores if min(c) > 245)
        return verde, blanco


# Chromium y Pillow viven en la imagen del worker, no en Cloud Shell. Que no
# estén no es un fallo de la pieza: es que esta máquina no puede mirar. Se
# dice y se sigue, en vez de teñir de rojo una prueba que pasó entera. Lo que
# NO se perdona es que estando los dos, el render falle.
try:
    import playwright, PIL                                             # noqa: F401
    puede_mirar = True
except ImportError as e:
    puede_mirar = False
    print(f"  · acá no se puede mirar el PNG: falta {e.name or e}.")
    print("    Las capas se verifican al renderizar, dentro del worker.")

if puede_mirar:
    try:
        verde, blanco = pintado(atras=True)
        ok("la capa de atrás se ve", verde > 100000, f"{verde} px verdes")
        ok("y el texto le queda encima", blanco > 20000, f"{blanco} px blancos")
        verde_e, blanco_e = pintado(atras=False)
        ok("la capa de encima tapa el texto", blanco_e < blanco / 4,
           f"{blanco_e} px blancos contra {blanco} de la de atrás")
    except Exception as e:
        ok("se pudo renderizar", False, e)

print("\n■ Que el motor avise cuando el dibujo tapa algo")
# La medida compara la pieza con y sin dibujo, así que hay que renderizar las
# dos. Los tres casos son los que separaron bien el 3/9/2026: una consola que
# cruza el pie (10%), unas formas en el fondo vacío (0%) y —el que costó una
# versión entera— un recuadro traslúcido DETRÁS del titular, que también da 0
# aunque cambie el fondo alrededor de cada letra.
CRUZA_EL_PIE = ("<svg viewBox='0 0 1080 1920'><g transform='translate(60 1560)' "
                "fill='none' stroke='#FFFFFF' stroke-width='8'>"
                "<rect width='900' height='300' rx='26'/>"
                "<circle cx='200' cy='150' r='90'/></g></svg>")
EN_EL_VACIO = ("<svg viewBox='0 0 1080 1920'><g fill='#FFFFFF' opacity='.5'>"
               "<circle cx='200' cy='430' r='34'/><circle cx='880' cy='330' r='30'/>"
               "</g></svg>")
DETRAS = ("<svg viewBox='0 0 1080 1920'><rect x='120' y='800' width='840' "
          "height='400' rx='40' fill='#00000055'/></svg>")


def avisos(dibujo):
    from motor import render
    import tempfile
    data = {"titulo": "Mañana es\nVIERNES", "estilo": "degrade",
            "alineacion": "centro", "dibujo": dibujo}
    with tempfile.TemporaryDirectory() as tmp:
        r = render.Render(m, MARCA)
        r.correr([{"nombre": "d", "plantilla": "titular", "formato": "story",
                   "data": data}], tmp)
        return r.avisos


# Un objeto que se sale por un lado (el megáfono del 4/9/2026, que quedó
# cortado y se leía como una taza) contra una franja que cruza la pieza y toca
# los dos costados a propósito.
SE_SALE = ("<svg viewBox='0 0 1080 1920'><path fill='#FFFFFF' "
           "d='M760 1100 L1000 1020 L1200 1060 L1200 1220 L1000 1260 L760 1180 Z'/></svg>")
CRUZA_ENTERA = ("<svg viewBox='0 0 1080 1920'><rect x='-200' y='640' width='1500' "
                "height='180' fill='#F5C518' transform='rotate(-8 540 730)'/></svg>")

if puede_mirar:
    try:
        a = avisos({"svg": CRUZA_EL_PIE})
        ok("avisa cuando el dibujo cruza el pie", len(a) == 1, a)
        ok("y dice dónde", a and "abajo a la izquierda" in a[0], a)
        ok("no avisa por un dibujo en el vacío", not avisos({"svg": EN_EL_VACIO}))
        ok("ni por una capa que va detrás del titular",
           not avisos({"svg": DETRAS, "atras": True}))

        a = avisos({"svg": SE_SALE})
        ok("avisa si el dibujo se sale por un solo lado",
           any("quedó cortado" in x for x in a), a)
        ok("y no por una franja que cruza y toca los dos",
           not any("quedó cortado" in x for x in avisos({"svg": CRUZA_ENTERA,
                                                         "atras": True})),
           avisos({"svg": CRUZA_ENTERA, "atras": True}))
    except Exception as e:
        ok("se pudo medir", False, e)


print("\n■ Que la marca se pueda agrandar desde un retoque")
# El 4/9/2026 se pidió el logo más grande, el agente escribió el retoque, y el
# isotipo salió idéntico: 48×40 px con y sin retoque. El tamaño iba en el
# atributo `style`, que le gana a cualquier clase. Ahora va como respaldo de
# una variable, y esta prueba mide la tinta blanca del isotipo en el PNG.
if puede_mirar:
    def isotipo(retoque=""):
        from motor import render
        from PIL import Image
        import tempfile
        data = {"titulo": "Mañana es\nVIERNES", "estilo": "degrade"}
        if retoque:
            data["retoque"] = retoque
        with tempfile.TemporaryDirectory() as tmp:
            r = render.Render(m, MARCA)
            hechas = r.correr([{"nombre": "d", "plantilla": "titular",
                                "formato": "story", "data": data}], tmp)
            im = Image.open(hechas[0]).convert("RGB").crop((0, 150, 700, 700))
            px = im.load(); xs = []
            for y in range(im.height):
                for x in range(im.width):
                    r_, g_, b_ = px[x, y]
                    if r_ > 245 and g_ > 245 and b_ > 245:
                        xs.append(x)
            return (max(xs) - min(xs) + 1) if xs else 0

    try:
        normal = isotipo()
        grande = isotipo(".marca-iso{--iso-ancho:150px;--iso-alto:150px}")
        ok("el isotipo sale con el tamaño del kit", 60 < normal < 90, f"{normal} px")
        ok("y un retoque lo agranda de verdad", grande > normal * 1.5,
           f"{normal} px → {grande} px")
    except Exception as e:
        ok("se pudo medir el isotipo", False, e)

print("\n  todo bien" if not fallos else f"\n  {len(fallos)} fallo(s): "
      + ", ".join(fallos))
sys.exit(1 if fallos else 0)
