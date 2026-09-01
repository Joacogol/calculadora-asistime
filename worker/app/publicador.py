# -*- coding: utf-8 -*-
"""La cola de publicación: de una fila en `publicaciones` a un posteo real.

## Por qué es una cola y no un botón que llama a la API

Porque publicar tarda y puede fallar a mitad de camino. Un reel de 30 segundos
puede pasar dos minutos procesándose del lado de Meta. Si eso colgara de una
petición del navegador, cerrar la pestaña dejaría el posteo en un limbo del que
nadie se entera.

Con una cola, la app sólo escribe una fila y se olvida. El worker —que ya
arranca cada minuto por los diseños— la levanta, la lleva hasta el final y va
contando en qué anda. Cerrar la pestaña no cambia nada, y programar para el
martes a las 9 es la misma fila con otra fecha.

## La máquina de estados

    programado ──(llegó la hora)──> subiendo ──> publicado
         ▲                             │
         └──── error temporal ─────────┴──> error   (con el motivo, en castellano)

`subiendo` guarda el id del contenedor de Instagram. Si la corrida se corta
—Cloud Run tiene un límite de tiempo— la siguiente encuentra el contenedor ya
creado y sigue desde ahí en vez de empezar de nuevo. Sin eso, un reel largo
nunca terminaría de publicarse: cada corrida volvería a subir el video.

## Nada se publica solo

Una fila en esta tabla la crea una persona apretando «Publicar» o programando
una fecha. El worker no decide publicar nada por su cuenta, y `disenar()` no
escribe acá. Es a propósito: el día que el agente se equivoque en una placa,
que el error quede en una pantalla y no en el feed del cliente.
"""
import logging
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image

from . import config, supa
from .instagram import (CODIGO_TOKEN, ESPERA_FOTO, ESPERA_VIDEO,
                        ErrorInstagram, Instagram)
from .supa import Cliente

log = logging.getLogger(__name__)

MAX_INTENTOS = 4
ESPERA_BASE = 5          # minutos; se multiplica por el número de intento

# Cuánto tiene que hacer que nadie toca una fila en `subiendo` para que otra
# corrida se anime a retomarla. Tiene que ser mayor que lo que tarda una
# corrida en soltarla (ESPERA_VIDEO, 90 segundos) o dos corridas trabajarían
# sobre la misma fila y publicarían dos veces.
RANCIO = timedelta(minutes=4)

# Cuántas veces se retoma un contenedor que sigue procesando antes de darlo por
# perdido. Con RANCIO de 4 minutos, 15 vueltas son una hora. Un video nuestro
# de 30 segundos tarda menos de dos minutos; si pasó una hora, no se está
# procesando, se colgó, y dejarlo girando para siempre es peor que decirlo.
MAX_ESPERAS = 15

# Instagram sólo acepta JPEG. Las placas salen en PNG, así que esto no es una
# optimización: es el paso sin el cual no publica nada.
CALIDAD_JPEG = 90

# Lo que el feed acepta: de 4:5 (una vertical) a 1.91:1 (una apaisada). Una
# story de 1080×1920 da 0,5625 y el feed la rechaza. Vale la pena chequearlo
# acá para poder decir QUÉ pieza está mal, en vez de recibir de Meta un
# «media no soportada» que no dice cuál de las cinco.
#
# Nuestros formatos: `post` da 1080×1080 (1,0) y `vert` da 1080×1350 (0,80
# exacto, el borde). `story` y `reel` dan 1080×1920 (0,5625) y por eso una
# story nunca puede ir al feed: no es una decisión de diseño, no entra.
FEED_MIN, FEED_MAX = 0.80, 1.91
# El margen es para el redondeo del borde, no para dejar pasar medidas que
# Instagram va a rechazar igual: 1080×1360 da 0,794 y tiene que frenar acá,
# donde el mensaje dice qué archivo es, y no allá, donde dice «media inválida».
MARGEN = 0.005

VIDEO_EXT = {".mp4", ".mov"}


def _ahora():
    return datetime.now(timezone.utc)


def _rancio() -> str:
    """El corte a partir del cual una fila en `subiendo` se considera colgada."""
    return (_ahora() - RANCIO).isoformat()


