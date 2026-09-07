# -*- coding: utf-8 -*-
"""Plantillas de Clínica Preventiva. Cada función devuelve el HTML completo.

Las tres primeras —`lateral`, `sangre` y `recorte`— no se inventaron: son las
tres que la cuenta viene publicando, reconstruidas mirando las piezas reales.

Hay una regla que atraviesa todo el sistema y es la firma de esta marca:
**el titular se parte en dos colores.** La primera parte va en gris o tinta y
la palabra que importa va en rojo.

    MÁS CERCA TUYO  →  CIUDAD DE LA COSTA
    ¿Te toca el carné de salud? Ahora incluye un test de  →  hepatitis C.

Por eso casi todas las plantillas toman `titulo` y `destacado` por separado en
vez de un solo campo con HTML adentro: si fuera un campo suelto, tarde o
temprano sale una pieza con el titular entero de un color y deja de parecer de
esta marca.
"""
import pathlib as _pl
import sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[3]))

from brand import (C, FONT_CSS, LOGO_CSS, logo, puntos, pastilla, sello,
                   ICONO_WA, ICONO_WEB, ICONO_TEL)
from motor import legibilidad

TEL = "092 566 967"
WEB = "www.clinicapreventiva.com"

BASE_CSS = FONT_CSS + LOGO_CSS + """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;overflow:hidden;background:#FFFFFF;-webkit-font-smoothing:antialiased}
.canvas{position:relative;width:1080px;overflow:hidden;background:#FFFFFF}
.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 50%}
.scrim{position:absolute;inset:0}
.pad{position:absolute;inset:0;display:flex;flex-direction:column}
.row{display:flex;justify-content:space-between;align-items:flex-start}
.grow{flex:1}
.kicker{font-family:'Mont',sans-serif;font-weight:700;letter-spacing:.12em;text-transform:uppercase}
.disp{font-family:'Mont',sans-serif;font-weight:800;text-transform:uppercase;
  letter-spacing:-.015em;line-height:1.02}
/* Un contenedor con text-transform:none apaga las mayúsculas de .disp adentro:
   la marca usa caja de oración cuando el titular es una pregunta larga. */
[style*="text-transform:none"] .disp{text-transform:none;letter-spacing:-.01em}
.disp-l{font-family:'Mont',sans-serif;font-weight:700;line-height:1.10}
.body{font-family:'Mont',sans-serif;font-weight:400;line-height:1.38}
.cp-puntos{position:absolute}
.precio{font-family:'Mont',sans-serif;font-weight:900;color:#EB3141;letter-spacing:-.02em}
"""


def _cuerpo(texto, base, ancho_car=11.0):
    """Achica el titular cuando es largo.

    El panel de la plantilla `lateral` tiene un ancho fijo y el texto lo escribe
    el pedido: «PSICOTÉCNICO» entra justo y se salía del borde derecho. En vez
    de bajar el cuerpo para todos —que deja las piezas cortas desperdiciando
    espacio— se calcula cuántos caracteres entran en la línea más larga.
    """
    largo = max((len(l) for l in str(texto).split("<br>")), default=0)
    if largo <= ancho_car:
        return base
    return max(int(base * 0.52), int(base * ancho_car / largo))


