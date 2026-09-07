# -*- coding: utf-8 -*-
"""Sistema de diseño Asistime.ai — tokens + componentes base.

Asistime es **clara por defecto**, al revés que Boss Padel. El fondo es un
blanco apenas azulado y el trabajo de acento lo hace un solo azul. El momento
oscuro existe —es el slide de impacto y el cierre— pero es una decisión, no el
estado normal de la marca.
"""
import base64
import pathlib

AQUI = pathlib.Path(__file__).resolve().parent

C = {
    # Azul de marca
    "azul":       "#006AFF",   # logo, botones, íconos
    "azul_texto": "#005CFF",   # palabra destacada sobre fondo claro
    "azul_deep":  "#0047CC",   # hover / profundidad
    "azul_glow":  "#2B8BFF",   # acento sobre fondo oscuro

    # Tinta
    "navy":       "#00082F",   # titulares y texto sobre claro
    "navy_70":    "#3A4160",   # texto secundario
    "navy_45":    "#7A8098",   # metadatos
    "tinta":      "#01030D",   # fondo del slide oscuro
    "tinta_2":    "#0A1226",   # cards sobre oscuro

    # Claros
    "fondo":      "#FBFCFE",
    "fondo_2":    "#EFF3FE",
    "blanco":     "#FFFFFF",
    "linea":      "rgba(0,10,60,.09)",

    # Semánticos
    "whatsapp":   "#25D366",   # EXCLUSIVO WhatsApp
    "ok":         "#12B76A",
    "warn":       "#F5A623",
    "alerta":     "#F04438",
}

# Los dos fondos firma. Todo lo demás es una variación de estos dos.
GRAD_CLARO = "linear-gradient(155deg,#FDFDFF 0%,#F6F9FE 45%,#E9F0FE 100%)"
GRAD_OSCURO = ("radial-gradient(120% 90% at 78% 62%,#062A6B 0%,"
               "#021340 38%,#01030D 78%)")

FORMATOS = {
    "post":  (1080, 1080),   # 1:1 feed
    "vert":  (1080, 1350),   # 4:5 feed — el de la marca
    "story": (1080, 1920),   # 9:16 historia
    "reel":  (1080, 1920),   # tapa de reel
}

FONT_CSS = """
@font-face{font-family:'Sora';src:url('fonts/sora-400.woff2') format('woff2');font-weight:400;font-display:block}
@font-face{font-family:'Sora';src:url('fonts/sora-500.woff2') format('woff2');font-weight:500;font-display:block}
@font-face{font-family:'Sora';src:url('fonts/sora-600.woff2') format('woff2');font-weight:600;font-display:block}
@font-face{font-family:'Sora';src:url('fonts/sora-700.woff2') format('woff2');font-weight:700;font-display:block}
@font-face{font-family:'Sora';src:url('fonts/sora-800.woff2') format('woff2');font-weight:800;font-display:block}
@font-face{font-family:'DMSans';src:url('fonts/dm-sans-400.woff2') format('woff2');font-weight:400;font-display:block}
@font-face{font-family:'DMSans';src:url('fonts/dm-sans-500.woff2') format('woff2');font-weight:500;font-display:block}
@font-face{font-family:'DMSans';src:url('fonts/dm-sans-700.woff2') format('woff2');font-weight:700;font-display:block}
"""


def _b64(nombre: str) -> str:
    """El PNG del logo embebido. Chromium abre el HTML desde una carpeta
    temporal en algunos caminos del motor y una ruta relativa se rompe;
    embebido no se rompe nunca y son 20 KB."""
    d = (AQUI / "logo" / nombre).read_bytes()
    return "data:image/png;base64," + base64.b64encode(d).decode()


_CACHE = {}


def _logo_src(nombre: str) -> str:
    if nombre not in _CACHE:
        _CACHE[nombre] = _b64(nombre)
    return _CACHE[nombre]


