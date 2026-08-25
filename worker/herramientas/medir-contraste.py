# -*- coding: utf-8 -*-
"""¿Se lee el texto de una pieza? Lo mide, no lo opina.

    python3 herramientas/medir-contraste.py pieza.html [ancho] [alto]

Nació de un reclamo concreto: «con la foto de fondo las letras blancas se
pierden un poco». Mirando la pieza era difícil decir cuánto, y sobre todo
dónde. Medido apareció en un renglón: la mediana del contraste daba 8,85:1 y
el peor punto 1,98:1. O sea, el 90% del texto estaba perfecto y se moría justo
donde cruzaba una paleta blanca. Con eso el arreglo fue obvio.

## Cómo mide

1. Abre la pieza y anota la caja y el color de cada bloque de texto.
2. La vuelve a dibujar con el texto en `color: transparent` —NO oculto— y se
   queda con esa imagen. La diferencia importa: la sombra de un texto se
   dibuja a partir de la silueta de la letra y no de su relleno, así que con
   el texto transparente la sombra SIGUE ahí. Ocultándolo mediríamos un fondo
   que en la pieza real no existe, y toda sombra parecería inútil.
3. Para cada caja saca el fondo de abajo y calcula el contraste WCAG.

## Dos decisiones que cambian el resultado

**Percentil 90 y no promedio.** Lo que arruina la lectura no es que el fondo
sea claro en promedio: es la mancha clara que se cruza con tres letras. El
promedio la esconde. Este es el punto entero de la herramienta.

**El contraste se calcula entre los DOS colores reales**, no contra blanco.
La primera versión asumía texto blanco y reportaba «1,00:1» en una chapita de
texto oscuro sobre fondo blanco —que en realidad es 15,9:1— y mandaba a
arreglar lo que estaba bien. Una medición que inventa fallos es peor que no
medir.

## Los objetivos

WCAG: 4,5:1 para texto normal, 3:1 para texto grande (≥ 24px en negrita).
Acá el corte es por tamaño de letra, leído del navegador.
"""
import asyncio
import io
import pathlib
import sys

CHROME = "/opt/pw-browsers/chromium"

#: Todo lo que puede llevar texto en las plantillas de las tres marcas.
SELECTOR = (".v-cond,.v-serif,.v-normal,.disp,.disp-x,.precio,"
            ".body,.kicker,.legal,h1,h2,h3,p,span,div")


def _lum(c):
    def f(v):
        v = v / 255
        return v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4
    return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2])


def contraste(a, b):
    l1, l2 = sorted((_lum(a), _lum(b)), reverse=True)
    return (l1 + .05) / (l2 + .05)


def _rgb(css):
    n = css.replace("rgba(", "").replace("rgb(", "").rstrip(")").split(",")
    return tuple(int(float(v)) for v in n[:3])


async def medir(html: pathlib.Path, ancho=1080, alto=1080):
    from playwright.async_api import async_playwright
    from PIL import Image

    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path=CHROME)
        pg = await b.new_page(viewport={"width": ancho, "height": alto})
        await pg.goto(html.resolve().as_uri(), wait_until="load")
        await pg.evaluate("document.fonts.ready")
        await pg.wait_for_timeout(400)

        cajas = []
        for el in await pg.query_selector_all(SELECTOR):
            # Sólo hojas: un contenedor con hijos devolvería el texto de todos
            # y una caja que no es la de ninguna línea.
            if await el.evaluate("e => e.children.length > 0"):
                continue
            txt = " ".join((await el.inner_text()).split())
            bb = await el.bounding_box()
            if not txt or not bb or bb["width"] < 8 or bb["height"] < 8:
                continue
            info = await el.evaluate(
                "e => { const s = getComputedStyle(e);"
                "return [s.color, parseFloat(s.fontSize), s.fontWeight]; }")
            cajas.append((txt, bb, _rgb(info[0]), info[1], info[2]))

        await pg.add_style_tag(content=(
            SELECTOR + "{color:transparent !important;"
            "-webkit-text-fill-color:transparent !important}"))
        await pg.wait_for_timeout(150)
        fondo = Image.open(io.BytesIO(await pg.screenshot())).convert("RGB")
        await pg.close()
        await b.close()

    print(f"\n{html.name} · {ancho}×{alto}")
    peor, fallos = 99.0, 0
    for txt, bb, tinta, cuerpo, peso in cajas:
        x, y = max(int(bb["x"]), 0), max(int(bb["y"]), 0)
        rec = fondo.crop((x, y, min(int(x + bb["width"]), fondo.width),
                          min(int(y + bb["height"]), fondo.height)))
        px = sorted(rec.resize((40, 40)).getdata(), key=_lum)
        p90, med = px[int(len(px) * .90)], px[len(px) // 2]
        c90, cmed = contraste(tinta, p90), contraste(tinta, med)
        grande = cuerpo >= 24 and (peso in ("bold", "bolder") or
                                   (peso.isdigit() and int(peso) >= 700))
        objetivo = 3.0 if grande else 4.5
        ok = c90 >= objetivo
        peor = min(peor, c90)
        fallos += 0 if ok else 1
        print(f"  {'OK  ' if ok else 'BAJO'} «{txt[:38]:38s}» {int(cuerpo):3d}px "
              f"{'#%02X%02X%02X' % tinta}  peor {c90:5.2f}:1  "
              f"mediana {cmed:5.2f}:1  (pide {objetivo})")
    print(f"  → peor punto: {peor:.2f}:1 · {fallos} bloque(s) por debajo")
    return fallos


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    ruta = pathlib.Path(sys.argv[1])
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 1080
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 1080
    raise SystemExit(1 if asyncio.run(medir(ruta, w, h)) else 0)
