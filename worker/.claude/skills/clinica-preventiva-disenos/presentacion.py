# -*- coding: utf-8 -*-
"""Presentaciones en PDF con la identidad de Clínica Preventiva.

Un deck es una lista de slides. Cada slide declara su `tipo` y trae sólo los
datos que ese tipo necesita; la maquetación no se negocia, viene de acá. Es la
misma idea que las plantillas de placas: el pedido aporta el contenido, el
sistema aporta la forma.

Se renderiza con el motor de impresión de Chromium, no con una librería de PDF.
Por eso la tipografía y las fotos salen exactamente como en las placas: es el
mismo navegador dibujando las mismas fuentes.

── Por qué existe este archivo ────────────────────────────────────────────

Hasta el 4/8/2026 esta marca **no tenía presentaciones**. El SKILL.md las
mencionaba, pero no había ni `presentacion.py` ni `PRESENTACION` en `marca.py`.

Cuando alguien pidió un deck para empresas, el agente improvisó con lo único
que había: el carrusel de Instagram. Salió un PDF de páginas 16:9 con las
diapositivas CUADRADAS centradas y franjas blancas a los costados, con las
flechas `> > >` y el índice `01 / 08` del carrusel adentro de un documento que
nadie desliza. Costó US$ 1,36 y 18 comandos de shell, porque el agente estuvo
inventando en vez de completar una plantilla.

La lección no es del agente: **una capacidad que el skill promete y no tiene,
el agente la va a improvisar.** Si dice «presentaciones», tiene que haber un
motor de presentaciones.

── En qué se diferencia del de Boss Padel ─────────────────────────────────

Boss es una marca oscura: fondo negro, texto blanco, foto a sangre. Clínica es
**clara** —fondo blanco, tinta casi negra, rojo de acento— y eso cambia toda la
estrategia visual. Un deck blanco con poco contenido se ve VACÍO, mientras que
uno negro se ve elegante. Por eso acá:

  · cada slide tiene una **franja de color** o una foto que ancla la
    composición, para que ninguna página quede siendo un texto flotando;
  · el pie es una **barra gris clara** con el logo y el número, no un texto
    suelto que se pierde en el blanco;
  · hay un tipo `servicios` con tarjetas en grilla, porque el 90% de lo que
    esta clínica presenta es una lista de prestaciones — y seis servicios en
    seis slides medio vacías es peor que seis tarjetas en una.

Formato 1600 × 900 px (16:9), que es lo que espera cualquier proyector y lo que
mejor se lee en un celular en horizontal.
"""
from brand import C, FONT_CSS, LOGO_CSS, logo, puntos

ANCHO, ALTO = 1600, 900

FONDO = "#FFFFFF"
PAPEL = "#F7F7F8"      # el gris casi blanco de las tarjetas y la barra de pie


