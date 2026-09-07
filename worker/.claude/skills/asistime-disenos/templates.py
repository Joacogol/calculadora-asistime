# -*- coding: utf-8 -*-
"""Plantillas de piezas Asistime.ai. Cada función devuelve HTML completo.

Convención de toda la carpeta: en el titular, la palabra que carga el
significado va entre `<b>` y sale en azul. No es negrita: es el destaque de
color de la marca. Una o dos palabras por titular — si pintás todo, el
destaque deja de destacar.
"""
import pathlib as _pl
import sys as _sys

from brand import (C, GRAD_CLARO, GRAD_OSCURO, FONT_CSS, LOGO_CSS, CHIP_CSS,
                   logo, lockup, chip, burbuja, icono, regla, boton, sitio)

_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[3]))
from motor import legibilidad  # noqa: E402


def _ruta(foto: str) -> str:
    r = _pl.Path(foto)
    return str(r if r.is_absolute() else _pl.Path(__file__).parent / r)


H = {"post": 1080, "vert": 1350, "story": 1920, "reel": 1920}

# Márgenes. En story hay que bajar del borde: arriba vive el anillo del perfil
# y abajo la caja de «enviar mensaje».
PAD = {"post": (78, 78, 78), "vert": (86, 86, 86),
       "story": (210, 84, 300), "reel": (210, 84, 300)}


BASE_CSS = FONT_CSS + LOGO_CSS + CHIP_CSS + """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;overflow:hidden;background:#FBFCFE;-webkit-font-smoothing:antialiased}
.canvas{position:relative;width:1080px;overflow:hidden;background:#FBFCFE}
.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 50%}
.scrim{position:absolute;inset:0}
.pad{position:absolute;inset:0;display:flex;flex-direction:column;z-index:3}
.row{display:flex;justify-content:space-between;align-items:flex-start}
.grow{flex:1;min-height:0;display:flex;flex-direction:column;justify-content:center}
.t{font-family:'Sora',sans-serif;font-weight:800;letter-spacing:-.038em;line-height:1.02}
.t b{font-weight:800}
.st{font-family:'Sora',sans-serif;font-weight:700;letter-spacing:-.025em}
.body{font-family:'DMSans',sans-serif;font-weight:400;line-height:1.42}
.meta{font-family:'Sora',sans-serif;font-weight:600;letter-spacing:-.01em}
.card{background:#FFFFFF;border-radius:20px;box-shadow:0 6px 24px rgba(0,20,80,.07);
  display:flex;align-items:center;gap:22px;padding:26px 30px}
.card-d{background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.10);
  border-radius:20px;display:flex;align-items:center;gap:22px;padding:26px 30px}
.glow{position:absolute;border-radius:50%;filter:blur(90px);opacity:.55}
"""


def _page(h, inner, extra=""):
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}'
            f'.canvas{{height:{h}px}} {extra}</style></head><body>'
            f'<div class="canvas">{inner}</div></body></html>')


def _claro(h, cuerpo, pad, marca_color="#006AFF", extra_fondo=""):
    """El envoltorio claro: gradiente firma + isotipo arriba a la izquierda."""
    t, l, b = pad
    return f"""
<div style="position:absolute;inset:0;background:{GRAD_CLARO}"></div>
<div class="glow" style="width:640px;height:640px;right:-190px;top:-160px;
  background:rgba(0,106,255,.10)"></div>{extra_fondo}
<div class="pad" style="padding:{t}px {l}px {b}px">
  <div class="row">{logo(1.0, marca_color)}</div>
  {cuerpo}
</div>"""


def _oscuro(h, cuerpo, pad, extra_fondo=""):
    t, l, b = pad
    return f"""
<div style="position:absolute;inset:0;background:{GRAD_OSCURO}"></div>
<div class="glow" style="width:720px;height:720px;right:-220px;bottom:-240px;
  background:rgba(43,139,255,.28)"></div>{extra_fondo}
<div class="pad" style="padding:{t}px {l}px {b}px">
  <div class="row">{logo(1.0, "#FFFFFF")}</div>
  {cuerpo}
</div>"""


def _tit(texto, size, color=None, destaque=None):
    col = color or C["navy"]
    dst = destaque or C["azul_texto"]
    return (f'<div class="t" style="font-size:{size}px;color:{col}">'
            f'{texto}</div>'
            f'<style>.t b{{color:{dst}}}</style>')


def _bajada(texto, size, color=None):
    if not texto:
        return ""
    col = color or C["navy_70"]
    return (f'<div class="body" style="font-size:{size}px;color:{col};'
            f'max-width:88%">{texto}</div>')


def _esc(x):
    return "" if x is None else str(x)


