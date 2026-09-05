#!/usr/bin/env python3
"""Prueba que el motor sepa DÓNDE cae el sujeto recortado dentro de la pieza.

    python3 herramientas/probar-silueta.py

Las figuras se dibujan acá con PIL, así que la prueba corre en un segundo, no
depende de ninguna foto del banco y da siempre el mismo número.

## Por qué existe

Porque el 4 y el 5/9/2026, cuatro veces seguidas, «ASISTIME.AI» salió escrito
encima de la oreja de Tony. El guardián de contraste lo veía —2,6:1 sobre el
pelaje— pero sólo DESPUÉS de renderizar: avisaba de un defecto ya cometido. Un
diseñador no firma sobre el sujeto y después mide si se lee; mira dónde está el
sujeto y firma en otro lado. Para poder mirar hay que saber dónde quedó el
recorte, y eso no es obvio: entra al lienzo con `object-fit: contain` y
`object-position`, así que no ocupa el rectángulo ni está donde está en el
archivo.

Lo que se fija acá es esa cuenta, que es la única parte del asunto que puede
estar mal en silencio: si `ocupacion` devuelve 0 cuando el sujeto está ahí, la
plantilla firma encima y nadie se entera hasta ver el PNG.

Las tres reglas de `motor/revisar.py` valen igual: **si no se puede medir, se
calla**. Por eso los casos 4 y 5 —una foto sin alfa, un archivo que no existe—
tienen que dar 0,0 y no una excepción: un falso «está tapado» haría desaparecer
la firma de piezas que estaban bien.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from motor import silueta                                    # noqa: E402

#: El lienzo de una story y la banda donde cae el pie de una marca: los 38 px
#: justo arriba del margen seguro de Instagram, que son 250 y no los 96 de la
#: plantilla. Son los números reales de Asistime, para que lo que se mide acá
#: sea lo mismo que se mide en la pieza.
ANCHO, ALTO = 1080, 1920
ABAJO, IZQUIERDA = 250, 96
PIE = (IZQUIERDA / ANCHO, (ALTO - ABAJO - 38) / ALTO, 0.55, (ALTO - ABAJO) / ALTO)


def _figura(carpeta, nombre, alto_figura, con_alfa=True):
    """Un PNG de 1080×1350 con una barra opaca abajo de `alto_figura` px.

    Es la forma de un recorte anclado abajo —Tony asomándose— reducida a lo
    único que importa acá: dónde hay píxeles opacos y dónde hay aire.
    """
    from PIL import Image, ImageDraw
    modo = "RGBA" if con_alfa else "RGB"
    fondo = (0, 0, 0, 0) if con_alfa else (200, 160, 90)
    im = Image.new(modo, (1080, 1350), fondo)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 1350 - alto_figura, 1080, 1350],
                fill=(200, 160, 90, 255) if con_alfa else (200, 160, 90))
    ruta = pathlib.Path(carpeta) / nombre
    im.save(ruta)
    return str(ruta)


def main() -> int:
    try:
        import PIL                                           # noqa: F401
    except Exception:
        print("sin PIL no hay nada que probar")
        return 0

    fallas = []

    def ok(bien, que, detalle=""):
        if bien:
            print(f"✓ {que}")
        else:
            fallas.append(f"✗ {que}" + (f"\n  {detalle}" if detalle else ""))

    with tempfile.TemporaryDirectory() as tmp:
        recorte = _figura(tmp, "recorte.png", 400)
        foto = _figura(tmp, "foto.png", 400, con_alfa=False)

        # ── 1 · anclado abajo: el sujeto está en la banda del pie ────────
        #
        # Con `foco` abajo, la imagen de 1350 de alto se apoya en el borde de
        # abajo del lienzo de 1920, así que sus últimos 400 px SON los últimos
        # 400 px de la pieza. La banda del pie cae entera adentro.
        abajo = silueta.ocupacion(recorte, ANCHO, ALTO, PIE, "50% 100%")
        ok(abajo > 0.9,
           f"anclado abajo, el sujeto ocupa la banda del pie ({abajo:.2f})",
           "Si esto da 0, la plantilla firma encima del sujeto y nadie avisa: "
           "es\n  exactamente lo que pasó con la oreja de Tony.")

        # ── 2 · centrado: la misma figura ya no llega al pie ─────────────
        #
        # Centrada, la imagen ocupa de 285 a 1635 y su barra va de 1235 a 1635.
        # La banda del pie arranca en 1632: apenas la roza. El caso importa
        # porque es el que separa «hay que hacer algo» de «no pasa nada», y si
        # los dos dieran parecido el umbral de la plantilla no significaría
        # nada.
        centro = silueta.ocupacion(recorte, ANCHO, ALTO, PIE, "50% 50%")
        ok(centro < 0.15,
           f"centrado, el mismo recorte casi no toca el pie ({centro:.2f})",
           "Con este valor alto, cualquier recorte borraría el pie de "
           "cualquier pieza.")

        ok(abajo - centro > 0.5,
           f"entre los dos casos hay {abajo - centro:.2f} de distancia",
           "Sin separación no hay umbral honesto que poner.")

        # ── 3 · arriba del todo: no hay nada en el pie ───────────────────
        arriba = silueta.ocupacion(recorte, ANCHO, ALTO, PIE, "50% 0%")
        ok(arriba == 0.0, f"anclado arriba, el pie queda libre ({arriba:.2f})")

        # ── 4 · una FOTO de fondo no es un sujeto ────────────────────────
        #
        # Una foto que ocupa el rectángulo entero está debajo de todo y no hay
        # adónde correr nada: para eso está el velo de `legibilidad`. Si esto
        # devolviera «tapado», toda pieza con foto perdería su firma.
        sin_alfa = silueta.ocupacion(foto, ANCHO, ALTO, PIE, "50% 100%")
        ok(sin_alfa == 0.0,
           f"una foto sin canal alfa no cuenta como sujeto ({sin_alfa:.2f})",
           "Una foto de fondo se resuelve con velo, no moviendo la firma.")

        # ── 5 · si no se puede medir, se calla ───────────────────────────
        for caso, valor in (("un archivo que no existe", f"{tmp}/no-esta.png"),
                            ("una foto vacía", ""),
                            ("un alto en cero", None)):
            v = silueta.ocupacion(valor if valor is not None else recorte,
                                  ANCHO, 0 if valor is None else ALTO, PIE)
            ok(v == 0.0, f"{caso} devuelve 0,0 y no revienta ({v})",
               "Regla 3 de motor/revisar.py: si no se puede medir, callarse.")

        # ── 6 · `object-position` en todas sus formas ────────────────────
        #
        # El banco escribe «50% 100%» y una plantilla puede escribir «center
        # bottom»: son lo mismo y tienen que medir lo mismo. Lo que no se
        # entiende cae en el centro, que es el default del navegador.
        palabras = silueta.ocupacion(recorte, ANCHO, ALTO, PIE, "center bottom")
        ok(abs(palabras - abajo) < 0.01,
           "«center bottom» y «50% 100%» miden lo mismo",
           f"{palabras:.3f} vs {abajo:.3f}")
        raro = silueta.ocupacion(recorte, ANCHO, ALTO, PIE, "vaya a saber")
        ok(abs(raro - centro) < 0.01,
           "un `foco` que no se entiende cae en el centro, como el navegador",
           f"{raro:.3f} vs {centro:.3f}")

    if fallas:
        print("\n" + "\n".join(fallas))
        return 1
    print("\nsilueta OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