def _es_video(url: str) -> bool:
    return Path(urlparse(url).path).suffix.lower() in VIDEO_EXT


# ─────────────────────────────────────────────────────────────── conversión

def _para_instagram(cli: Cliente, pub_id: str, indice: int, url: str,
                    carpeta: Path, feed: bool) -> str:
    """Devuelve una URL que Instagram sí acepte.

    Se guarda al lado de la pieza original, en `publicar/`, en vez de pisarla:
    el JPEG pierde calidad en cada guardado y la placa original es la que se
    descarga desde el chat. Son dos archivos con dos usos distintos.
    """
    ruta = Path(urlparse(url).path)
    if ruta.suffix.lower() in (".jpg", ".jpeg"):
        return url

    local = carpeta / f"{indice:02d}{ruta.suffix or '.png'}"
    supa.bajar(url, local)

    with Image.open(local) as im:
        ancho, alto = im.size
        proporcion = ancho / alto if alto else 0
        if feed and not (FEED_MIN - MARGEN <= proporcion <= FEED_MAX + MARGEN):
            raise ErrorInstagram(
                f"«{ruta.name}» mide {ancho}×{alto} y el feed de Instagram "
                f"sólo acepta entre 4:5 y 1.91:1. Si es una story, publicala "
                f"como story.")
        # El PNG puede traer transparencia; el JPEG no la tiene. Sin este
        # paso, lo transparente sale NEGRO, que en una marca que vive en
        # blanco es exactamente el peor resultado posible.
        if im.mode in ("RGBA", "LA", "P"):
            fondo = Image.new("RGB", im.size, (255, 255, 255))
            im = im.convert("RGBA")
            fondo.paste(im, mask=im.split()[-1])
            plano = fondo
        else:
            plano = im.convert("RGB")
        jpg = local.with_suffix(".jpg")
        plano.save(jpg, "JPEG", quality=CALIDAD_JPEG, optimize=True,
                   subsampling=0)

    destino = f"publicar/{pub_id}/{jpg.name}"
    return cli.subir(jpg, destino)


# ────────────────────────────────────────────────────────────── contenedores

def _armar(cli: Cliente, ig: Instagram, fila: dict, carpeta: Path) -> str:
    """Crea el contenedor que corresponde al tipo, y devuelve su id."""
    tipo = fila.get("tipo") or "post"
    urls = [u for u in (fila.get("urls") or []) if u]
    caption = fila.get("caption") or ""
    if not urls:
        raise ErrorInstagram("La publicación no tiene ninguna pieza.")

    if tipo == "reel":
        video = urls[0]
        if not _es_video(video):
            raise ErrorInstagram("Un reel necesita un video, y esto es una "
                                 "imagen. Publicalo como post.")
        # La segunda URL, si viene, es la tapa. Instagram la pide en JPEG
        # igual que todo lo demás.
        portada = ""
        if len(urls) > 1 and not _es_video(urls[1]):
            portada = _para_instagram(cli, fila["id"], 1, urls[1], carpeta,
                                      feed=False)
        return ig.contenedor_reel(video, caption, portada)

    if tipo == "story":
        pieza = urls[0]
        if _es_video(pieza):
            return ig.contenedor_story(pieza, es_video=True)
        return ig.contenedor_story(
            _para_instagram(cli, fila["id"], 0, pieza, carpeta, feed=False))

    if tipo == "carrusel":
        # Cada diapositiva es un contenedor «hijo»: se crea pero no se publica
        # sola. Recién el contenedor de carrusel las junta en un solo posteo.
        hijos = []
        for i, u in enumerate(urls[:10]):
            listo = _para_instagram(cli, fila["id"], i, u, carpeta, feed=True)
            hijos.append(ig.contenedor_imagen(listo, hijo=True))
        return ig.contenedor_carrusel(hijos, caption)

    return ig.contenedor_imagen(
        _para_instagram(cli, fila["id"], 0, urls[0], carpeta, feed=True),
        caption)


# ─────────────────────────────────────────────────────────────────── la cola

