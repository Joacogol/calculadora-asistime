# -*- coding: utf-8 -*-
"""Sistema de diseño de Clínica Preventiva — tokens y componentes base.

Los colores no salen de mirar una pantalla: el rojo y el gris están impresos
como especificación en el archivo original del logo («pantone 032 · 70% negro»),
y el resto se muestreó de los píxeles de piezas publicadas.

Ojo con una contradicción que existe en la marca: las placas que viene
publicando la cuenta usan un rojo más oscuro, `#E20613`, distinto al del logo.
Se resolvió a favor del logo, que es la especificación real. Si alguna vez hay
que volver atrás, es esta línea y nada más.
"""

C = {
    "blanco":    "#FFFFFF",   # el fondo. 37,6% de una pieza medida: es la marca
    "tinta":     "#181715",   # titulares y barra de pie
    "rojo":      "#EB3141",   # pantone 032 — el acento, nunca el fondo
    "gris":      "#6D6E70",   # 70% negro — primera línea de titular, metadatos
    "gris_claro":"#F0F0F0",   # fondo alternativo de las piezas con recorte
    "gris_suave":"#E7E7E8",   # fichas, separadores
    "verde":     "#25D366",   # el verde de WhatsApp, sólo para ese ícono
}

# Todo cuadrado, que es lo que la cuenta viene publicando. `vert` está para
# carruseles: 4:5 ocupa más pantalla en el feed y es donde conviene ir.
FORMATOS = {
    "post":  (1080, 1080),
    "vert":  (1080, 1350),
    "story": (1080, 1920),
    "reel":  (1080, 1920),
}

FONT_CSS = """
@font-face{font-family:'Mont';src:url('fonts/Montserrat-Regular.ttf');font-weight:400}
@font-face{font-family:'Mont';src:url('fonts/Montserrat-Medium.ttf');font-weight:500}
@font-face{font-family:'Mont';src:url('fonts/Montserrat-SemiBold.ttf');font-weight:600}
@font-face{font-family:'Mont';src:url('fonts/Montserrat-Bold.ttf');font-weight:700}
@font-face{font-family:'Mont';src:url('fonts/Montserrat-ExtraBold.ttf');font-weight:800}
@font-face{font-family:'Mont';src:url('fonts/Montserrat-Black.ttf');font-weight:900}
"""

import pathlib

_LOGO_SVG = (pathlib.Path(__file__).parent / "assets" / "clinica-logo.svg").read_text()
LOGO_RATIO = 2.369   # ancho / alto del lockup oficial, medido del vector


def logo(size=1.0, color=None, align="right"):
    """El lockup oficial: cruz con línea de pulso, CLÍNICA con el swoosh rojo
    debajo, y PREVENTIVA.

    `color` fuerza un color plano para toda la marca — se usa sobre foto
    oscura, donde el gris del original no tiene contraste. Sin argumento sale
    en sus dos colores reales, que es como va sobre blanco.
    """
    w = 190 * size
    svg = _LOGO_SVG
    if color:
        svg = svg.replace("CURRENTGRIS", color).replace("CURRENTROJO", color)
    else:
        svg = svg.replace("CURRENTGRIS", C["gris"]).replace("CURRENTROJO", C["rojo"])
    svg = svg.replace("<svg ", f'<svg style="width:{w:.1f}px;height:auto;display:block" ', 1)
    wrap = {"right": "margin-left:auto", "center": "margin:0 auto", "left": ""}[align]
    return f'<div class="cp-logo" style="width:{w:.1f}px;{wrap}">{svg}</div>'


LOGO_CSS = """
.cp-logo{display:block}
.cp-logo svg{overflow:visible}
"""


