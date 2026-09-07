# -*- coding: utf-8 -*-
"""Presentaciones en PDF con la identidad de Asistime.ai.

Un deck es una lista de slides. Cada uno declara su `tipo` y trae sólo los
datos que ese tipo necesita; la maquetación viene de acá. Es la misma idea que
las plantillas de placas: el pedido aporta el contenido, el sistema la forma.

Lo dibuja Chromium, no una librería de PDF: por eso la tipografía y las sombras
salen idénticas a las de las placas.

1600 × 900 px (16:9). Asistime es clara, así que el deck es claro: sólo la
portada, los cortes de sección y el cierre van en oscuro.
"""
from brand import (C, GRAD_CLARO, GRAD_OSCURO, FONT_CSS, LOGO_CSS,
                   logo, lockup, burbuja, icono)

ANCHO, ALTO = 1600, 900


def _css() -> str:
    return f"""
{FONT_CSS}{LOGO_CSS}
*{{margin:0;padding:0;box-sizing:border-box}}
@page{{size:{ANCHO}px {ALTO}px;margin:0}}
html,body{{background:{C['fondo']}}}
.slide{{position:relative;width:{ANCHO}px;height:{ALTO}px;overflow:hidden;
  background:{C['fondo']};color:{C['navy']};font-family:'DMSans',sans-serif;
  page-break-after:always;break-after:page}}
.slide:last-child{{page-break-after:auto;break-after:auto}}
.pad{{position:absolute;inset:0;padding:74px 96px 108px;display:flex;flex-direction:column}}
.h1{{font-family:'Sora',sans-serif;font-weight:800;font-size:88px;line-height:1.0;
  letter-spacing:-.04em}}
.h2{{font-family:'Sora',sans-serif;font-weight:800;font-size:62px;line-height:1.04;
  letter-spacing:-.035em}}
.h3{{font-family:'Sora',sans-serif;font-weight:700;font-size:34px;line-height:1.16;
  letter-spacing:-.02em}}
.h1 b,.h2 b{{color:{C['azul_texto']}}}
.kicker{{font-family:'Sora',sans-serif;font-weight:700;font-size:20px;
  letter-spacing:.14em;text-transform:uppercase;color:{C['azul_texto']}}}
.lead{{font-size:27px;line-height:1.5;color:{C['navy_70']};max-width:30ch}}
.body{{font-size:23px;line-height:1.6;color:{C['navy_70']}}}
.pie{{position:absolute;left:96px;right:96px;bottom:44px;display:flex;
  justify-content:space-between;align-items:flex-end;font-family:'Sora',sans-serif;
  font-weight:600;font-size:17px;letter-spacing:.10em;text-transform:uppercase;
  color:{C['navy_45']}}}
.card{{background:#fff;border-radius:20px;box-shadow:0 6px 24px rgba(0,20,80,.07);
  padding:30px 32px}}
.glow{{position:absolute;border-radius:50%;filter:blur(90px);opacity:.55}}
.osc{{background:{GRAD_OSCURO};color:#fff}}
.osc .lead,.osc .body{{color:rgba(255,255,255,.80)}}
.osc .kicker{{color:{C['azul_glow']}}}
.osc .h1 b,.osc .h2 b{{color:{C['azul_glow']}}}
.osc .pie{{color:rgba(255,255,255,.50)}}
.regla{{width:78px;height:6px;border-radius:3px;background:{C['azul']};margin:26px 0 22px}}
.osc .regla{{background:{C['azul_glow']}}}
.puntos{{list-style:none;margin-top:30px;display:flex;flex-direction:column;gap:18px}}
.puntos li{{position:relative;padding-left:38px;font-size:24px;line-height:1.4;
  color:{C['navy_70']}}}
.puntos li::before{{content:'';position:absolute;left:0;top:9px;width:18px;height:18px;
  border-radius:50%;background:{C['azul']}}}
.datos{{display:grid;gap:44px 36px;margin-top:52px}}
.dato .cifra{{font-family:'Sora',sans-serif;font-weight:800;font-size:82px;
  letter-spacing:-.045em;color:{C['azul_texto']};line-height:1}}
.dato .rot{{font-size:20px;color:{C['navy_45']};margin-top:8px;letter-spacing:.04em;
  text-transform:uppercase;font-family:'Sora';font-weight:600}}
.fila{{display:flex;justify-content:space-between;align-items:center;
  padding:22px 4px;border-bottom:1px solid {C['linea']}}}
.fila .izq{{font-family:'Sora';font-weight:600;font-size:26px;color:{C['navy']}}}
.fila .der{{font-family:'Sora';font-weight:800;font-size:26px;color:{C['azul_texto']}}}
.foto{{position:absolute;inset:0;background-size:cover;background-repeat:no-repeat}}
"""


