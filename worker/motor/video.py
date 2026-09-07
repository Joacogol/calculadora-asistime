# -*- coding: utf-8 -*-
"""Reels de Boss Padel: varios clips y fotos cortados y pegados en un video.

La idea es la misma que en las placas y en el PDF: el pedido aporta el
contenido, el sistema aporta la forma. Acá el renderizador es ffmpeg en vez de
Chromium, pero las tapas de entrada y de cierre las sigue dibujando Chromium —
así el reel arranca y termina con exactamente la misma tipografía que el resto
de las piezas.

Cómo está armado: cada tramo se renderiza por separado a un archivo normalizado
(1080×1920, 30 fps, audio 48k estéreo) y recién al final se concatenan. Es más
lento que un solo filter_complex gigante, pero cuando algo sale mal se ve
exactamente en qué tramo, y permite mezclar video con fotos sin que se rompa
nada.

    python3 video.py reel.json
"""
import contextlib
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

# ── De qué marca son los materiales ──────────────────────────────────────────
# El motor no tiene tipografías ni fotos propias: se los presta la marca. La
# carpeta se fija con `configurar()` antes de armar nada, y el valor por defecto
# apunta acá sólo para que importar el módulo no explote.
RAIZ = Path(__file__).resolve().parent
FUENTES = RAIZ / "fonts"
SALIDA = RAIZ / "out"
TIPO_TITULO = FUENTES / "Barlow-Black.ttf"
TIPO_PIE = FUENTES / "BarlowCondensed-Medium.ttf"
VELO_PNG = RAIZ / "assets" / "velo-reel.png"
_BANCO: dict = {}

log = logging.getLogger(__name__)

ANCHO, ALTO, FPS = 1080, 1920, 30
NEGRO = "0x0A0A0A"
LIMA = "0xE4FF02"


ANIMO = "club"
LOGO_HTML = ""
CSS_MARCA = ""


def configurar(raiz, titulo="Barlow-Black.ttf",
               pie="BarlowCondensed-Medium.ttf", acento=None, animo="club",
               logo_html="", css_marca=""):
    """Apunta el motor a los materiales de una marca.

    `titulo` y `pie` son los archivos de tipografía que la marca usa para los
    rótulos del reel. Tienen que ser TTF reales: ffmpeg dibuja el texto con
    freetype y no entiende fuentes variables — Archivo es variable y sale
    siempre en peso regular, por eso acá va Barlow Black.
    """
    global RAIZ, FUENTES, SALIDA, TIPO_TITULO, TIPO_PIE, VELO_PNG, _BANCO, LIMA
    global ANIMO, LOGO_HTML, CSS_MARCA
    RAIZ = Path(raiz)
    ANIMO = animo
    # El logo va como HTML porque es un SVG vectorial: pasarlo por PNG a esta
    # altura le comería el filo justo en la parte más chica de la pieza.
    LOGO_HTML, CSS_MARCA = logo_html, css_marca
    FUENTES = RAIZ / "fonts"
    SALIDA = RAIZ / "out"
    TIPO_TITULO = FUENTES / titulo
    TIPO_PIE = FUENTES / pie
    VELO_PNG = RAIZ / "assets" / "velo-reel.png"
    if acento:
        LIMA = acento if acento.startswith("0x") else "0x" + acento.lstrip("#")
    # El banco de fotos con los encuadres ya resueltos. El reel es 9:16 igual
    # que una historia, así que se reusa el valor de `story` y no se decide de
    # nuevo: así una jugadora se ve igual en la placa y en el reel.
    try:
        _BANCO = json.loads(
            (RAIZ / "referencias" / "fotos.json").read_text(encoding="utf-8"))
    except Exception:
        _BANCO = {}


def _correr(args, etapa=""):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        cola = "\n".join(r.stderr.strip().splitlines()[-12:])
        raise RuntimeError(f"ffmpeg falló{' en ' + etapa if etapa else ''}:\n{cola}")


def _texto_dibujado(texto: str, tmp: Path, i: int, pos="arriba") -> str:
    """Título que entra con un fundido y una subida corta.

    El texto va a un archivo aparte en vez de ir en la línea de comandos: los
    dos puntos, las comillas y los acentos rompen el escapado de drawtext, y
    «3, 2, 1…» tiene justamente comas y puntos.
    """
    if not texto:
        return ""
    archivo = tmp / f"txt{i}.txt"
    archivo.write_text(texto.upper(), encoding="utf-8")

    y_base = 300 if pos == "arriba" else ALTO - 520
    # sube 34 px durante los primeros 0.45 s y ahí se queda
    y = f"{y_base}+34*(1-min(1\\,t/0.45))"
    alfa = "min(1\\,t/0.35)"

    return (
        f"drawtext=textfile='{archivo}':fontfile='{TIPO_TITULO}':"
        f"fontsize=92:fontcolor=white@1:alpha='{alfa}':"
        f"x=(w-text_w)/2:y={y}:line_spacing=14:"
        f"shadowcolor=black@0.55:shadowx=0:shadowy=5"
    )


# Degradé oscuro arriba y abajo, generado con PIL en `assets/velo-reel.png`.
# Un drawbox pinta alfa constante y deja un borde recto bien visible cruzando
# la imagen; esto se funde de verdad. Sin velo, el texto blanco desaparece
# cuando abajo hay una cancha celeste iluminada.
# (VELO_PNG se fija en configurar(), junto al resto de los materiales.)

# Un MP4 guarda UN solo juego de parámetros de decodificación (el `avcC`) en el
# contenedor: el del primer tramo. ffmpeg es tolerante y relee los parámetros
# que vienen dentro del flujo, pero QuickTime no — usa el del contenedor y nada
# más. Si los tramos se codifican con ajustes distintos, en Mac se ve el primer
# cuadro congelado mientras el audio sigue corriendo.
#
# Por eso TODOS los tramos se codifican exactamente igual, con el nivel y la
# cantidad de cuadros de referencia fijados a mano en vez de dejar que el preset
# los deduzca. Así el `avcC` sirve para todo el archivo y el pegado sin
# recodificar (`-c copy`) es válido. No tocar sin volver a probar en un Mac.
#
# El preset es `veryfast` y no `slow`, y eso NO es una concesión de calidad:
# es la corrección de un error que costaba veinte minutos por reel.
#
# `slow` + `crf 18` es calidad de masterizado. Instagram recomprime todo lo
# que se sube a una fracción de ese bitrate, así que esa calidad no la ve
# NADIE: se paga entera en tiempo de máquina y se tira en el camino. Y no se
# paga una vez — este juego de parámetros se aplica UNA VEZ POR TRAMO, así
# que un reel de tres clips lo pagaba tres veces.
#
# Medido con los tres clips reales de Boss (61,3 s de material) en la máquina
# del job: con `slow` el pedido se comía los 30 minutos de límite y moría sin
# terminar. `veryfast` con `crf 20` da un archivo indistinguible después del
# recomprimido de Instagram.
#
# Lo que NO se toca es `ref` y `bframes`: van fijos acá abajo justamente para
# que el `avcC` siga siendo el mismo en todos los tramos. El preset cambia
# cuánto busca el codificador, no la forma del flujo.
VIDEO_X264 = [
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
    "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
    "-x264-params", "ref=4:bframes=3:keyint=60:min-keyint=30:scenecut=0",
    "-video_track_timescale", "30000",
    # El color también se fija a mano. Un clip de cámara viene etiquetado
    # bt709 y una foto o una placa no vienen etiquetadas: si se mezclan, el
    # color puede saltar de un tramo al siguiente. bt709 es lo que corresponde
    # en HD y lo que cualquier reproductor asume.
    "-colorspace", "bt709", "-color_primaries", "bt709",
    "-color_trc", "bt709", "-color_range", "tv",
]
AUDIO_AAC = ["-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"]


def _con_preset(base: list[str], preset: str, crf: int) -> list[str]:
    """El mismo juego de parámetros con otro preset. Se deriva y no se copia
    para que no se separen: si mañana cambia el color o el nivel, cambia acá y
    en el intermedio a la vez."""
    v = list(base)
    v[v.index("-preset") + 1] = preset
    v[v.index("-crf") + 1] = str(crf)
    return v


#: El codificador para los tramos que DESPUÉS se vuelven a codificar.
#:
#: Cuando el reel lleva subtítulos o hook, cada tramo es un archivo de paso: se
#: pega con los otros y esa unión se vuelve a codificar entera para quemarle el
#: texto encima. Poner cuidado en comprimir un archivo de paso es trabajo que se
#: tira: se paga la compresión buena y a los treinta segundos se descarta.
#:
#: `ultrafast` con un `crf` más fino invierte el trato: sale mucho más rápido y
#: ocupa más, pero eso que ocupa vive un rato en `/tmp` y llega al paso final
#: sin haber perdido nada que se note. Medido sobre un clip de 21 s: la misma
#: cadena tarda 44,5 s con `veryfast` y 32,3 s con `ultrafast`.
#:
#: Si NO hay texto que quemar, el tramo ES el resultado: ahí se usa
#: `VIDEO_X264` como siempre. Esa decisión la toma `reel()`, que es el único
#: lugar que sabe si viene una pasada más.
VIDEO_INTERMEDIO = _con_preset(VIDEO_X264, "ultrafast", 18)