def logo(size=1.0, color="#006AFF", align="left"):
    """El isotipo — la A con el destello. Es lo que va en la esquina de una
    pieza. `color` no recolorea nada: elige cuál de los tres archivos
    oficiales se usa, porque el logo NUNCA se recolorea a mano."""
    w = 62 * size
    claro = color.upper() in ("#FFFFFF", "#FFF", "BLANCO", "#FBFCFE")
    negro = color.upper() in ("#000000", "#01030D", "NEGRO")
    arch = ("isotipo-blanco.png" if claro
            else "isotipo-negro.png" if negro else "isotipo-azul.png")
    wrap = {"right": "margin-left:auto", "center": "margin:0 auto", "left": ""}[align]
    return (f'<img class="as-logo" src="{_logo_src(arch)}" alt="Asistime" '
            f'style="width:{w:.0f}px;height:{w:.0f}px;{wrap}">')


def lockup(ancho=340, color="#006AFF", align="left"):
    """El logo completo — isotipo + «Asistime.ai». Se reserva para el cierre
    de un carrusel, la portada de una presentación y los documentos."""
    claro = color.upper() in ("#FFFFFF", "#FFF", "BLANCO")
    arch = "lockup-blanco.png" if claro else "lockup-color.png"
    wrap = {"right": "margin-left:auto", "center": "margin:0 auto", "left": ""}[align]
    h = ancho * 400 / 2000
    return (f'<img class="as-lockup" src="{_logo_src(arch)}" alt="Asistime.ai" '
            f'style="width:{ancho:.0f}px;height:{h:.0f}px;{wrap}">')


LOGO_CSS = """
.as-logo{display:block}
.as-lockup{display:block}
"""


# ─────────────────────────────────────────────────────────────────── ÍCONOS
# SVG inline dentro de un círculo azul. Nunca emojis: dependen de la fuente del
# sistema, rompen el export y en Mac salen con el color de Apple.
_PATHS = {
    "chat":     "M21 11.5a8.4 8.4 0 0 1-9 8.4 9 9 0 0 1-4-.9L3 21l1.9-4.6A8.4 8.4 0 0 1 4 11.5 8.4 8.4 0 0 1 12.5 3 8.4 8.4 0 0 1 21 11.5z",
    "reloj":    "M12 7v5l3.5 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z",
    "rayo":     "M13 2 4.5 13.5H11l-1 8.5 8.5-11.5H12l1-8.5z",
    "check":    "M20 6 9 17l-5-5",
    "gente":    "M17 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M12.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",
    "grafico":  "M3 3v18h18M7 15l4-5 3 3 5-7",
    "ojo":      "M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7zM15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z",
    "mail":     "M3 6h18v12H3zM3 6l9 7 9-7",
    "calendario":"M3 6h18v15H3zM3 10h18M8 3v4M16 3v4",
    "engranaje":"M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7.5 19.4a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 3 15.1H3a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 4.6 7.5a1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 2.7 1.1 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z",
    "enchufe":  "M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0zM12 18v4",
    "candado":  "M5 11h14v10H5zM8 11V7a4 4 0 1 1 8 0v4",
    "robot":    "M12 2v3M6 8h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2zM9 13v2M15 13v2",
    "carpeta":  "M3 7h6l2 3h10v10H3z",
    "wpp":      "M20.5 11.9a8.4 8.4 0 0 1-12.5 7.3L3 21l1.9-4.8A8.4 8.4 0 1 1 20.5 12z",
    "instagram":"M7 3h10a4 4 0 0 1 4 4v10a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V7a4 4 0 0 1 4-4zM16 11.4A4 4 0 1 1 12.6 8 4 4 0 0 1 16 11.4zM17.5 6.5h.01",
    "flecha":   "M5 12h14M13 6l6 6-6 6",
    "alerta":   "M12 9v5M12 17.5h.01M10.3 3.9 2.4 17.3A2 2 0 0 0 4.1 20.3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z",
    "estrella": "m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9z",
    "dinero":   "M12 2v20M17 6.5c0-1.9-2.2-3-5-3s-5 1.1-5 3 2.2 2.7 5 3.3 5 1.4 5 3.4-2.2 3.3-5 3.3-5-1.4-5-3.3",
}


