# -*- coding: utf-8 -*-
"""Los ayudantes de dibujo que toda marca necesita, atados a SUS tokens.

── Por qué viven acá y no en cada marca ──────────────────────────────────

Hasta el 2/9/2026 cada marca traía su `brand.py` con estas mismas funciones
escritas a mano: `pastilla`, `barra`, `subrayado`, `sombra_texto`… Stadium
tenía once. Eran las mismas once que iba a necesitar el cliente siguiente, con
otro naranja. Y son 300 a 450 líneas de Python por marca que tenía que escribir
alguien que programe — o sea, el paso del alta que más tiempo llevaba y el
único que no podía hacer una persona de diseño.

Acá cada ayudante recibe la identidad de la marca (`motor.identidad`) y
devuelve la función que la plantilla usa. Mismo HTML que antes: la migración
de Stadium se verificó comparando las 20 salidas —5 plantillas × 4 formatos—
byte a byte contra su `brand.py`, y dan idénticas. Ver
`herramientas/probar-identidad.py`.

Lo que cambia entre marcas son **tokens**: qué color es el acento, cuál el
claro, qué dice la barra de pie, qué logo y con qué proporción. Todo eso está
en `marca.json` → `identidad`. Lo que no cambia —cómo se apila un descuento,
cuántas capas tiene una sombra, qué margen tapa Instagram— está acá una sola
vez, con la explicación de por qué es así.
"""
from __future__ import annotations


def _color(ident, rol, dado=None):
    """El color de un rol («acento», «claro», «tinta»…) o el que se pasó."""
    if dado:
        return dado
    return ident.C[ident.roles[rol]]


def _imagen_de_marca(ident, spec, clase=""):
    """Cómo dibujar un logo, sea vectorial o raster.

    Un SVG se pinta del color que se pida: se reemplaza un marcador dentro del
    archivo. Un PNG no se puede pintar, así que la identidad trae DOS archivos
    —`archivo` para fondos claros y `claro` para fondos oscuros— y acá se
    elige uno según el color pedido. Es lo que tiene la mayoría de los
    clientes: un lockup en color y otro en blanco, y ningún vector.

    ── Por qué el tamaño va en una variable ──────────────────────────────

    El 4/9/2026 se pidió «el logo más grande». El agente escribió un retoque,
    anotó en sus notas que lo había agrandado 1,8 veces, y el isotipo salió
    exactamente igual: 48×40 px, medido contra la pieza anterior. La marca se
    dibujaba con el tamaño en el atributo `style`, y un estilo en línea le gana
    a cualquier regla CSS. O sea que el pedido no era difícil: era imposible, y
    nada avisaba.

    Ahora el tamaño va como el VALOR DE RESPALDO de una variable CSS:

        width: var(--iso-ancho, 60px)

    y ahí está el detalle que importa. El primer intento fue declarar la
    variable en línea —`style="--iso-ancho:60px;width:var(--iso-ancho)"`— y no
    sirvió: una propiedad personalizada declarada en línea también le gana a la
    clase, así que el retoque volvía a no poder nada. Medido: el isotipo salía
    igual con y sin retoque.

    Como respaldo, en cambio, la variable NO está declarada en ningún lado
    mientras nadie la toque, y el 60px se usa. Basta con que un retoque diga
    `.marca-iso{--iso-ancho:110px;--iso-alto:110px}` para que gane, sin
    `!important` y sin tocar el motor.
    """
    archivo = spec["archivo"]
    es_svg = archivo.lower().endswith(".svg")
    claro = ident.C[ident.roles["claro"]].lower()
    # «marca-iso» → «--iso-ancho». Cada marca tiene las suyas: una pieza no
    # lleva las dos, pero si algún día las lleva no se pisan.
    v = clase.replace("marca-", "") or "marca"
    if es_svg:
        svg = ident.archivo_texto(archivo)
        marcador = spec.get("marcador", "CURRENT")
        color_defecto = ident.C[spec.get("color", ident.roles["acento"])]

        def dibujar(w, h, color):
            return (f'<div class="{clase}" '
                    f'style="width:var(--{v}-ancho,{w}px);'
                    f'height:var(--{v}-alto,{h}px)">'
                    f'{svg.replace(marcador, color or color_defecto)}</div>')
        return dibujar

    if not (ident.carpeta / archivo).exists():
        raise ValueError(f"«{ident.carpeta.name}» nombra {archivo} y no está")

    def dibujar(w, h, color):
        # Sobre oscuro va la versión clara, si la identidad la trae.
        usar = spec.get("claro") if (color and color.lower() == claro and spec.get("claro")) else archivo
        return (f'<img class="{clase}" src="{usar}" '
                f'style="width:var(--{v}-ancho,{w}px);'
                f'height:var(--{v}-alto,{h}px);'
                f'object-fit:contain;object-position:left center;display:block">')
    return dibujar