# ── rótulos ───────────────────────────────────────────────────────────────
# El texto de los reels lo dibuja Chromium, no `drawtext`. Tres razones: usa
# las tipografías reales de la marca con su interletrado, no hay que pelear
# con el escapado de acentos y comas, y sobre todo permite emoticones — que
# `drawtext` no puede porque las fuentes de emoji son mapas de bits a color.
#
# El truco para pintarlos de blanco es `filter: brightness(0) invert(1)`:
# aplasta cualquier glifo de color a negro y lo invierte a blanco puro.
ALTO_ROTULO = 460


def _rotulo_png(texto: str, emoji: str, tmp: Path, i: int, cuerpo: int = 96) -> Path:
    from playwright.sync_api import sync_playwright
    salida = tmp / f"rot{i:02d}.png"
    ico = (f'<span style="filter:brightness(0) invert(1);font-size:{int(cuerpo*1.02)}px;'
           f'line-height:1">{emoji}</span>') if emoji else ""
    html = f"""<html><head><meta charset="utf-8"><style>
      @font-face{{font-family:'Barlow';src:url('file://{FUENTES}/Barlow-Black.ttf');font-weight:900}}
      *{{margin:0;padding:0}}
      body{{width:{ANCHO}px;height:{ALTO_ROTULO}px;background:transparent;
        display:flex;align-items:center;justify-content:center}}
      .fila{{display:flex;align-items:center;gap:{int(cuerpo*0.34)}px;
        padding:0 60px;max-width:100%}}
      .txt{{font-family:'Barlow',sans-serif;font-weight:900;font-size:{cuerpo}px;
        line-height:1.06;color:#fff;text-transform:uppercase;letter-spacing:-.015em;
        text-shadow:0 5px 22px rgba(0,0,0,.62);text-align:center}}
    </style></head><body><div class="fila">
      <div class="txt">{texto}</div>{ico}
    </div></body></html>"""
    archivo = tmp / f"rot{i:02d}.html"
    archivo.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": ANCHO, "height": ALTO_ROTULO})
        pg.goto(f"file://{archivo}")
        pg.wait_for_timeout(320)
        pg.screenshot(path=str(salida), omit_background=True)
        b.close()
    return salida


def _velo(tmp: Path) -> Path:
    """El degradado oscuro de abajo, que es lo que hace legible cualquier texto.

    La marca puede traer el suyo en `assets/velo-reel.png`. Si no lo trae se
    dibuja acá, y eso NO es un adorno defensivo: sin velo el motor de varios
    clips no arranca —es una entrada obligada de la cadena de ffmpeg— y una
    marca que nunca hizo reels no tiene por qué tener ese archivo. Descubrirlo
    con un pedido real adentro sería un reel perdido por un PNG.

    Se dibuja con Chromium, como todo lo demás acá, para no sumar una librería
    de imágenes sólo por un degradado.
    """
    if VELO_PNG.exists():
        return VELO_PNG
    from playwright.sync_api import sync_playwright
    salida = tmp / "velo.png"
    if salida.exists():
        return salida
    html = f"""<html><head><style>
      *{{margin:0;padding:0}} body{{background:transparent}}
      .v{{width:{ANCHO}px;height:{ALTO}px;
        background:linear-gradient(to bottom,
          rgba(0,0,0,0) 56%, rgba(0,0,0,.30) 74%, rgba(0,0,0,.62) 100%)}}
    </style></head><body><div class="v"></div></body></html>"""
    arch = tmp / "velo.html"
    arch.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": ANCHO, "height": ALTO})
        pg.goto(f"file://{arch}")
        pg.wait_for_timeout(150)
        pg.locator(".v").screenshot(path=str(salida), omit_background=True)
        b.close()
    return salida


# ── subtítulos ────────────────────────────────────────────────────────────
# Un subtítulo NO se dibuja cuadro por cuadro como el rótulo, y es una decisión
# de costo medida, no un atajo. El rótulo sale barato porque se queda quieto:
# de 90 cuadros se capturan 23 y el resto se copia. Un subtítulo cambia de
# frase cada dos segundos durante TODO el reel, así que esa optimización no
# aplica: un reel de 60 segundos serían 1.800 capturas de Chromium.
#
# Acá se dibuja UNA imagen por frase y ffmpeg la muestra en su ventana de
# tiempo con `enable=between(t,…)`. Doce frases son doce capturas, y el texto
# igual sale con la tipografía de la marca, que es todo el punto de dibujarlo
# con Chromium en vez de con `drawtext`.
#
# Si algún día hace falta que el subtítulo ENTRE animado —palabra por palabra,
# tipo karaoke—, eso sí necesita cuadro por cuadro y va en `rotulos.py`. Pero
# es otra decisión, con otro costo, y conviene tomarla midiendo.

#: Alto de la franja donde puede caer el subtítulo.
ALTO_SUBTITULO = 300

#: Lo que se deja libre abajo. Instagram tapa esa zona con los botones de me
#: gusta, comentar y compartir, y con el pie de foto: un subtítulo ahí no se
#: lee. Es el mismo criterio que usa `_capa_rotulo`.
PIE_SUBTITULO = 330


@contextlib.contextmanager
def _chromium():
    """Un solo Chromium para todas las capas de texto del reel.

    Antes cada función de dibujo abría el suyo y lo cerraba. Para el hook, que
    es uno, da igual. Para los subtítulos NO: un reel de un minuto lleva unos
    treinta carteles, y eran treinta arranques de navegador —con su perfil
    nuevo, su GPU de mentira y su primera compilación de la hoja de estilo—
    para sacar treinta fotos de un texto blanco.
    """
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        try:
            yield b
        finally:
            b.close()


def _esperar_tipografia(pg) -> None:
    """Espera a que la tipografía esté cargada, en vez de dormir un rato fijo.

    Acá había un `wait_for_timeout(280)`, que es lo peor de los dos mundos: de
    más cuando la tipografía ya estaba —el caso normal, y con treinta
    subtítulos son ocho segundos regalados— y de menos el día que tarde, en el
    que `QUE_ENTRE` mediría la tipografía de reemplazo y achicaría la frase
    contra un ancho que no es el que se va a dibujar. `document.fonts.ready`
    es el dato exacto y llega apenas está.
    """
    try:
        pg.evaluate("document.fonts.ready.then(() => true)")
    except Exception:                                        # noqa: BLE001
        pg.wait_for_timeout(280)


def _html_subtitulo(texto: str, cuerpo: int = 68) -> str:
    """Una frase de subtítulo, con la tipografía de la marca y fondo transparente.

    El texto tiene que leerse sobre CUALQUIER cosa: un clip claro, uno oscuro,
    uno con la cámara moviéndose. Por eso no alcanza con el color: lleva una
    sombra dura y ancha que le hace borde por los cuatro lados.

    El cuerpo por defecto es grande —68 px— porque un reel se mira en un
    teléfono, con el pulgar encima y a veces sin sonido: el subtítulo ES el
    mensaje, no una nota al pie. Poner un número grande es seguro justamente
    porque después está el guardián: si la frase no entra, la achica sola.

    El tamaño lo termina de decidir `motor.render.QUE_ENTRE`, el mismo guardián
    que usan las placas. No es adorno: la regla de 42 caracteres por línea que
    valida el guion es una cuenta de LETRAS, y una cuenta de letras es
    exactamente lo que dejó salir «PAPANICOLAOU» cortado el 31/8. Acá se mide
    lo dibujado.
    """
    # El CSS de la marca va PRIMERO y las reglas de acá después, a propósito.
    # Al revés, el `.canvas{background:#FFFFFF}` de la hoja de la marca —que
    # para una placa está bien— pisaría el fondo transparente y el subtítulo
    # saldría con un rectángulo blanco de 1080×300 tapando el video. Es
    # exactamente la trampa que ya está anotada en `reelero.rotulo()`.
    return f"""<html><head><meta charset="utf-8"><style>
      {CSS_MARCA}
      @font-face{{font-family:'Sub';src:url('file://{TIPO_TITULO}');font-weight:900}}
      *{{margin:0;padding:0;box-sizing:border-box}}
      body{{background:transparent}}
      .canvas{{width:{ANCHO}px;height:{ALTO_SUBTITULO}px;position:relative;
        background:transparent;
        display:flex;align-items:center;justify-content:center;padding:0 96px}}
      .txt{{font-family:'Sub',sans-serif;font-weight:900;font-size:{cuerpo}px;
        line-height:1.18;color:#fff;text-align:center;letter-spacing:-.01em;
        text-shadow:0 3px 10px rgba(0,0,0,.95), 0 0 26px rgba(0,0,0,.85),
                    0 -2px 8px rgba(0,0,0,.8);}}
    </style></head><body>
      <div class="canvas"><div class="txt">{texto}</div></div>
    </body></html>"""