def _pie(meta, n=""):
    izq = meta.get("pie", "asistime.ai")
    der = f'<span>{meta.get("fecha","")}</span>' if meta.get("fecha") else "<span></span>"
    num = f'<span>{n}</span>' if n else "<span></span>"
    return f'<div class="pie"><span>{izq}</span>{der}{num}</div>'


def _portada(s, meta):
    foto = ""
    if s.get("foto"):
        foto = (f'<div class="foto" style="background-image:url({s["foto"]});'
                f'background-position:{s.get("foco","50% 40%")};opacity:.30"></div>')
    return f"""<div class="slide osc">
  <div style="position:absolute;inset:0;background:{GRAD_OSCURO}"></div>{foto}
  <div class="glow" style="width:700px;height:700px;right:-200px;bottom:-220px;
    background:rgba(43,139,255,.32)"></div>
  <div class="pad" style="justify-content:center">
    {lockup(300, "#FFFFFF")}
    <div style="height:52px"></div>
    <div class="kicker">{s.get('kicker','')}</div>
    <div class="h1" style="margin-top:18px;max-width:22ch">{s.get('titulo','')}</div>
    <div class="regla"></div>
    <div class="lead">{s.get('bajada','')}</div>
  </div>{_pie(meta)}</div>"""


def _seccion(s, meta, n):
    return f"""<div class="slide osc">
  <div style="position:absolute;inset:0;background:{GRAD_OSCURO}"></div>
  <div class="glow" style="width:640px;height:640px;left:-180px;top:-200px;
    background:rgba(43,139,255,.28)"></div>
  <div class="pad" style="justify-content:center">
    <div class="kicker">{s.get('kicker','')}</div>
    <div class="h1" style="margin-top:16px;max-width:20ch">{s.get('titulo','')}</div>
    <div class="regla"></div>
    <div class="lead">{s.get('bajada','')}</div>
  </div>{_pie(meta, n)}</div>"""


def _contenido(s, meta, n):
    lis = "".join(f"<li>{p}</li>" for p in s.get("puntos", []))
    foto = ""
    ancho = "58%"
    if s.get("foto"):
        foto = (f'<div style="position:absolute;right:0;top:0;bottom:0;width:40%;'
                f'background-image:url({s["foto"]});background-size:cover;'
                f'background-position:{s.get("foco","50% 40%")}"></div>')
    else:
        ancho = "78%"
    return f"""<div class="slide">
  <div style="position:absolute;inset:0;background:{GRAD_CLARO}"></div>{foto}
  <div class="pad" style="justify-content:center;width:{ancho}">
    {logo(0.9)}
    <div style="height:30px"></div>
    <div class="kicker">{s.get('kicker','')}</div>
    <div class="h2" style="margin-top:14px">{s.get('titulo','')}</div>
    <div class="regla"></div>
    <div class="body" style="max-width:34ch">{s.get('texto','')}</div>
    <ul class="puntos">{lis}</ul>
  </div>{_pie(meta, n)}</div>"""


