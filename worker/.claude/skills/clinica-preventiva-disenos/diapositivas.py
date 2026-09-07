# -*- coding: utf-8 -*-
"""Cómo se ve cada diapositiva de un carrusel de Clínica Preventiva.

La estructura —numeración, proporción única, índice, flechas, zonas seguras de
story, caja de respuesta— la pone `motor.carrusel` y es la misma para todas las
marcas. Acá va sólo el cuerpo de cada diapositiva.

Una diferencia importante con la otra marca del sistema: **acá el fondo por
defecto es blanco, no negro.** El helper `fondo()` del motor asume oscuro,
así que estas funciones no lo usan y dibujan su propio fondo claro. Cuando hay
foto a sangre sí hace falta oscurecerla, porque el titular va en blanco encima.
"""
import pathlib as _pl

from brand import C, logo, puntos, pastilla
from motor import legibilidad
LADO, ARRIBA = 62, 56

from motor.carrusel import SQ_TOP, SQ_BOT


def _pad(h: int, extra: int = 0) -> str:
    """El relleno de la diapositiva, según dónde se va a ver.

    En un carrusel de feed no hay nada encima de la pieza. En una **story**,
    Instagram dibuja arriba el nombre de la cuenta y abajo la caja de responder:
    lo que caiga ahí queda tapado. Hasta el 3/8/2026 sólo `cuadro` reservaba
    esas franjas, porque era la única diapositiva que llegaba a una secuencia.
    Ahora cualquiera puede, y cualquiera las necesita.
    """
    if h >= 1900:
        return f"{SQ_TOP}px {LADO}px {SQ_BOT + extra}px"
    return f"{ARRIBA}px {LADO}px {134 + extra}px"


def _ruta(foto: str) -> str:
    """La foto tal como la ve el disco.

    En el spec las rutas son relativas a la carpeta de la marca —así las
    resuelve Chromium al abrir el HTML—. Para MEDIR el brillo hay que abrir el
    archivo, y eso necesita la ruta completa.
    """
    if not foto:
        return ""
    r = _pl.Path(foto)
    return str(r if r.is_absolute() else _pl.Path(__file__).parent / r)


def _plan(d, zona=(0.42, 0.78)):
    """Qué velo lleva la foto y si el rojo aguanta como texto encima.

    Ver el bloque largo de `motor/legibilidad.py`. En resumen: el rojo de esta
    marca es de luminancia media y contra una túnica blanca da 1,02:1 —la
    palabra desaparece—. Cuando no llega, se dibuja en bloque.
    """
    return legibilidad.plan_titular(_ruta(d.get("foto")), _ac_hex(d),
                                    oscuro=C["tinta"], zona=zona)


def _ac_hex(d):
    return C.get(d.get("acento", "rojo"), C["rojo"])


def _titular(titulo: str, destacado: str, fs: int, tinta: str, ac: str,
             plan: dict) -> str:
    """El titular de dos colores, con la palabra destacada en texto o en bloque.

    `box-decoration-break:clone` es lo que hace que el bloque se dibuje bien
    cuando la palabra destacada ocupa dos renglones: sin eso, el fondo sale
    como una sola caja que se come el interlineado.
    """
    if not destacado:
        return (f'<div class="disp" style="color:{tinta};font-size:{fs}px">'
                f'{titulo}</div>')

    if plan.get("modo") == "bloque":
        dest = (f'<span style="background:{ac};color:{plan.get("tinta","#FFFFFF")};'
                f'padding:.02em .16em .08em;box-decoration-break:clone;'
                f'-webkit-box-decoration-break:clone;line-height:1.24">'
                f'{destacado}</span>')
    else:
        dest = f'<span style="color:{ac}">{destacado}</span>'
    return (f'<div class="disp" style="color:{tinta};font-size:{fs}px">'
            f'{titulo}<br>{dest}</div>')