def puntos(w=340, h=340, color=None, sep=17, r=2.6, opacidad=1.0):
    """La trama de puntos que aparece en casi todas las piezas de la marca.

    Es lo único decorativo del sistema y cumple una función real: llena el aire
    de las composiciones con mucho blanco sin competir con el texto. Va siempre
    detrás, en gris claro, y nunca encima de una cara.
    """
    color = color or C["gris"]
    cols, filas = int(w // sep), int(h // sep)
    ptos = "".join(
        f'<circle cx="{c*sep + r:.1f}" cy="{f*sep + r:.1f}" r="{r}" fill="{color}"/>'
        for f in range(filas) for c in range(cols))
    return (f'<svg class="cp-puntos" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" style="opacity:{opacidad}">{ptos}</svg>')


def pastilla(texto, fondo=None, color="#FFFFFF", cuerpo=27):
    """La etiqueta chica de fondo sólido que encabeza una pieza.

    En la marca aparece arriba del titular («EXAMEN PSICOTÉCNICO») y también
    como sello de garantía («✓ Resultados garantizados en 24 hs»).
    """
    fondo = fondo or C["rojo"]
    return (f'<div style="display:inline-block;background:{fondo};color:{color};'
            f'padding:11px 22px;font-family:\'Mont\',sans-serif;font-weight:700;'
            f'font-size:{cuerpo}px;letter-spacing:.10em;text-transform:uppercase;'
            f'line-height:1">{texto}</div>')


def sello(texto, cuerpo=22):
    """El distintivo de garantía: «Resultados garantizados en 24 hs».

    Era una píldora negra sólida, heredada de una pieza publicada. El negro no
    es un color de esta marca y un bloque oscuro al lado del precio compite con
    él justo donde la pieza tiene que ganar.

    Ahora es un contorno fino en gris con el tilde en rojo: dice lo mismo,
    aporta la garantía, y no le saca peso al precio.
    """
    # El pedido suele traer el tilde escrito adentro del texto («✓ Resultados
    # garantizados…»). Como el sello dibuja el suyo, sin esto salen dos.
    texto = str(texto).lstrip("✓✔✅ ").strip()
    return (f'<div style="display:inline-flex;align-items:center;gap:9px;'
            f'border:1.5px solid {C["gris_suave"]};border-radius:999px;'
            f'padding:9px 20px 9px 16px">'
            f'<span style="color:{C["rojo"]};font-size:{cuerpo}px;'
            f'font-weight:700;line-height:1">✓</span>'
            f'<span style="font-family:\'Mont\',sans-serif;font-weight:500;'
            f'font-size:{cuerpo}px;color:{C["gris"]};letter-spacing:.02em">'
            f'{texto}</span></div>')


ICONO_WA = ('<svg width="29" height="29" viewBox="0 0 24 24" fill="#EB3141">'
            '<path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38'
            'a9.86 9.86 0 0 0 4.79 1.22h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01'
            'A9.82 9.82 0 0 0 12.04 2m5.8 14.16c-.25.69-1.44 1.32-1.99 1.37-.53.05-1.02.24-3.45-.72'
            '-2.9-1.14-4.73-4.1-4.87-4.29-.14-.19-1.16-1.54-1.16-2.94s.73-2.09.99-2.37c.26-.29.57-.36.76-.36'
            'l.55.01c.17 0 .41-.07.64.49l.88 2.13c.07.15.12.32.02.51-.1.19-.15.31-.3.48l-.45.52'
            'c-.15.15-.3.31-.13.61.17.29.75 1.24 1.61 2.01 1.11.99 2.04 1.3 2.33 1.44.29.15.46.12.63-.07'
            'l.9-1.05c.21-.25.38-.19.64-.1l1.82.86c.26.13.44.19.5.29.07.11.07.6-.18 1.29"/></svg>')

ICONO_WEB = ('<svg width="27" height="27" viewBox="0 0 24 24" fill="none" stroke="#EB3141" '
             'stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/>'
             '<path d="M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18"/></svg>')


# El teléfono fijo. La marca lo usa junto al WhatsApp en las piezas de
# convenio, donde la empresa suele llamar antes de mandar un mensaje.
ICONO_TEL = ('<svg width="27" height="27" viewBox="0 0 24 24" fill="none" '
             'stroke="#EB3141" stroke-width="2" stroke-linecap="round" '
             'stroke-linejoin="round">'
             '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 '
             '19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3'
             'a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 '
             '9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.9.34 1.85.57 '
             '2.81.7A2 2 0 0 1 22 16.92z"/></svg>')
