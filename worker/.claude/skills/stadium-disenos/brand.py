# -*- coding: utf-8 -*-
"""Sistema de diseño de Stadium — tokens y componentes base.

Stadium es una cadena de 34 tiendas deportivas uruguayas, fundada en 1977.
Vende marcas de terceros —adidas, Nike, Umbro, Topper— y su comunicación gira
alrededor de **producto, precio y campaña**, no de servicios ni de sedes. Esa
diferencia es la que decide todo lo que sigue.

## De dónde salen los colores

El naranja NO se muestreó de una pantalla ni se copió de una pieza: está
escrito en el `logo.svg` oficial de stadium.com.uy como `fill: #f60`, y el
favicon —la S blanca sobre naranja— lo confirma píxel a píxel.

Ojo con una contradicción real de la marca: **el sitio usa `#EF6A00`** para su
interfaz, un naranja más apagado. Se resolvió a favor del logo, que es la
especificación de la marca y no una decisión de un tema de e-commerce. Si
alguna vez hay que volver atrás, es esta línea y nada más.

## Por qué una sola tipografía

El logotipo es un grotesco denso, de la familia de Helvetica. Archivo es
exactamente eso —un grotesco de esa línea— y en su versión variable cubre del
regular al black con un solo archivo. Se evaluó la alternativa de dos familias
(una geométrica tipo Gotham para titulares y otra para texto) y no compra nada:
el logo no es geométrico, así que una geométrica al lado se lee como un segundo
sistema, no como el mismo.

Montserrat queda sólo para los rótulos de los reels: ffmpeg dibuja con freetype,
que no entiende fuentes variables y sacaría todo en regular.
"""
import pathlib

C = {
    "naranja":    "#FF6600",   # el del logo. Acento, y fondo en las de impacto
    "tinta":      "#222222",   # titulares y texto sobre claro
    "blanco":     "#FFFFFF",
    "gris":       "#999999",   # metadatos, legales, el precio tachado
    "gris_claro": "#E1E3E4",   # fondo alternativo, separadores
    "negro":      "#0E0E0E",   # sólo para fondos a sangre de campaña
}

#: El naranja de la interfaz del sitio. NO se usa en las piezas — está acá
#: para que quien lo encuentre en una captura sepa que no es un error.
NARANJA_WEB = "#EF6A00"

FORMATOS = {
    "post":  (1080, 1080),
    "vert":  (1080, 1350),
    "story": (1080, 1920),
    "reel":  (1080, 1920),
}

FONT_CSS = """
@font-face{font-family:'Arch';src:url('fonts/Archivo-var.ttf');font-weight:100 900}
"""

#: Las clases que usan las plantillas. Deliberadamente pocas: cada una es una
#: decisión de la marca, no un atajo de maquetación.
#:
#: `disp` es el titular y el precio — Archivo en 800, muy apretado de tracking
#: e interlineado, que es como se comporta el logotipo. `precio` va todavía más
#: apretado porque un número tiene menos formas irregulares que una palabra y
#: aguanta más.
BASE_CSS = FONT_CSS + """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Arch',Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
.canvas{width:1080px;position:relative;overflow:hidden;background:#FFFFFF}
.pad{position:absolute;inset:0;display:flex;flex-direction:column}
.row{display:flex;align-items:center;justify-content:space-between}
.grow{flex:1}
.disp{font-weight:800;letter-spacing:-.03em;line-height:.94}
.disp-x{font-weight:900;letter-spacing:-.045em;line-height:.86}
.precio{font-weight:900;letter-spacing:-.05em;line-height:.84;font-variant-numeric:tabular-nums}
.body{font-weight:500;letter-spacing:-.01em;line-height:1.34}
.kicker{font-weight:700;letter-spacing:.16em;text-transform:uppercase}
.legal{font-weight:500;letter-spacing:.01em;line-height:1.3}
.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.scrim{position:absolute;inset:0}
/* El producto NO se recorta. Un championes con la puntera cortada es una pieza
   que no se puede publicar, y en retail la foto viene de un catálogo con
   proporciones que nadie controla. `contain` se ve peor en un caso y no se
   rompe en ninguno. */
.prod{width:100%;height:100%;object-fit:contain;object-position:center}
.tachado{position:relative;display:inline-block}
.tachado:after{content:'';position:absolute;left:-.04em;right:-.04em;top:52%;
  height:.075em;background:currentColor;transform:rotate(-6deg)}
"""