def _cuerpo_fs(h: int) -> int:
    """El tamaño del texto de apoyo, proporcional al alto de la pieza.

    Estaba fijo en 29-33px para TODOS los formatos. En una story de 1920 eso es
    el 1,7% del alto: al lado de un titular de 104px queda como una nota al pie,
    y encima cae en la franja donde Instagram dibuja la caja de respuesta.
    Medido contra una pieza real: el titular era 3,2 veces el cuerpo. En una
    story el cuerpo es el que trae la información — el titular sólo frena el
    dedo.
    """
    return int(h * 0.0225)          # story 43px · vertical 30px


def _titulo_fs(h: int, texto: str, forzado=None) -> int:
    """El titular se achica solo según su largo.

    Sin esto, un titular largo empuja el cuerpo hacia abajo y aparece el hueco
    blanco gigante que hacía ver la pieza vacía.
    """
    if forzado:
        return int(forzado)
    n = len(texto)
    return int(h * (0.058 if n <= 26 else 0.048 if n <= 48 else 0.040))


def _apoyo(texto: str, h: int, tinta: str, ac: str) -> str:
    """El texto de apoyo, pegado al titular y no descolgado abajo.

    La barrita roja no es decoración: es lo que dice «esto sigue al titular».
    Sin ella, y con 600px de blanco en el medio, el ojo lee dos piezas
    distintas y la frase se parte por la mitad.
    """
    if not (texto or "").strip():
        return ""
    return (f'<div style="width:64px;height:5px;background:{ac};margin:30px 0 24px"></div>'
            f'<div class="body" style="font-size:{_cuerpo_fs(h)}px;color:{tinta};'
            f'opacity:.88;max-width:880px;line-height:1.45;font-weight:500">{texto}</div>')


def _foto(d, oscuro=.55, velo=None):
    """La foto con su velo.

    `oscuro` era un número fijo por plantilla, calibrado a ojo contra las fotos
    que había. Ahora es sólo el PISO: si la foto que sube la persona es clara
    —una recepción iluminada, una túnica blanca— el velo medido lo sube solo.
    """
    if not d.get("foto"):
        return f'<div class="scrim" style="background:{C["blanco"]}"></div>'
    a = max(oscuro, velo if velo is not None else 0.0)
    return (f'<img class="bg" src="{d["foto"]}" style="object-position:'
            f'{d.get("foco","50% 40%")}">'
            f'<div class="scrim" style="background:linear-gradient(180deg,'
            f'rgba(0,0,0,{a*.55:.2f}) 0%,rgba(0,0,0,{a*.20:.2f}) 34%,'
            f'rgba(0,0,0,{a:.2f}) 74%,rgba(0,0,0,{min(a+.14,.94):.2f}) 100%)"></div>')


def _portada(d, w, h, ac):
    """La primera. Es la única que se ve en el feed sin deslizar."""
    claro = not d.get("foto")
    tinta = C["tinta"] if claro else "#FFFFFF"
    plan = _plan(d, (0.55, 0.92))
    return f"""
{_foto(d, .58, plan["velo"])}
<div style="position:absolute;right:-30px;top:-30px;opacity:{.24 if claro else .16}">
  {puntos(320, 280, None if claro else "#FFFFFF")}</div>
<div style="position:absolute;left:0;top:0;bottom:0;width:14px;background:{ac}"></div>
<div class="pad" style="padding:{_pad(h)};z-index:2">
  {logo(1.05, None if claro else "#FFFFFF")}
  <div class="grow"></div>
  {f'<div style="margin-bottom:20px">{pastilla(d["kicker"], ac)}</div>' if d.get('kicker') else ''}
  {_titular(d.get('titulo',''), d.get('destacado',''), int(h*0.072), tinta, ac, plan)}
  <div class="body" style="font-size:{_cuerpo_fs(h)}px;color:{tinta};opacity:.88;
    margin-top:22px;max-width:880px;line-height:1.45;font-weight:500">{d.get('bajada','')}</div>
</div>"""


