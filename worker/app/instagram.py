# -*- coding: utf-8 -*-
"""La API de publicación de Instagram, y nada más.

Este módulo no sabe qué es un diseño ni qué es un cliente: recibe URLs y
devuelve ids. Toda la lógica de cola vive en `publicador.py`. La separación
importa porque esta parte es la única que se rompe cuando Meta cambia algo, y
conviene que ese arreglo no toque el resto.

## Cómo publica Instagram

Nunca en una sola llamada. Siempre son dos pasos:

    1. crear un CONTENEDOR con la URL del archivo   → devuelve un id
    2. PUBLICAR ese contenedor                       → devuelve el id del posteo

El archivo lo baja Instagram de una URL pública nuestra; no se sube por la API.
Por eso las piezas tienen que estar en el Storage público antes de publicar, y
por eso un bucket privado rompería la publicación aunque el chat siguiera
andando.

Un contenedor sin publicar se vence solo a las 24 horas. Eso es lo que hace que
crear uno sea una prueba inofensiva.

## El detalle que cuesta una tarde

**Instagram no acepta PNG.** El endpoint devuelve un error genérico de «media
no soportada» que no menciona el formato. Nuestras placas salen en PNG, así que
la conversión a JPEG no es una optimización: sin ella no publica nada. La hace
`publicador.py` antes de llamar acá.

## Token

Es de 60 días y se renueva con `refrescar()`. Se puede renovar recién a las 24
horas de emitido, y no se puede renovar uno ya vencido: si se venció, hay que
volver a autorizar la app a mano. De ahí que el worker lo renueve con una
semana de anticipación y no el último día.
"""
import logging
import time

import requests

log = logging.getLogger(__name__)

BASE = "https://graph.instagram.com"
TIEMPO = 60

# Instagram corta el pie de foto en 2.200 caracteres. Si mandamos más, no
# devuelve error: publica el posteo con el texto cortado por la mitad. Mejor
# cortarlo nosotros y que se note en el log.
MAX_CAPTION = 2200

# Cuánto esperamos a que Instagram termine de procesar un contenedor DENTRO de
# una corrida. Si no llegó, el contenedor queda guardado y la corrida siguiente
# lo retoma: el worker arranca cada minuto, así que no se pierde nada. Bloquear
# quince minutos esperando un video frenaría los diseños de los demás clientes.
ESPERA_VIDEO = 90

# Una foto se procesa en un segundo o dos, así que veinte es de sobra y no vale
# la pena frenar la corrida más que eso. Pero **no es cero**: el 1/9/2026 una
# placa de Clínica se dio por perdida porque se publicó sin preguntar si estaba
# lista y Meta contestó «a mídia não está pronta». Casi siempre lo está; casi
# siempre no es siempre.
ESPERA_FOTO = 20


class ErrorInstagram(RuntimeError):
    """Un error que devolvió Meta, ya traducido a algo que se pueda leer."""

    def __init__(self, mensaje, codigo=None, subcodigo=None, reintentable=False):
        super().__init__(mensaje)
        self.codigo = codigo
        self.subcodigo = subcodigo
        self.reintentable = reintentable


# Los códigos que significan «volvé a intentar más tarde» y no «esto está mal».
# La diferencia decide si el publicador reintenta o si le avisa a la persona.
# 9007 es «la media todavía no está lista»: el propio mensaje de Meta dice que
# esperes un momento, así que darlo por perdido es no leer lo que dice.
CODIGOS_TEMPORALES = {1, 2, 4, 9007, 17, 32, 341, 613}
# 190 es token vencido o revocado: no se arregla reintentando, hay que
# reconectar la cuenta. Se trata aparte porque desactiva la cuenta entera.
CODIGO_TOKEN = 190