def _subtitulos_png(textos: list[str], tmp: Path, cuerpo: int = 68) -> list[Path]:
    """Los carteles de TODOS los subtítulos, en un solo navegador y una sola
    pestaña: cada frase es un `goto` a otro archivo, que cuesta milisegundos.
    """
    from .render import QUE_ENTRE, MARGEN_SEGURO

    salidas: list[Path] = []
    with _chromium() as b:
        pg = b.new_page(viewport={"width": ANCHO, "height": ALTO_SUBTITULO})
        for i, texto in enumerate(textos):
            archivo = tmp / f"sub{i:02d}.html"
            archivo.write_text(_html_subtitulo(texto, cuerpo), encoding="utf-8")
            pg.goto(f"file://{archivo}")
            _esperar_tipografia(pg)
            pg.evaluate(QUE_ENTRE, MARGEN_SEGURO)
            salida = tmp / f"sub{i:02d}.png"
            pg.locator(".canvas").screenshot(path=str(salida), omit_background=True)
            salidas.append(salida)
    return salidas


#: Cuánto se queda el hook en pantalla. Tres segundos es lo que tarda alguien
#: en decidir si sigue mirando; más que eso ya compite con los subtítulos.
DURA_HOOK = 3.0

#: Dónde vive: apenas debajo de los 250 px que Instagram tapa con el nombre de
#: la cuenta, y no más abajo.
#:
#: Estaba en 330 con 460 px de alto y en un video de alguien hablando el hook
#: caía justo sobre la cara. Un titular encima de la cara del que habla es peor
#: que no tener titular: tapa lo único que la persona vino a mirar.
#:
#: **No se detecta la cara, y es a propósito.** Se podría —hay librerías— pero
#: sumar una dependencia de visión por computadora al worker para acomodar un
#: texto es caro para lo que resuelve. La banda de arriba es donde va el hook
#: en cualquier reel bien hecho, con cara o sin cara, así que alcanza con
#: ponerlo ahí y no dejarlo crecer.
ALTO_HOOK, ARRIBA_HOOK = 300, 268

#: Cuántos renglones puede ocupar el hook. Dos.
#:
#: No es una preferencia: tres renglones de titular ocupan medio cuadro y a los
#: tres segundos se van, así que el reel arranca con la mitad de la pantalla
#: tapada. Si el texto no entra en dos, se achica hasta que entre — para eso
#: está el guardián de `render.py`, y acá se usa con un límite de alto en vez
#: de uno de ancho.
LINEAS_HOOK = 2


def _hook_png(texto: str, tmp: Path) -> Path:
    """El texto de enganche de los primeros segundos.

    Va en mayúsculas, grande y con la barra del color de la marca debajo. No es
    un subtítulo más grande: es lo único que se lee con el dedo listo para
    pasar de largo, así que se comporta como un titular de placa —el mismo
    peso, el mismo interletrado apretado— y por eso usa la misma tipografía de
    título que las piezas.
    """
    from .render import QUE_ENTRE, MARGEN_SEGURO

    salida = tmp / "hook.png"
    acento = "#" + LIMA.lstrip("0x").lstrip("#")
    html = f"""<html><head><meta charset="utf-8"><style>
      {CSS_MARCA}
      @font-face{{font-family:'Hook';src:url('file://{TIPO_TITULO}');font-weight:900}}
      *{{margin:0;padding:0;box-sizing:border-box}}
      body{{background:transparent}}
      .canvas{{width:{ANCHO}px;height:{ALTO_HOOK}px;position:relative;
        background:transparent;display:flex;flex-direction:column;
        align-items:center;justify-content:center;padding:0 80px;gap:26px}}
      .txt{{font-family:'Hook',sans-serif;font-weight:900;font-size:92px;
        line-height:1.02;color:#fff;text-align:center;text-transform:uppercase;
        letter-spacing:-.025em;
        text-shadow:0 4px 16px rgba(0,0,0,.92), 0 0 34px rgba(0,0,0,.8)}}
      .barra{{width:190px;height:14px;background:{acento};
        box-shadow:0 3px 14px rgba(0,0,0,.55)}}
    </style></head><body>
      <div class="canvas"><div class="txt">{texto}</div><div class="barra"></div></div>
    </body></html>"""
    arch = tmp / "hook.html"
    arch.write_text(html, encoding="utf-8")
    with _chromium() as b:
        pg = b.new_page(viewport={"width": ANCHO, "height": ALTO_HOOK})
        pg.goto(f"file://{arch}")
        _esperar_tipografia(pg)
        # Primero que entre en dos renglones, después que entre en el ancho.
        # En ese orden: achicar por el alto cambia cuántas líneas hay, así que
        # medir el ancho antes sería medir un texto que todavía va a cambiar.
        pg.evaluate(CABE_EN_DOS, LINEAS_HOOK)
        pg.evaluate(QUE_ENTRE, MARGEN_SEGURO)
        pg.locator(".canvas").screenshot(path=str(salida), omit_background=True)
    return salida


#: Achica el hook hasta que entre en la cantidad de renglones pedida.
CABE_EN_DOS = """
(maximo) => {
  const el = document.querySelector('.txt');
  if (!el) return 0;
  const alto = () => parseFloat(getComputedStyle(el).lineHeight) ||
                     parseFloat(getComputedStyle(el).fontSize) * 1.02;
  let fs = parseFloat(getComputedStyle(el).fontSize);
  let vueltas = 0;
  while (el.getBoundingClientRect().height > alto() * maximo + 2 &&
         vueltas < 40 && fs > 44) {
    fs *= 0.95;
    el.style.fontSize = fs + 'px';
    vueltas++;
  }
  return Math.round(fs);
}
"""


#: Cuánto dura la tapa de cierre. Segundo y medio: lo que tarda alguien en
#: leer dos renglones cortos. Más que eso y el reel «termina» antes de terminar,
#: que es peor que cortar en seco.
DURA_CIERRE = 1.6


def _cierre_png(texto: str, pie: str, tmp: Path) -> Path:
    """La placa del final: el fondo de la marca, la frase y la barra de acento.

    Un reel montado con material crudo termina donde se cortó el último clip,
    o sea en el medio de una frase. Eso se nota y se lee como un error, aunque
    el resto esté bien: el que mira no sabe si se cortó la carga o si el video
    era así.

    La tapa no arregla el contenido, pero pone un punto final. Es lo mínimo que
    hace que una pieza parezca terminada.
    """
    from .render import QUE_ENTRE, MARGEN_SEGURO

    salida = tmp / "cierre.png"
    acento = "#" + LIMA.lstrip("0x").lstrip("#")
    html = f"""<html><head><meta charset="utf-8"><style>
      {CSS_MARCA}
      @font-face{{font-family:'Hook';src:url('file://{TIPO_TITULO}');font-weight:900}}
      @font-face{{font-family:'Pie';src:url('file://{TIPO_PIE}');font-weight:500}}
      *{{margin:0;padding:0;box-sizing:border-box}}
      body{{background:{NEGRO.replace('0x', '#')}}}
      .canvas{{width:{ANCHO}px;height:{ALTO}px;background:{NEGRO.replace('0x', '#')};
        display:flex;flex-direction:column;align-items:center;
        justify-content:center;gap:34px;padding:0 110px}}
      .txt{{font-family:'Hook',sans-serif;font-weight:900;font-size:104px;
        line-height:1.02;color:#fff;text-align:center;text-transform:uppercase;
        letter-spacing:-.03em}}
      .barra{{width:220px;height:16px;background:{acento}}}
      .pie{{font-family:'Pie',sans-serif;font-weight:500;font-size:44px;
        color:#fff;opacity:.82;letter-spacing:.02em;text-align:center}}
    </style></head><body>
      <div class="canvas">
        <div class="txt">{texto}</div>
        <div class="barra"></div>
        {f'<div class="pie">{pie}</div>' if pie else ''}
      </div>
    </body></html>"""
    arch = tmp / "cierre.html"
    arch.write_text(html, encoding="utf-8")
    with _chromium() as b:
        pg = b.new_page(viewport={"width": ANCHO, "height": ALTO})
        pg.goto(f"file://{arch}")
        _esperar_tipografia(pg)
        pg.evaluate(QUE_ENTRE, MARGEN_SEGURO)
        pg.locator(".canvas").screenshot(path=str(salida))
    return salida