def _css(acento: str = "rojo") -> str:
    ac = C.get(acento, C["rojo"])
    return f"""
{FONT_CSS}
{LOGO_CSS}
*{{margin:0;padding:0;box-sizing:border-box}}
@page{{size:{ANCHO}px {ALTO}px;margin:0}}
html,body{{background:{FONDO}}}
.slide{{
  position:relative;width:{ANCHO}px;height:{ALTO}px;overflow:hidden;
  background:{FONDO};color:{C['tinta']};
  font-family:'Mont',sans-serif;
  page-break-after:always;break-after:page;
}}
.slide:last-child{{page-break-after:auto;break-after:auto}}
.pad{{position:absolute;inset:0;padding:74px 96px 122px;display:flex;flex-direction:column}}

/* ── tipografía ─────────────────────────────────────────────── */
.h1{{font-family:'Mont',sans-serif;font-weight:800;line-height:.98;
    letter-spacing:-.025em;text-transform:uppercase}}
.h2{{font-family:'Mont',sans-serif;font-weight:800;font-size:72px;line-height:1.02;
    letter-spacing:-.022em;text-transform:uppercase}}
.h3{{font-family:'Mont',sans-serif;font-weight:800;font-size:46px;line-height:1.10;
    letter-spacing:-.015em;text-transform:uppercase}}
.kicker{{font-family:'Mont',sans-serif;font-weight:700;font-size:20px;
    letter-spacing:.26em;text-transform:uppercase;color:{ac}}}
.lead{{font-size:29px;line-height:1.45;font-weight:400;color:{C['gris']}}}
.body{{font-size:24px;line-height:1.58;font-weight:400;color:{C['gris']}}}

/* La regla corta bajo el titular. Es el gesto que más «cierra» una página
   clara: sin ella el titular flota y la diapositiva parece un borrador. */
.regla{{width:74px;height:5px;background:{ac};margin:26px 0 0}}

/* ── el pie ─────────────────────────────────────────────────── */
/* Una BARRA y no un texto suelto: sobre blanco, un pie de 19px en gris se
   pierde y deja la página sin borde inferior. La barra le da suelo. */
.pie{{position:absolute;left:0;right:0;bottom:0;height:78px;background:{PAPEL};
   border-top:1px solid {C['gris_suave']};
   display:flex;align-items:center;justify-content:space-between;
   padding:0 96px;font-size:19px;letter-spacing:.12em;text-transform:uppercase;
   color:#9A9A9C;font-weight:500}}
.num{{color:{ac};font-weight:700;letter-spacing:.18em}}

/* ── foto ───────────────────────────────────────────────────── */
.foto{{position:absolute;background-size:cover;background-repeat:no-repeat}}
.velo{{position:absolute;inset:0}}

/* ── bullets ────────────────────────────────────────────────── */
.puntos{{list-style:none;margin-top:34px;display:flex;flex-direction:column;gap:19px}}
.puntos li{{position:relative;padding-left:40px;font-size:25px;line-height:1.42;
   font-weight:400;color:{C['tinta']}}}
/* Una cruz y no un círculo: es el símbolo del logo, reducido a su mínima
   expresión. Repetirlo en cada bullet cose la marca al documento sin gritar. */
.puntos li::before{{content:'';position:absolute;left:0;top:11px;width:17px;height:5px;
   background:{ac}}}
.puntos li::after{{content:'';position:absolute;left:6px;top:5px;width:5px;height:17px;
   background:{ac}}}

/* ── tarjetas de servicio ───────────────────────────────────── */
.grilla{{display:grid;gap:20px;margin-top:38px}}
.tarj{{background:{PAPEL};border:1px solid {C['gris_suave']};
   border-top:4px solid {ac};padding:30px 30px 32px;min-width:0}}
.tarj .t{{font-family:'Mont',sans-serif;font-weight:800;font-size:26px;
   line-height:1.14;letter-spacing:-.01em;color:{C['tinta']};
   text-transform:uppercase}}
.tarj .d{{margin-top:13px;font-size:20px;line-height:1.44;color:{C['gris']}}}
.tarj .n{{font-family:'Mont',sans-serif;font-weight:800;font-size:19px;
   letter-spacing:.14em;color:{ac};margin-bottom:12px}}

/* ── datos grandes ──────────────────────────────────────────── */
/* Grilla y no flex: con flex, un «+4.000» al lado de un «7» descalabra el
   ritmo de las columnas. En grilla todas miden lo mismo pase lo que pase. */
.datos{{display:grid;gap:48px 36px;margin-top:56px}}
.dato{{min-width:0;border-left:4px solid {ac};padding-left:26px}}
.dato .n{{font-family:'Mont',sans-serif;font-weight:800;line-height:.92;
   letter-spacing:-.035em;color:{C['tinta']}}}
.dato .t{{margin-top:14px;font-size:20px;letter-spacing:.14em;
   text-transform:uppercase;color:{C['gris']};max-width:14ch;line-height:1.4;
   font-weight:600}}

/* ── tabla ──────────────────────────────────────────────────── */
.tabla{{margin-top:40px;width:100%;border-collapse:collapse}}
.tabla td{{padding:20px 0;border-bottom:1px solid {C['gris_suave']};font-size:24px;
   font-weight:400;color:{C['tinta']};vertical-align:top}}
.tabla td:first-child{{font-weight:700;font-size:20px;letter-spacing:.12em;
   text-transform:uppercase;color:{ac};width:34%;padding-right:34px}}
.tabla td:last-child{{text-align:right;font-weight:700;white-space:nowrap}}
.tabla tr:last-child td{{border-bottom:none}}

/* La barra roja del borde izquierdo, la firma de las placas de esta marca. */
.filo{{position:absolute;left:0;top:0;bottom:0;width:14px;background:{ac}}}
.trama{{position:absolute;opacity:.5}}
"""


