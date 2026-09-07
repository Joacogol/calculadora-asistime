# -*- coding: utf-8 -*-
"""Cómo se ve cada diapositiva de un carrusel de Boss Padel.

Esto es lo de la marca. La estructura —numeración, proporción única, índice,
flechas, zonas seguras de story, caja de respuesta— la pone `motor.carrusel` y
sirve igual para cualquier cliente.

El reparto se ve en la firma: cada función recibe `(d, ancho, alto, acento)` y
devuelve el cuerpo del HTML. No sabe en qué posición va, ni cuántas hay, ni cómo
se va a llamar el archivo. De eso se ocupa el motor, que es justamente donde no
hay que volver a pensarlo por cada marca nueva.
"""
from brand import C, logo, aros, blob
LADO, ARRIBA = 76, 76

from motor.carrusel import fondo as _fondo, SQ_TOP, SQ_BOT


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


def _portada(d, w, h, ac):
    """La primera. Es la única que se ve en el feed sin deslizar, así que carga
    todo el peso: si no gana acá, el resto no existe."""
    big = int(h * 0.088)
    bl = blob(C[d.get("blob_color", "naranja")], 620, rot=0, opacity=1)
    return f"""
{_fondo(d, C['negro'], .58)}
<div style="position:absolute;top:-206px;right:-196px;width:600px;height:600px;z-index:1">{bl}</div>
<div class="pad" style="padding:{_pad(h)};z-index:2">
  <div class="row">
    <div class="kicker" style="color:{ac};font-size:34px;line-height:1.4;max-width:620px">
      {d.get('kicker','')}</div>
    {logo(1.15)}
  </div>
  <div class="grow"></div>
  <div class="disp-b" style="color:#FAFAFA;font-size:{big}px;line-height:.92;margin-bottom:18px">
    {d.get('titulo','')}</div>
  <div class="body" style="color:#FAFAFA;opacity:.80;font-size:30px;line-height:1.34;max-width:760px">
    {d.get('bajada','')}</div>
</div>"""


def _puesto(d, w, h, ac):
    """Un puesto del podio. El número manda: se lee de lejos y ordena la
    secuencia sin que haga falta leer nada más.

    Los campeones van en sólido y el resto en outline. Es la jerarquía sin
    tener que escribir «campeones» en ningún lado.
    """
    campeon = str(d.get("puesto", "")).strip() in ("1", "01", "1RO", "1ERO")
    num = int(h * 0.30)
    if campeon:
        estilo_num = f"color:{ac}"
        rotulo = d.get("rotulo", "CAMPEONES")
    else:
        estilo_num = ("color:transparent;-webkit-text-stroke:3px #FAFAFA;opacity:.62")
        rotulo = d.get("rotulo", "")
    return f"""
{_fondo(d, C['negro'], .70)}
<div class="pad" style="padding:{_pad(h)};z-index:2">
  <div class="row">
    <div class="kicker" style="color:{ac};font-size:30px">{d.get('detalle','')}</div>
    {logo(.92)}
  </div>
  <div class="grow" style="display:flex;align-items:center">
    <div class="disp-b" style="font-size:{num}px;line-height:.80;{estilo_num}">
      {d.get('puesto','')}</div>
  </div>
  <div>
    <div class="kicker" style="color:{ac};font-size:27px;margin-bottom:14px">{rotulo}</div>
    <div class="disp-b" style="color:#FAFAFA;font-size:{int(h*0.052)}px;line-height:1.02">
      {d.get('nombres','')}</div>
  </div>
</div>"""


def _punto(d, w, h, ac):
    """Un ítem de una lista. Número chico arriba, titular fuerte, y un texto
    corto abajo. Máximo dos renglones de texto: si necesita más, es otra
    diapositiva."""
    return f"""
{_fondo(d, C['negro'], .68)}
<div class="pad" style="padding:{_pad(h)};z-index:2">
  <div class="row">
    <div style="display:flex;align-items:baseline;gap:20px">
      <div class="disp-b" style="color:{ac};font-size:{int(h*0.085)}px;line-height:.86">
        {d.get('numero','')}</div>
      <div class="kicker" style="color:#FAFAFA;opacity:.55;font-size:25px">
        {d.get('detalle','')}</div>
    </div>
    {logo(.92)}
  </div>
  <div class="grow"></div>
  <div class="disp-b" style="color:#FAFAFA;font-size:{int(h*0.062)}px;line-height:1.00;margin-bottom:22px">
    {d.get('titulo','')}</div>
  <div class="body" style="color:#FAFAFA;opacity:.82;font-size:31px;line-height:1.36;max-width:800px">
    {d.get('texto','')}</div>
</div>"""