def _fallar(cli: Cliente, fila: dict, e: ErrorInstagram):
    """Decide si esto se reintenta o si hay que avisarle a la persona."""
    intentos = int(fila.get("intentos") or 0) + 1
    if e.reintentable and intentos < MAX_INTENTOS:
        cuando = _ahora() + timedelta(minutes=ESPERA_BASE * intentos)
        cli.marcar_publicacion(
            fila["id"], "programado",
            intentos=intentos, contenedor=None,
            publicar_en=cuando.isoformat(),
            mensaje=f"Reintento {intentos} de {MAX_INTENTOS}: {e}")
        log.warning("[%s] publicación %s se reintenta a las %s — %s",
                    cli.marca, fila["id"], cuando.strftime("%H:%M"), e)
        return
    cli.marcar_publicacion(fila["id"], "error", intentos=intentos,
                           mensaje=str(e)[:500])


def procesar(cli: Cliente, ig: Instagram, fila: dict):
    pub_id = fila["id"]
    previo = fila.get("estado") or "programado"

    if not cli.tomar_publicacion(pub_id, previo, _rancio()):
        log.info("[%s] publicación %s ya la tomó otra corrida", cli.marca, pub_id)
        return

    carpeta = Path(tempfile.mkdtemp(prefix="pub-", dir="/tmp"))
    try:
        contenedor = fila.get("contenedor") or ""
        if not contenedor:
            contenedor = _armar(cli, ig, fila, carpeta)
            # Se guarda ANTES de publicar. Si la corrida se muere en el medio,
            # la siguiente retoma este contenedor en vez de volver a subir
            # todo — y sobre todo, no crea un segundo posteo.
            cli.marcar_publicacion(pub_id, "subiendo", contenedor=contenedor)

        # Meta procesa el contenedor de su lado antes de dejar publicarlo. Si
        # no llegó a terminar, se deja como está: la corrida del minuto que
        # viene lo encuentra en `subiendo` con su contenedor y sigue esperando.
        #
        # **Esto se le pregunta a todo, no sólo a los videos.** Antes las fotos
        # se publicaban derecho, porque una foto está lista al instante — hasta
        # el 1/9/2026, cuando una placa de Clínica no lo estuvo, Meta contestó
        # «a mídia não está pronta para ser publicada» y el posteo se dio por
        # perdido con ese texto en portugués como toda explicación. Preguntar
        # cuesta una llamada y, cuando la foto ya está lista —que es casi
        # siempre—, esa llamada contesta FINISHED en el primer intento.
        tipo = fila.get("tipo") or "post"
        urls = fila.get("urls") or []
        lento = tipo == "reel" or (urls and _es_video(urls[0]))
        if not ig.esperar(contenedor, ESPERA_VIDEO if lento else ESPERA_FOTO):
            esperas = int(fila.get("esperas") or 0) + 1
            if esperas >= MAX_ESPERAS:
                raise ErrorInstagram(
                    "Instagram lleva más de una hora procesando la pieza y no "
                    "termina. " + ("Probá con un video más corto o más liviano."
                                   if lento else
                                   "Probá pidiéndola de nuevo."))
            # Se cuenta aparte de `intentos` a propósito: esperar a que Meta
            # termine no es haber fallado, y mezclarlos haría que un error de
            # red pasajero después de tres esperas se diera por perdido.
            # La marca de tiempo se refresca sola con el disparador: la fila
            # queda protegida otros cuatro minutos y después se retoma.
            cli.marcar_publicacion(pub_id, "subiendo", esperas=esperas)
            log.info("[%s] publicación %s: Instagram sigue procesando (%d)",
                     cli.marca, pub_id, esperas)
            return

        media = ig.publicar(contenedor)
        cli.marcar_publicacion(pub_id, "publicado", ig_id=media,
                               permalink=ig.permalink(media), mensaje=None)
        log.info("[%s] publicación %s salió en Instagram (%s)",
                 cli.marca, pub_id, media)

    except ErrorInstagram as e:
        if e.codigo == CODIGO_TOKEN:
            _desconectar(cli, str(e))
        _fallar(cli, fila, e)
    except requests.RequestException as e:
        # Bajar la pieza del Storage o subir el JPEG también puede fallar por
        # red, y eso no es culpa de Instagram ni motivo para dar el posteo por
        # perdido. Se trata como un error temporal y se reintenta.
        log.warning("[%s] publicación %s: problema de red — %s",
                    cli.marca, pub_id, e)
        _fallar(cli, fila, ErrorInstagram(
            f"Problema de red al preparar la pieza: {e}", reintentable=True))
    except Exception as e:
        log.exception("[%s] falló la publicación %s", cli.marca, pub_id)
        cli.marcar_publicacion(pub_id, "error", mensaje=str(e)[:500],
                               intentos=int(fila.get("intentos") or 0) + 1)
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