def icono(nombre, size=26, color="#FFFFFF", stroke=2.1):
    p = _PATHS.get(nombre, _PATHS["chat"])
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-linejoin="round" style="display:block"><path d="{p}"/></svg>')


def burbuja(nombre, d=58, fondo="#006AFF", tinta="#FFFFFF", size=None):
    """El ícono adentro del círculo azul. Es el componente más repetido de la
    marca: toda fila de una lista lleva uno."""
    s = size or round(d * 0.46)
    return (f'<div style="width:{d}px;height:{d}px;min-width:{d}px;border-radius:50%;'
            f'background:{fondo};display:flex;align-items:center;justify-content:center;'
            f'box-shadow:0 6px 18px rgba(0,106,255,.28)">{icono(nombre, s, tinta)}</div>')


def chip(texto, oscuro=False, color=None, icono_=None):
    """La pastilla que abre casi toda pieza de Asistime. Sobre claro es una
    barra de fondo azul muy diluido con el texto en azul; sobre oscuro es un
    borde con un punto.

    Es la firma de composición de la marca: si una pieza no sabe cómo empezar,
    empieza con un chip."""
    if oscuro:
        c = color or C["azul_glow"]
        punto = (f'<span style="width:12px;height:12px;min-width:12px;border-radius:50%;'
                 f'background:{c};display:block"></span>')
        return (f'<div class="as-chip" style="background:rgba(43,139,255,.16);'
                f'border:1px solid rgba(43,139,255,.34);color:#FFFFFF">'
                f'{punto}<span>{texto}</span></div>')
    c = color or C["azul_texto"]
    fondo = "rgba(0,106,255,.09)"
    ic = (f'<span style="display:flex">{icono(icono_, 27, c, 2.2)}</span>'
          if icono_ else "")
    return (f'<div class="as-chip" style="background:{fondo};color:{c}">'
            f'{ic}<span>{texto}</span></div>')


CHIP_CSS = """
.as-chip{display:flex;align-items:center;gap:13px;padding:17px 26px;
  border-radius:12px;font-family:'Sora',sans-serif;font-weight:700;
  font-size:30px;letter-spacing:-.015em;width:100%}
.as-chip svg{width:27px;height:27px}
"""


def regla(color="#006AFF", ancho=86, alto=6):
    """La regla corta debajo del titular. Separa el titular de la bajada sin
    meter una línea de ancho completo, que partiría la pieza en dos."""
    return (f'<div style="width:{ancho}px;height:{alto}px;background:{color};'
            f'border-radius:3px;margin:30px 0 26px"></div>')


def boton(texto, fondo="#25D366", tinta="#FFFFFF", icono_="wpp"):
    """El botón de CTA. Verde WhatsApp cuando el llamado es hablar con el
    agente —que es como se habla con Asistime— y azul cuando es otra cosa."""
    ic = f'<span>{icono(icono_, 26, tinta, 2.2)}</span>' if icono_ else ""
    sombra = ("0 10px 26px rgba(37,211,102,.34)" if fondo == C["whatsapp"]
              else "0 10px 26px rgba(0,106,255,.34)")
    return (f'<div style="display:inline-flex;align-items:center;gap:15px;'
            f'background:{fondo};color:{tinta};padding:22px 38px;border-radius:16px;'
            f'font-family:\'Sora\',sans-serif;font-weight:700;font-size:38px;'
            f'letter-spacing:-.02em;box-shadow:{sombra}">{ic}{texto}</div>')


def sitio(color="#7A8098", tinta="#006AFF", texto="asistime.ai"):
    return (f'<div style="display:flex;align-items:center;gap:14px">'
            f'{burbuja("flecha", 40, tinta, "#FFFFFF")}'
            f'<span style="font-family:\'Sora\',sans-serif;font-weight:600;'
            f'font-size:31px;color:{color};letter-spacing:-.01em">{texto}</span></div>')