def _page(h, inner, extra_css=""):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
.canvas{{height:{h}px}} {extra_css}</style></head><body>
<div class="canvas">{inner}</div></body></html>"""


def _pie(claro=True, tel=TEL, web=WEB, alto=86):
    """La barra de contacto. Está en TODAS las piezas y por eso es una función.

    Acá el teléfono va SIEMPRE: es una clínica sin agenda previa, así que el
    número no es un dato de más, es la conversión.

    **Sin negro.** La primera versión usaba una barra casi negra, muestreada de
    una pieza publicada — pero el negro no es un color de esta marca y una barra
    oscura al pie de una pieza clara pesa más que el contenido. Ahora es una
    banda blanca separada por una línea fina, con los rótulos en gris claro y
    los datos en el gris de marca. Los íconos son lo único en rojo, y chicos.

    Y nada en negrita: el peso 500 alcanza para que se lea y no compite con el
    titular, que es lo que tiene que ganar la pieza.
    """
    if not tel and not web:
        return ""
    fondo = C["blanco"] if claro else C["gris_claro"]
    bloques = []
    if tel:
        bloques.append(
            f'<div style="display:flex;align-items:center;gap:12px">'
            f'{ICONO_WA}'
            f'<div><div class="kicker" style="font-size:15px;font-weight:600;'
            f'letter-spacing:.16em;color:#A8A9AB;margin-bottom:2px">WhatsApp</div>'
            f'<div style="font-family:\'Mont\',sans-serif;font-weight:500;'
            f'font-size:29px;color:{C["gris"]};letter-spacing:.01em">{tel}</div>'
            f'</div></div>')
    if web:
        bloques.append(
            f'<div style="display:flex;align-items:center;gap:12px">'
            f'{ICONO_WEB}'
            f'<div><div class="kicker" style="font-size:15px;font-weight:600;'
            f'letter-spacing:.16em;color:#A8A9AB;margin-bottom:2px">Web</div>'
            f'<div style="font-family:\'Mont\',sans-serif;font-weight:500;'
            f'font-size:27px;color:{C["gris"]};letter-spacing:.01em">{web}</div>'
            f'</div></div>')
    # Un separador fino en gris en vez de un bloque de color: divide sin pesar.
    sep = (f'<div style="width:1px;height:38px;background:{C["gris_suave"]}"></div>'
           if len(bloques) == 2 else "")
    return (f'<div style="position:absolute;left:0;right:0;bottom:0;height:{alto}px;'
            f'background:{fondo};border-top:1px solid {C["gris_suave"]};'
            f'display:flex;align-items:center;justify-content:center;'
            f'gap:44px;z-index:5">{bloques[0] if bloques else ""}{sep}'
            f'{bloques[1] if len(bloques) > 1 else ""}</div>')


def _sedes(lista, fmt="post", sobre_foto=False, alineado="left", escala=1.0,
           oscuro=False):
    """El bloque de sedes: dónde estamos y a qué hora abrimos.

    Existe porque no existía. Las direcciones vivían en una sola línea de
    `marca.json` —«Gral. Flores 3131 esq. Bvar. Artigas · L-V 7:00-16:45 · Sáb
    8:00-11:45»— y el agente la pegaba tal cual en un campo de texto. Todo
    quedaba del mismo tamaño y del mismo color: el nombre de la sede, la calle y
    el horario compitiendo entre sí, separados por puntos medios. Nadie lee eso.

    ── Tres niveles, y el orden importa ──────────────────────────────────

    Quien mira la pieza busca las cosas en este orden: **cuál de las dos sedes
    me queda cerca** → **dónde queda** → **si estoy a tiempo de ir hoy**. La
    jerarquía tipográfica sigue ese orden y no el orden de importancia para la
    clínica:

      1. NOMBRE DE SEDE   chico, versalitas espaciadas, en rojo. Es un rótulo,
                          no un titular: su trabajo es dejarte saltar rápido a
                          la columna que te sirve.
      2. la dirección     el nivel dominante. Mont 700, en tinta. Es el dato
                          que la persona va a leer, copiar o buscar en el mapa.
      3. el horario       en gris y más chico, y **en dos líneas**: entre
                          semana y sábado son dos hechos distintos. Puestos en
                          una sola línea con un punto medio en el medio, el
                          ojo los lee como un solo bloque ilegible.

    Los tres niveles se separan por peso, tamaño Y color a la vez. Con una sola
    de esas tres cosas la diferencia no se ve a la distancia de un feed.

    ── Por qué en columnas y no en lista ─────────────────────────────────

    Dos sedes lado a lado se comparan de un vistazo: la línea divisoria dice
    «son dos opciones, elegí». Una debajo de la otra se leen como una secuencia
    y la segunda parece menos importante. En story no entran dos columnas, así
    que ahí sí van apiladas, pero con la divisoria horizontal cumpliendo el
    mismo trabajo.

    `sobre_foto` mete todo en una tarjeta blanca. La marca no tiene ningún
    color propio que dé contraste suficiente sobre una foto —el rojo #EB3141
    mide 1,4:1 sobre una foto clara— así que sobre foto el bloque no se tiñe:
    se apoya sobre blanco.
    """
    if not lista:
        return ""
    e = {"post": 1.0, "vert": 1.12, "story": 1.38, "reel": 1.38}.get(fmt, 1.0) * escala
    apilado = fmt in ("story", "reel") or len(lista) == 1

    # Sobre una foto con velo, el gris y la tinta de marca desaparecen y el rojo
    # del rótulo tampoco llega —es texto CHICO, y ahí el mínimo es 4,5:1, que
    # este rojo no alcanza ni contra negro puro—. En oscuro va todo en blanco y
    # la jerarquía la dan el peso y el tamaño, que es lo que sigue funcionando.
    c_rotulo = "#FFFFFF" if oscuro else C["rojo"]
    c_dir    = "#FFFFFF" if oscuro else C["tinta"]
    c_hora   = "rgba(255,255,255,.80)" if oscuro else C["gris"]
    c_raya   = "rgba(255,255,255,.35)" if oscuro else C["gris_suave"]

    def col(s):
        horas = [h for h in (s.get("horario", ""), s.get("horario2", "")) if h]
        lineas = "".join(
            f'<div class="body" style="font-size:{25*e:.0f}px;color:{c_hora};'
            f'line-height:1.34">{h}</div>' for h in horas)
        return (
            f'<div style="flex:1;text-align:{alineado}">'
            f'<div class="kicker" style="font-size:{20*e:.0f}px;font-weight:700;'
            f'letter-spacing:.15em;color:{c_rotulo};margin-bottom:{9*e:.0f}px">'
            f'{s.get("nombre","")}</div>'
            f'<div class="disp-l" style="font-size:{33*e:.0f}px;color:{c_dir};'
            f'line-height:1.18;margin-bottom:{10*e:.0f}px">{s.get("direccion","")}</div>'
            f'{lineas}</div>')

    cols = [col(s) for s in lista]
    if apilado:
        raya = (f'<div style="height:1px;background:{c_raya};'
                f'margin:{22*e:.0f}px 0"></div>')
        cuerpo = raya.join(cols)
        caja = f'<div style="display:block">{cuerpo}</div>'
    else:
        raya = (f'<div style="width:1px;align-self:stretch;'
                f'background:{c_raya};margin:0 {30*e:.0f}px"></div>')
        caja = (f'<div style="display:flex;align-items:stretch">'
                f'{raya.join(cols)}</div>')

    if sobre_foto:
        return (f'<div style="background:#FFF;padding:{28*e:.0f}px {32*e:.0f}px;'
                f'box-shadow:0 6px 30px rgba(0,0,0,.14)">{caja}</div>')
    return caja


def _titular(titulo, destacado, cuerpo, color=None, color_dest=None):
    """El titular en dos colores — la firma de la marca."""
    color = color or C["tinta"]
    color_dest = color_dest or C["rojo"]
    partes = f'<span style="color:{color}">{titulo}</span>' if titulo else ""
    if destacado:
        if partes:
            partes += "<br>"
        partes += f'<span style="color:{color_dest}">{destacado}</span>'
    return f'<div class="disp" style="font-size:{cuerpo}px">{partes}</div>'


# ───────────────────────────────────────────────────────── 01 FOTO LATERAL
def lateral(d, fmt="post"):
    """Foto a la izquierda, panel blanco a la derecha. La plantilla de servicio.

    Es la que usa la marca cuando hay un precio y una promesa de plazo, que es
    su argumento de venta más repetido. d: kicker, titulo, destacado, texto,
    sello, precio, precio_pie, foto, foco
    """
    h = {"post": 1080, "vert": 1350, "story": 1920, "reel": 1920}[fmt]
    ancho_foto = 0.44 if fmt == "post" else 0.40
    cuerpo = {"post": 76, "vert": 88, "story": 104, "reel": 104}[fmt]
    pie = 86 if fmt in ("post", "vert") else 150
    garantia = (f'<div style="margin-top:22px">{sello(d["sello"])}</div>'
                if d.get("sello") else "")
    precio = ""
    if d.get("precio"):
        precio = (f'<div style="margin-top:26px;display:flex;align-items:baseline;gap:14px">'
                  f'<div class="precio" style="font-size:{int(cuerpo*1.02)}px">{d["precio"]}</div>'
                  f'<div class="body" style="font-size:23px;color:{C["gris"]}">'
                  f'{d.get("precio_pie","IVA incluido")}</div></div>')
    return _page(h, f"""