# ══════════════════════════════════════════════════════ 01 · GANCHO (claro)
def gancho(d, fmt="vert"):
    """La tapa. chip + titular + regla + bajada. Es la que se ve en el feed.

    d: chip, titulo, bajada, icono, acento(azul), foto(opcional), foco
    """
    h = H[fmt]
    ts = {"post": 84, "vert": 92, "story": 100, "reel": 100}[fmt]
    bs = {"post": 33, "vert": 35, "story": 38, "reel": 38}[fmt]
    foto = ""
    if d.get("foto"):
        foto = (f'<div style="position:absolute;left:0;right:0;bottom:0;height:38%;'
                f'overflow:hidden"><img src="{d["foto"]}" style="width:100%;height:100%;'
                f'object-fit:cover;object-position:{d.get("foco","50% 50%")}"></div>'
                f'<div style="position:absolute;left:0;right:0;bottom:38%;height:180px;'
                f'background:linear-gradient(180deg,rgba(251,252,254,1),rgba(251,252,254,0))'
                f';z-index:2"></div>')
    cuerpo = f"""
  <div class="grow">
    {chip(d["chip"], icono_=d.get("icono")) if d.get("chip") else ""}
    <div style="height:34px"></div>
    {_tit(d["titulo"], ts)}
    {regla()}
    {_bajada(d.get("bajada",""), bs)}
  </div>"""
    return _page(h, _claro(h, cuerpo, PAD[fmt], extra_fondo=foto))


# ══════════════════════════════════════════════════════ 02 · LISTA (claro)
def lista(d, fmt="vert"):
    """chip + titular + 3 o 4 filas con burbuja de ícono. El caballito de
    batalla: sirve para «cómo funciona», «qué incluye», «tres señales».

    d: chip, titulo, items=[[icono, texto]], pie, acento
    """
    h = H[fmt]
    ts = {"post": 66, "vert": 72, "story": 80, "reel": 80}[fmt]
    fs = {"post": 30, "vert": 32, "story": 35, "reel": 35}[fmt]
    filas = "".join(
        f'<div class="card">{burbuja(ic)}'
        f'<div class="body" style="font-size:{fs}px;color:{C["navy"]};line-height:1.32">'
        f'{tx}</div></div>' for ic, tx in d["items"])
    pie = (f'<div class="meta" style="font-size:{fs-3}px;color:{C["navy_45"]};'
           f'margin-top:34px">{d["pie"]}</div>') if d.get("pie") else ""
    cuerpo = f"""
  <div class="grow">
    {chip(d["chip"], icono_=d.get("icono")) if d.get("chip") else ""}
    <div style="height:30px"></div>
    {_tit(d["titulo"], ts)}
    <div style="height:44px"></div>
    <div style="display:flex;flex-direction:column;gap:22px">{filas}</div>
    {pie}
  </div>"""
    return _page(h, _claro(h, cuerpo, PAD[fmt]))


# ══════════════════════════════════════════════════════ 03 · NÚMEROS (claro)
def numeros(d, fmt="vert"):
    """Filas con un dato a la derecha. Es la plantilla que convierte una
    afirmación en un argumento.

    d: chip, titulo, filas=[[icono, rotulo, valor]], remate_1, remate_2
    """
    h = H[fmt]
    ts = {"post": 66, "vert": 72, "story": 80, "reel": 80}[fmt]
    fs = {"post": 29, "vert": 31, "story": 34, "reel": 34}[fmt]
    vs = {"post": 40, "vert": 44, "story": 48, "reel": 48}[fmt]
    filas = "".join(
        f'<div class="card">{burbuja(ic)}'
        f'<div class="body" style="font-size:{fs}px;color:{C["navy"]};flex:1">{ro}</div>'
        f'<div class="t" style="font-size:{vs}px;color:{C["azul_texto"]}">{va}</div>'
        f'</div>' for ic, ro, va in d["filas"])
    remate = ""
    if d.get("remate_1"):
        remate = f"""
    <div style="height:34px"></div>
    <div style="height:5px;background:{C['azul']};border-radius:3px"></div>
    <div style="display:flex;align-items:center;gap:20px;margin-top:30px">
      {burbuja("check", 52)}
      <div class="t" style="font-size:{vs+2}px;color:{C['navy']};line-height:1.06">
        {d['remate_1']}<br><span style="color:{C['azul_texto']}">{d.get('remate_2','')}</span></div>
    </div>"""
    cuerpo = f"""
  <div class="grow">
    {chip(d["chip"], icono_=d.get("icono")) if d.get("chip") else ""}
    <div style="height:30px"></div>
    {_tit(d["titulo"], ts)}
    <div style="height:42px"></div>
    <div style="display:flex;flex-direction:column;gap:20px">{filas}</div>
    {remate}
  </div>"""
    return _page(h, _claro(h, cuerpo, PAD[fmt]))