# ── piezas compartidas ────────────────────────────────────────────────────

def _pie(meta, s):
    return (f'<div class="pie"><span>{meta.get("pie", "")}</span>'
            f'<span class="num">{s.get("_n", "")}</span></div>')


def _cuerpo_portada(titulo: str) -> int:
    """Cuánto mide el titular de portada según cuánto texto trae.

    A 118px sólo entran dos líneas cortas. Un titular de seis palabras se parte
    en cuatro y se come el logo de arriba y el pie de abajo. En vez de dejar
    que el texto decida por desborde, se decide acá.
    """
    n = len(titulo)
    if n <= 16:
        return 118
    if n <= 28:
        return 94
    if n <= 44:
        return 74
    return 60


# ── slides ────────────────────────────────────────────────────────────────

def _portada(s, ac, meta):
    """Panel de texto a la izquierda, foto a sangre a la derecha.

    No es foto a sangre completa con el texto encima, que es lo que haría una
    marca oscura. Acá el texto vive sobre BLANCO: se lee perfecto sin velo, la
    foto se ve entera y sin apagar, y no hay que medir ningún contraste. En una
    marca clara, separar es más limpio que superponer.
    """
    foto = ""
    if s.get("foto"):
        foto = (f'<div class="foto" style="right:0;top:0;bottom:0;width:46%;'
                f'background-image:url({s["foto"]});'
                f'background-position:{s.get("foco", "50% 40%")}"></div>'
                # Un filo rojo entre la foto y el panel: cierra el corte.
                f'<div style="position:absolute;right:46%;top:0;bottom:0;'
                f'width:8px;background:{ac}"></div>')
    ancho = "54%" if s.get("foto") else "100%"
    return f"""<div class="slide">{foto}
  <div class="filo"></div>
  <div class="trama" style="left:60px;bottom:150px">{puntos(210, 150, C['gris_suave'])}</div>
  <div class="pad" style="width:{ancho};padding-right:60px">
    <div style="flex:0 0 auto">{logo(1.30, None, 'left')}</div>
    <div style="margin-top:auto">
      <div class="kicker" style="margin-bottom:22px">{s.get('kicker', 'Clínica Preventiva')}</div>
      <div class="h1" style="font-size:{_cuerpo_portada(s['titulo'])}px">{s['titulo']}</div>
      <div class="regla"></div>
      {f'<div class="lead" style="margin-top:26px;max-width:26ch">{s["bajada"]}</div>' if s.get('bajada') else ''}
    </div>
    <div style="height:20px;flex:0 0 auto"></div>
  </div>
  <div class="pie" style="right:{'46%' if s.get('foto') else '0'}">
    <span>{meta.get('pie', '')}</span><span class="num">{meta.get('fecha', '')}</span></div>
</div>"""


def _seccion(s, ac, meta):
    """El separador de capítulo. Fondo de color pleno para cortar el ritmo.

    En un deck claro, todas las páginas blancas seguidas se confunden entre sí.
    Una página roja cada tanto le dice al que mira «arrancó otra cosa» sin
    tener que leer nada.
    """
    return f"""<div class="slide" style="background:{ac};color:#FFFFFF">
  <div class="trama" style="right:-40px;bottom:-30px;opacity:.22">{puntos(320, 260, '#FFFFFF')}</div>
  <div class="pad" style="justify-content:center">
    <div class="kicker" style="color:rgba(255,255,255,.78);margin-bottom:26px">{s.get('kicker', '')}</div>
    <div class="h2" style="max-width:17ch">{s['titulo']}</div>
    <div class="regla" style="background:#FFFFFF"></div>
    {f'<div class="lead" style="margin-top:28px;max-width:36ch;color:rgba(255,255,255,.92)">{s["bajada"]}</div>' if s.get('bajada') else ''}
  </div>
  <div class="pie" style="background:rgba(0,0,0,.14);border-top:none;color:rgba(255,255,255,.75)">
    <span>{meta.get('pie', '')}</span><span class="num" style="color:#FFFFFF">{s.get('_n', '')}</span></div>
</div>"""


