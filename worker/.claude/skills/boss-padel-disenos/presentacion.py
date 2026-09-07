# -*- coding: utf-8 -*-
"""Presentaciones en PDF con la identidad de Boss Padel.

Un deck es una lista de slides. Cada slide declara su `tipo` y trae sólo los
datos que ese tipo necesita; la maquetación no se negocia, viene de acá. Es la
misma idea que las plantillas de placas: el pedido aporta el contenido, el
sistema aporta la forma.

Se renderiza con el motor de impresión de Chromium, no con una librería de PDF.
Por eso la tipografía, el interletrado y las fotos salen exactamente como en las
placas: es el mismo navegador dibujando las mismas fuentes.

Formato 1600 × 900 px (16:9), que es lo que espera cualquier proyector y lo que
mejor se lee en un celular en horizontal.
"""
from brand import C, FONT_CSS, LOGO_CSS, aros, blob, logo

ANCHO, ALTO = 1600, 900

# El acento cambia por sede; el resto de la paleta es fija.
ACENTOS = {"lima": C["lima"], "naranja": C["naranja"], "azul": C["azul"]}


def _css(acento: str) -> str:
    ac = ACENTOS.get(acento, C["lima"])
    return f"""
{FONT_CSS}
{LOGO_CSS}
*{{margin:0;padding:0;box-sizing:border-box}}
@page{{size:{ANCHO}px {ALTO}px;margin:0}}
html,body{{background:{C['negro']}}}
.slide{{
  position:relative;width:{ANCHO}px;height:{ALTO}px;overflow:hidden;
  background:{C['negro']};color:{C['blanco']};
  font-family:'Barlow',sans-serif;
  page-break-after:always;break-after:page;
}}
.slide:last-child{{page-break-after:auto;break-after:auto}}
.pad{{position:absolute;inset:0;padding:80px 104px 132px;display:flex;flex-direction:column}}

/* ── tipografía ─────────────────────────────────────────────── */
/* El cuerpo del título de portada se calcula según el largo del texto: un
   titular de cuatro palabras y uno de doce no pueden entrar al mismo tamaño
   sin desbordar la página. Ver _cuerpo_portada(). */
.h1{{font-family:'Archivo',sans-serif;font-weight:800;line-height:.92;
    letter-spacing:-.035em;text-transform:uppercase}}
.h2{{font-family:'Archivo',sans-serif;font-weight:800;font-size:78px;line-height:1.0;
    letter-spacing:-.03em;text-transform:uppercase}}
.h3{{font-family:'Archivo',sans-serif;font-weight:700;font-size:46px;line-height:1.1;
    letter-spacing:-.02em}}
.kicker{{font-family:'BarlowC',sans-serif;font-weight:500;font-size:23px;
    letter-spacing:.34em;text-transform:uppercase;color:{ac}}}
.lead{{font-size:31px;line-height:1.5;font-weight:300;color:#D8D8D8;max-width:20ch}}
.body{{font-size:25px;line-height:1.62;font-weight:300;color:#C4C4C4}}
.pie{{position:absolute;left:104px;right:104px;bottom:52px;display:flex;
     justify-content:space-between;align-items:flex-end;
     font-family:'BarlowC',sans-serif;font-size:19px;letter-spacing:.2em;
     text-transform:uppercase;color:#6E6E6E}}
.num{{color:{ac}}}

/* ── foto de fondo ──────────────────────────────────────────── */
.foto{{position:absolute;inset:0;background-size:cover;background-repeat:no-repeat}}
.velo{{position:absolute;inset:0}}
.velo-izq{{background:linear-gradient(100deg,
   rgba(10,10,10,.97) 0%,rgba(10,10,10,.92) 34%,rgba(10,10,10,.45) 60%,rgba(10,10,10,.2) 100%)}}
.velo-full{{background:linear-gradient(0deg,
   rgba(10,10,10,.96) 0%,rgba(10,10,10,.55) 45%,rgba(10,10,10,.35) 100%)}}
.velo-suave{{background:rgba(10,10,10,.62)}}

/* ── bullets ────────────────────────────────────────────────── */
.puntos{{list-style:none;margin-top:40px;display:flex;flex-direction:column;gap:22px}}
.puntos li{{position:relative;padding-left:38px;font-size:26px;line-height:1.45;
   font-weight:300;color:#D0D0D0}}
.puntos li::before{{content:'';position:absolute;left:0;top:15px;width:15px;height:15px;
   border:2.4px solid {ac};border-radius:50%}}

/* ── datos grandes ──────────────────────────────────────────── */
/* Grilla y no flex: con flex, un "+4.000" al lado de un "7" descalabra el
   ritmo de las columnas. En grilla todas miden lo mismo pase lo que pase. */
.datos{{display:grid;gap:56px 40px;margin-top:64px}}
.dato{{min-width:0}}
.dato .n{{font-family:'Archivo',sans-serif;font-weight:800;font-size:112px;line-height:.9;
   letter-spacing:-.045em;color:{ac}}}
.dato .t{{margin-top:16px;font-family:'BarlowC',sans-serif;font-size:21px;
   letter-spacing:.24em;text-transform:uppercase;color:#9A9A9A;max-width:13ch;line-height:1.4}}

/* ── tabla ──────────────────────────────────────────────────── */
.tabla{{margin-top:48px;width:100%;border-collapse:collapse}}
.tabla td{{padding:22px 0;border-bottom:1px solid #262626;font-size:25px;
   font-weight:300;color:#D0D0D0;vertical-align:top}}
.tabla td:first-child{{font-family:'BarlowC',sans-serif;font-size:21px;letter-spacing:.2em;
   text-transform:uppercase;color:{ac};width:32%;padding-right:36px}}

.esq{{position:absolute;top:0;right:0}}
.aros-bg{{position:absolute;right:-60px;bottom:-110px;opacity:.13}}
"""