# ══════════════════════════════════════════════════════ 04 · CHECKS (claro)
def checks(d, fmt="vert"):
    """Lista de beneficios con tilde. Más liviana que `lista`: sin tarjeta,
    sólo el tilde y la línea. Para el «todo en un solo lugar».

    d: chip, titulo, items=[texto], pie
    """
    h = H[fmt]
    ts = {"post": 66, "vert": 72, "story": 80, "reel": 80}[fmt]
    fs = {"post": 31, "vert": 33, "story": 36, "reel": 36}[fmt]
    filas = "".join(
        f'<div style="display:flex;align-items:flex-start;gap:22px">'
        f'{burbuja("check", 46)}'
        f'<div class="body" style="font-size:{fs}px;color:{C["navy"]};line-height:1.3;'
        f'padding-top:4px">{tx}</div></div>' for tx in d["items"])
    pie = (f'<div class="meta" style="font-size:{fs-4}px;color:{C["navy_45"]};'
           f'margin-top:40px">{d["pie"]}</div>') if d.get("pie") else ""
    cuerpo = f"""
  <div class="grow">
    {chip(d["chip"], icono_=d.get("icono")) if d.get("chip") else ""}
    <div style="height:30px"></div>
    {_tit(d["titulo"], ts)}
    <div style="height:46px"></div>
    <div style="display:flex;flex-direction:column;gap:30px">{filas}</div>
    {pie}
  </div>"""
    return _page(h, _claro(h, cuerpo, PAD[fmt]))


# ══════════════════════════════════════════════════════ 05 · PASOS (claro)
def pasos(d, fmt="vert"):
    """El paso a paso numerado. Distinta de `lista`: acá el orden importa y
    se ve, porque los pasos van encadenados por una línea.

    d: chip, titulo, pasos=[[titulo, texto]], pie
    """
    h = H[fmt]
    ts = {"post": 64, "vert": 70, "story": 78, "reel": 78}[fmt]
    fs = {"post": 27, "vert": 29, "story": 32, "reel": 32}[fmt]
    n = len(d["pasos"])
    filas = ""
    for i, (tt, tx) in enumerate(d["pasos"], 1):
        linea = ("" if i == n else
                 f'<div style="position:absolute;left:29px;top:64px;bottom:-30px;'
                 f'width:2px;background:rgba(0,106,255,.22)"></div>')
        filas += f"""
      <div style="position:relative;display:flex;gap:24px;padding-bottom:30px">
        {linea}
        <div style="width:58px;height:58px;min-width:58px;border-radius:50%;
          background:{C['azul']};color:#fff;display:flex;align-items:center;
          justify-content:center;font-family:'Sora';font-weight:800;font-size:27px;
          box-shadow:0 6px 18px rgba(0,106,255,.28);z-index:1">{i:02d}</div>
        <div style="padding-top:5px">
          <div class="st" style="font-size:{fs+6}px;color:{C['navy']}">{tt}</div>
          <div class="body" style="font-size:{fs}px;color:{C['navy_70']};margin-top:8px">{tx}</div>
        </div>
      </div>"""
    pie = (f'<div class="meta" style="font-size:{fs-2}px;color:{C["navy_45"]}">'
           f'{d["pie"]}</div>') if d.get("pie") else ""
    cuerpo = f"""
  <div class="grow">
    {chip(d["chip"], icono_=d.get("icono")) if d.get("chip") else ""}
    <div style="height:30px"></div>
    {_tit(d["titulo"], ts)}
    <div style="height:44px"></div>
    <div>{filas}</div>
    {pie}
  </div>"""
    return _page(h, _claro(h, cuerpo, PAD[fmt]))