def _punto(d, w, h, ac):
    """Un ítem de una lista. El número grande en rojo ordena la secuencia."""
    claro = not d.get("foto")
    tinta = C["tinta"] if claro else "#FFFFFF"
    plan = _plan(d, (0.55, 0.92))
    return f"""
{_foto(d, .62, plan["velo"])}
<div style="position:absolute;left:44px;bottom:{(SQ_BOT + 30) if h >= 1900 else 170}px;
  opacity:{.22 if claro else .14}">
  {puntos(210, 180, None if claro else "#FFFFFF")}</div>
<div class="pad" style="padding:{_pad(h)};z-index:2">
  <div class="row">
    <div style="display:flex;align-items:baseline;gap:18px">
      <div class="disp" style="color:{ac};font-size:{int(h*0.080)}px;line-height:.88">
        {d.get('numero','')}</div>
      <div class="kicker" style="color:{tinta};opacity:.60;font-size:24px">
        {d.get('detalle','')}</div>
    </div>
    {logo(.92, None if claro else "#FFFFFF")}
  </div>
  <div class="grow"></div>
  <div class="disp" style="color:{tinta};font-size:{int(h*0.056)}px;margin-bottom:20px">
    {d.get('titulo','')}</div>
  <div class="body" style="font-size:{_cuerpo_fs(h)}px;color:{tinta};opacity:.88;
    max-width:880px;line-height:1.45;font-weight:500">{d.get('texto','')}</div>
</div>"""


def _dato(d, w, h, ac):
    """Una cifra grande sola. Para precios, plazos y datos de salud.

    Existe porque los argumentos de esta marca son casi todos numéricos —$1.600,
    24 horas, 45 minutos, 14 años— y meterlos en un titular común los
    desperdicia.
    """
    claro = not d.get("foto")
    tinta = C["tinta"] if claro else "#FFFFFF"
    plan = _plan(d)
    return f"""
{_foto(d, .62, plan["velo"])}
<div style="position:absolute;right:-30px;bottom:-20px;opacity:{.22 if claro else .14}">
  {puntos(300, 260, None if claro else "#FFFFFF")}</div>
<div class="pad" style="padding:{_pad(h)};z-index:2">
  <div class="row">
    <div class="kicker" style="color:{ac};font-size:26px">{d.get('kicker','')}</div>
    {logo(.92, None if claro else "#FFFFFF")}
  </div>
  <div class="grow" style="display:flex;flex-direction:column;justify-content:center">
    <div class="disp" style="color:{ac};font-size:{int(h*0.155)}px;line-height:.86">
      {d.get('cifra','')}</div>
    <div class="disp" style="color:{tinta};font-size:{int(h*0.042)}px;margin-top:14px">
      {d.get('titulo','')}</div>
  </div>
  <div class="body" style="font-size:{_cuerpo_fs(h)}px;color:{tinta};opacity:.88;
    max-width:880px;line-height:1.45;font-weight:500">{d.get('texto','')}</div>
</div>"""


def _texto(d, w, h, ac):
    """Tipográfica pura sobre blanco. Respiro entre dos diapositivas con foto."""
    return f"""
<div class="scrim" style="background:{C['blanco']}"></div>
<div style="position:absolute;left:-30px;bottom:-30px;opacity:.22">{puntos(320, 280)}</div>
<div style="position:absolute;left:0;top:0;bottom:0;width:14px;background:{ac}"></div>
<div class="pad" style="padding:{_pad(h)};z-index:2">
  <div class="row">
    <div class="kicker" style="color:{ac};font-size:26px">{d.get('kicker','')}</div>
    {logo(.92)}
  </div>
  <div class="grow" style="display:flex;flex-direction:column;justify-content:center">
    {_titular(d.get('titulo',''), d.get('destacado',''), _titulo_fs(h, d.get('titulo','') + d.get('destacado','')), C['tinta'], ac, {"modo":"texto"})}
    {_apoyo(d.get('texto',''), h, C['tinta'], ac)}
  </div>
</div>"""