def _quemar_textos(mudo: Path, subs: list[dict], hook: str, tmp: Path) -> Path:
    """Quema los subtítulos Y el hook sobre el reel ya concatenado, en UNA pasada.

    Va DESPUÉS del concatenado y no adentro de cada tramo porque un subtítulo
    vive en la línea de tiempo del reel: puede empezar en un clip y terminar en
    el siguiente. Y va ANTES de la mezcla de audio porque esa etapa copia el
    video sin recodificar; si se hiciera al revés, no habría dónde dibujar.

    **Los dos textos van juntos a propósito.** Antes eran dos funciones y dos
    llamadas a ffmpeg, y cada una recodificaba el reel ENTERO: el hook —un
    cartel que se ve tres segundos— costaba una pasada completa de codificación
    sobre el minuto de video. Son la misma operación (pegar un PNG encima del
    cuadro durante un rato) y el `filter_complex` encadena tantas capas como
    haga falta, así que separarlas no compraba nada y costaba el doble.

    Acá se fija el codificador con `VIDEO_X264` en vez de dejar el que ffmpeg
    elige solo. No es cosmética: sin decirlo, ffmpeg usa `preset medium` y
    `crf 23`, o sea que esta pasada —la última que toca la imagen— salía más
    lenta Y peor que los tramos. Con el juego de parámetros de arriba también
    quedan los mismos tags de color, que es lo que evita el salto de tono entre
    un clip de cámara y una placa.
    """
    if not subs and not hook:
        return mudo

    # Todos los carteles se dibujan de una, con un solo Chromium.
    capas: list[Path] = _subtitulos_png([s["texto"] for s in subs], tmp) if subs else []
    #: (desde, hasta, y) de cada capa, en el mismo orden que `capas`.
    cuando = [(float(s["desde"]), float(s["hasta"]),
               ALTO - ALTO_SUBTITULO - PIE_SUBTITULO) for s in subs]

    # El hook va ÚLTIMO en la cadena, o sea encima de todo. En los tres
    # primeros segundos puede haber subtítulo y hook a la vez, y si se
    # superponen el que tiene que ganar es el hook: es lo que decide si la
    # persona se queda.
    if hook:
        capas.append(_hook_png(hook, tmp))
        cuando.append((0.0, float(DURA_HOOK), ARRIBA_HOOK))

    entradas = []
    for c in capas:
        entradas += ["-i", str(c)]

    pasos, etiqueta = [], "0:v"
    for i, (desde, hasta, y) in enumerate(cuando):
        sig = f"v{i}"
        pasos.append(
            f"[{etiqueta}][{i+1}:v]overlay=x=0:y={y}:"
            f"enable='between(t,{desde:.3f},{hasta:.3f})'[{sig}]")
        etiqueta = sig

    con = tmp / "con-textos.mp4"
    _correr(["ffmpeg", "-v", "error", "-y", "-i", str(mudo), *entradas,
             "-filter_complex", ";".join(pasos),
             "-map", f"[{etiqueta}]", "-map", "0:a?",
             *VIDEO_X264, "-c:a", "copy",
             "-movflags", "+faststart", str(con)],
            "subtítulos y hook")
    return con


def _capa_rotulo(entrada: str, pos: str) -> str:
    """Superpone la secuencia del rótulo.

    Ya no hay fundido ni subida acá: **la animación completa viene dibujada en
    la secuencia PNG**, con easing de verdad. Lo único que queda es ponerla en
    su lugar. Ver `motor/rotulos.py` para el porqué.

    La `y` deja libres los 250 px de arriba —donde Instagram pone el nombre de
    la cuenta— y los 300 de abajo, donde van los botones y el pie de foto.
    """
    y = 250 if pos == "arriba" else ALTO - ALTO_ROTULO - 300
    return (f"[{entrada}]format=rgba[rot];"
            f"[base][rot]overlay=x=0:y={y}:shortest=0")


def _fondo_y_frente(recorte: float, foco_x: float) -> str:
    """Encuadre vertical de una fuente apaisada.

    Llevar un 16:9 a 9:16 recortando deja sólo un tercio del ancho: en pádel
    eso parte la cancha al medio y se pierden dos jugadores. Pero dejar el
    clip entero tampoco sirve — a ancho completo ocupa el 32% de la altura y
    se lee como una tirita perdida en el medio.

    El punto medio: se recorta la fuente a una proporción intermedia
    (`recorte`, por defecto 1:1) y ESO va a ancho completo. Con 1:1 la imagen
    ocupa el 56% del alto, que es lo que se ve en los reels del club. El resto
    lo llena el mismo clip desenfocado. `foco_x` mueve el recorte a los lados
    para seguir la acción: 0.5 es el centro.
    """
    return (
        f"[0:v]split=2[bg][fg];"
        # El fondo se desenfoca EN CHICO y recién después se agranda.
        #
        # Antes se hacía al derecho: agrandar la fuente hasta cubrir 1080×1920
        # y aplicar `gblur=sigma=42` sobre esos dos millones de píxeles. Para
        # un 16:9 eso significaba escalar a 3413×1920 —tres veces el cuadro
        # final— y desenfocar todo eso, cuadro por cuadro. Era, de lejos, el
        # filtro más caro del motor.
        #
        # Y era gratis de arreglar, porque **un desenfoque fuerte destruye
        # justamente el detalle que la resolución aporta**: achicar a un sexto,
        # desenfocar ahí con un sexto del radio y volver a agrandar da una
        # imagen que no se distingue de la otra, con 36 veces menos píxeles que
        # tocar. Es el mismo truco que usan los fondos difuminados de
        # cualquier interfaz.
        #
        # El agrandado final va con `bilinear` a propósito: sobre una imagen ya
        # desenfocada no hay borde que un escalador caro pueda conservar, así
        # que lanczos acá sólo costaría tiempo.
        f"[bg]scale={ANCHO//6}:{ALTO//6}:force_original_aspect_ratio=increase,"
        f"crop={ANCHO//6}:{ALTO//6},gblur=sigma=7,"
        f"eq=brightness=-0.16:saturation=0.65,"
        f"scale={ANCHO}:{ALTO}:flags=bilinear[bgb];"
        # De un 16:9 recortado a vertical sólo quedan 608 px de ancho que hay
        # que estirar a 1080: un aumento de 1,78×. Con el escalador por
        # defecto la imagen queda blanda al lado de las fotos, que son
        # nítidas. Lanczos conserva bastante más borde, y el `unsharp` de
        # después le devuelve el filo que igual se pierde. Los valores son
        # suaves a propósito: pasarse de rosca hace aparecer halos alrededor
        # de los jugadores, que se ve peor que la imagen blanda.
        f"[fg]crop=w='min(iw\\,ih*{recorte})':h=ih:"
        f"x='(iw-min(iw\\,ih*{recorte}))*{foco_x}':y=0,"
        f"scale={ANCHO}:-2:flags=lanczos,"
        f"unsharp=luma_msize_x=5:luma_msize_y=5:luma_amount=0.9[fgs];"
        # Golpe de zoom: entra 7% más grande y se asienta en un cuarto de
        # segundo. Da la sensación de que la cámara empuja en el corte.
        f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,"
        f"scale=w='{ANCHO}*(1+0.07*exp(-7*t))':h='{ALTO}*(1+0.07*exp(-7*t))':"
        f"eval=frame:flags=bicubic,crop={ANCHO}:{ALTO}[compuesto];"
        f"[1:v]scale={ANCHO}:{ALTO}[velo];"
        f"[compuesto][velo]overlay=0:0"
    )


def _marco_y_frente(alto_ventana: int, fondo: str) -> str:
    """El clip ENTERO, centrado, con bandas de marca arriba y abajo.

    Es la alternativa a recortar. Un punto de pádel filmado de lejos es una
    unidad —los cuatro jugadores, la pelota y las paredes—: llevarlo a 9:16
    recortando se lleva un tercio del ancho y con él la mitad de lo que hace
    que la jugada se entienda.

    El espacio que sobra no es relleno: es **donde el texto no tapa la
    jugada**. Ahí van el logo y el título.
    """
    return (
        f"color=c={fondo}:s={ANCHO}x{ALTO}:r={FPS}[bg];"
        f"[0:v]scale={ANCHO}:-2:flags=lanczos,"
        f"unsharp=luma_msize_x=5:luma_msize_y=5:luma_amount=0.7,"
        f"fps={FPS},setsar=1[fgs];"
        f"[bg][fgs]overlay=(W-w)/2:(H-h)/2:shortest=1[conclip];"
        # El marco va ENCIMA del clip y no debajo: así el filo de acento y las
        # bandas recortan el video en vez de quedar tapados por él.
        f"[conclip][1:v]overlay=0:0[compuesto];"
        f"[compuesto]null"
    )


