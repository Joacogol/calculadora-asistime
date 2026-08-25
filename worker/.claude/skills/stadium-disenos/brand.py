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

## Lo que corrigió el feed

Todo lo de arriba se escribió mirando el sitio y el logo. Después se miraron 24
posts reales de @stadium_uruguay y dos cosas resultaron falsas:

1. **El naranja casi no aparece.** Está en 1 de esos 24 —un sorteo—. La grilla
   es beige, tan, kraft, gris, marrón y blanco. El naranja del logo es la
   identidad de la TIENDA; el contenido tiene otra. Por eso el naranja quedó en
   el logo, en la barra de pie y en las piezas de promo, y NO como fondo o
   acento por defecto de todo.
2. **Cada campaña trae su propia identidad y pisa la de la marca.** «Con papá
   siempre hay equipo» va celeste sobre kraft con una condensada de póster;
   «Para la N°1 de mi equipo» va marrón sobre crema con una serif. No son
   desvíos: es cómo funciona esta marca. De ahí salen `VOCES` y `PALETAS`.

Y una tercera que no cambia nada pero conviene saber: **más de la mitad de los
posts no tienen una sola letra encima.** Producto y punto. Por eso existe la
plantilla `producto`, que parece que no hace nada y es la que más se usa.
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
@font-face{font-family:'Play';src:url('fonts/PlayfairDisplay-var.ttf');font-weight:400 900}
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
/* Las tres VOCES de titular. No son tres gustos: son los tres sistemas que la
   marca ya usa, uno por tipo de campaña. Ver VOCES más abajo. */
.v-cond{font-family:'Arch';font-weight:900;font-variation-settings:'wdth' 64,'wght' 900;
  letter-spacing:-.005em;line-height:.88;text-transform:uppercase}
/* `lining-nums`: Playfair trae cifras de estilo antiguo por defecto y el «1»
   de «N°1» salía del tamaño de una minúscula, media letra más abajo que la
   N. En un titular de campaña eso se lee como un error de tipeo. */
.v-serif{font-family:'Play';font-weight:500;letter-spacing:.005em;line-height:1.02;
  font-variant-numeric:lining-nums;font-feature-settings:'lnum' 1}
.v-normal{font-family:'Arch';font-weight:900;letter-spacing:-.045em;line-height:.86}
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


# ═══ Campañas: la capa que pisa a la marca ═══════════════════════════════════
#
# Stadium no comunica siempre igual. Cada campaña trae su propia paleta y su
# propia tipografía, y mientras dura, manda ella. Se vio en el feed: la de Día
# del Padre es celeste sobre papel kraft con una condensada de póster; la de
# Día de la Madre es marrón sobre crema con una serif. Son marcas distintas
# conviviendo bajo el mismo logo.
#
# Por eso `campana` no tiene "el" color de Stadium: recibe el suyo.

#: Las tres voces tipográficas, y cuándo usar cada una.
VOCES = {
    "cond":   "Condensada de póster (Archivo al ancho 64, peso 900, en mayúsculas). "
              "La de las campañas de volumen y precio: grita y ocupa poco ancho. "
              "Es la de «CON PAPÁ SIEMPRE HAY EQUIPO».",
    "serif":  "Serif de contraste alto (Playfair Display). Para lo aspiracional "
              "y lo femenino: Día de la Madre, botas, una cápsula. Es la de "
              "«PARA LA N°1 DE MI EQUIPO».",
    "normal": "Archivo black de ancho normal. La voz neutra de la marca, la "
              "misma del logotipo. Cuando la campaña no tiene identidad propia.",
}