def _cierre(d, w, h, ac):
    """La última. Acá el llamado a la acción es el teléfono, no «guardá».

    En una marca de contenido, la última diapositiva pide guardar. En una
    clínica sin agenda previa, lo que hay que hacer es escribir por WhatsApp:
    pedir un guardado sería desperdiciar el único lugar donde alguien que llegó
    hasta el final está dispuesto a actuar.

    **Iba sobre negro pleno hasta el 3/8/2026.** El negro no es un color de esta
    marca —ya lo habíamos sacado del pie de las placas y del sello— y quedaba
    justo acá, en la diapositiva que más se mira. Ahora va en claro, como el
    resto, con la barra roja del costado.
    """
    from templates import TEL, WEB
    tel = d.get("tel", TEL)
    claro = not d.get("foto")
    tinta = C["tinta"] if claro else "#FFFFFF"
    plan = _plan(d)
    return f"""
{_foto(d, .70, plan["velo"])}
<div style="position:absolute;left:0;top:0;bottom:0;width:14px;background:{ac}"></div>
<div style="position:absolute;right:-30px;top:{(SQ_TOP+30) if h >= 1900 else 60}px;
  opacity:{.22 if claro else .16}">{puntos(320, 280, None if claro else "#FFFFFF")}</div>
<div class="pad" style="padding:{_pad(h)};z-index:2">
  <div class="row">
    <div class="kicker" style="color:{ac};font-size:26px">{d.get('kicker','')}</div>
    {logo(1.0, None if claro else "#FFFFFF")}
  </div>
  <div class="grow" style="display:flex;flex-direction:column;justify-content:center">
    {_titular(d.get('titulo',''), d.get('destacado',''), _titulo_fs(h, d.get('titulo','') + d.get('destacado','')), tinta, ac, plan)}
    <div style="margin-top:34px">
      <div style="display:inline-block;background:{ac};color:#FFF;padding:20px 36px">
        <span class="disp" style="font-size:34px">{d.get('cta','ESCRIBINOS POR WHATSAPP')}</span>
      </div>
      <div class="disp" style="font-size:52px;color:{tinta};margin-top:22px">{tel}</div>
      <div class="body" style="font-size:{_cuerpo_fs(h)}px;color:{tinta};opacity:.7;
        margin-top:6px;font-weight:500">{d.get('texto', WEB)}</div>
    </div>
  </div>
</div>"""


def _cuadro(d, w, h, ac):
    """Un cuadro de una secuencia de stories. Dos segundos de atención: una idea.

    El índice y la caja de respuesta los dibuja el motor.

    **Rehecho el 3/8/2026.** La versión anterior centraba el titular en todo el
    espacio libre y clavaba el texto de apoyo abajo de todo. Con un titular
    corto quedaban 600 píxeles de blanco entre una cosa y la otra, y el lector
    tenía que cruzar ese vacío para terminar una frase que empezaba arriba.
    Ahora titular y apoyo son **un solo bloque** centrado, unidos por la barra
    roja.
    """
    claro = not d.get("foto")
    tinta = C["tinta"] if claro else "#FFFFFF"
    aire = 150 if d.get("responder") else 0
    tit = d.get("titulo", "")
    dest = d.get("destacado", "")
    fs = _titulo_fs(h, f"{tit} {dest}", d.get("cuerpo"))
    plan = _plan(d)
    return f"""
{_foto(d, .60, plan["velo"]) if not claro else f'<div class="scrim" style="background:{C["blanco"]}"></div>'}
<div style="position:absolute;right:-30px;top:{SQ_TOP+40}px;opacity:{.22 if claro else .14}">
  {puntos(300, 260, None if claro else "#FFFFFF")}</div>
<div class="pad" style="padding:{_pad(h, aire)};z-index:2">
  <div class="row">
    <div class="kicker" style="color:{ac};font-size:30px">{d.get('kicker','')}</div>
    {logo(1.05, None if claro else "#FFFFFF")}
  </div>
  <div class="grow" style="display:flex;flex-direction:column;justify-content:center">
    {_titular(tit, dest, fs, tinta, ac, plan)}
    {_apoyo(d.get('texto',''), h, tinta, ac)}
  </div>
</div>"""


DIAPOS = {
    "portada": _portada,
    "punto":   _punto,
    "dato":    _dato,
    "texto":   _texto,
    "cierre":  _cierre,
    "cuadro":  _cuadro,
}
