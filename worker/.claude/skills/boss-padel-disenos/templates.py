# -*- coding: utf-8 -*-
"""Plantillas de piezas Boss Padel. Cada función devuelve HTML completo."""
import pathlib as _pl
import re as _re

from brand import C, FONT_CSS, LOGO_CSS, logo, aros, blob

import sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[3]))
from motor import legibilidad  # noqa: E402


def _ruta(foto: str) -> str:
    """La foto tal como la ve el disco.

    En el spec las rutas son relativas a la carpeta de la marca, porque así las
    resuelve Chromium al abrir el HTML. Para medir el brillo de la imagen hay
    que abrir el archivo, y eso necesita la ruta completa."""
    r = _pl.Path(foto)
    return str(r if r.is_absolute() else _pl.Path(__file__).parent / r)

BASE_CSS = FONT_CSS + LOGO_CSS + """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;overflow:hidden;background:#0A0A0A;-webkit-font-smoothing:antialiased}
.canvas{position:relative;width:1080px;overflow:hidden;background:#0A0A0A}
.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 50%}
.scrim{position:absolute;inset:0}
.pad{position:absolute;inset:0;padding:76px;display:flex;flex-direction:column}
.row{display:flex;justify-content:space-between;align-items:flex-start}
.grow{flex:1}
.kicker{font-family:'BarlowC',sans-serif;font-weight:500;letter-spacing:.30em;text-transform:uppercase}
.eyebrow{font-family:'Barlow',sans-serif;font-weight:400;letter-spacing:.14em;text-transform:uppercase}
.disp{font-family:'Archivo',sans-serif;font-weight:300;text-transform:uppercase;letter-spacing:-.005em}
.disp-b{font-family:'Archivo',sans-serif;font-weight:700;text-transform:uppercase;letter-spacing:-.01em}
.body{font-family:'Barlow',sans-serif;font-weight:400}
.bp-aros{display:block}
.bp-blob{position:absolute}
.sponsors{display:flex;gap:44px;align-items:center;opacity:.75}
.sponsors span{font-family:'Barlow',sans-serif;font-weight:600;font-size:26px;letter-spacing:.10em;
  text-transform:uppercase;color:#FAFAFA}
"""