def _traducir(error: dict) -> ErrorInstagram:
    """El JSON de error de Meta, convertido en algo que sirva para mostrar.

    `error_user_msg` es el texto que Meta escribió para mostrarle a una
    persona; cuando viene, es mucho mejor que `message`, que está escrito para
    un programador.
    """
    codigo = error.get("code")
    sub = error.get("error_subcode")
    texto = (error.get("error_user_msg")
             or error.get("message")
             or "Instagram rechazó la publicación")

    if codigo == CODIGO_TOKEN:
        texto = ("La conexión con Instagram se venció o se revocó. "
                 "Hay que volver a conectar la cuenta.")
    elif codigo == 9 or sub == 2207042:
        texto = ("Instagram no deja publicar más por hoy: son 100 posteos "
                 "cada 24 horas por cuenta.")
    elif sub in (2207003, 2207004, 2207032):
        texto = ("Instagram no pudo bajar el archivo. Revisá que la pieza "
                 "siga publicada en el Storage.")
    elif sub in (2207005, 2207009, 2207023):
        texto = ("Formato o proporción que Instagram no acepta para este tipo "
                 "de posteo.")
    elif codigo == 9007 or sub == 2207027:
        # Meta lo contesta en el idioma de la app, que acá sale en portugués:
        # «A mídia não está pronta para ser publicada». Mostrárselo así a
        # alguien que quiso subir una foto no le dice nada.
        texto = ("Instagram todavía estaba terminando de procesar la pieza. "
                 "Se reintenta solo en unos minutos.")

    return ErrorInstagram(
        texto, codigo, sub,
        reintentable=codigo in CODIGOS_TEMPORALES)