# ═════════════════════════════════════════════════ 06 · COMPARACIÓN (claro)
def comparacion(d, fmt="vert"):
    """Antes / después. Dos columnas: la de la izquierda gris y tachada, la
    de la derecha azul. Es la pieza que más rápido explica para qué sirve
    Asistime, porque el lector se reconoce en la columna de la izquierda.

    d: chip, titulo, antes_rotulo, antes=[texto], despues_rotulo, despues=[texto]
    """
    h = H[fmt]
    ts = {"post": 62, "vert": 68, "story": 76, "reel": 76}[fmt]
    fs = {"post": 25, "vert": 27, "story": 30, "reel": 30}[fmt]

    def col(rot, items, azul):
        borde = C["azul"] if azul else "rgba(0,10,60,.12)"
        fondo = "#FFFFFF" if azul else "rgba(0,10,60,.028)"
        tinta = C["navy"] if azul else C["navy_45"]
        rc = C["azul_texto"] if azul else C["navy_45"]
        marca = ("check" if azul else "alerta")
        col_b = C["azul"] if azul else "#B9BFD0"
        lis = "".join(
            f'<div style="display:flex;align-items:flex-start;gap:14px">'
            f'{burbuja(marca, 34, col_b, "#FFFFFF")}'
            f'<div class="body" style="font-size:{fs}px;color:{tinta};line-height:1.28">'
            f'{t}</div></div>' for t in items)
        return (f'<div style="flex:1;background:{fondo};border:2px solid {borde};'
                f'border-radius:22px;padding:30px 26px;display:flex;flex-direction:column;gap:20px">'
                f'<div class="st" style="font-size:{fs+3}px;color:{rc};'
                f'text-transform:uppercase;letter-spacing:.06em">{rot}</div>{lis}</div>')

    cuerpo = f"""
  <div class="grow">
    {chip(d["chip"], icono_=d.get("icono")) if d.get("chip") else ""}
    <div style="height:30px"></div>
    {_tit(d["titulo"], ts)}
    <div style="height:44px"></div>
    <div style="display:flex;gap:22px;align-items:stretch">
      {col(d.get("antes_rotulo","Hoy"), d["antes"], False)}
      {col(d.get("despues_rotulo","Con Asistime"), d["despues"], True)}
    </div>
  </div>"""
    return _page(h, _claro(h, cuerpo, PAD[fmt]))


# ══════════════════════════════════════════════════════ 07 · CASO (claro)
def caso(d, fmt="vert"):
    """El caso de uso de un rubro. Rubro arriba, la situación, y qué hace el
    agente. Es lo que hace que un dueño de pyme diga «esto es lo mío».

    d: chip, rubro, titulo, situacion, hace=[texto], resultado
    """
    h = H[fmt]
    ts = {"post": 60, "vert": 66, "story": 74, "reel": 74}[fmt]
    fs = {"post": 27, "vert": 29, "story": 32, "reel": 32}[fmt]
    lis = "".join(
        f'<div style="display:flex;align-items:flex-start;gap:16px">'
        f'{burbuja("flecha", 36)}'
        f'<div class="body" style="font-size:{fs}px;color:{C["navy"]};line-height:1.3">'
        f'{t}</div></div>' for t in d.get("hace", []))
    res = ""
    if d.get("resultado"):
        res = (f'<div style="margin-top:34px;background:{C["azul"]};border-radius:22px;'
               f'padding:30px 32px;box-shadow:0 12px 34px rgba(0,106,255,.26)">'
               f'<div class="meta" style="font-size:{fs-6}px;color:rgba(255,255,255,.72);'
               f'text-transform:uppercase;letter-spacing:.10em">Resultado</div>'
               f'<div class="t" style="font-size:{fs+12}px;color:#fff;margin-top:10px;'
               f'line-height:1.1">{d["resultado"]}</div></div>')
    cuerpo = f"""
  <div class="grow">
    {chip(d.get("chip") or d.get("rubro",""), icono_=d.get("icono"))}
    <div style="height:30px"></div>
    {_tit(d["titulo"], ts)}
    {regla()}
    {_bajada(d.get("situacion",""), fs+2)}
    <div style="height:34px"></div>
    <div style="display:flex;flex-direction:column;gap:20px">{lis}</div>
    {res}
  </div>"""
    return _page(h, _claro(h, cuerpo, PAD[fmt]))


# ══════════════════════════════════════════════════════ 08 · CITA (claro)
def cita(d, fmt="vert"):
    """Testimonio o frase. La comilla es un elemento gráfico grande, no un
    signo de puntuación.

    d: chip, frase, autor, rol, foto(opcional)
    """
    h = H[fmt]
    fzs = {"post": 58, "vert": 64, "story": 70, "reel": 70}[fmt]
    fs = {"post": 27, "vert": 29, "story": 32, "reel": 32}[fmt]
    av = ""
    if d.get("foto"):
        av = (f'<img src="{d["foto"]}" style="width:96px;height:96px;border-radius:50%;'
              f'object-fit:cover;object-position:{d.get("foco","50% 40%")}">')
    cuerpo = f"""
  <div class="grow">
    {chip(d["chip"], icono_=d.get("icono")) if d.get("chip") else ""}
    <div style="height:26px"></div>
    <div style="font-family:'Sora';font-weight:800;font-size:190px;color:{C['azul']};
      line-height:.6;opacity:.20;height:110px">&ldquo;</div>
    <div class="t" style="font-size:{fzs}px;color:{C['navy']};line-height:1.16;
      font-weight:700;letter-spacing:-.03em">{d['frase']}</div>
    <div style="height:44px"></div>
    <div style="display:flex;align-items:center;gap:22px">{av}
      <div>
        <div class="st" style="font-size:{fs+5}px;color:{C['navy']}">{d['autor']}</div>
        <div class="body" style="font-size:{fs-2}px;color:{C['navy_45']};margin-top:4px">
          {d.get('rol','')}</div>
      </div>
    </div>
  </div>"""
    return _page(h, _claro(h, cuerpo, PAD[fmt]))