<div style="position:absolute;left:0;top:0;bottom:{pie}px;width:{ancho_foto*100:.0f}%;overflow:hidden">
  <img src="{d['foto']}" style="width:100%;height:100%;object-fit:cover;
    object-position:{d.get('foco','50% 40%')}">
</div>
<div style="position:absolute;right:0;top:0;bottom:{pie}px;width:{(1-ancho_foto)*100:.0f}%;
  background:{C['blanco']};padding:58px 62px;display:flex;flex-direction:column">
  {logo(1.0)}
  <div class="grow"></div>
  {f'<div style="margin-bottom:20px">{pastilla(d["kicker"])}</div>' if d.get('kicker') else ''}
  {_titular(d.get('titulo',''), '', _cuerpo(d.get('titulo',''), cuerpo))}
  {f'<div style="margin-top:12px;display:inline-block;background:{C["rojo"]};color:#fff;padding:10px 20px"><span class="disp" style="font-size:{_cuerpo(d["destacado"], cuerpo)}px">{d["destacado"]}</span></div>' if d.get('destacado') else ''}
  <div class="body" style="font-size:27px;color:{C['tinta']};margin-top:22px">
    {d.get('texto','')}</div>
  {garantia}{precio}
  <div class="grow"></div>
</div>
{_pie(True, d.get('tel', TEL), d.get('web', WEB), pie)}
""")


def _titular_sobre_foto(titulo, destacado, cuerpo, plan):
    """El titular de dos colores cuando abajo hay una foto y no un fondo liso.

    Es el mismo titular de siempre con una diferencia: la palabra destacada se
    dibuja como TEXTO rojo sólo si `plan` midió que el rojo se lee ahí. Si no,
    se dibuja como bloque rojo con tinta blanca.

    El bloque lleva `box-decoration-break: clone` porque si la frase destacada
    ocupa dos renglones, sin eso el fondo se dibuja como un solo rectángulo que
    envuelve los dos y tapa media foto. Con clone, cada renglón trae su propio
    bloque ajustado al texto.

    Y le saca la sombra de texto: sobre un bloque sólido no hace falta y se ve
    como suciedad en el borde.
    """
    partes = f'<span style="color:#FFFFFF">{titulo}</span>' if titulo else ""
    if destacado:
        if partes:
            partes += "<br>"
        if plan.get("modo") == "bloque":
            partes += (
                f'<span style="background:{C["rojo"]};color:{plan.get("tinta","#FFFFFF")};'
                f'padding:.06em .20em .12em;'
                f'-webkit-box-decoration-break:clone;box-decoration-break:clone;'
                f'text-shadow:none;line-height:1.30">{destacado}</span>')
        else:
            partes += f'<span style="color:{C["rojo"]}">{destacado}</span>'
    return f'<div class="disp" style="font-size:{cuerpo}px">{partes}</div>'


# ────────────────────────────────────────────────────────── 02 FOTO A SANGRE
def sangre(d, fmt="post"):
    """Foto ocupando todo, titular abajo sobre el degradé.

    Para noticias y novedades: cuando lo que importa es el ambiente —la sala de
    espera, el equipo, la sede— y no un precio. d: kicker, titulo, destacado,
    texto, foto, foco
    """
    h = {"post": 1080, "vert": 1350, "story": 1920, "reel": 1920}[fmt]
    cuerpo = {"post": 58, "vert": 66, "story": 78, "reel": 78}[fmt]
    pie = 96 if fmt in ("post", "vert") else 160
    top = 60 if fmt in ("post", "vert") else 190

    # ── Dónde cae el titular ──────────────────────────────────────────────
    # No es siempre el mismo lugar, y eso importa: el velo y la decisión de
    # cómo dibujar el acento se calculan midiendo la foto EN ESA FRANJA. Con la
    # tarjeta de sedes abajo, el titular sube casi diez puntos.
    zona = (0.44, 0.68) if d.get("sedes") else (0.55, 0.94)

    # El velo NO es un número fijo. Se mide la foto en la franja donde va a caer
    # el titular y se calcula el mínimo que hace falta. Un valor fijo calibrado
    # con una foto oscura deja ilegible una foto clara —una sala de espera
    # blanca, por ejemplo— y sobre una oscura tapa de más.
    #
    # ── Y el rojo no siempre se puede leer, por mucho velo que se ponga ────
    #
    # Medido sobre la pieza «Te esperamos en nuestras dos sedes» publicada el
    # 4/8: el rojo dio **2,19:1** donde el mínimo para texto grande es 3,0. El
    # techo teórico de este rojo es 5,05:1 contra negro PURO — para llegar a 3
    # sobre una foto hay que taparla tanto que ya no vale la pena la foto.
    #
    # `plan_titular` decide eso midiendo, y cuando el acento no llega devuelve
    # `bloque`: la palabra destacada pasa de ser tinta roja a ser un bloque
    # rojo con tinta blanca. Da 4,16:1 pase lo que pase debajo, porque deja de
    # depender de la foto. La firma de la marca se conserva: la palabra que
    # importa sigue siendo la roja.
    plan = legibilidad.plan_titular(
        _pl.Path(__file__).resolve().parent / d["foto"],
        acento=C["rojo"], oscuro=C["tinta"], zona=zona,
        objetivo_blanco=4.5, objetivo_acento=3.0)
    # El degradé tiene que entregar el velo completo DONDE ARRANCA el texto, no
    # al 80% fijo de la altura: ése era justamente el error que dejaba el rojo
    # en 2,19 cuando la cuenta prometía 3,8.
    velo = legibilidad.degrade(plan["velo"], tope=zona[0])
    return _page(h, f"""
