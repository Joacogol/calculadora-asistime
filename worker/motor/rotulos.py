# -*- coding: utf-8 -*-
"""Rótulos animados para los reels.

## Por qué cuadro por cuadro y no un filtro de ffmpeg

Hasta acá el rótulo era **un PNG fijo** con un fundido y una subida de 38
píxeles hechos con expresiones de ffmpeg. Eso alcanzaba en 2022. Hoy un reel
deportivo se reconoce por cómo ENTRA el texto: la palabra que salta con
rebote, el bloque que se revela detrás de una barra que barre, las palabras que
aparecen una atrás de otra.

Nada de eso se puede hacer con expresiones de ffmpeg: `overlay` sabe mover y
`fade` sabe desvanecer, pero no hay forma de escalar con rebote ni de recortar
progresivamente por palabra.

Sí se puede hacer con CSS. Así que el rótulo se dibuja con **Chromium, un cuadro
por vez**, y sale una secuencia de PNG con transparencia que ffmpeg superpone.
Es el mismo reparto de siempre en este sistema: **Chromium dibuja, ffmpeg
compone.**

## El truco para renderizar un cuadro exacto

Una animación CSS no se puede «buscar» como un video. Pero se puede **pausar** y
correrle el reloj hacia atrás:

    animation-play-state: paused;
    animation-delay: calc(-1 * var(--t));

Con `--t` en 0,20s, el navegador dibuja exactamente el instante 0,20 de la
animación. Cambiando la variable y sacando una captura por valor sale la
secuencia completa, y **sin depender de cuánto tarde en renderizar cada
cuadro**: no hay carrera contra el reloj real.

## Sólo se dibujan los cuadros que cambian

Un rótulo de 3 segundos a 30 fps son 90 cuadros, pero entre que termina de
entrar y empieza a salir **son todos idénticos**. Se capturan sólo los de
entrada y los de salida, y el tramo quieto del medio se copia del último cuadro
asentado. En un rótulo de 3 segundos son 23 capturas en vez de 90.

## La regla que ordena los estilos

De la guía de tipografía cinética: *«una animación bien puesta le gana a diez
efectos simultáneos»*, y el texto tiene que quedar **quieto y legible al menos
medio segundo** después de asentarse. Por eso ninguna de las entradas dura más
de 0,55 s y ninguna sigue moviéndose después.
"""
import logging
import math
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

FPS = 30
ENTRADA = 0.46          # segundos que tarda en entrar
SALIDA = 0.30           # segundos que tarda en salir
MIN_QUIETO = 0.5        # lo que tiene que quedarse quieto para poder leerse

# Las curvas. `rebote` pasa apenas de largo y vuelve: es lo que hace que el
# texto se sienta puesto por alguien y no interpolado por una máquina.
REBOTE = "cubic-bezier(.2,1.5,.4,1)"
SUAVE = "cubic-bezier(.16,1,.3,1)"


ESTILOS = ("pop", "barrido", "palabra", "bloque")


def _css_animacion(estilo: str, ac: str, n_palabras: int) -> str:
    """El CSS de cada estilo.

    **Los retrasos NO se ponen acá.** La forma corta `animation:` acepta una
    lista de animaciones pero un solo `animation-delay` se aplica a todas y pisa
    los demás: con `entra` y `sale` en el mismo elemento, el retraso de la
    salida desaparecía y ninguna de las dos animaba. Los retrasos los pone
    `_cuadro()` por JavaScript, elemento por elemento, que además se puede
    inspeccionar.
    """
    # `fill-mode` en lista, y el segundo valor es `forwards` A PROPÓSITO.
    #
    # Con `both` en las dos animaciones, la de SALIDA aplica su estado inicial
    # *antes de empezar* —eso es el relleno hacia atrás— y como va segunda en la
    # lista, pisa a la de entrada en las propiedades que comparten. Resultado:
    # el texto aparecía ya asentado y la entrada no se veía nunca.
    #
    # `forwards` hace que la salida no exista hasta que le toca.
    comun = """
    .rot,.pal,.barra{animation-play-state:paused;animation-fill-mode:both,forwards}
    """
    if estilo == "pop":
        return comun + f"""
        .rot{{animation-name:entra,sale;
              animation-duration:{ENTRADA}s,{SALIDA}s;
              animation-timing-function:{REBOTE},{SUAVE}}}
        @keyframes entra{{from{{opacity:0;transform:scale(.84) translateY(26px)}}
                          to{{opacity:1;transform:none}}}}
        @keyframes sale{{from{{opacity:1;transform:none}}
                         to{{opacity:0;transform:scale(.97) translateY(-14px)}}}}
        """
    if estilo == "barrido":
        # El texto se revela detrás de una barra del color de acento que barre
        # de izquierda a derecha y sigue de largo. Es la entrada más «deportiva»
        # de las cuatro y la que mejor le queda a un titular corto.
        return comun + f"""
        .rot{{animation-name:revela,sale;
              animation-duration:{ENTRADA}s,{SALIDA}s;
              animation-timing-function:{SUAVE},{SUAVE}}}
        @keyframes revela{{from{{clip-path:inset(0 100% 0 0)}}
                           to{{clip-path:inset(0 0 0 0)}}}}
        @keyframes sale{{from{{opacity:1}} to{{opacity:0}}}}
        .barra{{position:absolute;top:0;bottom:0;width:26px;background:{ac};
          box-shadow:0 0 40px {ac};
          animation-name:barre;animation-duration:{ENTRADA + 0.14}s;
          animation-timing-function:{SUAVE}}}
        @keyframes barre{{from{{left:-4%;opacity:1}}
                          60%{{opacity:1}} to{{left:104%;opacity:0}}}}
        """
    if estilo == "palabra":
        return comun + f"""
        .pal{{animation-name:entra;animation-duration:{ENTRADA*0.75:.2f}s;
              animation-timing-function:{REBOTE}}}
        .rot{{animation-name:sale;animation-duration:{SALIDA}s;
              animation-timing-function:{SUAVE}}}
        @keyframes entra{{from{{opacity:0;transform:translateY(30px) scale(.9)}}
                          to{{opacity:1;transform:none}}}}
        @keyframes sale{{from{{opacity:1}} to{{opacity:0}}}}
        """
    # bloque: una pastilla sólida del color de acento que crece desde el centro
    return comun + f"""
    .rot{{animation-name:crece,sale;
          animation-duration:{ENTRADA}s,{SALIDA}s;
          animation-timing-function:{REBOTE},{SUAVE}}}
    @keyframes crece{{from{{opacity:0;transform:scaleX(.2)}}
                      to{{opacity:1;transform:none}}}}
    @keyframes sale{{from{{opacity:1;transform:none}}
                     to{{opacity:0;transform:scaleY(.7)}}}}
    """