#: Paletas de campaña listas para usar.
#:
#: ⚠️ Los colores de las campañas de acá abajo están SACADOS A OJO DE CAPTURAS
#: del feed, no de un manual. Sirven para que una pieza salga parecida, no para
#: decir que ese es el color. Cuando Stadium mande la campaña con sus valores,
#: se corrigen acá y quedan bien para siempre. Los de `stadium` sí son
#: exactos: salen del logo oficial.
PALETAS = {
    "stadium": {"fondo": C["blanco"], "tinta": C["tinta"],
                "acento": C["naranja"], "voz": "normal", "subrayado": False},
    "papa":    {"fondo": "#D8C4A4", "tinta": "#2E93D4",
                "acento": C["blanco"], "voz": "cond", "subrayado": True},
    "papa_estudio": {"fondo": C["blanco"], "tinta": "#2E93D4",
                     "acento": C["tinta"], "voz": "cond", "subrayado": True},
    "madre":   {"fondo": "#F2EBE1", "tinta": "#6E4B2E",
                "acento": "#A8825C", "voz": "serif", "subrayado": False},
    "promo":   {"fondo": C["naranja"], "tinta": C["blanco"],
                "acento": C["blanco"], "voz": "cond", "subrayado": False},
    "oscura":  {"fondo": C["negro"], "tinta": C["blanco"],
                "acento": C["naranja"], "voz": "normal", "subrayado": False},
}


def paleta(nombre=None, **cambios):
    """La paleta de una campaña, con lo que se quiera pisar encima.

    Se resuelve así y no eligiendo entre preset O valores sueltos porque el
    caso real es mixto: «la de papá pero sobre foto», «la de la madre con otro
    fondo». Un preset que no se puede retocar termina en que nadie lo usa.
    """
    base = dict(PALETAS.get(nombre or "stadium", PALETAS["stadium"]))
    base.update({k: v for k, v in cambios.items() if v})
    return base


def subrayado(color=None, ancho=1.0, grosor=1.0):
    """El subrayado dibujado a mano de los titulares de campaña.

    Es un trazo irregular, no una línea recta: en las piezas de Stadium se ve
    hecho con pincel, con la punta más fina y el cuerpo más grueso. Una línea
    de CSS (`border-bottom`) al lado se lee como un enlace de página web.
    """
    w, h = 520 * ancho, 26 * grosor
    return (
        f'<svg viewBox="0 0 520 26" width="{w:.0f}" height="{h:.0f}" '
        f'style="display:block" preserveAspectRatio="none">'
        f'<path d="M6 17 C 90 7, 180 5, 262 9 C 350 13, 438 12, 514 6" '
        f'fill="none" stroke="{color or C["blanco"]}" stroke-width="9" '
        f'stroke-linecap="round"/></svg>')


def etiqueta_persona(nombre, area=None, fondo=None, color=None, cuerpo=26):
    """La chapita con el nombre de quien sale en la foto y su área.

    Stadium pone a su propia gente en las campañas —«Jorge Colina ·
    Logística»— y esa etiqueta es la que convierte un retrato cualquiera en
    una pieza de la marca. El nombre va en cursiva y el área abajo, más chica:
    la persona primero, el puesto después.
    """
    return (
        f'<div style="display:inline-block;background:{fondo or C["blanco"]};'
        f'color:{color or C["tinta"]};padding:{cuerpo * 0.5:.0f}px {cuerpo * 0.8:.0f}px">'
        f'<div class="body" style="font-style:italic;font-weight:600;'
        f'font-size:{cuerpo}px;line-height:1.1">{nombre}</div>'
        + (f'<div class="body" style="font-size:{cuerpo * 0.78:.0f}px;'
           f'opacity:.72;line-height:1.2;margin-top:{cuerpo * 0.12:.0f}px">'
           f'-{area}</div>' if area else "")
        + '</div>')


def fila_logos(logos, alto=52, color=None, separador=True):
    """La fila de logos de los socios de una promo, separados por barras.

    `logos` son rutas de imagen. Van todos al MISMO alto de caja y con
    `contain`, así que ninguno se deforma por más raro que venga el archivo:
    un logo de un tercero estirado es la forma más rápida de perder el acuerdo.
    El separador es la barrita vertical que ya usan en el sorteo.
    """
    sep = (f'<span style="width:2px;height:{alto * 0.62:.0f}px;'
           f'background:{color or C["blanco"]};opacity:.55"></span>')
    piezas = []
    for i, l in enumerate(logos):
        if i and separador:
            piezas.append(sep)
        piezas.append(
            f'<img src="{l}" style="height:{alto}px;max-width:{alto * 4.2:.0f}px;'
            f'object-fit:contain;display:block">')
    return (f'<div style="display:flex;align-items:center;'
            f'gap:{alto * 0.42:.0f}px;flex-wrap:wrap">' + "".join(piezas) + '</div>')