def _texto(d, w, h, ac):
    """Puro tipográfico sobre el negro de la marca. Sirve de respiro entre dos
    diapositivas con foto y para las frases que no necesitan imagen."""
    return f"""
{_fondo({}, C['negro'])}
<div style="position:absolute;left:-120px;bottom:-90px;z-index:1;opacity:.14">{aros(360)}</div>
<div class="pad" style="padding:{_pad(h)};z-index:2">
  <div class="row">
    <div class="kicker" style="color:{ac};font-size:30px">{d.get('kicker','')}</div>
    {logo(.92)}
  </div>
  <div class="grow" style="display:flex;align-items:center">
    <div class="disp-b" style="color:#FAFAFA;font-size:{int(h*0.072)}px;line-height:1.02">
      {d.get('titulo','')}</div>
  </div>
  <div class="body" style="color:#FAFAFA;opacity:.78;font-size:30px;line-height:1.36;max-width:800px">
    {d.get('texto','')}</div>
</div>"""


def _cierre(d, w, h, ac):
    """La última. Pide GUARDAR, no seguir.

    El guardado es donde el carrusel le saca nueve veces a la foto sola, y es
    la señal que más pesa para que Instagram lo siga mostrando. Pedir seguidores
    en la última diapositiva desperdicia el único lugar donde la gente que llegó
    hasta el final está dispuesta a hacer algo.
    """
    cta = d.get("cta", "GUARDÁ ESTE POSTEO")
    return f"""
{_fondo(d, C['negro'], .74)}
<div class="pad" style="padding:{_pad(h)};z-index:2">
  <div class="row">
    <div class="kicker" style="color:{ac};font-size:30px">{d.get('kicker','')}</div>
    {logo(1.05)}
  </div>
  <div class="grow" style="display:flex;align-items:center">
    <div class="disp-b" style="color:#FAFAFA;font-size:{int(h*0.070)}px;line-height:1.00">
      {d.get('titulo','')}</div>
  </div>
  <div>
    <div style="display:inline-block;background:{ac};color:#0A0A0A;padding:20px 40px;margin-bottom:20px">
      <span class="eyebrow" style="font-weight:700;font-size:29px;letter-spacing:.15em">{cta}</span>
    </div>
    <div class="body" style="color:#FAFAFA;opacity:.75;font-size:28px;line-height:1.34">
      {d.get('texto','')}</div>
  </div>
</div>"""


def _sq_cuadro(d, w, h, ac):
    """Un cuadro de una secuencia de stories. Una idea, grande, y nada más.

    Tiene dos segundos de atención real: el 57-67% de la gente avanza tocando.
    Un párrafo no se lee.

    El índice y la caja de respuesta los dibuja el motor. Acá sólo va el cuerpo.
    Lo único que hay que respetar es dejar aire abajo cuando el cuadro pide
    responder, o el texto queda debajo de la caja.
    """
    aire = "margin-bottom:150px" if d.get("responder") else ""
    return f"""
{_fondo(d, C['negro'], .66)}
<div class="pad" style="padding:{_pad(h)};z-index:2">
  <div class="row">
    <div class="kicker" style="color:{ac};font-size:32px">{d.get('kicker','')}</div>
    {logo(1.05)}
  </div>
  <div class="grow" style="display:flex;align-items:center">
    <div class="disp-b" style="color:#FAFAFA;font-size:{d.get('cuerpo', 112)}px;line-height:.98">
      {d.get('titulo','')}</div>
  </div>
  <div class="body" style="color:#FAFAFA;opacity:.82;font-size:34px;line-height:1.34;
    max-width:840px;{aire}">
    {d.get('texto','')}</div>
</div>"""



# Los tipos que ofrece esta marca. `portada` y `cierre` son obligatorios para
# cualquier carrusel; `cuadro` es lo que hace falta para secuencias de stories.
DIAPOS = {
    "portada": _portada,
    "puesto":  _puesto,
    "punto":   _punto,
    "texto":   _texto,
    "cierre":  _cierre,
    "cuadro":  _sq_cuadro,
}