# ═══════════════════════════════════════════════════ 09 · PRODUCTO (claro)
def producto(d, fmt="vert"):
    """Una captura de la plataforma adentro del mockup de un navegador.
    Es la única forma honesta de mostrar el producto: un pantallazo suelto
    parece un recorte, adentro del marco parece software.

    d: chip, titulo, bajada, captura, url
    """
    h = H[fmt]
    ts = {"post": 60, "vert": 66, "story": 74, "reel": 74}[fmt]
    bs = {"post": 28, "vert": 30, "story": 33, "reel": 33}[fmt]
    puntos = "".join(
        f'<span style="width:12px;height:12px;border-radius:50%;background:{c}"></span>'
        for c in ("#FF5F57", "#FEBC2E", "#28C840"))
    url = d.get("url", "admin.asistime.ai")
    mock = f"""
    <div style="border-radius:20px;overflow:hidden;background:#fff;
      box-shadow:0 24px 60px rgba(0,30,110,.18);border:1px solid rgba(0,10,60,.08)">
      <div style="height:52px;background:#F2F5FB;border-bottom:1px solid rgba(0,10,60,.07);
        display:flex;align-items:center;gap:9px;padding:0 20px">{puntos}
        <div style="flex:1;margin-left:14px;height:28px;border-radius:8px;background:#fff;
          border:1px solid rgba(0,10,60,.08);display:flex;align-items:center;padding:0 12px;
          font-family:'DMSans';font-size:16px;color:{C['navy_45']}">{url}</div></div>
      <img src="{d['captura']}" style="width:100%;display:block">
    </div>"""
    cuerpo = f"""
  <div class="grow">
    {chip(d["chip"], icono_=d.get("icono")) if d.get("chip") else ""}
    <div style="height:28px"></div>
    {_tit(d["titulo"], ts)}
    <div style="height:22px"></div>
    {_bajada(d.get("bajada",""), bs)}
    <div style="height:40px"></div>
    {mock}
  </div>"""
    return _page(h, _claro(h, cuerpo, PAD[fmt]))


# ══════════════════════════════════════════════════ 10 · IMPACTO (oscuro)
def impacto(d, fmt="vert"):
    """El slide oscuro. Una palabra o un número gigante y nada más.
    **Una vez por carrusel, como máximo.** Funciona porque es la excepción.

    d: chip, palabra_1, palabra_2, texto, pie
    """
    h = H[fmt]
    gs = {"post": 138, "vert": 152, "story": 168, "reel": 168}[fmt]
    bs = {"post": 31, "vert": 33, "story": 36, "reel": 36}[fmt]
    cuerpo = f"""
  <div class="grow">
    {chip(d["chip"], oscuro=True) if d.get("chip") else ""}
    <div style="height:40px"></div>
    <div class="t" style="font-size:{gs}px;line-height:.94;
      color:{C['azul_glow']};text-shadow:0 0 70px rgba(43,139,255,.55)">{d['palabra_1']}</div>
    <div class="t" style="font-size:{gs}px;line-height:.98;color:#FFFFFF">
      {d.get('palabra_2','')}</div>
    <div style="height:5px;background:rgba(255,255,255,.22);border-radius:3px;
      margin:36px 0 30px"></div>
    <div class="body" style="font-size:{bs}px;color:rgba(255,255,255,.80);max-width:92%">
      {d.get('texto','')}</div>
    {f'<div class="meta" style="font-size:{bs-5}px;color:rgba(255,255,255,.50);margin-top:26px">{d["pie"]}</div>' if d.get("pie") else ""}
  </div>"""
    return _page(h, _oscuro(h, cuerpo, PAD[fmt]))