def _segmento_video(t: dict, i: int, tmp: Path, codec=None) -> Path:
    desde = float(t.get("desde", 0))
    dura = float(t["dura"])
    fuente = (RAIZ / t["archivo"]) if not Path(t["archivo"]).is_absolute() else Path(t["archivo"])
    salida = tmp / f"seg{i:02d}.mp4"

    # `dura` es siempre lo que el tramo ocupa EN EL REEL. Con cámara lenta o
    # rápida, lo que hay que tomar del original es otra cosa: un tramo de 4
    # segundos a velocidad 0,5 se come 2 segundos de material. Mantener `dura`
    # como la duración final es lo que hace que los eventos de sonido y la
    # suma total sigan cerrando sin tocar nada más.
    vel = float(t.get("velocidad", 1) or 1)
    dura_fuente = round(dura * vel, 3)

    # Tres formas de meter un clip en 9:16, y la elección es de diseño:
    #   `lleno`  (por defecto) el clip llena el cuadro y se pierde ancho
    #   `marco`  el clip queda ENTERO y las bandas llevan logo y título
    #   `recorte` mayor a 1 → bandas desenfocadas (el look viejo, casi nunca)
    marco_png = None
    if t.get("encuadre") == "marco":
        from . import analisis, rotulos
        ficha = analisis.sondear(fuente)
        prop = (ficha["ancho"] / ficha["alto"]) if ficha["alto"] else 1.0
        alto_ventana = int(round(ANCHO / max(prop, 0.05) / 2) * 2)
        marco_png, banda_sup, banda_inf = rotulos.marco(
            tmp / f"marco{i:02d}.png", ANCHO, ALTO, alto_ventana,
            logo_html=LOGO_HTML, css_marca=CSS_MARCA,
            fondo=t.get("fondo", "#0A0A0A"),
            acento="#" + LIMA.lstrip("0x").lstrip("#"))
        cadena = _marco_y_frente(alto_ventana, t.get("fondo", "#0A0A0A"))
    else:
        cadena = _fondo_y_frente(float(t.get("recorte", ANCHO / ALTO)),
                                 float(t.get("foco_x", 0.5)))
    # setpts va ANTES del fps: primero se estira o comprime el tiempo, y
    # recién después se fija la cadencia final. Al revés, la cámara lenta sale
    # a tirones porque ffmpeg duplica cuadros ya fijados.
    if vel != 1:
        cadena += f",setpts={1/vel:.6f}*PTS"
    cadena += f",fps={FPS},setsar=1"
    rot = None
    if t.get("texto"):
        from . import rotulos
        rot = tmp / f"rot{i:02d}"
        rotulos.secuencia(
            t["texto"], dura, rot, TIPO_TITULO, ANCHO, ALTO_ROTULO,
            estilo=t.get("estilo", "pop"), emoji=t.get("emoji", ""),
            cuerpo=int(t.get("cuerpo", 96)),
            acento="#" + LIMA.lstrip("0x").lstrip("#"), tinta="#0A0A0A",
            fps=FPS)
        pos = t.get("pos", "arriba")
        if marco_png:
            # En modo marco el título va en la banda, no encima de la jugada:
            # ese es todo el punto del marco.
            y = max(20, (ALTO - alto_ventana) // 2 - ALTO_ROTULO - 10) if pos == "arriba" \
                else min(ALTO - ALTO_ROTULO - 20,
                         (ALTO + alto_ventana) // 2 + 10)
            cadena += (f"[base];[3:v]format=rgba[rot];"
                       f"[base][rot]overlay=x=0:y={y}:shortest=0")
        else:
            cadena += "[base];" + _capa_rotulo("3:v", pos)
    cadena += ",format=yuv420p[v]"

    def intento(pista_audio: str):
        # La secuencia trae exactamente los cuadros que dura el tramo, así que
        # no lleva `-loop` ni `-t`: se lee como un video mudo de la duración
        # justa. `-framerate` va ANTES de `-i` — después no aplica a la entrada.
        extra = (["-framerate", str(FPS), "-i", str(rot / "%04d.png")]
                 if rot else [])
        return ["ffmpeg", "-v", "error", "-y", "-ss", str(desde),
                "-t", str(dura_fuente),
                "-i", str(fuente),
                # La entrada 1 es el velo en modo lleno y el MARCO en modo
                # marco: las dos son un PNG del tamaño del cuadro que se
                # superpone al final, así que ocupan el mismo lugar y el resto
                # de la cadena no cambia.
                "-i", str(marco_png or _velo(tmp)),
                # La pista de silencio siempre está: para concatenar, todos los
                # tramos tienen que tener las mismas pistas, y una foto o una
                # placa no traen audio propio.
                "-f", "lavfi", "-t", str(dura), "-i", "anullsrc=r=48000:cl=stereo",
                *extra,
                "-filter_complex", cadena,
                "-map", "[v]", "-map", pista_audio,
                *(codec or VIDEO_X264), *AUDIO_AAC,
                "-shortest", str(salida)]

    # Un tramo a otra velocidad va MUDO a propósito. Estirar el audio con
    # `atempo` deja la voz con tono de dibujo animado, y un tramo en cámara
    # lenta es casi siempre material de ambiente donde el sonido no aporta.
    # La música y los efectos siguen corriendo por encima en la mezcla final.
    if t.get("audio", True) and vel == 1:
        try:
            _correr(intento("0:a"), f"tramo {i} (video)")
            return salida
        except RuntimeError as e:
            # Un clip sin pista de audio, o con una que ffmpeg no puede
            # remuestrear, no debería tirar abajo el reel entero.
            print(f"  ⚠ tramo {i}: sin audio utilizable, va en silencio ({str(e)[:60]})")
    _correr(intento("2:a"), f"tramo {i} (video, en silencio)")
    return salida


def _foco_del_banco(nombre: str) -> tuple[float, float]:
    """El encuadre que ya está resuelto en fotos.json, reusado para video.

    El reel es 9:16 igual que una historia, así que corresponde el valor de
    `story`. No hay que volver a decidirlo acá: si se decide de nuevo, la misma
    foto sale distinta en la placa y en el reel.
    """
    ficha = _BANCO.get(Path(nombre).stem, {})
    foco = ficha.get("foco", {}).get("story", "50% 50%")
    try:
        x, y = (float(v.rstrip("%")) / 100 for v in foco.split())
        return x, y
    except ValueError:
        return 0.5, 0.5


def _segmento_foto(t: dict, i: int, tmp: Path, codec=None) -> Path:
    """Una foto quieta en un reel se lee como un error. Siempre lleva un
    acercamiento lento — el ojo necesita movimiento para no leerlo como que el
    video se colgó."""
    dura = float(t.get("dura", 2.5))
    fuente = (RAIZ / t["archivo"]) if not Path(t["archivo"]).is_absolute() else Path(t["archivo"])
    salida = tmp / f"seg{i:02d}.mp4"
    cuadros = int(dura * FPS)
    zoom_fin = float(t.get("zoom", 1.12))
    fx, fy = _foco_del_banco(t["archivo"])
    fx = float(t.get("foco_x", fx))
    fy = float(t.get("foco_y", fy))
    # Una foto no tiene modo marco: el título va encima, como siempre. Estos
    # dos nombres se usaban más abajo sin definirse acá —copiados de
    # `_segmento_video`— y una foto con texto moría con NameError.
    marco_png, alto_ventana = None, 0

    # PRIMERO recortar a 9:16, DESPUÉS el acercamiento. Al revés —que es como
    # estaba— zoompan toma una región con la proporción de la foto original
    # (2:3) y la mete a la fuerza en 1080×1920 (9:16): la imagen sale aplastada
    # un 16% a lo ancho. Se ve como gente más flaca y más alta. Recortando
    # antes, la región y la salida tienen la misma proporción y no hay
    # deformación posible.
    rel = ANCHO / ALTO
    cadena = (
        f"[0:v]crop=w='min(iw\\,ih*{rel})':h='min(ih\\,iw/{rel})':"
        f"x='(iw-min(iw\\,ih*{rel}))*{fx}':y='(ih-min(ih\\,iw/{rel}))*{fy}',"
        f"scale={ANCHO*2}:{ALTO*2},"
        f"zoompan=z='(1+({zoom_fin}-1)*on/{cuadros})*(1+0.07*exp(-7*on/{FPS}))':d={cuadros}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={ANCHO}x{ALTO}:fps={FPS}[b0];"
        f"[1:v]scale={ANCHO}:{ALTO}[velo];"
        f"[b0][velo]overlay=0:0,setsar=1"
    )
    rot = None
    if t.get("texto"):
        from . import rotulos
        rot = tmp / f"rot{i:02d}"
        rotulos.secuencia(
            t["texto"], dura, rot, TIPO_TITULO, ANCHO, ALTO_ROTULO,
            estilo=t.get("estilo", "pop"), emoji=t.get("emoji", ""),
            cuerpo=int(t.get("cuerpo", 96)),
            acento="#" + LIMA.lstrip("0x").lstrip("#"), tinta="#0A0A0A",
            fps=FPS)
        pos = t.get("pos", "arriba")
        if marco_png:
            # En modo marco el título va en la banda, no encima de la jugada:
            # ese es todo el punto del marco.
            y = max(20, (ALTO - alto_ventana) // 2 - ALTO_ROTULO - 10) if pos == "arriba" \
                else min(ALTO - ALTO_ROTULO - 20,
                         (ALTO + alto_ventana) // 2 + 10)
            cadena += (f"[base];[3:v]format=rgba[rot];"
                       f"[base][rot]overlay=x=0:y={y}:shortest=0")
        else:
            cadena += "[base];" + _capa_rotulo("3:v", pos)
    cadena += ",format=yuv420p[v]"

    _correr(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", str(dura), "-i", str(fuente),
             "-i", str(_velo(tmp)),
             "-f", "lavfi", "-t", str(dura), "-i", "anullsrc=r=48000:cl=stereo",
             *(["-loop", "1", "-t", str(dura), "-i", str(rot)] if rot else []),
             "-filter_complex", cadena, "-map", "[v]", "-map", "2:a",
             *(codec or VIDEO_X264), *AUDIO_AAC,
             "-shortest", str(salida)], f"tramo {i} (foto)")
    return salida


def _segmento_placa(png: Path, dura: float, i: int, tmp: Path, codec=None) -> Path:
    """Una placa ya dibujada por Chromium, convertida en tramo de video."""
    salida = tmp / f"seg{i:02d}.mp4"
    _correr(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", str(dura), "-i", str(png),
             "-f", "lavfi", "-t", str(dura), "-i", "anullsrc=r=48000:cl=stereo",
             "-vf", (f"scale={ANCHO}:{ALTO}:force_original_aspect_ratio=decrease,"
                    f"pad={ANCHO}:{ALTO}:(ow-iw)/2:(oh-ih)/2:color=#0A0A0A,"
                    f"fps={FPS},setsar=1,format=yuv420p"),
             "-map", "0:v", "-map", "1:a",
             *(codec or VIDEO_X264), *AUDIO_AAC,
             "-shortest", str(salida)], f"tramo {i} (placa)")
    return salida


def _firma(ruta: Path) -> str:
    """Los parámetros que tienen que ser idénticos para poder pegar sin recodificar."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,pix_fmt,profile,level,r_frame_rate,color_range,color_space,sample_aspect_ratio",
         "-of", "compact=p=0:nk=1", str(ruta)], capture_output=True, text=True)
    return r.stdout.strip()


def _verificar_uniformidad(segmentos: list[Path]):
    """Todos los tramos tienen que compartir parámetros o el reel no se ve en Mac.

    Esto ya pasó una vez: las placas salían en nivel 4.0 y el resto en 5.0, el
    MP4 se quedaba con el `avcC` del primero, y en QuickTime se veía el primer
    cuadro congelado con el audio corriendo. En ffmpeg se veía perfecto, así
    que el error pasó desapercibido hasta que alguien lo abrió en una Mac.
    Es barato chequearlo acá y carísimo descubrirlo del otro lado.
    """
    firmas = {}
    for s in segmentos:
        firmas.setdefault(_firma(s), []).append(s.name)
    if len(firmas) > 1:
        detalle = "\n".join(f"    {f}  <-  {', '.join(n)}" for f, n in firmas.items())
        raise RuntimeError(
            "los tramos no comparten parámetros de codificación, así que el reel "
            "no se vería en QuickTime:\n" + detalle)


def _eventos_sonoros(spec: dict, duraciones: list[float]) -> list[tuple]:
    """Dónde va cada efecto. El motor ya sabe dónde están los cortes.

    Un `whoosh` sobre el corte y un `impacto` apenas después: el barrido tapa
    el salto de imagen y el golpe le pone el pie. El `pop` va con el rótulo,
    unas milésimas después del corte para que no se pisen entre sí.
    """
    eventos, t = [], 0.0
    for i, (tramo, dur) in enumerate(zip(spec["tramos"], duraciones)):
        if i > 0:
            eventos.append((max(0, t - 0.10), "whoosh", 0.55))
            eventos.append((t, "impacto", 0.60))
        # El golpecito del rótulo se puede apagar por tramo o para todo el
        # reel: en una pieza con alguien hablando molesta más de lo que suma.
        if tramo.get("texto") and tramo.get("sonido_rotulo", True) \
                and spec.get("sonido", {}).get("rotulos", True):
            eventos.append((t + 0.06, "pop", 0.42))
        t += dur
    # el riser desemboca justo en el último tramo, que es el cierre
    if len(duraciones) > 1:
        eventos.append((max(0, t - duraciones[-1] - 1.25), "riser", 0.34))
    return eventos


def _mezclar(mudo: Path, final: Path, spec: dict, duraciones: list[float]):
    """Mezcla el audio original con la música y los efectos.

    Tres pistas y nada más: el sonido de cancha de los clips, la cama musical
    bien abajo, y los efectos por encima. Los volúmenes están puestos para que
    en un celular con el parlante chico se oiga el golpe y no la música.

    Al final va `loudnorm` a -14 LUFS, que es el nivel al que normalizan
    Instagram, TikTok y YouTube. Sin esto el reel sale bajo comparado con lo
    que hay alrededor en el feed, y encima el volumen salta entre un tramo con
    audio de cancha y uno de foto que sólo tiene la música.
    """
    from . import sonido
    dur = sum(duraciones)
    son = spec.get("sonido", {})

    entradas, mezcla, etiquetas = [], [], []
    entradas += ["-i", str(mudo)]
    mezcla.append(f"[0:a]volume={son.get('vol_original', 0.60)}[a0]")
    etiquetas.append("[a0]")

    # La música y los efectos SE PIDEN. No vienen por defecto desde el
    # 31/8/2026, y el cambio salió de escuchar un reel.
    #
    # Venían prendidos los dos, con una razón buena para la música: por la API
    # de Instagram no se le puede agregar música al publicar —un reel que sale
    # por ahí sale con el audio que tenga el archivo—, así que si no va adentro,
    # no va. Y meterla adentro no tiene problema de licencia porque `sonido.py`
    # la SINTETIZA: no se descarga nada, la cama es nuestra.
    #
    # Lo que ese razonamiento no contemplaba es un video de alguien HABLANDO a
    # cámara. Ahí una cama musical y unos golpes sintetizados encima de la voz
    # no adornan: ensucian. Y es el caso que más va a crecer, porque es el que
    # lleva subtítulos.
    #
    # Poner el default en «no» es la decisión conservadora de las dos: un reel
    # que sale sin música se publica igual y se le agrega después; uno que sale
    # con música encima de la voz hay que rehacerlo. Para que vuelva, se pide
    # —`musica` en el guion, o `efectos: true`— y eso es una palabra.
    if son.get("musica", False):
        pista = son.get("archivo_musica")
        ruta = (Path(pista) if pista
                else sonido.musica(dur, son.get("bpm"),
                                   son.get("animo", ANIMO)))
        entradas += ["-i", str(ruta)]
        n = len(etiquetas)
        mezcla.append(f"[{n}:a]volume={son.get('vol_musica', 0.26)},"
                      f"aformat=sample_rates=48000:channel_layouts=stereo[a{n}]")
        etiquetas.append(f"[a{n}]")

    if son.get("efectos", False):
        ruta = sonido.pista_efectos(_eventos_sonoros(spec, duraciones), dur)
        entradas += ["-i", str(ruta)]
        n = len(etiquetas)
        mezcla.append(f"[{n}:a]volume={son.get('vol_efectos', 0.85)},"
                      f"aformat=sample_rates=48000:channel_layouts=stereo[a{n}]")
        etiquetas.append(f"[a{n}]")

    cadena = ";".join(mezcla) + ";" + "".join(etiquetas) + \
        f"amix=inputs={len(etiquetas)}:normalize=0:duration=first," \
        f"loudnorm=I=-14:TP=-1.5:LRA=11," \
        f"aformat=sample_rates=48000:channel_layouts=stereo[out]"

    _correr(["ffmpeg", "-v", "error", "-y", *entradas,
             "-filter_complex", cadena,
             "-map", "0:v", "-map", "[out]",
             "-c:v", "copy", *AUDIO_AAC,
             "-movflags", "+faststart", str(final)], "mezcla de audio")


def reel(spec: dict, salida: Path = SALIDA) -> Path:
    """Arma el reel completo. Devuelve la ruta del mp4.

    `salida` es parámetro para poder escribir directo en la carpeta de
    entrega y ahorrarse el turno de copiar desde `out/`.
    """
    SALIDA = Path(salida)
    SALIDA.mkdir(parents=True, exist_ok=True)
    tmp = SALIDA / f"_tmp_{spec['nombre']}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    # La tapa de cierre entra como un tramo de tipo `placa`, que el motor ya
    # sabe pegar. No hace falta ninguna maquinaria nueva: es una imagen fija
    # con una duración, igual que una foto.
    tramos = list(spec["tramos"])
    cierre = spec.get("cierre") or {}
    if cierre.get("texto"):
        png = _cierre_png(str(cierre["texto"]), str(cierre.get("pie") or ""), tmp)
        tramos.append({"tipo": "placa", "archivo": str(png),
                       "dura": float(cierre.get("dura") or DURA_CIERRE)})

    # Si después viene una pasada de texto, los tramos son archivos de paso y
    # se codifican rápido: lo que se comprima con cuidado acá se descarta en
    # esa pasada. Si no viene ninguna, el tramo es el resultado.
    subs = spec.get("subtitulos") or []
    hook = str(spec.get("hook") or "")
    codec = VIDEO_INTERMEDIO if (subs or hook) else VIDEO_X264

    segmentos = []
    for i, t in enumerate(tramos):
        tipo = t.get("tipo", "video")
        if tipo == "video":
            segmentos.append(_segmento_video(t, i, tmp, codec))
        elif tipo == "foto":
            segmentos.append(_segmento_foto(t, i, tmp, codec))
        elif tipo == "placa":
            ruta = (RAIZ / t["archivo"]) if not Path(t["archivo"]).is_absolute() else Path(t["archivo"])
            segmentos.append(_segmento_placa(ruta, float(t.get("dura", 1.6)), i, tmp, codec))
        else:
            raise ValueError(f"tipo de tramo desconocido: {tipo}")
        print(f"  tramo {i+1}/{len(tramos)} · {tipo}")

    _verificar_uniformidad(segmentos)

    lista = tmp / "lista.txt"
    lista.write_text("".join(f"file '{s.resolve()}'\n" for s in segmentos), encoding="utf-8")

    final = SALIDA / f"{spec['nombre']}.mp4"
    mudo = tmp / "sin-mezclar.mp4"
    # Todos los tramos salieron con los mismos parámetros, así que el concat
    # puede copiar los flujos sin recodificar: es instantáneo y sin pérdida.
    _correr(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
             "-i", str(lista), "-c", "copy", "-movflags", "+faststart",
             str(mudo)], "concatenado")

    if subs or hook:
        print(f"  quemando {len(subs)} subtítulos"
              + (f" y el hook «{hook}»" if hook else ""))
        mudo = _quemar_textos(mudo, subs, hook, tmp)

    duraciones = [float(t.get("dura", 2.5)) for t in tramos]
    if spec.get("sonido", {}).get("activo", True):
        print("  mezclando audio")
        _mezclar(mudo, final, spec, duraciones)
    else:
        shutil.copy(mudo, final)

    if not spec.get("conservar_tmp"):
        shutil.rmtree(tmp, ignore_errors=True)
    return final


def duracion(ruta: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(ruta)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


if __name__ == "__main__":
    # video.py reel.json [carpeta-de-salida]
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    ruta = reel(spec, Path(sys.argv[2]) if len(sys.argv) > 2 else SALIDA)
    print(f"→ {ruta.name}  ·  {duracion(ruta):.1f}s  ·  "
          f"{ruta.stat().st_size/1024/1024:.1f} MB")


def desde_guion(g: dict, nombre: str, carpeta_material, salida: Path,
                materiales: dict | None = None,
                vocabulario: str = "", marca: str = "",
                correcciones: list[dict] | None = None
                ) -> tuple[Path, list[str], dict]:
    """Valida un guion de edición, lo traduce y lo renderiza.

    Es la puerta que usa el agente. Existe para que el guion se valide SIEMPRE
    antes de encodear: un encode tarda minutos y descubrir a los tres minutos
    que un tramo pedía un segundo que no existe es tirar esos tres minutos, con
    un error de ffmpeg que no explica nada.

    Devuelve (ruta del mp4, avisos, guion armado). El tercero es el guion ya
    resuelto —tramos concretos, subtítulos escritos, hook decidido—: es lo que
    permite retocar el reel después sin volver a transcribir. Ver el comentario
    al final de esta función.
    """
    from . import analisis as _analisis
    from . import guion as _guion
    # Acá arriba y no adentro de cada rama: con correcciones aprendidas se
    # usaba antes del primer `import` de más abajo, y como ese import lo hace
    # local a la función, Python lo veía como «usado antes de asignar».
    from . import habla as _habla

    base = Path(carpeta_material)
    avisos_previos: list[str] = []

    # Las correcciones que la marca ya aprendió entran DOS veces, y las dos
    # hacen falta.
    #
    # **Antes de escuchar**, como vocabulario: al modelo se le dice que estas
    # palabras existen, y muchas veces con eso ya las escribe bien. Eso es
    # evitar el error.
    #
    # **Después de escribir**, como reemplazo sobre el texto. Eso es taparlo,
    # y hace falta igual: el vocabulario ayuda pero no garantiza nada, y la
    # persona que corrigió «vos panel» una vez tiene derecho a no volver a
    # verlo nunca más.
    # Las palabras que Gemini oyó o vio en ESTE material (ver `motor/mirar.py`).
    # El vocabulario de la marca sabe de qué habla la marca; esto sabe de qué
    # habla el video, que no es lo mismo: en un video de pádel de Asistime,
    # «pádel» no está en ningún lado salvo en el video.
    del_video = _habla.en_frase([str(w).strip() for w in (g.get("vocabulario") or [])
                                 if str(w).strip()])
    if del_video:
        vocabulario = " ".join(x for x in (vocabulario, del_video) if x)

    correcciones = [c for c in (correcciones or [])
                    if str(c.get("de") or "").strip()]
    if correcciones:
        # Se pega como una FRASE, no como una lista separada por comas: el
        # modelo copia la puntuación de lo que se le pasa, y una lista le
        # enseña a escribir sin signos. Ver `habla.vocabulario_de`.
        propios = _habla.en_frase(sorted({str(c["a"]).strip() for c in correcciones
                                          if str(c.get("a") or "").strip()}))
        vocabulario = " ".join(x for x in (vocabulario, propios) if x)

    def _corregido(texto: str) -> str:
        for c in correcciones:
            texto = texto.replace(str(c["de"]).strip(), str(c.get("a") or "").strip())
        return texto

    # Un tramo sin `hasta` llega hasta el final del clip. Es lo que permite
    # escribir «usá este video» sin haberlo mirado, y lo que hace que el guion
    # mínimo sea una lista de archivos y nada más.
    faltan = [t0 for t0 in (g.get("tramos") or []) if t0.get("hasta") is None]
    if faltan:
        from . import analisis as _an0
        g = dict(g)
        g["tramos"] = [dict(t0) for t0 in g["tramos"]]
        for t0 in g["tramos"]:
            if t0.get("hasta") is None:
                ruta = base / (t0.get("archivo") or "")
                try:
                    t0["hasta"] = round(_an0.sondear(ruta)["duracion"], 2)
                    t0.setdefault("desde", 0.0)
                except Exception as e:                       # noqa: BLE001
                    log.warning("no pude medir %s: %s", ruta, e)

    # `cortar_silencios` saca los tiempos muertos: un tramo se abre en varios,
    # uno por cada pedazo donde alguien habla. Va ANTES de los subtítulos
    # porque cambia los tramos, y los subtítulos se calculan sobre los tramos
    # finales — al revés, cada frase caería en el segundo equivocado.
    if g.get("cortar_silencios"):
        from . import analisis as _an
        from . import habla as _habla
        g = dict(g)
        abiertos = []
        for t0 in (g.get("tramos") or []):
            arch = (t0.get("archivo") or "").strip()
            ruta = base / arch
            if not arch or not ruta.exists():
                abiertos.append(t0)
                continue
            try:
                pedazos = _an.tramos_hablados(
                    ruta, desde=float(t0.get("desde", 0)),
                    hasta=float(t0["hasta"]) if t0.get("hasta") is not None else None,
                    palabras=_habla.palabras(ruta, vocabulario or ""))
            except Exception as e:                           # noqa: BLE001
                log.warning("no pude medir los silencios de %s: %s", arch, e)
                pedazos = []
            if not pedazos:
                abiertos.append(t0)
                continue
            for a, b in pedazos:
                abiertos.append({**t0, "desde": a, "hasta": b})
        quitado = sum(float(x["hasta"]) - float(x["desde"]) for x in (g.get("tramos") or [])) \
            - sum(float(x["hasta"]) - float(x["desde"]) for x in abiertos)
        g["tramos"] = abiertos
        if quitado > 0.2:
            log.info("tiempos muertos sacados: %.1fs", quitado)
            avisos_previos.append(
                f"se sacaron {quitado:.1f}s de tiempos muertos y quedaron "
                f"{len(abiertos)} tramos")

    # `duracion_objetivo` — cuando alguien pide un largo, se elige QUÉ entra.
    #
    # Va después del recorte de silencios y antes de los subtítulos: necesita
    # los tramos ya definidos para saber cuánto dura cada uno, y los subtítulos
    # se calculan sobre los tramos finales.
    #
    # **Sin objetivo no se descarta nada.** Sacar los silencios es indiscutible
    # —nadie extraña una pausa—, pero tirar una frase entera es una decisión
    # editorial, y un motor no debería tomarla sin que se la pidan. Un reel
    # largo se acorta; una frase que el sistema tiró en silencio no se
    # recupera.
    objetivo = float(g.get("duracion_objetivo") or 0)
    if objetivo > 0 and (g.get("tramos") or []):
        from . import habla as _habla
        g = dict(g)
        conteo = []
        for t0 in g["tramos"]:
            desde0 = float(t0.get("desde", 0))
            hasta0 = float(t0.get("hasta", desde0))
            vel0 = float(t0.get("velocidad", 1) or 1)
            pal = _habla.palabras(base / (t0.get("archivo") or ""), vocabulario or "")
            dicho = " ".join(w["texto"] for w in pal
                             if desde0 <= w["desde"] < hasta0)
            conteo.append({"dura": (hasta0 - desde0) / vel0, "texto": dicho})
        quedan = _habla.elegir_tramos(conteo, objetivo, marca)
        if len(quedan) < len(g["tramos"]):
            fuera = sum(conteo[i]["dura"] for i in range(len(conteo))
                        if i not in quedan)
            g["tramos"] = [g["tramos"][i] for i in quedan]
            avisos_previos.append(
                f"para llegar a los {objetivo:.0f}s se dejaron afuera "
                f"{len(conteo) - len(quedan)} tramos ({fuera:.0f}s)")

    # `encuadre: "caras"` — el recorte vertical va a donde están las caras.
    #
    # Va DESPUÉS de los silencios y del largo objetivo, porque parte los
    # tramos que quedaron; y ANTES de los subtítulos, porque partir un tramo
    # en pedazos contiguos no cambia el reloj del reel y los subtítulos se
    # calculan sobre los tramos finales. Ver `motor/encuadre.py` para qué
    # decide y con qué datos. Si no puede, los tramos quedan como estaban.
    if str(g.get("encuadre") or "").strip().lower() == "caras" and (g.get("tramos") or []):
        from . import encuadre as _encuadre
        g = dict(g)
        try:
            g["tramos"], avisos_enc = _encuadre.aplicar(g["tramos"], base)
            avisos_previos += avisos_enc
        except Exception as e:                               # noqa: BLE001
            log.warning("no pude encuadrar por caras: %s; sale centrado", e)
            avisos_previos.append(f"no pude encuadrar por caras ({e}); sale centrado")

    # `subtitulos: "auto"` significa «sacalos de lo que se dice en el video».
    # Se resuelve ACÁ y no en cada puerta porque por acá pasan las dos: la tool
    # del chat y el agente diseñador que corre `video.py guion.json`. Una sola
    # vez, y ninguna de las dos se puede olvidar.
    #
    # Va ANTES de validar a propósito: lo que salga de la transcripción se
    # valida igual que si lo hubiera escrito una persona. Si el audio no tiene
    # voz, esto devuelve una lista vacía y el reel sale sin subtítulos, que es
    # lo correcto — no todo video tiene algo que subtitular.
    if isinstance(g.get("subtitulos"), str) and \
            g["subtitulos"].strip().lower() in ("auto", "automatico", "automático"):
        from . import habla as _habla
        g = dict(g)
        try:
            frases = _habla.para_guion(g, base, vocabulario or "")
            if correcciones:
                arregladas = 0
                for f in frases:
                    antes = f.get("texto", "")
                    f["texto"] = _corregido(antes)
                    arregladas += f["texto"] != antes
                if arregladas:
                    log.info("%d frases arregladas con lo que la marca ya sabe",
                             arregladas)
            g["subtitulos"] = frases
            log.info("subtítulos automáticos: %d frases", len(g["subtitulos"]))

            # ── Si NADIE habla, el reel sale con música ─────────────────
            #
            # La música quedó apagada por defecto el 31/8/2026 y por una razón
            # buena, que sigue estando escrita en `_mezclar`: encima de alguien
            # hablando a cámara, una cama musical no adorna, ensucia.
            #
            # Pero ese argumento vale sólo cuando hay una voz. Un clip generado
            # por IA, o un peloteo filmado sin nadie hablando, sale mudo — y un
            # reel mudo en Instagram es un reel que se pasa de largo: no hay
            # nada que sostenga los tres segundos que decide el pulgar.
            #
            # Así que la regla completa es: **la música se apaga porque hay una
            # voz, no porque sí.** Si se escuchó el material y no se dijo una
            # sola palabra, vuelve. Y si el guion ya opinó —en un sentido o en
            # el otro— manda el guion: esto no pisa una decisión, llena un
            # hueco.
            if not frases:
                son = dict(g.get("sonido") or {})
                if "musica" not in son:
                    son["musica"] = True
                    g["sonido"] = son
                    log.info("nadie habla en el material: el reel va con música")
        except Exception as e:                               # noqa: BLE001
            # Un reel sin subtítulos es peor que uno con subtítulos, pero es
            # muchísimo mejor que ningún reel. Se sigue y se avisa.
            log.warning("no pude sacar los subtítulos del audio: %s", e)
            g["subtitulos"] = []
            avisos_previos.append(
                "no pude sacar los subtítulos del audio, así que el reel sale "
                f"sin ellos ({e})")

    # `hook: "auto"` — el sistema escribe la frase de enganche a partir de lo
    # que se dice. Va DESPUÉS de los subtítulos porque los reusa: el texto ya
    # está transcrito y sale gratis.
    #
    # El hook escrito a mano gana siempre: si el guion trae una frase, esa
    # frase manda y no se llama a nadie. «auto» es para cuando quien pide el
    # reel no sabe qué dice el video —que es el caso del chat, donde el agente
    # no puede escuchar el material.
    if isinstance(g.get("hook"), str) and \
            g["hook"].strip().lower() in ("auto", "automatico", "automático"):
        from . import habla as _habla
        g = dict(g)
        dicho = " ".join(s.get("texto", "") for s in (g.get("subtitulos") or []))
        g["hook"] = _corregido(_habla.hook_de(dicho, marca)) if dicho else ""
        if g["hook"]:
            log.info("hook automático: «%s»", g["hook"])
        else:
            avisos_previos.append(
                "no pude escribir el hook automático, el reel sale sin él")
    if materiales is None:
        # Si no vino el análisis hecho, se sondean los archivos del guion. Es
        # barato —leer cabeceras, no decodificar— y hace que la validación
        # funcione igual aunque alguien llame a esto a mano.
        materiales = {}
        for t in (g.get("tramos") or []):
            arch = (t.get("archivo") or "").strip()
            if arch and arch not in materiales and (base / arch).exists():
                try:
                    materiales[arch] = _analisis.sondear(base / arch)["duracion"]
                except Exception:
                    pass
        # La música puede no tener archivo: ahí es la cama sintetizada.
        pista = (g.get("musica") or {}).get("archivo")
        if pista and (base / pista).exists():
            materiales.setdefault(pista, 0.0)

    avisos = avisos_previos + _guion.verificar(g, materiales)

    # El guion RESUELTO, para poder retocar el reel después sin rehacerlo.
    #
    # Hasta acá `g` fue pasando de lo que pidió la persona —«usá estos tres
    # videos, sacá los tiempos muertos, subtítulos automáticos»— a algo
    # concreto: diez tramos con su entrada y su salida, veintidós frases con su
    # segundo, un hook escrito. Eso es lo caro y lo que no se repite igual:
    # volver a escuchar el audio da los mismos errores de transcripción otra
    # vez, y volver a medir los silencios puede dar tramos apenas distintos.
    #
    # Guardarlo hace que corregir una frase sea corregir UNA FRASE: se cambia
    # ese texto y se vuelve a dibujar, y todo lo demás queda idéntico. Sin
    # esto, cualquier retoque obligaría a rehacer el reel entero y con él a
    # rehacer los aciertos.
    #
    # No es un formato nuevo: **es un guion válido**, el mismo que entra por
    # arriba. Devolvérselo a esta función lo vuelve a dibujar igual.
    #
    # Las dos órdenes que YA se ejecutaron se sacan, y eso no es un detalle: si
    # quedaran, la próxima vuelta volvería a recortar unos tramos ya recortados
    # y a elegir dentro de una selección ya hecha. Se irían comiendo el reel de
    # a poco en cada retoque.
    armado = {k: v for k, v in g.items()
              if k not in ("cortar_silencios", "duracion_objetivo", "encuadre")}

    spec = _guion.a_spec(g, nombre, base)
    return reel(spec, salida), avisos, armado
