# -*- coding: utf-8 -*-
"""Sistema de diseño Boss Padel — tokens + componentes base."""

C = {
    "negro":     "#0A0A0A",
    "navy":      "#1B365D",
    "negro_puro":"#000000",
    "blanco":    "#FAFAFA",
    "azul":      "#1C5D7D",
    "azul_deep": "#123C51",
    "lima":      "#E4FF02",
    "naranja":   "#ED7F3E",
    "gris":      "#8C8C8C",
    "gris_osc":  "#1C1C1C",
}

FORMATOS = {
    "post":   (1080, 1080),   # 1:1 feed
    "vert":   (1080, 1350),   # 4:5 feed
    "story":  (1080, 1920),   # 9:16 historia
    "reel":   (1080, 1920),   # tapa de reel
}

FONT_CSS = """
@font-face{font-family:'Barlow';src:url('fonts/Barlow-Light.ttf');font-weight:300}
@font-face{font-family:'Barlow';src:url('fonts/Barlow-Regular.ttf');font-weight:400}
@font-face{font-family:'Barlow';src:url('fonts/Barlow-Medium.ttf');font-weight:500}
@font-face{font-family:'Barlow';src:url('fonts/Barlow-SemiBold.ttf');font-weight:600}
@font-face{font-family:'Barlow';src:url('fonts/Barlow-Bold.ttf');font-weight:700}
@font-face{font-family:'Barlow';src:url('fonts/Barlow-Black.ttf');font-weight:900}
@font-face{font-family:'Barlow';src:url('fonts/Barlow-BlackItalic.ttf');font-weight:900;font-style:italic}
@font-face{font-family:'BarlowC';src:url('fonts/BarlowCondensed-Light.ttf');font-weight:300}
@font-face{font-family:'BarlowC';src:url('fonts/BarlowCondensed-Regular.ttf');font-weight:400}
@font-face{font-family:'BarlowC';src:url('fonts/BarlowCondensed-Medium.ttf');font-weight:500}
@font-face{font-family:'BarlowC';src:url('fonts/BarlowCondensed-Bold.ttf');font-weight:700}
@font-face{font-family:'Archivo';src:url('fonts/Archivo-var.ttf');font-weight:100 900}
"""


import pathlib

_LOGO_SVG = (pathlib.Path(__file__).parent / "assets" / "boss-logo.svg").read_text()
LOGO_RATIO = 2.805  # ancho / alto del lockup oficial


def logo(size=1.0, color="#FAFAFA", align="right"):
    """Lockup oficial BOSS / PADEL 0000 (vectorial, del archivo original del club)."""
    w = 152 * size
    svg = _LOGO_SVG.replace("CURRENTBOSS", color)
    svg = svg.replace('<svg ', f'<svg style="width:{w:.1f}px;height:auto;display:block" ', 1)
    wrap = {"right": "margin-left:auto", "center": "margin:0 auto", "left": ""}[align]
    return f'<div class="bp-logo" style="width:{w:.1f}px;{wrap}">{svg}</div>'


LOGO_CSS = """
.bp-logo{display:block}
.bp-logo svg{overflow:visible}
"""


def aros(size=300, color="#FAFAFA", stroke=2.2, n=4, opacity=1.0):
    """Los 4 aros del '0000' — sello gráfico de la marca."""
    r = size / 2
    step = size * 0.34
    total = size + step * (n - 1)
    circles = "".join(
        f'<circle cx="{r + i*step:.1f}" cy="{r:.1f}" r="{r - stroke:.1f}" fill="none" '
        f'stroke="{color}" stroke-width="{stroke}"/>' for i in range(n)
    )
    return (f'<svg class="bp-aros" width="{total:.0f}" height="{size}" viewBox="0 0 {total:.0f} {size}" '
            f'style="opacity:{opacity}">{circles}</svg>')


# "Salpicón": trazos capsulares que salen de un núcleo, el gesto orgánico
# que el club usa en la esquina de las placas de torneo.
SALPICON = [  # (ángulo°, largo, grosor) — abanico hacia abajo-izquierda
    (132, 250, 104), (158, 330, 122), (183, 400, 132),
    (208, 320, 116), (233, 230, 98),
]


def blob(color="#ED7F3E", w=430, rot=0, opacity=1.0):
    cx, cy = 300, 190
    parts = [f'<circle cx="{cx}" cy="{cy}" r="132" fill="{color}"/>']
    for ang, lar, gro in SALPICON:
        parts.append(
            f'<rect x="{cx}" y="{cy-gro/2:.0f}" width="{lar}" height="{gro}" rx="{gro/2:.0f}" '
            f'fill="{color}" transform="rotate({ang} {cx} {cy})"/>')
    return (f'<svg class="bp-blob" width="{w}" height="{w}" viewBox="0 0 600 600" '
            f'style="transform:rotate({rot}deg);opacity:{opacity}">{"".join(parts)}</svg>')