# ═══════════════════════════════════════════════════ 11 · CIERRE (oscuro)
def cierre(d, fmt="vert"):
    """La última. Titular, el chip de credencial, «Hablá con Tony» y el sitio.
    Nunca pide seguidores: pide una conversación, que es lo que vende.

    d: titulo, chip, cta, sitio, pie
    """
    h = H[fmt]
    ts = {"post": 74, "vert": 80, "story": 88, "reel": 88}[fmt]
    cuerpo = f"""
  <div class="grow">
    {_tit(d["titulo"], ts, "#FFFFFF", C["azul_glow"])}
    <div style="width:86px;height:6px;background:{C['azul_glow']};border-radius:3px;
      margin:34px 0 30px"></div>
    {chip(d["chip"], oscuro=True) if d.get("chip") else ""}
    <div style="height:44px"></div>
    {boton(d.get("cta","Hablá con Tony"))}
    <div style="height:32px"></div>
    {sitio("rgba(255,255,255,.80)", C['azul_glow'], d.get("sitio","asistime.ai"))}
    {f'<div class="body" style="font-size:26px;color:rgba(255,255,255,.50);margin-top:26px">{d["pie"]}</div>' if d.get("pie") else ""}
  </div>"""
    return _page(h, _oscuro(h, cuerpo, PAD[fmt]))


# ═════════════════════════════════════════════════════ 12 · TONY (oscuro)
def tony(d, fmt="vert"):
    """Tony a sangre sobre el azul profundo, con el titular arriba. Es la
    pieza de presentación del agente y la que mejor rinde de la cuenta.

    d: titulo, bajada, foto (el PNG de Tony, con fondo recortado), pie,
       ajuste (`contain` si el PNG viene recortado con transparencia —que es
       lo normal—, `cover` si es una foto rectangular a sangre)
    """
    h = H[fmt]
    ts = {"post": 80, "vert": 88, "story": 96, "reel": 96}[fmt]
    bs = {"post": 30, "vert": 32, "story": 35, "reel": 35}[fmt]
    t, l, b = PAD[fmt]
    img = ""
    if d.get("foto"):
        # Un Tony recortado va con `contain` y anclado abajo: con `cover` se le
        # corta la cabeza o los pies según la proporción del PNG, y el recorte
        # sobre transparencia no deja rastro de que pasó.
        aj = d.get("ajuste", "contain")
        pos = d.get("foco", "50% 100%" if aj == "contain" else "50% 20%")
        img = (f'<img src="{d["foto"]}" style="position:absolute;left:0;right:0;bottom:0;'
               f'width:100%;height:{d.get("alto","62%")};object-fit:{aj};'
               f'object-position:{pos};z-index:2">')
    velo = (f'<div style="position:absolute;left:0;right:0;bottom:0;height:34%;z-index:2;'
            f'background:linear-gradient(180deg,rgba(1,10,45,0),rgba(1,10,45,.72))"></div>')
    pie = (f'<div class="meta" style="font-size:{bs-2}px;color:rgba(255,255,255,.72);'
           f'position:absolute;left:{l}px;bottom:{b}px;z-index:4">{d["pie"]}</div>'
           ) if d.get("pie") else ""
    inner = f"""
<div style="position:absolute;inset:0;background:{GRAD_OSCURO}"></div>
<div class="glow" style="width:760px;height:760px;left:-200px;top:-200px;
  background:rgba(43,139,255,.30)"></div>
{img}{velo}
<div style="position:absolute;top:{t}px;left:{l}px;right:{l}px;z-index:4">
  {logo(1.0, "#FFFFFF")}
  <div style="height:34px"></div>
  {_tit(d["titulo"], ts, "#FFFFFF", C["azul_glow"])}
  <div style="height:22px"></div>
  {_bajada(d.get("bajada",""), bs, "rgba(255,255,255,.80)")}
</div>{pie}"""
    return _page(h, inner)


# ═══════════════════════════════════════════════════ 13 · ALERTA (oscuro)
def alerta(d, fmt="vert"):
    """La novedad urgente: un cambio de Meta, una función nueva, un aviso.
    Chip rojo, titular pesado en mayúsculas y nada más. **Sólo cuando el
    contenido de verdad es una novedad** — usarla para contenido normal
    quema el recurso y la próxima ya no frena a nadie.

    d: rotulo, titulo, bajada, captura(opcional), pie
    """
    h = H[fmt]
    ts = {"post": 84, "vert": 92, "story": 100, "reel": 100}[fmt]
    bs = {"post": 30, "vert": 32, "story": 35, "reel": 35}[fmt]
    rojo = C["alerta"]
    cap = ""
    if d.get("captura"):
        cap = (f'<div style="margin-top:42px;border-radius:20px;overflow:hidden;'
               f'border:1px solid rgba(255,255,255,.14);box-shadow:0 20px 50px rgba(0,0,0,.45)">'
               f'<img src="{d["captura"]}" style="width:100%;display:block"></div>')
    rot = (f'<div style="display:inline-flex;align-items:center;gap:12px;background:{rojo};'
           f'color:#fff;padding:13px 24px;border-radius:10px;font-family:\'Sora\';'
           f'font-weight:800;font-size:30px;letter-spacing:.06em;text-transform:uppercase;'
           f'align-self:flex-start">{icono("alerta",26,"#fff")}{d.get("rotulo","Atención")}</div>')
    cuerpo = f"""
  <div class="grow">
    {rot}
    <div style="height:34px"></div>
    <div class="t" style="font-size:{ts}px;color:#FFFFFF;line-height:.98;
      text-transform:uppercase">{d['titulo']}</div>
    <div style="height:26px"></div>
    {_bajada(d.get("bajada",""), bs, "rgba(255,255,255,.82)")}
    {cap}
    {f'<div class="meta" style="font-size:{bs-5}px;color:rgba(255,255,255,.52);margin-top:30px">{d["pie"]}</div>' if d.get("pie") else ""}
  </div>"""
    return _page(h, _oscuro(h, cuerpo, PAD[fmt]))