def _contenido(s, ac, meta):
    """Texto y bullets, con foto opcional a la derecha."""
    lista = ""
    if s.get("puntos"):
        items = "".join(f"<li>{p}</li>" for p in s["puntos"])
        lista = f'<ul class="puntos">{items}</ul>'
    texto = (f'<div class="body" style="margin-top:26px;max-width:44ch">{s["texto"]}</div>'
             if s.get("texto") else "")
    lado = ""
    if s.get("foto"):
        lado = (f'<div class="foto" style="right:0;top:0;bottom:0;width:40%;'
                f'background-image:url({s["foto"]});'
                f'background-position:{s.get("foco", "50% 40%")}"></div>'
                f'<div style="position:absolute;right:40%;top:0;bottom:0;width:8px;'
                f'background:{ac}"></div>')
    ancho = "max-width:54%" if s.get("foto") else "max-width:80%"
    return f"""<div class="slide">{lado}
  <div class="pad" style="justify-content:center">
    <div style="{ancho}">
      <div class="kicker" style="margin-bottom:20px">{s.get('kicker', '')}</div>
      <div class="h3">{s['titulo']}</div>
      <div class="regla"></div>
      {texto}{lista}
    </div>
  </div>
  <div class="pie" style="right:{'40%' if s.get('foto') else '0'}">
    <span>{meta.get('pie', '')}</span><span class="num">{s.get('_n', '')}</span></div>
</div>"""


def _servicios(s, ac, meta):
    """Tarjetas en grilla. El tipo que más se va a usar en esta marca.

    Casi todo lo que esta clínica presenta a una empresa es una lista de
    prestaciones. Antes cada una se llevaba una diapositiva entera con una foto
    de la sala de espera y tres renglones de texto: ocho páginas para decir
    seis cosas, y el que mira pierde el hilo de cuál es cuál.

    En tarjetas se comparan de un vistazo, entran seis en una página, y el deck
    baja de ocho páginas a cuatro sin perder una palabra.
    """
    items = s["servicios"]
    cols = 3 if len(items) > 4 else max(1, min(3, len(items)))
    celdas = ""
    for i, it in enumerate(items, 1):
        if isinstance(it, (list, tuple)):
            titulo, detalle = (list(it) + [""])[:2]
        else:
            titulo, detalle = it.get("titulo", ""), it.get("detalle", "")
        det = f'<div class="d">{detalle}</div>' if detalle else ""
        celdas += (f'<div class="tarj"><div class="n">{i:02d}</div>'
                   f'<div class="t">{titulo}</div>{det}</div>')
    return f"""<div class="slide">
  <div class="pad" style="justify-content:center">
    <div class="kicker" style="margin-bottom:18px">{s.get('kicker', '')}</div>
    <div class="h3" style="max-width:26ch">{s['titulo']}</div>
    <div class="regla"></div>
    <div class="grilla" style="grid-template-columns:repeat({cols},1fr)">{celdas}</div>
  </div>
  {_pie(meta, s)}
</div>"""


def _datos(s, ac, meta):
    datos = s["datos"]
    cols = min(4, len(datos)) or 1
    ancho_col = (ANCHO - 192 - 36 * (cols - 1)) / cols
    largo = max(len(str(n)) for n, _ in datos)
    # Montserrat 800 mide ~0.64 em por dígito. Se calcula el cuerpo que hace
    # entrar la cifra más larga en su columna, con tope de 104.
    cuerpo = int(min(104, (ancho_col - 30) / (largo * 0.64)))
    if len(datos) > 4:
        cuerpo = min(cuerpo, 78)
    celdas = "".join(
        f'<div class="dato"><div class="n" style="font-size:{cuerpo}px">{n}</div>'
        f'<div class="t">{t}</div></div>' for n, t in datos)
    return f"""<div class="slide">
  <div class="trama" style="right:-30px;top:-30px">{puntos(280, 220, C['gris_suave'])}</div>
  <div class="pad" style="justify-content:center">
    <div class="kicker" style="margin-bottom:18px">{s.get('kicker', '')}</div>
    <div class="h3" style="max-width:24ch">{s['titulo']}</div>
    <div class="datos" style="grid-template-columns:repeat({cols},1fr)">{celdas}</div>
  </div>
  {_pie(meta, s)}
</div>"""