# ── slides ────────────────────────────────────────────────────────────────

def _cuerpo_portada(titulo: str) -> int:
    """Cuánto mide el titular de portada según cuánto texto trae.

    A 132px sólo entran dos líneas cortas. Un titular de seis palabras se
    parte en cuatro y se come el logo de arriba y el pie de abajo. En vez de
    dejar que el texto decida por desborde, se decide acá.
    """
    n = len(titulo)
    if n <= 16:
        return 132
    if n <= 28:
        return 104
    if n <= 44:
        return 82
    return 66


def _portada(s, ac, meta):
    fondo = ""
    if s.get("foto"):
        fondo = (f'<div class="foto" style="background-image:url({s["foto"]});'
                 f'background-position:{s.get("foco", "50% 40%")}"></div>'
                 f'<div class="velo velo-izq"></div>')
    cuerpo = _cuerpo_portada(s["titulo"])
    return f"""<div class="slide">{fondo}
  <div class="pad">
    <div style="flex:0 0 auto">{logo(1.35, C['blanco'], 'left')}</div>
    <div style="margin-top:auto;max-width:62%">
      <div class="kicker" style="margin-bottom:24px;white-space:nowrap">{s.get('kicker', 'Boss Padel')}</div>
      <div class="h1" style="font-size:{cuerpo}px">{s['titulo']}</div>
      {f'<div class="lead" style="margin-top:30px;font-size:27px;max-width:30ch">{s["bajada"]}</div>' if s.get('bajada') else ''}
    </div>
    <div style="height:26px;flex:0 0 auto"></div>
  </div>
  <div class="pie"><span>{meta.get('pie', 'bosspadel.uy')}</span><span>{meta.get('fecha', '')}</span></div>
</div>"""


def _seccion(s, ac, meta):
    return f"""<div class="slide">
  <div class="aros-bg">{aros(340, ACENTOS.get(ac, C['lima']), 3.2, 4)}</div>
  <div class="pad" style="justify-content:center">
    <div class="kicker" style="margin-bottom:30px">{s.get('kicker', '')}</div>
    <div class="h2" style="max-width:17ch">{s['titulo']}</div>
    {f'<div class="lead" style="margin-top:36px;max-width:34ch">{s["bajada"]}</div>' if s.get('bajada') else ''}
  </div>
  <div class="pie"><span>{meta.get('pie', 'bosspadel.uy')}</span><span class="num">{s.get('_n', '')}</span></div>
</div>"""


def _contenido(s, ac, meta):
    puntos = ""
    if s.get("puntos"):
        items = "".join(f"<li>{p}</li>" for p in s["puntos"])
        puntos = f'<ul class="puntos">{items}</ul>'
    texto = f'<div class="body" style="margin-top:30px;max-width:44ch">{s["texto"]}</div>' if s.get("texto") else ""
    lado = ""
    if s.get("foto"):
        # El degradé va ENCIMA del borde izquierdo de la foto, no al lado:
        # así el corte entre texto y foto se difumina en vez de ser un filo.
        lado = (f'<div style="position:absolute;right:0;top:0;bottom:0;width:42%;'
                f'background-image:url({s["foto"]});background-size:cover;'
                f'background-position:{s.get("foco", "50% 40%")}"></div>'
                f'<div style="position:absolute;right:42%;top:0;bottom:0;width:190px;'
                f'transform:translateX(190px);'
                f'background:linear-gradient(90deg,{C["negro"]} 0%,rgba(10,10,10,.75) 45%,'
                f'rgba(10,10,10,0) 100%)"></div>')
    ancho = "max-width:50%" if s.get("foto") else "max-width:78%"
    return f"""<div class="slide">{lado}
  <div class="pad">
    <div style="{ancho}">
      <div class="kicker" style="margin-bottom:22px">{s.get('kicker', '')}</div>
      <div class="h3">{s['titulo']}</div>
      {texto}{puntos}
    </div>
  </div>
  <div class="pie"><span>{meta.get('pie', 'bosspadel.uy')}</span><span class="num">{s.get('_n', '')}</span></div>
</div>"""