def _page(h, inner, extra_css=""):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
.canvas{{height:{h}px}} {extra_css}</style></head><body>
<div class="canvas">{inner}</div></body></html>"""


# ═══════════════════════════════════════════════════════════════════════════
#  Plantillas agregadas el 3/8/2026, después de mirar qué hacen los clubes
#  que mejor comunican en el mundo (Padium, Padel Haus, Padel Social Club).
#
#  El hallazgo que las ordena: esos clubes no publican «lo que pasó hoy».
#  Publican SECCIONES con nombre propio que se repiten. Padium tiene 30.100
#  seguidores con 213 publicaciones; un club español que mirábamos tiene 8.375
#  publicaciones y 5.153 seguidores. La diferencia no es cuánto publican.
# ═══════════════════════════════════════════════════════════════════════════


VELO_DUELO = 0.52   # el mínimo de diseño; la medición sólo puede subirlo


# ────────────────────────────────────────────────────────────── 12 DUELO
def duelo(d, fmt="post"):
    """Dos cosas enfrentadas con un VS en el medio. Sirve para dos trabajos:

    1. **La pregunta de la semana** — bandeja o víbora, Carrasco o Hípico.
       Metricool midió sobre 24 millones de posteos que pedir un comentario da
       +202,78% de comentarios y que una pregunta da +36,70%.
    2. **El desafío o partido** — una dupla contra otra, con la hora abajo.
       Es la misma pieza: dos nombres, el VS, y el pie diciendo cuándo.

    El segundo uso estuvo perdido hasta el 7/8/2026: el agente pidió una pieza
    «tipo VS» para un desafío y armó una `titular` con los nombres apretados en
    el pie, anotando en `copy.txt` que «no existe una plantilla tipo VS en el
    sistema». Existía. Lo que faltaba era que el skill la llamara por ese
    nombre. Una capacidad que el skill tiene y no nombra es una capacidad que
    no existe.

    Funciona sin fotos —dos bloques de color y listo— y mejor con fotos.

    d: pregunta, a, b, fotoa, fotob, pie, acento
    """
    h = {"post": 1080, "vert": 1350, "story": 1920, "reel": 1920}[fmt]
    ac = C[d.get("acento", "lima")]
    op_fs = {"post": 82, "vert": 92, "story": 104, "reel": 104}[fmt]

    # Una palabra como «BANDEJA» entra a tamaño completo; «PABLO SCIARRA» es el
    # borde exacto del ancho útil. De ahí en adelante se achica proporcional,
    # porque los nombres propios no se pueden acortar y una pieza con el
    # apellido cortado por la mitad no se publica.
    _lineas = [x.strip() for x in _re.split(r"<br\s*/?>", f"{d['a']}<br>{d['b']}")
               if x.strip()]
    _largo = max((len(x) for x in _lineas), default=1)
    if _largo > 13:
        op_fs = round(op_fs * 13 / _largo)
    top = 76 if fmt in ("post", "vert") else 190
    bot = 76 if fmt in ("post", "vert") else 250

    def mitad(texto, foto, foco, tinte):
        if foto:
            velo = max(VELO_DUELO, legibilidad.velo_necesario(
                _ruta(foto), color_texto="#FAFAFA", objetivo=3.6,
                zona=(0.0, 1.0), maximo=0.80))
            capa = (f'<img class="bg" src="{foto}" style="object-position:{foco}">'
                    f'<div class="scrim" style="background:rgba(10,10,10,{velo:.2f})"></div>')
        else:
            capa = f'<div class="scrim" style="background:{tinte}"></div>'
        return (f'<div style="position:relative;flex:1;display:flex;align-items:center;'
                f'justify-content:center;overflow:hidden">{capa}'
                f'<div class="disp-b" style="position:relative;color:#FAFAFA;'
                f'font-size:{op_fs}px;line-height:1.0;text-align:center;padding:0 90px;'
                f'letter-spacing:-.01em">{texto}</div></div>')

    arriba = mitad(d["a"], d.get("fotoa"), d.get("focoa", "50% 50%"),
                   f'linear-gradient(140deg,{C["azul"]},{C["azul_deep"]})')
    abajo = mitad(d["b"], d.get("fotob"), d.get("focob", "50% 50%"),
                  f'linear-gradient(140deg,{C["gris_osc"]},{C["negro_puro"]})')

    inner = f"""
<div style="position:absolute;inset:0;display:flex;flex-direction:column">{arriba}{abajo}</div>
<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  background:{ac};width:132px;height:132px;border-radius:50%;display:flex;
  align-items:center;justify-content:center;z-index:3">
  <span class="disp-b" style="color:#0A0A0A;font-size:52px;letter-spacing:-.02em">VS</span></div>
<div class="pad" style="padding:{top}px 76px {bot}px;z-index:4;pointer-events:none">
  <div class="row">
    <div class="kicker" style="color:{ac};font-size:29px;letter-spacing:.32em;max-width:620px;
      line-height:1.5">{d['pregunta']}</div>
    {logo(1.15)}
  </div>
  <div class="grow"></div>
  <div class="kicker" style="color:#FAFAFA;font-size:27px;letter-spacing:.20em;
    text-align:center;text-shadow:0 2px 18px rgba(0,0,0,.9)">
    {d.get('pie','CONTESTÁ EN LOS COMENTARIOS')}</div>