_AQUI = pathlib.Path(__file__).parent
_LOGO = (_AQUI / "assets" / "stadium-logo.svg").read_text(encoding="utf-8")
_ISO = (_AQUI / "assets" / "stadium-iso.svg").read_text(encoding="utf-8")

#: Medidos de los vectores oficiales, no estimados.
LOGO_RATIO = 201.9 / 24.6      # 8.207 — el lockup horizontal
ISO_RATIO = 29.0 / 23.47       # 1.236 — la S sola


def logo(size=1.0, color=None, align="left"):
    """El logotipo STADIUM, horizontal.

    `color` lo pinta plano: blanco cuando va sobre naranja o sobre foto
    oscura. Sin argumento sale en el naranja de marca, que es como va sobre
    blanco.

    El ancho base son 300 px sobre un lienzo de 1080 — un 28%. Es más chico de
    lo que pide el instinto, y a propósito: en una pieza de retail el que tiene
    que gritar es el precio, no la tienda. La marca ya está en el naranja.
    """
    ancho = 300 * size
    svg = _LOGO.replace("CURRENT", color or C["naranja"])
    caja = {"left": "flex-start", "center": "center", "right": "flex-end"}[align]
    return (f'<div style="display:flex;justify-content:{caja}">'
            f'<div style="width:{ancho:.0f}px;height:{ancho / LOGO_RATIO:.1f}px">'
            f'{svg}</div></div>')


def iso(size=1.0, color=None):
    """La S sola, sacada del propio logotipo oficial.

    Va donde el lockup horizontal no entra o competiría: la esquina de una
    pieza a sangre, el sello de una story. Nunca las dos cosas en la misma
    pieza — la marca se firma una vez.
    """
    alto = 96 * size
    svg = _ISO.replace("CURRENT", color or C["naranja"])
    return (f'<div style="width:{alto * ISO_RATIO:.1f}px;height:{alto:.0f}px">'
            f'{svg}</div>')


def pastilla(texto, fondo=None, color=None, cuerpo=26):
    """El rótulo de campaña: «PRECIOS DE LOCOS», «NUEVO», «ÚLTIMAS UNIDADES».

    Rectangular y sin radio a propósito. La marca no tiene una sola esquina
    redondeada —ni en el logo, ni en el sitio— y una pastilla con radio se ve
    prestada de otra marca.
    """
    return (f'<span class="kicker" style="display:inline-block;'
            f'background:{fondo or C["naranja"]};color:{color or C["blanco"]};'
            f'padding:{cuerpo * 0.42:.0f}px {cuerpo * 0.72:.0f}px;'
            f'font-size:{cuerpo}px">{texto}</span>')


def descuento(porcentaje, cuerpo=150, color=None, fondo=None):
    """El bloque de descuento. El número manda y el «%» y el «OFF» lo escoltan.

    Se dibuja así —y no como un texto suelto «50% OFF»— porque puestos al mismo
    cuerpo, el signo y la palabra le comen la mitad del peso al número, que es
    lo único que la persona lee desde el feed.
    """
    return (
        f'<div style="display:flex;align-items:flex-start;gap:{cuerpo * 0.06:.0f}px;'
        f'color:{color or C["blanco"]};background:{fondo or "transparent"}">'
        f'<span class="precio" style="font-size:{cuerpo}px">{porcentaje}</span>'
        f'<div style="display:flex;flex-direction:column;'
        f'padding-top:{cuerpo * 0.09:.0f}px;line-height:1">'
        f'<span class="disp-x" style="font-size:{cuerpo * 0.42:.0f}px">%</span>'
        f'<span class="kicker" style="font-size:{cuerpo * 0.17:.0f}px;'
        f'letter-spacing:.1em;margin-top:{cuerpo * 0.05:.0f}px">OFF</span>'
        f'</div></div>')


def barra(alto=88, fondo=None):
    """La barra de pie: naranja plena, con la web centrada.

    Existe porque una pieza de retail termina en «vení» o «comprá online», y
    quien la ve necesita saber dónde. Es el único elemento fijo de la marca en
    la pieza además del logo.
    """
    return (f'<div style="height:{alto}px;background:{fondo or C["naranja"]};'
            f'display:flex;align-items:center;justify-content:center;'
            f'color:{C["blanco"]}">'
            f'<span class="kicker" style="font-size:{alto * 0.29:.0f}px;'
            f'letter-spacing:.2em">stadium.com.uy</span></div>')