def _tabla(s, ac, meta):
    """Filas de dos columnas. La segunda va alineada a la derecha: es para
    precios y plazos, y una columna de números alineada a la izquierda no se
    puede comparar de un vistazo."""
    filas = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in s["filas"])
    return f"""<div class="slide">
  <div class="pad" style="justify-content:center">
    <div class="kicker" style="margin-bottom:18px">{s.get('kicker', '')}</div>
    <div class="h3" style="max-width:26ch">{s['titulo']}</div>
    <div class="regla"></div>
    <table class="tabla">{filas}</table>
  </div>
  {_pie(meta, s)}
</div>"""


def _foto(s, ac, meta):
    """Foto a sangre con una tarjeta blanca encima.

    La tarjeta y no texto sobre la foto: el rojo de esta marca mide 1,4:1 sobre
    una foto clara y el blanco tampoco está garantizado. Sobre una tarjeta
    blanca los dos se leen siempre, sin velo y sin apagar la imagen. Ver
    `motor/legibilidad.py`.
    """
    return f"""<div class="slide">
  <div class="foto" style="inset:0;background-image:url({s['foto']});
       background-position:{s.get('foco', '50% 40%')}"></div>
  <div class="pad" style="justify-content:flex-end;padding-bottom:150px">
    <div style="background:#FFFFFF;border-left:8px solid {ac};
                padding:38px 44px;max-width:60%;
                box-shadow:0 10px 44px rgba(0,0,0,.22)">
      <div class="kicker" style="margin-bottom:14px">{s.get('kicker', '')}</div>
      <div class="h3" style="font-size:42px;max-width:20ch">{s['titulo']}</div>
      {f'<div class="body" style="margin-top:16px;max-width:46ch">{s["bajada"]}</div>' if s.get('bajada') else ''}
    </div>
  </div>
  {_pie(meta, s)}
</div>"""


def _cierre(s, ac, meta):
    """El cierre es un llamado a la acción, no un «gracias».

    Quien llega a la última página de una propuesta ya decidió si le interesa.
    Lo único que falta es que sepa a qué número escribir, y por eso el teléfono
    va del tamaño de un titular y no de un pie de página.
    """
    lineas = "".join(f'<div style="margin-top:12px">{l}</div>'
                     for l in s.get("lineas", []))
    tel = ""
    if s.get("telefono"):
        tel = (f'<div style="font-family:\'Mont\',sans-serif;font-weight:800;'
               f'font-size:56px;letter-spacing:-.01em;margin-top:34px">'
               f'{s["telefono"]}</div>')
    return f"""<div class="slide" style="background:{C['tinta']};color:#FFFFFF">
  <div class="trama" style="left:-40px;bottom:-40px;opacity:.14">{puntos(340, 280, '#FFFFFF')}</div>
  <div style="position:absolute;left:0;top:0;bottom:0;width:14px;background:{ac}"></div>
  <div class="pad" style="justify-content:center;align-items:center;text-align:center">
    <div style="margin-bottom:44px">{logo(1.55, '#FFFFFF', 'center')}</div>
    <div class="h2" style="font-size:62px;max-width:22ch">{s.get('titulo', 'Hablemos')}</div>
    <div style="width:74px;height:5px;background:{ac};margin:28px 0 0"></div>
    {tel}
    <div class="body" style="margin-top:18px;color:rgba(255,255,255,.80)">{lineas}</div>
  </div>
</div>"""


TIPOS = {"portada": _portada, "seccion": _seccion, "contenido": _contenido,
         "servicios": _servicios, "datos": _datos, "tabla": _tabla,
         "foto": _foto, "cierre": _cierre}


def deck(d: dict) -> str:
    """Arma el HTML completo de la presentación."""
    ac = C.get(d.get("acento", "rojo"), C["rojo"])
    meta = {"pie": d.get("pie", "clinicapreventiva.com · 092 566 967"),
            "fecha": d.get("fecha", "")}
    partes, n = [], 0
    for s in d["slides"]:
        tipo = s.get("tipo", "contenido")
        if tipo not in TIPOS:
            raise ValueError(
                f"No existe el tipo de slide «{tipo}». Los que hay son: "
                + ", ".join(TIPOS))
        if tipo not in ("portada", "cierre"):
            n += 1
            s = {**s, "_n": f"{n:02d}"}
        partes.append(TIPOS[tipo](s, ac, meta))
    return (f'<!doctype html><html><head><meta charset="utf-8">'
            f'<style>{_css(d.get("acento", "rojo"))}</style></head>'
            f'<body>{"".join(partes)}</body></html>')