# Cuánto se escalona cada palabra en el estilo `palabra`.
ESCALON = 0.075


_JS_CUADRO = """
([t, tsale, escalon]) => {
  const rot = document.querySelector('.rot');
  const barra = document.querySelector('.barra');
  const pals = document.querySelectorAll('.pal');
  // Un retraso NEGATIVO adelanta la animación: -0.2s dibuja el instante 0,2.
  // Como está pausada, el navegador pinta ese cuadro exacto y no corre nada.
  if (pals.length) {
    pals.forEach((p, i) => { p.style.animationDelay = (-(t - i * escalon)) + 's'; });
    rot.style.animationDelay = (tsale - t) + 's';
  } else {
    rot.style.animationDelay = (-t) + 's, ' + (tsale - t) + 's';
  }
  if (barra) barra.style.animationDelay = (-t) + 's';
  return t;
}
"""


def _html(texto, emoji, estilo, cuerpo, ancho, alto, fuente, ac, tinta) -> str:
    palabras = [p for p in texto.split() if p]
    if estilo == "palabra":
        cuerpo_html = "".join(f'<span class="pal">{p}</span>' for p in palabras)
    else:
        cuerpo_html = texto
    ico = (f'<span class="emo">{emoji}</span>') if emoji else ""

    if estilo == "bloque":
        caja = (f"background:{ac};color:{tinta};padding:.14em .34em;"
                f"box-shadow:0 10px 40px rgba(0,0,0,.45)")
    else:
        caja = "color:#fff;text-shadow:0 5px 26px rgba(0,0,0,.66)"

    return f"""<html><head><meta charset="utf-8"><style>
    @font-face{{font-family:'RotuloTitulo';src:url('file://{fuente}');font-weight:900}}
    *{{margin:0;padding:0;box-sizing:border-box}}
    html{{--t:0s;--tsale:99s}}
    body{{width:{ancho}px;height:{alto}px;background:transparent;overflow:hidden;
      display:flex;align-items:center;justify-content:center;position:relative}}
    .rot{{font-family:'RotuloTitulo',sans-serif;font-weight:900;
      font-size:{cuerpo}px;line-height:1.04;text-transform:uppercase;
      letter-spacing:-.018em;text-align:center;padding:0 56px;
      display:flex;align-items:center;justify-content:center;gap:{int(cuerpo*.30)}px;
      flex-wrap:wrap;max-width:100%;{caja}}}
    .pal{{display:inline-block}}
    .emo{{filter:brightness(0) invert(1);font-size:{int(cuerpo*1.02)}px}}
    {_css_animacion(estilo, ac, len(palabras))}
    </style></head><body>
      {'<div class="barra"></div>' if estilo == 'barrido' else ''}
      <div class="rot">{cuerpo_html}{ico}</div>
    </body></html>"""