class Instagram:
    """La cuenta de Instagram de UN cliente."""

    def __init__(self, token: str, ig_user_id: str = ""):
        self.token = token
        self.id = ig_user_id or ""

    # ─────────────────────────────────────────────────────────────── básico

    def _pedir(self, metodo: str, camino: str, campos: dict) -> dict:
        campos = {k: v for k, v in campos.items() if v not in (None, "")}
        campos["access_token"] = self.token
        try:
            if metodo == "POST":
                r = requests.post(f"{BASE}/{camino}", data=campos, timeout=TIEMPO)
            else:
                r = requests.get(f"{BASE}/{camino}", params=campos, timeout=TIEMPO)
        except requests.RequestException as e:
            raise ErrorInstagram(f"No se pudo hablar con Instagram: {e}",
                                 reintentable=True) from e

        try:
            datos = r.json()
        except ValueError:
            raise ErrorInstagram(
                f"Instagram respondió algo que no es JSON ({r.status_code})",
                reintentable=r.status_code >= 500)

        if isinstance(datos, dict) and "error" in datos:
            err = _traducir(datos["error"])
            # El token NUNCA se escribe en el log. `campos` lo tiene adentro,
            # así que se loguea el camino y no los campos.
            log.warning("instagram %s %s → %s (código %s/%s)",
                        metodo, camino, err, err.codigo, err.subcodigo)
            raise err
        if r.status_code >= 400:
            raise ErrorInstagram(f"Instagram devolvió {r.status_code}",
                                 reintentable=r.status_code >= 500)
        return datos

    def quien(self) -> dict:
        """De qué cuenta es este token. Sirve para confirmar antes de publicar."""
        d = self._pedir("GET", "me", {"fields": "id,username"})
        if d.get("id"):
            self.id = d["id"]
        return d

    def _asegurar_id(self):
        if not self.id:
            self.quien()
        if not self.id:
            raise ErrorInstagram("No pude identificar la cuenta de Instagram")

    # ─────────────────────────────────────────────────────────── contenedores

    def contenedor_imagen(self, url: str, caption: str = "",
                          hijo: bool = False) -> str:
        """Una foto sola de feed, o una diapositiva de un carrusel.

        `hijo=True` es lo que hace que la imagen NO se publique por su cuenta:
        queda esperando a que un contenedor de carrusel la reclame.
        """
        self._asegurar_id()
        campos = {"image_url": url}
        if hijo:
            campos["is_carousel_item"] = "true"
        else:
            campos["caption"] = _recortar(caption)
        return self._pedir("POST", f"{self.id}/media", campos)["id"]

    def contenedor_carrusel(self, hijos: list[str], caption: str = "") -> str:
        """El posteo que agrupa entre 2 y 10 diapositivas ya creadas.

        Para Instagram esto es UN posteo: cuenta uno solo contra el límite
        diario de 100, y en el feed ocupa un lugar. Es por lejos la forma más
        barata de publicar cinco piezas.
        """
        self._asegurar_id()
        if not 2 <= len(hijos) <= 10:
            raise ErrorInstagram(
                f"Un carrusel lleva entre 2 y 10 imágenes, y este trae "
                f"{len(hijos)}.")
        return self._pedir("POST", f"{self.id}/media", {
            "media_type": "CAROUSEL",
            "children": ",".join(hijos),
            "caption": _recortar(caption),
        })["id"]

    def contenedor_reel(self, video_url: str, caption: str = "",
                        portada: str = "", al_feed: bool = True) -> str:
        """Un reel. Instagram lo procesa en segundo plano: hay que esperarlo.

        `al_feed=True` hace que además aparezca en la grilla del perfil. Es lo
        que quiere una marca: si no, el reel existe sólo en la pestaña de reels
        y el perfil queda con huecos.
        """
        self._asegurar_id()
        return self._pedir("POST", f"{self.id}/media", {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": _recortar(caption),
            "cover_url": portada,
            "share_to_feed": "true" if al_feed else "false",
        })["id"]

    def contenedor_story(self, url: str, es_video: bool = False) -> str:
        """Una story. No lleva pie de foto: Instagram lo ignora."""
        self._asegurar_id()
        campos = {"media_type": "STORIES"}
        campos["video_url" if es_video else "image_url"] = url
        return self._pedir("POST", f"{self.id}/media", campos)["id"]

    # ──────────────────────────────────────────────────────────────── estado

    def estado(self, contenedor: str) -> tuple[str, str]:
        """(status_code, detalle). IN_PROGRESS, FINISHED, ERROR o EXPIRED."""
        d = self._pedir("GET", contenedor, {"fields": "status_code,status"})
        return d.get("status_code", ""), d.get("status", "")

    def esperar(self, contenedor: str, limite: int = ESPERA_VIDEO) -> bool:
        """Espera a que el contenedor termine de procesarse. True si quedó listo.

        Devuelve False —sin error— si se acabó el tiempo pero sigue
        procesando: eso no es una falla, es un video largo, y la corrida
        siguiente lo retoma.

        **Va para todo, no sólo para los videos.** Una foto está lista casi
        siempre al instante, y por eso durante meses se publicó sin preguntar;
        el día que una no lo estuvo, Meta contestó «la media no está lista» y
        el posteo se dio por perdido. Preguntar cuesta una llamada.
        """
        empezo = time.monotonic()
        espera = 3
        while time.monotonic() - empezo < limite:
            code, detalle = self.estado(contenedor)
            if code == "FINISHED":
                return True
            if code in ("ERROR", "EXPIRED"):
                raise ErrorInstagram(
                    f"Instagram no pudo procesar la pieza ({code}). {detalle}")
            time.sleep(espera)
            espera = min(espera * 1.5, 15)
        return False

    # ────────────────────────────────────────────────────────────── publicar

    def publicar(self, contenedor: str) -> str:
        """El paso que lo hace público. Devuelve el id del posteo."""
        self._asegurar_id()
        return self._pedir("POST", f"{self.id}/media_publish",
                           {"creation_id": contenedor})["id"]

    def permalink(self, media_id: str) -> str:
        """El link del posteo. Si falla, no es motivo para dar error: ya se
        publicó, y lo único que se pierde es el botón para abrirlo."""
        try:
            return self._pedir("GET", media_id, {"fields": "permalink"}
                               ).get("permalink", "")
        except ErrorInstagram:
            return ""

    def cupo(self) -> int:
        """Cuántos posteos se usaron de los 100 de las últimas 24 horas."""
        try:
            d = self._pedir("GET", f"{self.id}/content_publishing_limit",
                            {"fields": "quota_usage"})
            return int(d.get("data", [{}])[0].get("quota_usage", 0))
        except Exception:
            return -1

    # ───────────────────────────────────────────────────────────────── token

    def refrescar(self) -> tuple[str, int]:
        """Devuelve (token nuevo, segundos que dura).

        Meta no extiende el token viejo: emite uno nuevo. El anterior sigue
        andando hasta que se vence, así que guardar el nuevo no corta nada en
        el medio.
        """
        d = self._pedir("GET", "refresh_access_token",
                        {"grant_type": "ig_refresh_token"})
        nuevo = d.get("access_token", "")
        if not nuevo:
            raise ErrorInstagram("Meta no devolvió un token nuevo")
        return nuevo, int(d.get("expires_in", 60 * 24 * 3600))


def _recortar(caption: str) -> str:
    caption = (caption or "").strip()
    if len(caption) <= MAX_CAPTION:
        return caption
    log.warning("caption de %d caracteres: lo corto a %d",
                len(caption), MAX_CAPTION)
    return caption[:MAX_CAPTION - 1].rstrip() + "…"