<img class="bg" src="{d['foto']}" style="object-position:{d.get('foco','50% 40%')}">
<div style="position:absolute;left:0;right:0;top:0;height:10px;background:{C['rojo']};z-index:4"></div>
<div class="scrim" style="background:{velo}"></div>
<div class="pad" style="padding:{top}px 60px {pie if d.get('sedes') else pie+38}px;z-index:2">
  {logo(1.15, "#FFFFFF", "center")}
  <div class="grow"></div>
  {f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px"><div style="width:5px;height:24px;background:{C["rojo"]};flex:none"></div><div class="kicker" style="color:#FFFFFF;font-size:26px">{d["kicker"]}</div></div>' if d.get('kicker') else ''}
  <div style="text-transform:none;text-shadow:0 2px 14px rgba(0,0,0,.75)">
    {_titular_sobre_foto(d.get('titulo',''), d.get('destacado',''), cuerpo, plan)}</div>
  {f'''<div class="body" style="font-size:27px;color:rgba(255,255,255,.90);margin-top:18px;
    max-width:840px">{d['texto']}</div>''' if d.get('texto') else ''}
  {f'<div style="margin-top:26px">{_sedes(d["sedes"], fmt, sobre_foto=True)}</div>' if d.get('sedes') else ''}
</div>
{_pie(True, d.get('tel', TEL), d.get('web', WEB), pie)}
""")


# ──────────────────────────────────────────────────────── 03 RECORTE CLARO
def recorte(d, fmt="post"):
    """Persona recortada sobre fondo gris claro, titular a la derecha.

    La más limpia de las tres y la que mejor tolera un texto largo. Las fichas
    blancas con sombra son para los datos duros: horarios, servicios, dirección.
    d: titulo, destacado, foto, foco, fichas[[rótulo, valor]], pie1, pie2
    """
    h = {"post": 1080, "vert": 1350, "story": 1920, "reel": 1920}[fmt]
    cuerpo = {"post": 62, "vert": 72, "story": 84, "reel": 84}[fmt]
    fichas = ""
    for rot, val in d.get("fichas", []):
        fichas += (f'<div style="background:#FFF;box-shadow:0 4px 22px rgba(0,0,0,.10);'
                   f'padding:18px 26px;margin-top:13px;text-align:right;display:inline-block;min-width:290px">'
                   f'<div class="body" style="font-size:24px;color:{C["gris"]}">{rot}</div>'
                   f'<div class="disp-l" style="font-size:29px;color:{C["tinta"]}">{val}</div></div>')
    return _page(h, f"""
<div class="scrim" style="background:{C['gris_claro']}"></div>
<div style="position:absolute;left:44px;top:44px;opacity:.30">{puntos(190, 190)}</div>
<div style="position:absolute;right:-24px;top:{int(h*0.30)}px;opacity:.20">{puntos(240, 220)}</div>
<div style="position:absolute;left:0;bottom:0;top:{int(h*0.155)}px;width:50%;overflow:hidden">
  <img src="{d['foto']}" style="width:100%;height:100%;object-fit:cover;
    object-position:{d.get('foco','50% 20%')}">
</div>
<div class="pad" style="padding:52px 58px 58px;z-index:3">
  {logo(1.05, None, "center")}
  <div style="margin-top:{int(h*0.055)}px;margin-left:47%;text-align:right">
    {_titular(d.get('titulo',''), d.get('destacado',''), cuerpo, C['gris'], C['rojo'])}
    {fichas}
    {f'<div style="margin-top:30px">{_sedes(d["sedes"], fmt, alineado="right")}</div>' if d.get('sedes') else ''}
  </div>
  <div class="grow"></div>
  <div style="text-align:right">
    <div class="body" style="font-size:25px;color:{C['gris']}">{d.get('pie1','')}</div>
    <div class="disp-l" style="font-size:30px;color:{C['tinta']}">{d.get('pie2','')}</div>
  </div>
</div>
""")


# ──────────────────────────────────────────────────────────── 04 TIPOGRÁFICA
def tipografica(d, fmt="post"):
    """Sólo texto sobre blanco, con la trama de puntos y una barra roja.

    Para avisos, cambios de horario y datos de salud pública, donde una foto de
    banco no aporta nada y encima ensucia. d: kicker, titulo, destacado, texto
    """
    h = {"post": 1080, "vert": 1350, "story": 1920, "reel": 1920}[fmt]
    cuerpo = {"post": 74, "vert": 86, "story": 100, "reel": 100}[fmt]
    pie = 86 if fmt in ("post", "vert") else 150
    return _page(h, f"""
<div class="scrim" style="background:{C['blanco']}"></div>
<div style="position:absolute;right:-40px;top:-40px;opacity:.26">{puntos(360, 300)}</div>
<div style="position:absolute;left:56px;bottom:{pie+40}px;opacity:.20">{puntos(200, 160)}</div>
<div style="position:absolute;left:0;top:0;bottom:0;width:14px;background:{C['rojo']}"></div>
<div class="pad" style="padding:58px 66px {pie+50}px 74px;z-index:2">
  {logo(1.05)}
  <div class="grow"></div>
  {f'<div style="margin-bottom:22px">{pastilla(d["kicker"])}</div>' if d.get('kicker') else ''}
  {_titular(d.get('titulo',''), d.get('destacado',''), cuerpo)}
  {f'''<div class="body" style="font-size:29px;color:{C['tinta']};margin-top:24px;max-width:830px">
    {d['texto']}</div>''' if d.get('texto') else ''}
  {f'<div style="margin-top:38px;max-width:900px">{_sedes(d["sedes"], fmt)}</div>' if d.get('sedes') else ''}
  <div class="grow"></div>
</div>
{_pie(True, d.get('tel', TEL), d.get('web', WEB), pie)}
""")


# ────────────────────────────────────────────────────────────── 05 CONVENIO
def _ruta_foto(foto: str) -> str:
    """La ruta absoluta, que es lo que necesita PIL para medir el brillo.

    En el spec las rutas son relativas a la carpeta de la marca —así las
    resuelve Chromium al abrir el HTML—, pero medir el velo pide abrir el
    archivo de verdad.
    """
    r = _pl.Path(foto)
    return str(r if r.is_absolute() else _pl.Path(__file__).parent / r)


def convenio(d, fmt="post"):
    """El cupón de un acuerdo con una empresa: dos marcas, un precio, un canje.

    d: empresa, logo_socio, servicio, condicion, precio, precio_pie,
       tel, whatsapp, sedes, sello, foto, foco

    ── El logo del socio ─────────────────────────────────────────────────

    Es la única plantilla donde **entra una marca que no es la nuestra**, y eso
    cambia las reglas. El logo llega como archivo subido, así que no se sabe
    nada de él: puede ser apaisado o cuadrado, con fondo transparente o blanco.

    Por eso no se dibuja, se **encaja**: va adentro de una caja de medida fija
    con `object-fit: contain`, que lo achica hasta que entre sin deformarlo
    jamás. Un logo estirado es la forma más rápida de que la empresa con la que
    firmaste el convenio no quiera volver a firmar.

    Sobre foto el nuestro va en blanco, y el del socio en una tarjeta blanca:
    es la única forma de garantizar que se vea sin saber de qué color es.

    ── La foto va de fondo, a sangre ─────────────────────────────────────

    Como en el resto de las piezas de la marca. Se intentaron antes dos cosas
    que NO funcionan y conviene no repetir:

      · **La foto detrás del texto sin velo medido.** Es lo que hacía la pieza
        de referencia: el médico recortado tapaba media frase.
      · **La foto en una banda aparte.** Se lee bien, pero no es lo que la
        marca hace en ninguna otra plantilla y se nota como un parche.

    Acá la foto ocupa todo y el velo se **mide**: `velo_necesario` calcula la
    opacidad mínima para que el texto BLANCO llegue a 4,6:1 sobre esa foto en
    particular. Una recepción clara pide mucho velo; una foto nocturna, casi
    nada. Un valor fijo se rompe con la primera foto que no se parezca a la que
    se usó para calibrarlo.

    Y el texto pasa entero a blanco, incluido el rótulo de las sedes: acá el
    rojo de la marca es texto CHICO, y para texto chico el mínimo es 4,5:1, que
    este rojo no alcanza ni contra negro puro. Lo único que sigue siendo rojo
    es el precio, porque va adentro de una pastilla sólida: ahí el contraste es
    blanco sobre rojo, 4,16:1 pase lo que pase debajo.
    """
    h = {"post": 1080, "vert": 1350, "story": 1920, "reel": 1920}[fmt]
    ac = C.get(d.get("acento", "rojo"), C["rojo"])
    hay_foto = bool(d.get("foto"))

    # Con foto entra un poco menos de texto: la columna se dibuja algo más
    # chica. Es una sola palanca en vez de recortar elementos de a uno.
    escala = 0.92 if hay_foto else 1.0
    e = {"post": 1.0, "vert": 1.14, "story": 1.42, "reel": 1.42}[fmt] * escala
    e_marco = {"post": 1.0, "vert": 1.14, "story": 1.42, "reel": 1.42}[fmt]

    tinta = "#FFFFFF" if hay_foto else C["tinta"]
    suave = "rgba(255,255,255,.85)" if hay_foto else C["gris"]
    c_kicker = "#FFFFFF" if hay_foto else ac
    bar_fondo = "rgba(255,255,255,.96)" if hay_foto else C["gris"]
    bar_tinta = C["tinta"] if hay_foto else "#FFFFFF"

    # ── El fondo ─────────────────────────────────────────────────────────
    fondo = f'<div class="scrim" style="background:{C["blanco"]}"></div>'
    if hay_foto:
        # Objetivo 7,0 y percentil 95, mucho más exigente que en el resto de las
        # plantillas. El motivo: acá NO hay un titular grande y tres palabras
        # sueltas — hay teléfonos, horarios y direcciones, todo texto CHICO,
        # que pide 4,5:1 y encima repartido por toda la pieza. Medido con el
        # objetivo 4,6 habitual, la mitad de esas zonas quedaba en 3,6:1.
        #
        # Y el percentil 95 y no el 75: una foto oscura con un sujeto CLARO en
        # el medio —una túnica blanca, una cara iluminada— tiene una mediana
        # baja y un centro brillante justo donde cae el texto. Medido: al 88 el
        # velo daba 0,00 y la condición quedaba en 2,05:1.
        #
        # Sí, oscurece bastante la foto. Es el precio de poner un cupón entero
        # encima de una imagen, y un cupón que no se lee no sirve de nada.
        alfa = legibilidad.velo_necesario(
            _ruta_foto(d["foto"]), color_texto="#FFFFFF", objetivo=7.0,
            zona=(0.0, 1.0), maximo=0.90, percentil=95)
        fondo = (f'<img class="bg" src="{d["foto"]}" '
                 f'style="object-position:{d.get("foco", "50% 40%")}">'
                 f'<div class="scrim" style="background:rgba(0,0,0,{alfa:.2f})"></div>')

    # ── Las dos marcas ───────────────────────────────────────────────────
    socio = ""
    if d.get("logo_socio"):
        caja = f'background:#FFFFFF;padding:{12*e:.0f}px {18*e:.0f}px;' if hay_foto else ""
        raya = "rgba(255,255,255,.45)" if hay_foto else C["gris_suave"]
        socio = (f'<div style="width:1px;height:{62*e:.0f}px;background:{raya}"></div>'
                 f'<div style="{caja}height:{74*e:.0f}px;max-width:{330*e:.0f}px;'
                 f'display:flex;align-items:center">'
                 f'<img src="{d["logo_socio"]}" alt="{d.get("empresa","")}" '
                 f'style="max-height:100%;max-width:100%;width:auto;height:auto;'
                 f'object-fit:contain;display:block"></div>')
    marcas = (f'<div style="display:flex;align-items:center;justify-content:center;'
              f'gap:{34*e:.0f}px">'
              f'{logo(1.15*e, "#FFFFFF" if hay_foto else None, "center")}{socio}</div>')

    # ── El precio, que es lo que la persona vino a ver ───────────────────
    precio = ""
    if d.get("precio"):
        # Sobre foto la pastilla va RELLENA: un contorno fino sobre una imagen
        # se pierde, y el relleno da blanco sobre rojo, que es 4,16:1 fijo.
        if hay_foto:
            precio = (f'<div style="display:inline-block;background:{ac};'
                      f'border-radius:999px;padding:{18*e:.0f}px {58*e:.0f}px {22*e:.0f}px">'
                      f'<span class="precio" style="font-size:{92*e:.0f}px;'
                      f'line-height:1;color:#FFFFFF">{d["precio"]}</span></div>')
        else:
            precio = (f'<div style="display:inline-block;border:{4*e:.0f}px solid {ac};'
                      f'border-radius:999px;padding:{16*e:.0f}px {58*e:.0f}px {20*e:.0f}px">'
                      f'<span class="precio" style="font-size:{92*e:.0f}px;'
                      f'line-height:1;color:{ac}">{d["precio"]}</span></div>')

    pie_precio = ""
    if d.get("precio_pie"):
        pie_precio = (f'<div style="font-family:\'Mont\',sans-serif;font-weight:700;'
                      f'font-size:{22*e:.0f}px;color:{c_kicker};'
                      f'margin-top:{12*e:.0f}px">{d["precio_pie"]}</div>')

    condicion = ""
    if d.get("condicion"):
        condicion = (f'<div class="body" style="font-size:{29*e:.0f}px;color:{suave};'
                     f'margin-top:{26*e:.0f}px;max-width:28ch">{d["condicion"]}</div>')

    contacto = ""
    filas = [(ICONO_TEL, d["tel"])] if d.get("tel") else []
    if d.get("whatsapp"):
        filas.append((ICONO_WA, d["whatsapp"]))
    if filas:
        items = "".join(
            f'<div style="display:flex;align-items:center;gap:{13*e:.0f}px">'
            f'<span style="display:flex;transform:scale({1.25*e:.2f})">'
            f'{ico.replace(C["rojo"], "#FFFFFF") if hay_foto else ico}</span>'
            f'<span style="font-family:\'Mont\',sans-serif;font-weight:800;'
            f'font-size:{40*e:.0f}px;color:{tinta};letter-spacing:-.01em">'
            f'{txt}</span></div>' for ico, txt in filas)
        contacto = (f'<div style="display:flex;justify-content:center;'
                    f'gap:{54*e:.0f}px;margin-top:{18*e:.0f}px">{items}</div>')

    marca_sello = ""
    if d.get("sello"):
        if hay_foto:
            t = str(d["sello"]).lstrip("✓✔✅ ").strip()
            marca_sello = (
                f'<div style="margin-top:{22*e:.0f}px;display:inline-flex;'
                f'align-items:center;gap:{9*e:.0f}px;border:1.5px solid '
                f'rgba(255,255,255,.55);border-radius:999px;'
                f'padding:{9*e:.0f}px {20*e:.0f}px">'
                f'<span style="color:#FFFFFF;font-size:{22*e:.0f}px;'
                f'font-weight:700;line-height:1">✓</span>'
                f'<span style="font-family:\'Mont\',sans-serif;font-weight:500;'
                f'font-size:{22*e:.0f}px;color:#FFFFFF">{t}</span></div>')
        else:
            marca_sello = f'<div style="margin-top:{24*e:.0f}px">{sello(d["sello"])}</div>'

    bloque_sedes = ""
    if d.get("sedes"):
        bloque_sedes = (
            f'<div style="margin-top:{30*e:.0f}px;width:100%">'
            f'{_sedes(d["sedes"], fmt, alineado="center", escala=escala, oscuro=hay_foto)}'
            f'</div>')

    trama = ""
    if not hay_foto:
        trama = (f'<div style="position:absolute;right:-30px;top:{int(h*0.10)}px;opacity:.55">'
                 f'{puntos(int(210*e), int(150*e), C["gris_suave"])}</div>'
                 f'<div style="position:absolute;left:-24px;bottom:{int(h*0.03)}px;opacity:.45">'
                 f'{puntos(int(180*e), int(200*e), C["gris_suave"])}</div>')

    servicio = ""
    if d.get("servicio"):
        servicio = (f'<div style="background:{bar_fondo};color:{bar_tinta};'
                    f'padding:{15*e:.0f}px {34*e:.0f}px;font-family:\'Mont\',sans-serif;'
                    f'font-weight:800;font-size:{40*e:.0f}px;letter-spacing:-.01em;'
                    f'text-transform:uppercase;line-height:1.12;max-width:94%">'
                    f'{d["servicio"]}</div>')

    return _page(h, f"""
{fondo}
{trama}
<div style="position:absolute;left:0;top:0;bottom:0;width:{12*e_marco:.0f}px;background:{ac};z-index:6"></div>

<div class="pad" style="padding:{54*e_marco:.0f}px {62*e_marco:.0f}px {44*e_marco:.0f}px;
     z-index:2;align-items:center;text-align:center">
  {marcas}
  <div class="grow"></div>
  <div class="kicker" style="font-size:{26*e:.0f}px;letter-spacing:.30em;
       color:{c_kicker};margin-bottom:{16*e:.0f}px">{d.get('titulo', 'Convenio')}</div>
  {servicio}
  {condicion}
  <div style="margin-top:{26*e:.0f}px">{precio}</div>
  {pie_precio}
  {contacto}
  {marca_sello}
  {bloque_sedes}
  <div class="grow"></div>
</div>
""")


PLANTILLAS = {
    "lateral": lateral,
    "sangre": sangre,
    "recorte": recorte,
    "tipografica": tipografica,
    "convenio": convenio,
}