def _datos(s, meta, n):
    ds = s.get("datos", [])
    cols = min(len(ds), 4) or 1
    cel = "".join(f'<div class="dato"><div class="cifra">{c}</div>'
                  f'<div class="rot">{r}</div></div>' for c, r in ds)
    return f"""<div class="slide">
  <div style="position:absolute;inset:0;background:{GRAD_CLARO}"></div>
  <div class="glow" style="width:520px;height:520px;right:-150px;top:-160px;
    background:rgba(0,106,255,.12)"></div>
  <div class="pad" style="justify-content:center">
    {logo(0.9)}
    <div style="height:30px"></div>
    <div class="kicker">{s.get('kicker','')}</div>
    <div class="h2" style="margin-top:14px;max-width:24ch">{s.get('titulo','')}</div>
    <div class="datos" style="grid-template-columns:repeat({cols},1fr)">{cel}</div>
  </div>{_pie(meta, n)}</div>"""


def _tabla(s, meta, n):
    filas = "".join(f'<div class="fila"><div class="izq">{a}</div>'
                    f'<div class="der">{b}</div></div>' for a, b in s.get("filas", []))
    return f"""<div class="slide">
  <div style="position:absolute;inset:0;background:{GRAD_CLARO}"></div>
  <div class="pad" style="justify-content:center">
    {logo(0.9)}
    <div style="height:26px"></div>
    <div class="kicker">{s.get('kicker','')}</div>
    <div class="h2" style="margin-top:14px">{s.get('titulo','')}</div>
    <div class="card" style="margin-top:34px;padding:14px 32px">{filas}</div>
  </div>{_pie(meta, n)}</div>"""


def _foto(s, meta, n):
    return f"""<div class="slide osc">
  <div class="foto" style="background-image:url({s.get('foto','')});
    background-position:{s.get('foco','50% 40%')}"></div>
  <div style="position:absolute;inset:0;background:linear-gradient(90deg,
    rgba(1,10,45,.92) 0%,rgba(1,10,45,.60) 46%,rgba(1,10,45,.20) 100%)"></div>
  <div class="pad" style="justify-content:center;width:62%">
    <div class="kicker">{s.get('kicker','')}</div>
    <div class="h2" style="margin-top:14px;color:#fff">{s.get('titulo','')}</div>
    <div class="regla"></div>
    <div class="lead">{s.get('bajada','')}</div>
  </div>{_pie(meta, n)}</div>"""


def _cierre(s, meta):
    lineas = "<br>".join(s.get("lineas", []))
    return f"""<div class="slide osc">
  <div style="position:absolute;inset:0;background:{GRAD_OSCURO}"></div>
  <div class="glow" style="width:720px;height:720px;left:50%;top:60%;
    transform:translate(-50%,-50%);background:rgba(43,139,255,.30)"></div>
  <div class="pad" style="justify-content:center;align-items:center;text-align:center">
    {lockup(320, "#FFFFFF", "center")}
    <div style="height:46px"></div>
    <div class="h2" style="max-width:22ch">{s.get('titulo','Hablemos')}</div>
    <div class="body" style="margin-top:28px;color:rgba(255,255,255,.82)">{lineas}</div>
  </div>{_pie(meta)}</div>"""


TIPOS = {"portada": _portada, "seccion": _seccion, "contenido": _contenido,
         "datos": _datos, "tabla": _tabla, "foto": _foto, "cierre": _cierre}


def deck(d: dict) -> str:
    meta = {"pie": d.get("pie", "asistime.ai · @asistime.ai"),
            "fecha": d.get("fecha", "")}
    partes, n = [], 0
    for s in d["slides"]:
        tipo = s.get("tipo", "contenido")
        if tipo in ("portada", "cierre"):
            partes.append(TIPOS[tipo](s, meta))
        else:
            n += 1
            partes.append(TIPOS[tipo](s, meta, f"{n:02d}"))
    return (f'<!doctype html><html><head><meta charset="utf-8">'
            f'<style>{_css()}</style></head><body>{"".join(partes)}</body></html>')
