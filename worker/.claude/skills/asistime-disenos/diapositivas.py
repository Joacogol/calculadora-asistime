# -*- coding: utf-8 -*-
"""Cómo se ve cada diapositiva de un carrusel de Asistime.

La estructura —numeración, proporción única, índice, flechas, zonas seguras de
story, caja de respuesta— la pone `motor.carrusel` y sirve para cualquier
marca. Acá está sólo lo que es de Asistime.

Cada función recibe `(d, ancho, alto, acento)` y devuelve el **cuerpo** del
HTML, no la página entera: no sabe en qué posición va ni cuántas hay.
"""
from brand import (C, GRAD_CLARO, GRAD_OSCURO, logo, lockup, chip, burbuja,
                   icono, boton, sitio)
from motor.carrusel import SQ_TOP, SQ_BOT

LADO = 84


def _pad(h: int, extra: int = 0) -> str:
    """En un carrusel de feed no hay nada encima de la pieza. En una story,
    Instagram dibuja arriba el nombre de la cuenta y abajo la caja de
    responder: lo que caiga ahí queda tapado."""
    if h >= 1900:
        return f"{SQ_TOP}px {LADO}px {SQ_BOT + extra}px"
    return f"86px {LADO}px {130 + extra}px"


def _claro(h, cuerpo, extra_fondo=""):
    return f"""
<div style="position:absolute;inset:0;background:{GRAD_CLARO}"></div>
<div class="glow" style="width:640px;height:640px;right:-190px;top:-170px;
  background:rgba(0,106,255,.10)"></div>{extra_fondo}
<div class="pad" style="padding:{_pad(h)}">
  <div class="row">{logo(1.0)}</div>
  {cuerpo}
</div>"""


def _oscuro(h, cuerpo, extra_fondo=""):
    return f"""
<div style="position:absolute;inset:0;background:{GRAD_OSCURO}"></div>
<div class="glow" style="width:760px;height:760px;right:-230px;bottom:-250px;
  background:rgba(43,139,255,.30)"></div>{extra_fondo}
<div class="pad" style="padding:{_pad(h)}">
  <div class="row">{logo(1.0,"#FFFFFF")}</div>
  {cuerpo}
</div>"""


def _t(txt, size, color=None, destaque=None):
    return (f'<div class="t" style="font-size:{size}px;color:{color or C["navy"]}">'
            f'{txt}</div><style>.t b{{color:{destaque or C["azul_texto"]}}}</style>')


def _esc(h, base):
    """Escala de tipografía según el alto de la diapositiva. Un carrusel 4:5 y
    una story usan las mismas funciones y no pueden usar el mismo cuerpo."""
    return round(base * (h / 1350) ** 0.55)


# ───────────────────────────────────────────────────────────────── PORTADA
def _portada(d, w, h, ac):
    """La primera. Es la única que se ve en el feed sin deslizar."""
    cuerpo = f"""
  <div class="grow">
    {chip(d.get("chip",""), icono_=d.get("icono")) if d.get("chip") else ""}
    <div style="height:34px"></div>
    {_t(d.get("titulo",""), _esc(h, 92))}
    <div style="width:86px;height:6px;background:{ac};border-radius:3px;
      margin:32px 0 26px"></div>
    <div class="body" style="font-size:{_esc(h,35)}px;color:{C['navy_70']};max-width:86%">
      {d.get('bajada','')}</div>
  </div>"""
    return _claro(h, cuerpo)


# ─────────────────────────────────────────────────────────────────── FILAS
def _filas(d, w, h, ac):
    """Tres tarjetas con burbuja de ícono. El «cómo funciona»."""
    fs = _esc(h, 32)
    items = "".join(
        f'<div class="card">{burbuja(ic, 58, ac)}'
        f'<div class="body" style="font-size:{fs}px;color:{C["navy"]};line-height:1.32">'
        f'{tx}</div></div>' for ic, tx in d.get("items", []))
    return _claro(h, f"""
  <div class="grow">
    {chip(d.get("chip",""), icono_=d.get("icono")) if d.get("chip") else ""}
    <div style="height:30px"></div>
    {_t(d.get("titulo",""), _esc(h, 72))}
    <div style="height:44px"></div>
    <div style="display:flex;flex-direction:column;gap:22px">{items}</div>
  </div>""")


# ─────────────────────────────────────────────────────────────────── DATOS
def _datos(d, w, h, ac):
    """Filas con el número a la derecha, y el remate abajo. Es la diapositiva
    que convierte una afirmación en un argumento."""
    fs = _esc(h, 31)
    vs = _esc(h, 44)
    filas = "".join(
        f'<div class="card">{burbuja(ic, 58, ac)}'
        f'<div class="body" style="font-size:{fs}px;color:{C["navy"]};flex:1">{ro}</div>'
        f'<div class="t" style="font-size:{vs}px;color:{C["azul_texto"]}">{va}</div>'
        f'</div>' for ic, ro, va in d.get("filas", []))
    remate = ""
    if d.get("remate_1"):
        remate = f"""
    <div style="height:32px"></div>
    <div style="height:5px;background:{ac};border-radius:3px"></div>
    <div style="display:flex;align-items:center;gap:20px;margin-top:28px">
      {burbuja("check", 52, ac)}
      <div class="t" style="font-size:{vs+2}px;color:{C['navy']};line-height:1.06">
        {d['remate_1']}<br><span style="color:{C['azul_texto']}">{d.get('remate_2','')}</span></div>
    </div>"""
    return _claro(h, f"""
  <div class="grow">
    {chip(d.get("chip",""), icono_=d.get("icono")) if d.get("chip") else ""}
    <div style="height:30px"></div>
    {_t(d.get("titulo",""), _esc(h, 72))}
    <div style="height:40px"></div>
    <div style="display:flex;flex-direction:column;gap:20px">{filas}</div>
    {remate}
  </div>""")