def _datos(s, ac, meta):
    datos = s["datos"]
    cols = min(4, len(datos)) or 1
    ancho_col = (1600 - 208 - 40 * (cols - 1)) / cols
    largo = max(len(str(n)) for n, _ in datos)
    # Archivo 800 mide ~0.62 em por dígito. Se calcula el cuerpo que hace
    # entrar la cifra más larga en su columna, con tope de 112.
    cuerpo = int(min(112, ancho_col / (largo * 0.62)))
    if len(datos) > 4:
        cuerpo = min(cuerpo, 84)
    celdas = "".join(
        f'<div class="dato"><div class="n" style="font-size:{cuerpo}px">{n}</div>'
        f'<div class="t">{t}</div></div>' for n, t in datos)
    return f"""<div class="slide">
  <div class="aros-bg">{aros(300, C['blanco'], 2.6, 4)}</div>
  <div class="pad" style="justify-content:center">
    <div class="kicker" style="margin-bottom:22px">{s.get('kicker', '')}</div>
    <div class="h3" style="max-width:24ch">{s['titulo']}</div>
    <div class="datos" style="grid-template-columns:repeat({cols},1fr)">{celdas}</div>
  </div>
  <div class="pie"><span>{meta.get('pie', 'bosspadel.uy')}</span><span class="num">{s.get('_n', '')}</span></div>
</div>"""


def _tabla(s, ac, meta):
    filas = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in s["filas"])
    return f"""<div class="slide">
  <div class="pad">
    <div class="kicker" style="margin-bottom:22px">{s.get('kicker', '')}</div>
    <div class="h3" style="max-width:26ch">{s['titulo']}</div>
    <table class="tabla">{filas}</table>
  </div>
  <div class="pie"><span>{meta.get('pie', 'bosspadel.uy')}</span><span class="num">{s.get('_n', '')}</span></div>
</div>"""


def _foto(s, ac, meta):
    return f"""<div class="slide">
  <div class="foto" style="background-image:url({s['foto']});
       background-position:{s.get('foco', '50% 40%')}"></div>
  <div class="velo velo-full"></div>
  <div class="pad" style="justify-content:flex-end">
    <div style="max-width:56%">
      <div class="kicker" style="margin-bottom:20px">{s.get('kicker', '')}</div>
      <div class="h2" style="font-size:58px;max-width:18ch">{s['titulo']}</div>
      {f'<div class="lead" style="margin-top:22px;font-size:26px;max-width:46ch">{s["bajada"]}</div>' if s.get('bajada') else ''}
    </div>
  </div>
  <div class="pie"><span>{meta.get('pie', 'bosspadel.uy')}</span><span class="num">{s.get('_n', '')}</span></div>
</div>"""


def _cierre(s, ac, meta):
    lineas = "".join(f'<div style="margin-top:14px">{l}</div>' for l in s.get("lineas", []))
    fondo = ""
    if s.get("foto"):
        fondo = (f'<div class="foto" style="background-image:url({s["foto"]});'
                 f'background-position:{s.get("foco", "50% 40%")}"></div>'
                 f'<div class="velo velo-suave"></div>')
    return f"""<div class="slide">{fondo}
  <div class="pad" style="justify-content:center;align-items:center;text-align:center">
    <div style="margin-bottom:54px">{logo(1.6, C['blanco'], 'center')}</div>
    <div class="h2" style="font-size:70px;max-width:20ch">{s.get('titulo', 'Hablemos')}</div>
    <div class="body" style="margin-top:34px;color:#D8D8D8">{lineas}</div>
  </div>
</div>"""


TIPOS = {"portada": _portada, "seccion": _seccion, "contenido": _contenido,
         "datos": _datos, "tabla": _tabla, "foto": _foto, "cierre": _cierre}


def deck(d: dict) -> str:
    """Arma el HTML completo de la presentación."""
    ac = d.get("acento", "lima")
    meta = {"pie": d.get("pie", "bosspadel.uy · @boss.padel"), "fecha": d.get("fecha", "")}
    partes = []
    n = 0
    for s in d["slides"]:
        tipo = s.get("tipo", "contenido")
        if tipo not in ("portada", "cierre"):
            n += 1
            s = {**s, "_n": f"{n:02d}"}
        partes.append(TIPOS[tipo](s, ac, meta))
    return (f'<!doctype html><html><head><meta charset="utf-8">'
            f'<style>{_css(ac)}</style></head><body>{"".join(partes)}</body></html>')