</div>"""
    return _page(h, inner)


# ────────────────────────────────────────────────────────────── 14 HORARIOS
def horarios(d, fmt="story"):
    """Los horarios libres del día. La pieza diaria del club.

    ## Por qué no es un carrusel

    El 7/8/2026 se pidieron tres —Carrasco, Hípico y Punta— y salieron tres
    carruseles de cinco y seis diapositivas. No estaba mal armado: era la mejor
    salida con las plantillas que había. Pero el contenido se resistía, y se
    nota en dos síntomas.

    El primero: para que entrara, hubo que **agrupar y perder el dato**. La
    diapositiva de Carrasco terminó diciendo «08:00 — 11 canchas» en vez de
    cuáles. La de Hípico juntó ocho horarios en dos bloques de rango.

    El segundo, más caro: **quien mira busca SU hora.** «¿Hay algo a las nueve?»
    es una pregunta que se contesta de un vistazo sobre una grilla, y que en un
    carrusel obliga a deslizar hasta encontrarla. Un carrusel es para una idea
    que avanza; esto es una tabla, y una tabla partida en cinco pantallas deja
    de ser una tabla.

    ## Las tres decisiones

    **La hora es el héroe, la cancha no.** Nadie elige «cancha 7 · Radio
    Disney»: elige jugar a las nueve. El número de cancha se decide en la app de
    reservas, no mirando una placa. Acá la cancha sólo aparece como un contador
    chiquito al lado de la hora —«08:00 · 11»— que además comunica urgencia sin
    decir nada: once es «hay lugar», dos es «apurate».

    **El precio agrupa.** Hípico no tiene ocho precios: tiene dos, techada y
    abierta. Un grupo por precio y las horas adentro, en vez de repetir el mismo
    número ocho veces.

    **Va en story.** Es contenido que vence en un día. Un posteo de feed sobre
    los horarios de mañana queda para siempre en la grilla del perfil,
    desactualizado desde pasado mañana. Igual la plantilla soporta los cuatro
    formatos, porque a veces se quiere fijar el finde entero.

    d: kicker, dia, sede, grupos=[{rotulo, precio, horas}], cta, nota, acento
       Cada hora es "08:00" o ("08:00", "11") si se quiere el contador.
    """
    h = {"post": 1080, "vert": 1350, "story": 1920, "reel": 1920}[fmt]
    ac = C[d.get("acento", "lima")]
    grupos = d.get("grupos") or []

    # El tamaño de las fichas sale de cuántas horas hay que meter, no de una
    # tabla de formatos: la misma story con seis horas y con veinte no puede
    # usar la misma medida. Se cuenta una vez y se decide.
    total = sum(len(g.get("horas") or []) for g in grupos)
    if fmt in ("story", "reel"):
        opciones, fs = [3, 4], (74 if total <= 12 else (58 if total <= 24 else 46))
    elif fmt == "vert":
        opciones, fs = [3, 4, 5], (62 if total <= 12 else (50 if total <= 24 else 40))
    else:
        opciones, fs = [4, 5, 6], (52 if total <= 12 else (42 if total <= 20 else 34))

    # De las columnas posibles se elige la que deja la última fila más llena.
    # Diez horas en tres columnas dejan una ficha sola abajo y la grilla se lee
    # rota; en cinco quedan dos filas parejas. Empate: gana la de menos
    # columnas, que hace las fichas más grandes.
    def _huecos(c):
        mayor = max(len(g.get("horas") or []) for g in grupos) if grupos else 0
        return ((-mayor) % c, c)
    cols = min(opciones, key=_huecos)

    def ficha(hora):
        cupos = ""
        if isinstance(hora, (list, tuple)):
            hora, n = (list(hora) + [""])[:2]
            if str(n).strip():
                cupos = (f'<span class="eyebrow" style="color:{ac};font-size:{fs*.38:.0f}px;'
                         f'margin-left:{fs*.14:.0f}px;letter-spacing:.06em">{n}</span>')
        return (f'<div style="background:rgba(250,250,250,.07);'
                f'border:1px solid rgba(250,250,250,.14);border-radius:{fs*.20:.0f}px;'
                f'padding:{fs*.30:.0f}px {fs*.12:.0f}px;text-align:center;'
                f'display:flex;align-items:baseline;justify-content:center">'
                f'<span class="disp-b" style="color:#FAFAFA;font-size:{fs}px;'
                f'line-height:1;letter-spacing:-.02em">{hora}</span>{cupos}</div>')

    bloques = []
    for g in grupos:
        horas = g.get("horas") or []
        if not horas:
            continue
        # El rótulo y el precio en la misma línea, separados por una regla: es
        # el encabezado de una tabla, no un titular.
        precio = (f'<div class="disp-b" style="color:{ac};font-size:{fs*.62:.0f}px;'
                  f'line-height:1">{g["precio"]}</div>') if g.get("precio") else ""
        rotulo = (f'<div class="kicker" style="color:#FAFAFA;opacity:.85;'
                  f'font-size:{fs*.34:.0f}px">{g["rotulo"]}</div>') if g.get("rotulo") else ""
        bloques.append(f"""
        <div style="margin-bottom:{fs*.66:.0f}px">
          <div style="display:flex;justify-content:space-between;align-items:baseline;
            border-bottom:2px solid {ac};padding-bottom:{fs*.16:.0f}px;
            margin-bottom:{fs*.34:.0f}px">{rotulo}{precio}</div>
          <div style="display:grid;grid-template-columns:repeat({cols},1fr);
            gap:{fs*.20:.0f}px">{''.join(ficha(x) for x in horas)}</div>
        </div>""")

    top = 76 if fmt in ("post", "vert") else 190
    bot = 76 if fmt in ("post", "vert") else 250
    tit = {"post": 96, "vert": 112, "story": 130, "reel": 130}[fmt]

    # El kicker va arriba a la derecha con el tracking abierto de la marca, que
    # come mucho ancho: «VIERNES 8 DE AGOSTO» entra justo y una palabra más se
    # parte en dos líneas desalineadas. Se achica en vez de partirse.
    _k = d.get("kicker", "")
    _kfs = tit * .22
    if len(_k) > 20:
        _kfs = _kfs * 20 / len(_k)
    nota = (f'<div class="body" style="color:#FAFAFA;opacity:.62;'
            f'font-size:{tit*.24:.0f}px;margin-top:{tit*.10:.0f}px">{d["nota"]}</div>'
            ) if d.get("nota") else ""

    inner = f"""