# ────────────────────────────────────────────────────────────────── CHECKS
def _checks(d, w, h, ac):
    """El «todo en un solo lugar». Va casi siempre en la anteúltima."""
    fs = _esc(h, 33)
    items = "".join(
        f'<div style="display:flex;align-items:flex-start;gap:22px">'
        f'{burbuja("check", 46, ac)}'
        f'<div class="body" style="font-size:{fs}px;color:{C["navy"]};line-height:1.3;'
        f'padding-top:3px">{t}</div></div>' for t in d.get("items", []))
    return _claro(h, f"""
  <div class="grow">
    {chip(d.get("chip",""), icono_=d.get("icono")) if d.get("chip") else ""}
    <div style="height:30px"></div>
    {_t(d.get("titulo",""), _esc(h, 72))}
    <div style="height:46px"></div>
    <div style="display:flex;flex-direction:column;gap:30px">{items}</div>
  </div>""")


# ───────────────────────────────────────────────────────────────── IMPACTO
def _impacto(d, w, h, ac):
    """La oscura. **Una por carrusel, como máximo.** Funciona porque es la
    excepción: si hay tres, deja de ser un impacto y es un carrusel oscuro."""
    gs = _esc(h, 152)
    return _oscuro(h, f"""
  <div class="grow">
    {chip(d.get("chip",""), oscuro=True) if d.get("chip") else ""}
    <div style="height:38px"></div>
    <div class="t" style="font-size:{gs}px;line-height:.94;color:{C['azul_glow']};
      text-shadow:0 0 70px rgba(43,139,255,.55)">{d.get('palabra_1','')}</div>
    <div class="t" style="font-size:{gs}px;line-height:.98;color:#FFFFFF">
      {d.get('palabra_2','')}</div>
    <div style="height:5px;background:rgba(255,255,255,.22);border-radius:3px;
      margin:34px 0 28px"></div>
    <div class="body" style="font-size:{_esc(h,33)}px;color:rgba(255,255,255,.80);
      max-width:92%">{d.get('texto','')}</div>
  </div>""")


# ─────────────────────────────────────────────────────────────────── TEXTO
def _texto(d, w, h, ac):
    """Respiro tipográfico: un titular y una bajada, sin tarjetas. Sirve para
    separar dos diapositivas cargadas."""
    return _claro(h, f"""
  <div class="grow">
    {chip(d.get("chip",""), icono_=d.get("icono")) if d.get("chip") else ""}
    <div style="height:32px"></div>
    {_t(d.get("titulo",""), _esc(h, 84))}
    <div style="height:28px"></div>
    <div class="body" style="font-size:{_esc(h,34)}px;color:{C['navy_70']};max-width:88%">
      {d.get('texto','')}</div>
  </div>""")


# ─────────────────────────────────────────────────────────────────── CIERRE
def _cierre(d, w, h, ac):
    """La última. Pide una conversación, no seguidores: es lo único que en
    esta marca se convierte en un cliente."""
    return _oscuro(h, f"""
  <div class="grow">
    {_t(d.get("titulo",""), _esc(h, 80), "#FFFFFF", C["azul_glow"])}
    <div style="width:86px;height:6px;background:{C['azul_glow']};border-radius:3px;
      margin:32px 0 28px"></div>
    {chip(d["chip"], oscuro=True) if d.get("chip") else ""}
    <div style="height:42px"></div>
    {boton(d.get("cta","Hablá con Tony"))}
    <div style="height:30px"></div>
    {sitio("rgba(255,255,255,.80)", C['azul_glow'], d.get("sitio","asistime.ai"))}
  </div>""")


# ─────────────────────────────────────────────────── CUADRO (secuencia story)
def _cuadro(d, w, h, ac):
    """Un cuadro de una secuencia de stories. Dos segundos de atención: un
    titular de 2 a 4 palabras y nada más."""
    osc = bool(d.get("oscuro"))
    foto = ""
    if d.get("foto"):
        foto = (f'<img class="bg" src="{d["foto"]}" style="object-position:'
                f'{d.get("foco","50% 40%")}">'
                f'<div class="scrim" style="background:linear-gradient(180deg,'
                f'rgba(1,3,13,.42),rgba(1,3,13,.18) 40%,rgba(1,3,13,.80))"></div>')
        osc = True
    cuerpo = f"""
  <div class="grow" style="justify-content:flex-end">
    {chip(d.get("chip",""), oscuro=osc) if d.get("chip") else ""}
    <div style="height:30px"></div>
    {_t(d.get("titulo",""), d.get("cuerpo", 112),
        "#FFFFFF" if osc else None, C["azul_glow"] if osc else None)}
    <div style="height:24px"></div>
    <div class="body" style="font-size:36px;
      color:{'rgba(255,255,255,.82)' if osc else C['navy_70']};max-width:88%">
      {d.get('texto','')}</div>
  </div>"""
    if foto:
        return (f'<div style="position:absolute;inset:0;background:{GRAD_OSCURO}"></div>'
                + foto +
                f'<div class="pad" style="padding:{_pad(h, 120)}">'
                f'<div class="row">{logo(1.0,"#FFFFFF")}</div>{cuerpo}</div>')
    return (_oscuro(h, cuerpo) if osc else _claro(h, cuerpo)).replace(
        f'padding:{_pad(h)}', f'padding:{_pad(h, 120)}')


DIAPOS = {
    "portada": _portada,
    "filas":   _filas,
    "datos":   _datos,
    "checks":  _checks,
    "impacto": _impacto,
    "texto":   _texto,
    "cierre":  _cierre,
    "cuadro":  _cuadro,
}