# ──────────────────────────────────────────────────────────────────── cuenta

def _desconectar(cli: Cliente, motivo: str):
    cuenta = cli.leer_cuenta_ig()
    if cuenta:
        cli.guardar_cuenta_ig(cuenta["id"], activa=False, mensaje=motivo)
    log.error("[%s] cuenta de Instagram desactivada: %s", cli.marca, motivo)


def _mantener_token(cli: Cliente, ig: Instagram, cuenta: dict):
    """Renueva el token de 60 días una semana antes de que se venza.

    Se hace con anticipación a propósito: un token vencido no se puede
    renovar, hay que volver a autorizar la app a mano desde el panel de Meta.
    Una semana de margen aguanta que el worker esté caído unos días sin que se
    pierda la conexión.
    """
    vence = cuenta.get("expira_en")
    if not vence:
        # Un token recién conectado no trae fecha: los del panel de Meta duran
        # 60 días desde que se generan. Se anota la estimación y en la próxima
        # renovación queda la fecha exacta que devuelve Meta.
        estimado = datetime.fromisoformat(
            cuenta["renovado_en"].replace("Z", "+00:00")) + timedelta(days=60)
        cli.guardar_cuenta_ig(cuenta["id"], expira_en=estimado.isoformat())
        return

    if datetime.fromisoformat(vence.replace("Z", "+00:00")) > _ahora() + timedelta(days=7):
        return

    try:
        nuevo, dura = ig.refrescar()
    except ErrorInstagram as e:
        log.error("[%s] no pude renovar el token de Instagram: %s", cli.marca, e)
        if e.codigo == CODIGO_TOKEN:
            _desconectar(cli, "El token se venció. Hay que reconectar la cuenta.")
        return

    ig.token = nuevo
    cli.guardar_cuenta_ig(
        cuenta["id"], token=nuevo, renovado_en=_ahora().isoformat(),
        expira_en=(_ahora() + timedelta(seconds=dura)).isoformat(),
        activa=True, mensaje=None)
    log.info("[%s] token de Instagram renovado por %d días",
             cli.marca, dura // 86400)


def atender(cli: Cliente) -> int:
    """Todo lo que este cliente tenga para publicar ahora."""
    cuenta = cli.leer_cuenta_ig()
    if not cuenta or not cuenta.get("token"):
        return 0                       # publicar es opcional, y no todos lo usan

    ig = Instagram(cuenta["token"], cuenta.get("ig_user_id") or "")
    _mantener_token(cli, ig, cuenta)

    if not ig.id:
        # La primera vez se le pregunta a Meta de qué cuenta es el token y se
        # guarda, para no gastar una llamada por corrida el resto del año.
        try:
            quien = ig.quien()
        except ErrorInstagram as e:
            if e.codigo == CODIGO_TOKEN:
                _desconectar(cli, str(e))
            log.error("[%s] token de Instagram sin identificar: %s", cli.marca, e)
            return 0
        cli.guardar_cuenta_ig(cuenta["id"], ig_user_id=quien.get("id"),
                              usuario=quien.get("username"))
        log.info("[%s] Instagram conectado como @%s",
                 cli.marca, quien.get("username"))

    filas = cli.leer_publicaciones(config.MAX_PUBLICACIONES, _rancio())
    if not filas:
        return 0
    log.info("[%s] %d publicación(es) en cola", cli.marca, len(filas))
    for fila in filas:
        procesar(cli, ig, fila)
    return len(filas)