# ══════════════════════════════════════════════════════ 14 · CLIP (oscuro)
def clip(d, fmt="vert"):
    """Tapa de reel o de corte de podcast: foto a sangre, velo, y el titular
    abajo en dos colores. Es la única pieza de la marca con foto de persona
    real ocupando todo el cuadro.

    d: titulo_1, titulo_2, foto, foco, rotulo, color_1, color_2
    """
    h = H[fmt]
    ts = {"post": 88, "vert": 96, "story": 108, "reel": 108}[fmt]
    t, l, b = PAD[fmt]
    c1 = d.get("color_1", "#FFFFFF")
    c2 = d.get("color_2", C["azul_glow"])
    rot = ""
    if d.get("rotulo"):
        rot = (f'<div style="display:inline-flex;align-items:center;gap:12px;'
               f'background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.24);'
               f'color:#fff;padding:12px 22px;border-radius:999px;font-family:\'Sora\';'
               f'font-weight:700;font-size:26px;margin-bottom:26px;align-self:flex-start">'
               f'{icono("estrella",22,"#fff")}{d["rotulo"]}</div>')
    inner = f"""
<img class="bg" src="{d['foto']}" style="object-position:{d.get('foco','50% 40%')}">
<div class="scrim" style="background:linear-gradient(180deg,rgba(1,3,13,.55) 0%,
  rgba(1,3,13,.10) 34%,rgba(1,3,13,.62) 74%,rgba(1,3,13,.93) 100%)"></div>
<div class="pad" style="padding:{t}px {l}px {b}px">
  <div class="row">{logo(1.0,"#FFFFFF")}</div>
  <div class="grow" style="justify-content:flex-end">
    {rot}
    <div class="t" style="font-size:{ts}px;color:{c1};line-height:.96">{d['titulo_1']}</div>
    <div class="t" style="font-size:{ts}px;color:{c2};line-height:.96">{d.get('titulo_2','')}</div>
  </div>
</div>"""
    return _page(h, inner)


# ═══════════════════════════════════════════════════ 15 · PREGUNTA (claro)
def pregunta(d, fmt="vert"):
    """Tipográfica pura: una pregunta gigante y nada más. El gancho más
    barato de producir y de los que mejor rinden, porque no compite con
    ninguna imagen.

    d: titulo, pie, oscuro(bool), foto(opcional, se recorta abajo a la derecha)
    """
    h = H[fmt]
    ts = {"post": 108, "vert": 120, "story": 134, "reel": 134}[fmt]
    osc = bool(d.get("oscuro"))
    t, l, b = PAD[fmt]
    img = ""
    if d.get("foto"):
        img = (f'<img src="{d["foto"]}" style="position:absolute;right:-40px;bottom:0;'
               f'height:{d.get("alto","44%")};z-index:2">')
    cuerpo = f"""
  <div class="grow">
    {_tit(d["titulo"], ts, "#FFFFFF" if osc else None,
          C["azul_glow"] if osc else None)}
    {f'<div style="height:36px"></div>' if d.get("pie") else ""}
    {f'<div class="meta" style="font-size:32px;color:{"rgba(255,255,255,.72)" if osc else C["navy_45"]}">{d["pie"]}</div>' if d.get("pie") else ""}
  </div>"""
    env = _oscuro if osc else _claro
    return _page(h, env(h, cuerpo, PAD[fmt], extra_fondo=img))