def secuencia(texto: str, dur: float, destino: Path, fuente: Path,
              ancho: int, alto: int, *, estilo: str = "pop", emoji: str = "",
              cuerpo: int = 96, acento: str = "#E4FF02", tinta: str = "#0A0A0A",
              fps: int = FPS) -> tuple[Path, int]:
    """Dibuja el rótulo animado. Devuelve (carpeta, cantidad de cuadros).

    Los archivos salen numerados `0001.png`, que es lo que ffmpeg espera para
    leer una secuencia como si fuera un video.
    """
    from playwright.sync_api import sync_playwright

    if estilo not in ESTILOS:
        log.warning("estilo de rótulo desconocido «%s»: uso pop", estilo)
        estilo = "pop"

    # Con un rótulo muy corto no entra la entrada, el descanso y la salida.
    # Antes de deformar la animación, se recorta la SALIDA: que el texto se vaya
    # de golpe con el corte se nota mucho menos que una entrada apurada.
    minimo = ENTRADA + MIN_QUIETO
    salida_dur = SALIDA if dur >= minimo + SALIDA else max(0.0, dur - minimo)
    t_sale = max(ENTRADA, dur - salida_dur)

    destino.mkdir(parents=True, exist_ok=True)
    total = max(1, int(round(dur * fps)))

    # Sólo los cuadros donde algo se mueve. El resto es copia del último
    # asentado, que es idéntico y cuesta mil veces menos.
    def movil(i):
        t = i / fps
        return t <= ENTRADA + 0.05 or t >= t_sale - 0.02

    html = _html(texto, emoji, estilo, cuerpo, ancho, alto, fuente, acento, tinta)
    pagina = destino / "_rotulo.html"
    pagina.write_text(html, encoding="utf-8")

    quieto = None
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": ancho, "height": alto})
        pg.goto(f"file://{pagina}")
        pg.wait_for_function("document.fonts.ready.then(()=>true)")
        for i in range(total):
            arch = destino / f"{i + 1:04d}.png"
            if movil(i) or quieto is None:
                pg.evaluate(_JS_CUADRO, [round(i / fps, 3), round(t_sale, 3), ESCALON])
                pg.screenshot(path=str(arch), omit_background=True)
                if not movil(i):
                    quieto = arch
            else:
                shutil.copy(quieto, arch)
        b.close()
    pagina.unlink(missing_ok=True)
    return destino, total


# ═══════════════════════════════════════════════════════════════════════════
#  El marco: cuando el clip NO se recorta
#
#  Un punto de pádel filmado en cuadrado es una unidad: los cuatro jugadores,
#  la pelota y las paredes. Recortarlo a 9:16 se lleva un tercio del ancho y se
#  pierde la mitad de lo que hace que la jugada se entienda.
#
#  La respuesta NO es el fondo desenfocado —eso se ve viejo y además no aporta
#  nada—: es un **marco de marca**. El clip queda entero y centrado, y el
#  espacio que sobra arriba y abajo deja de ser relleno para volverse la parte
#  gráfica de la pieza: el logo arriba, el título abajo.
#
#  Es lo que hace cualquier cuenta deportiva con material de cancha, y tiene una
#  ventaja sobre el recorte que no es estética: **el espacio que sobra es donde
#  el texto no tapa la jugada.**
# ═══════════════════════════════════════════════════════════════════════════

def marco(destino: Path, ancho: int, alto: int, alto_ventana: int, *,
          logo_html: str = "", css_marca: str = "", fondo: str = "#0A0A0A",
          acento: str = "#E4FF02", textura: str = "") -> tuple[Path, int, int]:
    """El marco con el hueco transparente donde va el clip.

    Devuelve (png, y de la ventana, alto de la banda de abajo) — quien llama
    necesita las dos medidas para ubicar el video y el título.
    """
    from playwright.sync_api import sync_playwright

    alto_ventana = max(120, min(int(alto_ventana), alto - 200))
    banda_sup = (alto - alto_ventana) // 2
    banda_inf = alto - alto_ventana - banda_sup

    html = f"""<html><head><meta charset="utf-8"><style>
    {css_marca}
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:{ancho}px;height:{alto}px;background:transparent;overflow:hidden}}
    .banda{{position:absolute;left:0;right:0;background:{fondo};overflow:hidden}}
    .sup{{top:0;height:{banda_sup}px;display:flex;align-items:center;
      justify-content:center;padding-top:{int(banda_sup*0.18)}px}}
    .inf{{bottom:0;height:{banda_inf}px}}
    /* La línea de acento pega el clip al marco: sin ella el video parece
       apoyado encima y no incrustado. */
    .filo{{position:absolute;left:0;right:0;height:5px;background:{acento}}}
    .filo.a{{top:{banda_sup - 5}px}} .filo.b{{bottom:{banda_inf - 5}px}}
    {textura}
    </style></head><body>
      <div class="banda sup">{logo_html}</div>
      <div class="banda inf"></div>
      <div class="filo a"></div><div class="filo b"></div>
    </body></html>"""

    destino.parent.mkdir(parents=True, exist_ok=True)
    pagina = destino.with_suffix(".html")
    pagina.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": ancho, "height": alto})
        pg.goto(f"file://{pagina}")
        pg.wait_for_function("document.fonts.ready.then(()=>true)")
        pg.wait_for_timeout(220)
        pg.screenshot(path=str(destino), omit_background=True)
        b.close()
    pagina.unlink(missing_ok=True)
    return destino, banda_sup, banda_inf