<div class="scrim" style="background:{d.get('fondo', C['negro'])}"></div>
<div style="position:absolute;top:-120px;right:-190px;opacity:.30">{aros(380,'#FAFAFA',2.4)}</div>
<div style="position:absolute;bottom:-150px;left:-180px;opacity:.16">{aros(330,ac,2.2)}</div>
<div class="pad" style="padding:{top}px 76px {bot}px">
  <div class="row">{logo(1.35, align='left')}
    <div class="kicker" style="color:{ac};font-size:{_kfs:.0f}px;text-align:right;
      max-width:560px;line-height:1.5">{_k}</div></div>
  <div style="margin-top:{tit*.42:.0f}px">
    <div class="disp" style="color:#FAFAFA;font-size:{tit*.52:.0f}px;line-height:1">
      Horarios libres</div>
    <div class="disp-b" style="color:#FAFAFA;font-size:{tit}px;line-height:.94;
      margin-top:{tit*.04:.0f}px">{d.get('sede','')}</div>
    {nota}
  </div>
  <div class="grow" style="display:flex;flex-direction:column;justify-content:center;
    padding:{tit*.34:.0f}px 0">{''.join(bloques)}</div>
  <div style="display:flex;align-items:center;gap:{tit*.18:.0f}px">
    <div style="flex:0 0 auto;background:{ac};border-radius:{tit*.06:.0f}px;
      padding:{tit*.14:.0f}px {tit*.24:.0f}px">
      <span class="kicker" style="color:#0A0A0A;font-size:{tit*.20:.0f}px;
        font-weight:700">{d.get('cta','RESERVÁ TU CANCHA')}</span></div>
    <div class="body" style="color:#FAFAFA;opacity:.55;font-size:{tit*.19:.0f}px;
      letter-spacing:.06em">{d.get('contacto','')}</div>
  </div>
</div>"""
    return _page(h, inner)


# Las únicas dos que siguen siendo código. No es una deuda: `horarios` elige
# cuerpo tipográfico y cantidad de columnas según cuántas horas entran, y
# `duelo` mide la foto y arma su propia estructura. Eso no es un diseño con
# variables, es un programa — forzarlo a plantilla sería inventar un lenguaje
# de programación adentro del HTML.
#
# Las otras doce viven en `plantillas/<id>/` y las carga `motor.plantillas`.
# Se editan y se publican sin desplegar. `marca.py` junta las dos cosas.
PLANTILLAS = {"duelo": duelo, "horarios": horarios}