def logo(ident):
    """El logotipo horizontal, como HTML.

    `color` lo pinta plano cuando es un SVG; cuando es un PNG, elige la
    versión clara sobre fondos oscuros. Sin argumento sale como va sobre
    claro.

    El ancho base sale de la identidad (Stadium: 300 px sobre 1080, un 28%).
    Es más chico de lo que pide el instinto, y a propósito: en una pieza de
    retail el que tiene que gritar es el precio, no la tienda.
    """
    dibujar = _imagen_de_marca(ident, ident.logo, "marca-logo")
    ratio, base = ident.logo["ratio"], ident.logo.get("ancho", 300)

    def _logo(size=1.0, color=None, align="left"):
        ancho = base * size
        caja = {"left": "flex-start", "center": "center", "right": "flex-end"}[align]
        return (f'<div style="display:flex;justify-content:{caja}">'
                f'{dibujar(f"{ancho:.0f}", f"{ancho / ratio:.1f}", color)}</div>')
    return _logo


def iso(ident):
    """El isotipo —la letra sola, el escudo— donde el lockup no entra.

    Nunca los dos en la misma pieza: la marca se firma una vez.
    """
    if not ident.iso:
        return None
    dibujar = _imagen_de_marca(ident, ident.iso, "marca-iso")
    ratio, base = ident.iso["ratio"], ident.iso.get("alto", 96)

    def _iso(size=1.0, color=None):
        alto = base * size
        return dibujar(f"{alto * ratio:.1f}", f"{alto:.0f}", color)
    return _iso


def pastilla(ident):
    """El rótulo de campaña: «PRECIOS DE LOCOS», «NUEVO», «ÚLTIMAS UNIDADES».

    Rectangular y sin radio a propósito, salvo que la identidad diga otra
    cosa: una marca sin una sola esquina redondeada en su logo se ve prestada
    con una pastilla redondeada.
    """
    radio = ident.componentes.get("pastilla", {}).get("radio", 0)
    radio_css = f"border-radius:{radio}px;" if radio else ""

    def _pastilla(texto, fondo=None, color=None, cuerpo=26):
        return (f'<span class="kicker" style="display:inline-block;'
                f'background:{_color(ident, "acento", fondo)};'
                f'color:{_color(ident, "claro", color)};'
                f'padding:{cuerpo * 0.42:.0f}px {cuerpo * 0.72:.0f}px;'
                f'{radio_css}'
                f'font-size:{cuerpo}px">{texto}</span>')
    return _pastilla


def descuento(ident):
    """El bloque de descuento. El número manda y el «%» y el «OFF» lo escoltan.

    No es un texto suelto «50% OFF» porque, al mismo cuerpo, el signo y la
    palabra le comen la mitad del peso al número, que es lo único que se lee
    desde el feed.
    """
    palabra = ident.componentes.get("descuento", {}).get("palabra", "OFF")

    def _descuento(porcentaje, cuerpo=150, color=None, fondo=None):
        return (
            f'<div style="display:flex;align-items:flex-start;gap:{cuerpo * 0.06:.0f}px;'
            f'color:{_color(ident, "claro", color)};background:{fondo or "transparent"}">'
            f'<span class="precio" style="font-size:{cuerpo}px">{porcentaje}</span>'
            f'<div style="display:flex;flex-direction:column;'
            f'padding-top:{cuerpo * 0.09:.0f}px;line-height:1">'
            f'<span class="disp-x" style="font-size:{cuerpo * 0.42:.0f}px">%</span>'
            f'<span class="kicker" style="font-size:{cuerpo * 0.17:.0f}px;'
            f'letter-spacing:.1em;margin-top:{cuerpo * 0.05:.0f}px">{palabra}</span>'
            f'</div></div>')
    return _descuento