# ══════════════════════════════════════════════════════ 16 · AGENDA (claro)
def agenda(d, fmt="vert"):
    """Charla, webinar, demo: una fecha que hay que agendar.

    d: chip, titulo, dia, mes, hora, lugar, bajada, cta
    """
    h = H[fmt]
    ts = {"post": 64, "vert": 70, "story": 78, "reel": 78}[fmt]
    fs = {"post": 28, "vert": 30, "story": 33, "reel": 33}[fmt]
    filas = []
    for ic, tx in (("calendario", f"{d.get('dia','')} de {d.get('mes','')}"),
                   ("reloj", d.get("hora", "")), ("gente", d.get("lugar", ""))):
        if tx and tx.strip(" de"):
            filas.append(f'<div class="card">{burbuja(ic)}'
                         f'<div class="st" style="font-size:{fs+2}px;color:{C["navy"]}">'
                         f'{tx}</div></div>')
    cuerpo = f"""
  <div class="grow">
    {chip(d["chip"], icono_=d.get("icono","calendario")) if d.get("chip") else ""}
    <div style="height:30px"></div>
    {_tit(d["titulo"], ts)}
    {regla()}
    {_bajada(d.get("bajada",""), fs)}
    <div style="height:36px"></div>
    <div style="display:flex;flex-direction:column;gap:18px">{"".join(filas)}</div>
    <div style="height:38px"></div>
    {boton(d.get("cta","Quiero mi lugar"), C["azul"], "#FFFFFF", "flecha")}
  </div>"""
    return _page(h, _claro(h, cuerpo, PAD[fmt]))


# ═════════════════════════════════════════════════════ 17 · EQUIPO (claro)
def equipo(d, fmt="vert"):
    """La tarjeta de una persona del equipo. Una marca de software que
    muestra caras vende distinto que una que muestra sólo pantallas.

    d: chip, nombre, rol, frase, foto, foco
    """
    h = H[fmt]
    ns = {"post": 72, "vert": 78, "story": 86, "reel": 86}[fmt]
    fs = {"post": 28, "vert": 30, "story": 33, "reel": 33}[fmt]
    ret = ""
    if d.get("foto"):
        ret = (f'<div style="border-radius:26px;overflow:hidden;height:{d.get("alto","46%")};'
               f'box-shadow:0 18px 46px rgba(0,30,110,.16)">'
               f'<img src="{d["foto"]}" style="width:100%;height:100%;object-fit:cover;'
               f'object-position:{d.get("foco","50% 30%")}"></div>')
    cuerpo = f"""
  <div class="grow">
    {chip(d["chip"], icono_=d.get("icono","gente")) if d.get("chip") else ""}
    <div style="height:28px"></div>
    {ret}
    <div style="height:34px"></div>
    <div class="t" style="font-size:{ns}px;color:{C['navy']}">{d['nombre']}</div>
    <div class="st" style="font-size:{fs+2}px;color:{C['azul_texto']};margin-top:10px">
      {d.get('rol','')}</div>
    {f'<div class="body" style="font-size:{fs}px;color:{C["navy_70"]};margin-top:22px">{d["frase"]}</div>' if d.get("frase") else ""}
  </div>"""
    return _page(h, _claro(h, cuerpo, PAD[fmt]))


# ═══════════════════════════════════════════════════════ 18 · DESTACADA
def destacada(d, fmt="post"):
    """Portada de historia destacada. Instagram la recorta **en un círculo
    desde el centro**: todo vive adentro de un círculo imaginario y nada se
    apoya en los bordes. Se ve a ~64 px, por eso el ícono es enorme acá.

    d: titulo, icono, oscuro(bool)
    """
    h = H["post"]
    osc = bool(d.get("oscuro"))
    fondo = GRAD_OSCURO if osc else GRAD_CLARO
    tinta = "#FFFFFF" if osc else C["navy"]
    burb = C["azul_glow"] if osc else C["azul"]
    inner = f"""
<div style="position:absolute;inset:0;background:{fondo}"></div>
<div style="position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:44px">
  {burbuja(d.get("icono","chat"), 300, burb, "#FFFFFF", 150)}
  <div class="t" style="font-size:96px;color:{tinta};text-align:center;
    text-transform:uppercase;letter-spacing:-.02em">{d['titulo']}</div>
</div>"""
    return _page(h, inner)


PLANTILLAS = {
    "gancho": gancho,
    "lista": lista,
    "numeros": numeros,
    "checks": checks,
    "pasos": pasos,
    "comparacion": comparacion,
    "caso": caso,
    "cita": cita,
    "producto": producto,
    "impacto": impacto,
    "cierre": cierre,
    "tony": tony,
    "alerta": alerta,
    "clip": clip,
    "pregunta": pregunta,
    "agenda": agenda,
    "equipo": equipo,
    "destacada": destacada,
}