def barra(ident):
    """La barra de pie: acento pleno, con el texto de la marca centrado.

    Una pieza de retail termina en «vení» o «comprá online», y quien la ve
    necesita saber dónde. Qué dice —la web, el teléfono— lo pone la identidad.
    """
    texto = ident.componentes.get("barra", {}).get("texto", ident.web or "")

    def _barra(alto=88, fondo=None):
        return (f'<div style="height:{alto}px;background:{_color(ident, "acento", fondo)};'
                f'display:flex;align-items:center;justify-content:center;'
                f'color:{_color(ident, "claro")}">'
                f'<span class="kicker" style="font-size:{alto * 0.29:.0f}px;'
                f'letter-spacing:.2em">{texto}</span></div>')
    return _barra


def paleta(ident):
    """La paleta de una campaña, con lo que se quiera pisar encima.

    Se resuelve así y no eligiendo entre preset O valores sueltos porque el
    caso real es mixto: «la de papá pero sobre foto». Un preset que no se
    puede retocar termina en que nadie lo usa.
    """
    paletas = ident.PALETAS
    base_nombre = ident.componentes.get("paleta", {}).get("por_defecto") \
        or (next(iter(paletas)) if paletas else None)

    def _paleta(nombre=None, **cambios):
        base = dict(paletas.get(nombre or base_nombre, paletas.get(base_nombre, {})))
        base.update({k: v for k, v in cambios.items() if v})
        return base
    return _paleta


def subrayado(ident):
    """El subrayado dibujado a mano de los titulares de campaña.

    Un trazo irregular, no una línea recta: con la punta más fina y el cuerpo
    más grueso. Un `border-bottom` al lado se lee como un enlace de página web.
    """
    def _subrayado(color=None, ancho=1.0, grosor=1.0):
        w, h = 520 * ancho, 26 * grosor
        return (
            f'<svg viewBox="0 0 520 26" width="{w:.0f}" height="{h:.0f}" '
            f'style="display:block" preserveAspectRatio="none">'
            f'<path d="M6 17 C 90 7, 180 5, 262 9 C 350 13, 438 12, 514 6" '
            f'fill="none" stroke="{_color(ident, "claro", color)}" stroke-width="9" '
            f'stroke-linecap="round"/></svg>')
    return _subrayado


def etiqueta_persona(ident):
    """La chapita con el nombre de quien sale en la foto y su área.

    El nombre en cursiva y el área abajo, más chica: la persona primero, el
    puesto después.
    """
    def _etiqueta(nombre, area=None, fondo=None, color=None, cuerpo=26):
        return (
            f'<div style="display:inline-block;background:{_color(ident, "claro", fondo)};'
            f'color:{_color(ident, "tinta", color)};padding:{cuerpo * 0.5:.0f}px {cuerpo * 0.8:.0f}px">'
            f'<div class="body" style="font-style:italic;font-weight:600;'
            f'font-size:{cuerpo}px;line-height:1.1">{nombre}</div>'
            + (f'<div class="body" style="font-size:{cuerpo * 0.78:.0f}px;'
               f'opacity:.72;line-height:1.2;margin-top:{cuerpo * 0.12:.0f}px">'
               f'-{area}</div>' if area else "")
            + '</div>')
    return _etiqueta


def fila_logos(ident):
    """La fila de logos de los socios de una promo, separados por barras.

    Todos al MISMO alto de caja y con `contain`: un logo de un tercero
    estirado es la forma más rápida de perder el acuerdo.
    """
    def _fila(logos, alto=52, color=None, separador=True):
        sep = (f'<span style="width:2px;height:{alto * 0.62:.0f}px;'
               f'background:{_color(ident, "claro", color)};opacity:.55"></span>')
        piezas = []
        for i, l in enumerate(logos):
            if i and separador:
                piezas.append(sep)
            piezas.append(
                f'<img src="{l}" style="height:{alto}px;max-width:{alto * 4.2:.0f}px;'
                f'object-fit:contain;display:block">')
        return (f'<div style="display:flex;align-items:center;'
                f'gap:{alto * 0.42:.0f}px;flex-wrap:wrap">' + "".join(piezas) + '</div>')
    return _fila


def sombra_texto(ident):
    """La sombra que hace que el texto claro sobreviva a una mancha clara.

    El velo se calcula con el brillo PROMEDIO de una zona, y un promedio
    esconde la mancha —un reflejo, el césped al sol— que se cruza con tres
    letras y se las come. La sombra es local: viaja pegada a cada letra.

    Tres capas y no una: una pegada que define el borde, una media que da
    cuerpo, una grande y difusa que separa el bloque del fondo. Todas CON
    DESENFOQUE: una sombra dura sobre una foto se lee como un segundo texto.

    Devuelve la declaración CERRADA CON PUNTO Y COMA. Se inserta en medio de
    un `style=""`, y sin el `;` el navegador se come lo que viene después.
    """
    def _sombra(fuerza=1.0):
        f = max(0.0, min(float(fuerza), 2.0))
        return ("text-shadow:"
                f"0 1px 2px rgba(0,0,0,{.42 * f:.2f}),"
                f"0 2px 10px rgba(0,0,0,{.40 * f:.2f}),"
                f"0 4px 30px rgba(0,0,0,{.34 * f:.2f});")
    return _sombra


#: Lo que Instagram dibuja encima de un reel y de una story. No se recorta:
#: se TAPA, o sea que el archivo se ve perfecto y en el teléfono no se lee.
#: Sale de un pack de edición de reels probado en piezas publicadas. Reel y
#: story NO son iguales: el reel tiene el epígrafe y la música abajo y la
#: columna de botones a la derecha; la story, la barra de responder.
ZONAS_SEGURAS = {
    "reel":  {"arriba": 250, "abajo": 420, "izquierda": 60, "derecha": 144},
    "story": {"arriba": 250, "abajo": 250, "izquierda": 60, "derecha": 60},
}


def pad_seguro(ident):
    """El `padding` de la pieza, respetando lo que Instagram tapa.

    Nunca achica: si la plantilla pedía más margen del que exige Instagram,
    gana la plantilla.
    """
    zonas = ident.ZONAS_SEGURAS or ZONAS_SEGURAS

    def _pad(fmt, pad):
        z = zonas.get(fmt)
        if not z:
            return f"{pad}px"
        return (f"{max(pad, z['arriba'])}px {max(pad, z['derecha'])}px "
                f"{max(pad, z['abajo'])}px {max(pad, z['izquierda'])}px")
    return _pad


def firma(ident):
    """Con qué marca firma ESTA pieza. La firma no es siempre la misma.

    Una marca no se firma igual en todas las piezas y tratarla así es lo que
    hace que un feed se vea armado con una plantilla. El isotipo solo alcanza
    cuando el público ya sabe de quién es la cuenta; una pieza de expectativa,
    un anuncio o algo que va a ver gente de afuera necesita el nombre escrito.
    Y cuando el protagonista es una foto o un mockup, el logo arriba compite
    con lo que hay que mirar: ahí conviene firmar sólo abajo.

    Tres valores, y el que no diga nada sigue teniendo lo de siempre.
    """
    _iso, _logo = iso(ident), logo(ident)

    def _firma(cual="iso", size=1.0, color=None):
        cual = (cual or "iso").strip().lower()
        if cual in ("ninguna", "sin", "no"):
            return ""
        if cual in ("lockup", "logo") and _logo:
            # El lockup es ancho: al mismo `size` que el isotipo se comería
            # media pieza, así que se lee como «la firma ocupa esto de alto».
            return _logo(size * 1.15, color)
        return _iso(size, color) if _iso else ""
    return _firma


TODOS = {
    "logo": logo, "iso": iso, "firma": firma, "pastilla": pastilla, "descuento": descuento,
    "barra": barra, "paleta": paleta, "subrayado": subrayado,
    "etiqueta_persona": etiqueta_persona, "fila_logos": fila_logos,
    "sombra_texto": sombra_texto, "pad_seguro": pad_seguro,
}
