# -*- coding: utf-8 -*-
"""El reelero: convierte una foto de producto en un reel de la marca.

## Por qué esto vive en el worker y no en una tool de Asistime

Una tool de Asistime tiene un timeout configurable, y las de Stadium están
entre 60 y 120 segundos —`estado_diseno` incluso espera adentro hasta 75—. O
sea que sí puede esperar un rato: no es cierto que se corte a los pocos
segundos.

Lo que no puede es esperar **cuatro minutos**, que es lo que tarda generar el
video. Y aunque se pudiera subir el timeout, no convendría: la tool corre
dentro del turno del agente, así que el chat se queda mudo todo ese rato y si
la conversación se corta en el medio, el pedido se pierde con ella.

Por eso el reel sigue el mismo camino que ya sigue un diseño.

Así que el reel sigue el mismo camino que ya sigue un diseño:

    el agente anota la fila  →  el worker la levanta y la trabaja

`crear_reel` escribe en `reels` y contesta al instante. Este módulo hace el
resto, repartido en los ciclos que hagan falta.

## El estado tiene que sobrevivir a que el worker se muera

El worker es un *job* de Cloud Run: corre un ciclo y termina. Cloud Scheduler lo
vuelve a llamar cada minuto. O sea que entre que se pide el video y que está
listo, este proceso arranca y muere unas cuatro veces.

Por eso la fila guarda `tarea` —el id que devuelve Magnific— apenas se pide. El
ciclo siguiente ve una fila en `generando` CON tarea y pregunta por ella en vez
de pedir un video nuevo. Sin eso, cada minuto se pediría otro video y el mismo
reel saldría cinco veces, cobrado cinco veces.

## Los estados

    pendiente  → recién anotado por el agente
    estimando  → se está calculando cuánto sale (no gasta nada)
    rechazado  → sale más caro que el tope de la marca; NO se generó
    generando  → pedido a Magnific; `tarea` tiene el id
    montando   → el clip está; falta el rótulo y el ffmpeg
    listo      → el MP4 está en el bucket, `url` lo apunta
    error      → algo falló; `notas` dice qué
"""
import json
import logging
import os
import pathlib
import subprocess
import tempfile
import urllib.request

import requests

log = logging.getLogger(__name__)

API = "https://api.magnific.com/v1/ai/video"

#: Cuántos créditos sale un video, por resolución y por segundo.
#:
#: NO sale de una tabla publicada: Magnific no expone un endpoint de precios y
#: su estimador vive sólo en el conector, que necesita una sesión con OAuth y
#: por lo tanto no sirve acá. Estos números se MIDIERON con `simulate_cost` el
#: 25/8/2026, sobre 8 segundos en 9:16:
#:
#:     480p → 1.600      720p → 3.520      1080p → 6.320
#:
#: Si Magnific cambia los precios, esto queda viejo sin avisar. Por eso el tope
#: de la marca es lo que realmente protege: aunque la tabla mienta, el gasto
#: queda acotado por `creditos_maximos`.
PRECIO_POR_SEGUNDO = {"480p": 200, "720p": 440, "1080p": 790}

#: Lo que se le pide a Magnific si la marca no dice otra cosa.
#:
#: **720p y seis segundos: 2.640 créditos.** Es una decisión de compromiso y
#: conviene entender las dos puntas antes de moverla.
#:
#: Magnific llama «720p» al lado largo, así que el clip sale de 406×720 y hay
#: que estirarlo a 1080×1920 — 2,7 veces. En 480p serían 270×480, o sea 4
#: veces, y a esa altura el video se ve blando. En 1080p sale 608×1080 y estira
#: 1,8, pero cuesta 4.740 por los mismos seis segundos.
#:
#: La duración es el otro cursor, y es lineal: cada segundo de 720p son 440
#: créditos. Seis alcanzan para los tres tiempos de un reel de producto
#: (producto quieto, la persona entra, la caminata). Menos de cinco y el tercer
#: tiempo no llega a leerse.
POR_DEFECTO = {"resolucion": "720p", "duracion": 6, "relacion": "social_story_9_16"}


def precio(resolucion: str, duracion: int) -> int:
    """Lo que va a salir este video, antes de pedirlo."""
    return PRECIO_POR_SEGUNDO.get(resolucion, PRECIO_POR_SEGUNDO["1080p"]) * duracion


def _clave() -> str:
    c = (os.environ.get("MAGNIFIC_CLAVE") or "").strip()
    if not c:
        raise RuntimeError(
            "falta MAGNIFIC_CLAVE. Es la clave de API de Magnific, que NO es la "
            "misma que el conector: el conector entra con la cuenta de una "
            "persona por OAuth y sirve sólo dentro de un chat. El worker corre "
            "solo y necesita una llave propia.")
    return c


def _pedir(ruta: str, cuerpo: dict | None = None, metodo: str = "POST") -> dict:
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pedido = urllib.request.Request(
        f"{API}/{ruta}", data=datos, method=metodo,
        headers={"x-magnific-api-key": _clave(),
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=60) as r:
        return json.loads(r.read().decode())


# ═══ 1. Pedir el video ═══════════════════════════════════════════════════════

def pedir_clip(fila: dict, ficha: dict) -> str:
    """Le pide el video a Magnific y devuelve el id de tarea.

    Manda la foto en `reference_images` y no en `image`. La diferencia importa:
    con `image` el video ARRANCA de esa foto y sigue desde ahí, y una foto de
    catálogo sobre fondo blanco da un reel sobre fondo blanco. Como referencia,
    en cambio, la foto le dice al modelo CÓMO ES el producto y lo deja componer
    una escena. El producto se mantiene y el fondo es de verdad.

    Los planos van en `multishot` porque un reel de retail son tres tiempos, y
    describirlos por separado da mucho más control que un párrafo largo. Se
    probó: pidiendo un plano solo, el modelo se saltea la mitad de lo pedido.
    """
    res = ficha.get("resolucion") or POR_DEFECTO["resolucion"]
    dur = int(ficha.get("duracion") or POR_DEFECTO["duracion"])
    planos = fila.get("metricas", {}).get("planos") or _planos(fila, dur)
    cuerpo = {
        "prompt": fila["mensaje"],
        "reference_images": [fila["foto"]],
        "multishot": planos,
        "duration": dur,
        "aspect_ratio": POR_DEFECTO["relacion"],
        "sound_effects": True,
        # La música la pone el worker desde el banco de la marca: es más barata
        # (una pista de 30 s se genera una vez y se reusa en todos los reels) y
        # sobre todo es SIEMPRE la misma, que es lo que hace que una cuenta
        # suene a una cuenta y no a veinte piezas sueltas.
        "no_music": True,
    }
    return _pedir(f"seedance-2-5-pro-{res}", cuerpo)["data"]["task_id"]


def _planos(fila: dict, dur: int) -> list[dict]:
    """Los tres tiempos de un reel de producto, repartidos en `dur` segundos.

    **Nada de manipulación del producto.** Se midió: pidiéndole a un pie que se
    calce la zapatilla, el modelo directamente no lo hace —el pie queda al lado
    cinco segundos y después hay un corte donde ya la tiene puesta— y además
    deforma el producto en los planos de movimiento (la caña alta desapareció y
    la suela cambió de color). Con el producto quieto y la persona entrando
    después, el mismo modelo lo mantiene fiel los ocho segundos.
    """
    a = max(2, round(dur * 0.40))
    b = max(1, round(dur * 0.25))
    return [
        {"prompt": f"Vertical product shot, warm natural light. {fila['foto_texto']} "
                   "stands still on a clean surface. Every detail of the product "
                   "stays exactly as it is. Shallow depth of field, background "
                   "softly blurred. Camera pushes in very slowly. Realistic retail "
                   "product photography, no text.", "duration": a},
        {"prompt": "The camera stays. A person steps into the frame next to the "
                   "product, casual and relaxed. The product does not move and "
                   "keeps its exact shape. Realistic, no text.", "duration": b},
        {"prompt": "Cut to a sunlit city sidewalk. A young person seen from behind "
                   "walks away from camera using the product, relaxed confident "
                   "stride. The product stays clearly visible and undistorted. "
                   "Natural daylight, realistic street style, no text.",
         "duration": dur - a - b},
    ]


def estado_clip(tarea: str, resolucion: str) -> tuple[str, str | None]:
    """`(estado, url)` de una tarea. La URL vive 24 horas: hay que bajarla ya."""
    d = _pedir(f"seedance-2-5-pro-{resolucion}/{tarea}", metodo="GET")["data"]
    urls = d.get("generated") or []
    return d.get("status", "").upper(), (urls[0] if urls else None)


# ═══ 2. Montar la pieza ══════════════════════════════════════════════════════

def montar(clip: pathlib.Path, rotulo: pathlib.Path, musica: pathlib.Path | None,
           salida: pathlib.Path, dur: float) -> pathlib.Path:
    """Escala el clip a 1080×1920, le monta el rótulo y le pone la música.

    Tres cosas que costaron encontrar y que no se pueden sacar:

    · `-loop 1 -t` en la entrada del PNG. Sin eso la imagen es UN fotograma, se
      agota en el primer instante y **el rótulo no aparece en ningún lado** —
      sin ningún error. El MP4 sale perfecto y sin rótulo.
    · El ambiente del clip baja a 0.28 y la música va arriba. Si van parejos,
      los pasos y el viento le compiten a la música y suena a video casero.
    · `loudnorm=I=-14` al final. Es el nivel de redes; sin eso el reel suena
      más bajo que todo lo demás del feed.

    Y una cuarta que se agregó después: **no se da por hecho que el clip traiga
    audio**. Seedance devuelve sonido casi siempre, pero no siempre, y
    `[0:a]volume=0.28` contra un clip mudo no es un video sin ambiente: es un
    ffmpeg que aborta. Ahí se pierde el montaje entero de un video que ya se
    pagó —2.640 créditos— y la fila termina en `error` con un mensaje de ffmpeg
    que no explica nada. Por eso se pregunta antes.
    """
    ambiente = _tiene_audio(clip)
    filtro = [
        f"[0:v]scale=1080:1920:flags=lanczos,fade=t=out:st={dur-0.5:.2f}:d=0.5[base]",
        f"[1:v]format=rgba,fade=t=in:st=0.3:d=0.5:alpha=1,"
        f"fade=t=out:st={dur-0.8:.2f}:d=0.6:alpha=1[rot]",
        "[base][rot]overlay=0:0:shortest=1[vout]",
    ]
    orden = ["-i", str(clip), "-loop", "1", "-t", f"{dur+0.1:.2f}", "-i", str(rotulo)]
    if musica:
        orden += ["-i", str(musica)]
        filtro.append(
            f"[2:a]atrim=0:{dur:.2f},afade=t=in:st=0:d=0.3,"
            f"afade=t=out:st={dur-0.7:.2f}:d=0.7[mus]")
        if ambiente:
            filtro += [
                "[0:a]volume=0.28[amb]",
                "[mus][amb]amix=inputs=2:duration=first:dropout_transition=0,"
                "loudnorm=I=-14:TP=-1:LRA=11[aout]",
            ]
        else:
            filtro.append("[mus]loudnorm=I=-14:TP=-1:LRA=11[aout]")
    elif ambiente:
        filtro.append("[0:a]loudnorm=I=-14:TP=-1:LRA=11[aout]")

    # Sin música y sin ambiente el reel sale mudo, y hay que decírselo a ffmpeg
    # con `-an`: mapear un `[aout]` que ningún filtro creó es un error, no un
    # silencio.
    audio = ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    if not (musica or ambiente):
        audio = ["-an"]

    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *orden,
         "-filter_complex", ";".join(filtro),
         "-map", "[vout]", *audio,
         "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-r", "24",
         "-movflags", "+faststart", str(salida)],
        check=True)
    return salida


def _tiene_audio(clip: pathlib.Path) -> bool:
    """¿El clip trae pista de audio? Barato de preguntar, caro de suponer.

    Si `ffprobe` no está, contesta que NO, y esa elección tiene una razón: de
    los dos errores posibles, uno cuesta el ambiente del clip —que va al 0.28
    debajo de la música y casi no se nota— y el otro cuesta el montaje entero
    de un video ya pagado. Se elige el barato.
    """
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=index", "-of", "csv=p=0", str(clip)],
            capture_output=True, text=True)
    except FileNotFoundError:
        log.warning("no encontré ffprobe: monto el reel sin el ambiente del clip")
        return False
    return bool(r.stdout.strip())


def bajar(url: str, destino: pathlib.Path) -> pathlib.Path:
    """Baja el clip. Ojo: la URL de Magnific caduca a las 24 horas."""
    with urllib.request.urlopen(url, timeout=180) as r, open(destino, "wb") as f:
        f.write(r.read())
    return destino


# ═══ 3. El ciclo ═════════════════════════════════════════════════════════════

def _pendientes(cli, estado: str, limite: int = 3) -> list[dict]:
    r = requests.get(
        cli._url("reels"), headers=cli._cab(), timeout=30,
        params={"estado": f"eq.{estado}", "order": "creado_en.asc",
                "limit": str(limite),
                # `creditos_estimados` está en la lista porque el paso de
                # montaje lo copia a `creditos_gastados`. Faltaba, y el efecto
                # era mudo: el reel salía bien y quedaba registrado con gasto
                # cero. El tope del mes seguía andando —suma estimados, no
                # gastados— así que nada fallaba; simplemente el registro de lo
                # que se gastó decía cero para siempre.
                "select": "id,creado_en,actualizado_en,mensaje,foto,titulo,"
                          "kicker,bajada,musica,tarea,resolucion,duracion,"
                          "clip_url,quien,metricas,creditos_estimados"})
    if r.status_code in (400, 404):
        return []            # esta base todavía no tiene la tabla
    r.raise_for_status()
    return r.json()


def _tomar(cli, rid: str, de: str, a: str) -> bool:
    """Pasa la fila de un estado a otro, y dice si LA TOMÓ ESTE proceso.

    El filtro por el estado viejo va en el PATCH a propósito. Cloud Scheduler
    llama cada minuto y un ciclo puede tardar más que eso, así que dos worker
    pueden estar vivos a la vez. Sin este filtro los dos leerían la misma fila
    en `pendiente` y los dos pedirían el video: el reel saldría dos veces y se
    cobraría dos veces. Con el filtro, el segundo recibe cero filas y sigue de
    largo.
    """
    r = requests.patch(
        cli._url("reels"), headers={**cli._cab(), "Prefer": "return=representation"},
        params={"id": f"eq.{rid}", "estado": f"eq.{de}"},
        data=json.dumps({"estado": a}), timeout=30)
    r.raise_for_status()
    return bool(r.json())


def _marcar(cli, rid: str, estado: str, **campos):
    requests.patch(
        cli._url("reels"), headers=cli._cab(), params={"id": f"eq.{rid}"},
        data=json.dumps({"estado": estado, **campos}), timeout=30).raise_for_status()


#: Cuánto se le aguanta a una tarea antes de darla por perdida.
#:
#: Estaba en 40 minutos —«diez veces lo que tarda un video»— y se midió que no
#: alcanza: el primer reel de verdad estuvo más de una hora en `IN_PROGRESS` y
#: seguía vivo. Lo que tarda Seedance no es sólo generar, es también la cola de
#: Magnific, y esa no la controlamos. Dos horas no es una estimación de cuánto
#: tarda: es el punto en que ya no se puede seguir diciendo «sigue
#: generándose» sin que alguien mire.
TOPE_GENERANDO = 2 * 60 * 60


def _colgada(fila: dict) -> bool:
    """¿Esta fila lleva demasiado ESPERANDO A MAGNIFIC?

    Se mide contra `actualizado_en` —el trigger `reels_tocar` lo pone en cada
    UPDATE, así que es el momento en que la fila pasó a `generando`— y NO
    contra `creado_en`.

    La diferencia parecía un detalle y no lo era. Con `creado_en`, un pedido
    que estuvo dos horas en `pendiente` esperando la clave de Magnific ya nacía
    vencido: el worker pedía el video, gastaba los 2.640 créditos, y al minuto
    siguiente daba la tarea por colgada sin haberle dado un solo minuto. Pasó
    con el primer reel, el 26/8/2026.
    """
    from datetime import datetime, timezone
    crudo = fila.get("actualizado_en") or fila.get("creado_en")
    if not crudo:
        return False
    try:
        cuando = datetime.fromisoformat(crudo.replace("Z", "+00:00"))
    except ValueError:
        return False
    if cuando.tzinfo is None:
        cuando = cuando.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - cuando).total_seconds() > TOPE_GENERANDO


def _gastado_este_mes(cli) -> int:
    """Lo que ya se comprometió este mes, para el tope mensual.

    Suma `creditos_estimados` y no `creditos_gastados`: lo que protege es lo que
    se va a gastar, no lo que ya se gastó. Un video pedido hace treinta segundos
    todavía no figura como gastado y sin embargo la plata ya salió.
    """
    from datetime import datetime, timezone
    desde = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0,
                                               microsecond=0).isoformat()
    r = requests.get(cli._url("reels"), headers=cli._cab(), timeout=30,
                     params={"creado_en": f"gte.{desde}",
                             "estado": "not.in.(rechazado,error)",
                             "select": "creditos_estimados"})
    if r.status_code in (400, 404):
        return 0
    return sum((f.get("creditos_estimados") or 0) for f in r.json())


def atender_todos(cli, ficha: dict, armar_rotulo, subir, musica_de_fila) -> int:
    """Un ciclo. Devuelve cuántas filas movió.

    `armar_rotulo(fila, destino) -> Path` dibuja el PNG transparente con la
    plantilla `campana` en modo `sobre_video`. `subir(Path, nombre) -> url` lo
    sube al bucket. `musica_de_fila(fila) -> url | None` decide qué pista lleva.
    Los tres entran por parámetro y no por import para que este módulo se pueda
    probar sin levantar el motor entero.

    El destino lo elige ESTA función y no el que dibuja, porque el PNG tiene que
    vivir dentro del `TemporaryDirectory` de la fila: si el que dibuja se hace
    su propio temporal, nadie lo borra y cada reel deja un archivo de 1080×1920
    tirado en el disco del job.
    """
    # El tope por pieza tiene que ser MAYOR que lo que cuesta el default, o
    # todo se rechaza y nadie entiende por qué. 3.000 deja pasar los 2.640 de
    # 720p/6s y frena un 1080p de ocho segundos (6.320), que es exactamente la
    # línea que se quiso poner.
    tope_pieza = int(ficha.get("creditos_maximos") or 3000)
    tope_mes = int(ficha.get("creditos_maximos_mes") or 20000)
    res = ficha.get("resolucion") or POR_DEFECTO["resolucion"]
    dur = int(ficha.get("duracion") or POR_DEFECTO["duracion"])
    movidas = 0

    # --- a) recién anotados: ¿cuánto sale? ----------------------------------
    nuevos = _pendientes(cli, "pendiente")

    # La clave se mira ANTES de tocar una fila, y por eso está acá y no adentro
    # del for. Si faltara, `pedir_clip` reventaría con la fila ya movida a
    # `estimando` — un estado que nadie vuelve a levantar—: el pedido quedaría
    # trabado para siempre y el día que aparezca el secreto no se destrabaría
    # solo. Así, en cambio, las filas se quedan quietas en `pendiente`, el log
    # dice qué falta, y salen solas en la primera corrida después del secreto.
    if nuevos and not (os.environ.get("MAGNIFIC_CLAVE") or "").strip():
        log.warning("[%s] %d reel(s) esperando: falta MAGNIFIC_CLAVE en el job",
                    getattr(cli, "marca", "?"), len(nuevos))
        nuevos = []

    for fila in nuevos:
        if not _tomar(cli, fila["id"], "pendiente", "estimando"):
            continue
        try:
            cuesta = precio(res, dur)
            ya = _gastado_este_mes(cli)
            if cuesta > tope_pieza:
                _marcar(cli, fila["id"], "rechazado", creditos_estimados=cuesta,
                        notas=f"{cuesta} créditos supera el tope por pieza ({tope_pieza}). "
                              f"Bajá la resolución o la duración en marca.json.")
            elif ya + cuesta > tope_mes:
                _marcar(cli, fila["id"], "rechazado", creditos_estimados=cuesta,
                        notas=f"este reel sale {cuesta} créditos, este mes ya hay "
                              f"{ya} comprometidos y el tope mensual es {tope_mes}.")
            else:
                tarea = pedir_clip({**fila, "foto_texto": fila.get("titulo") or "the product"},
                                   {"resolucion": res, "duracion": dur})
                _marcar(cli, fila["id"], "generando", tarea=tarea, modelo="seedance-2-5-pro",
                        resolucion=res, duracion=dur, creditos_estimados=cuesta)
        except Exception as e:                               # noqa: BLE001
            # A `error` y NO de vuelta a `pendiente`, aunque reintentar sería
            # más cómodo. Si `pedir_clip` se cortó por timeout, el video puede
            # estar pedido —y cobrado— del otro lado sin que nos haya llegado
            # el id: devolver la fila a la cola pediría un segundo video y lo
            # cobraría de nuevo. Un reel que hay que volver a pedir a mano
            # cuesta un mensaje; uno cobrado dos veces cuesta plata.
            log.exception("[%s] falló el reel %s", getattr(cli, "marca", "?"), fila["id"])
            _marcar(cli, fila["id"], "error", notas=f"al pedir el video: {e}")
        movidas += 1

    # --- b) pedidos a Magnific: ¿ya está? -----------------------------------
    # NO se vuelve a pedir: se pregunta por la tarea que ya existe. Es la
    # diferencia entre cobrar una vez y cobrar una vez por minuto.
    for fila in _pendientes(cli, "generando"):
        if not fila.get("tarea"):
            _marcar(cli, fila["id"], "error", notas="quedó en generando sin id de tarea")
            continue
        try:
            estado, url = estado_clip(fila["tarea"], fila.get("resolucion") or res)
        except Exception as e:                               # noqa: BLE001
            # Preguntar no cuesta ni cobra, así que un fallo acá no mata la
            # fila: se deja en `generando` y se vuelve a preguntar el minuto
            # que viene. Lo que sí importa es que el `try` esté: sin él, una
            # tarea que contesta 401 se lleva puesto el resto de la corrida y
            # los reels que YA estaban listos no se montan.
            log.warning("[%s] no pude preguntar por el reel %s: %s",
                        getattr(cli, "marca", "?"), fila["id"], e)
            if _colgada(fila):
                _marcar(cli, fila["id"], "error",
                        notas=f"lleva más de {TOPE_GENERANDO // 3600} horas sin "
                              f"respuesta de Magnific: {e}")
                movidas += 1
            continue
        if estado in ("FAILED", "ERROR"):
            _marcar(cli, fila["id"], "error", notas=f"Magnific devolvió {estado}")
            movidas += 1
        elif estado == "COMPLETED" and url:
            _marcar(cli, fila["id"], "montando", clip_url=url)
            movidas += 1
        elif _colgada(fila):
            # Un video sale en unos cuatro minutos. Pasada media hora larga no
            # va a salir, y dejar la fila en `generando` para siempre es
            # dejarle al cliente un «sigue generándose» eterno: peor que un
            # error, porque nadie sabe que hay que hacer algo.
            _marcar(cli, fila["id"], "error",
                    notas=f"Magnific lo dejó en «{estado}» más de "
                          f"{TOPE_GENERANDO // 3600} horas")
            movidas += 1
        # si sigue en curso no se toca: el ciclo que viene vuelve a preguntar

    # --- c) el clip está: rótulo y montaje ----------------------------------
    # Acá NO hay toma atómica, y es a propósito. Si dos worker agarran la misma
    # fila, los dos bajan el clip y los dos lo montan: se gasta CPU de más y
    # gana el último que escribe, pero no se cobra nada —el video ya está
    # generado y pagado—. Poner un estado más para cubrir eso agregaría un
    # camino donde una fila puede quedar trabada en «montando_en_curso» si el
    # worker se muere en el medio, que es peor que renderizar dos veces.
    for fila in _pendientes(cli, "montando"):
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            try:
                clip = bajar(fila["clip_url"], t / "clip.mp4")
                rotulo = armar_rotulo(fila, t / "rotulo.png")
                # La pista se resuelve acá y no se lee de la fila: lo que
                # el agente escribió en `musica` es una clave del banco
                # (`street`), no una URL, y `bajar` necesita una URL.
                #
                # Y si la pista no baja, el reel sale igual, mudo. No es una
                # concesión: en este punto el video YA está generado y pagado
                # —2.640 créditos—, así que dejar caer el montaje por una
                # canción que falta cambia «un reel sin música» por «ningún
                # reel y la plata gastada». La nota queda escrita para que se
                # pueda arreglar y volver a montar.
                musica, falta_musica = None, ""
                pista = musica_de_fila(fila)
                if pista:
                    try:
                        musica = bajar(pista, t / "musica.mp3")
                    except Exception as e:                   # noqa: BLE001
                        falta_musica = f"sin música: no pude bajar {pista} ({e})"
                        log.warning("[%s] %s", getattr(cli, "marca", "?"), falta_musica)
                final = montar(clip, rotulo, musica, t / "reel.mp4",
                               float(fila.get("duracion") or dur))
                _marcar(cli, fila["id"], "listo",
                        url=subir(final, f"reels/{fila['id']}.mp4"),
                        creditos_gastados=fila.get("creditos_estimados"),
                        **({"notas": falta_musica} if falta_musica else {}))
            except Exception as e:                       # noqa: BLE001
                _marcar(cli, fila["id"], "error", notas=f"al montar: {e}")
        movidas += 1

    return movidas


# ═══ 4. El enganche con el worker ════════════════════════════════════════════
#
# Todo lo de arriba no sabe nada del worker a propósito: recibe `cli`, una ficha
# y dos funciones. Lo que sigue es lo único que sí lo sabe, y está separado para
# que el módulo se pueda probar sin levantar el motor entero.

def _ficha(marca: str) -> dict:
    """El bloque `reels` del `marca.json`, o vacío si la marca no tiene.

    Que esté vacío es la señal de que esta marca NO hace reels, y con eso
    alcanza para no tocarle la cola. Boss y Clínica no lo tienen: sus bases ni
    siquiera tienen la tabla `reels`, y aunque `_pendientes` sabe aguantar el
    404, preguntar cada minuto por algo que se sabe que no existe es ruido en
    el log de dos clientes para servir a un tercero.
    """
    from .disenador import _ficha as ficha_de_marca
    return (ficha_de_marca(marca) or {}).get("reels") or {}


def musica_de(cli, ficha: dict, pedida: str | None) -> str | None:
    """La URL de la pista, a partir de lo que haya pedido el agente.

    Tres caminos para elegir la clave, y el tercero es el que importa:

    · una URL https entera → se usa tal cual (sirve para probar con una pista
      suelta sin tocar el banco);
    · una clave del banco (`street`) → esa;
    · **nada** → la primera pista del banco.

    Ese último no es una comodidad: es la decisión de que un reel de Stadium
    SIEMPRE lleva música. Si «sin pedido» quisiera decir «sin música», el reel
    saldría mudo cada vez que el agente se olvide de nombrarla, y un reel mudo
    en el feed se lee como un error, no como una elección.

    Y después, dónde está el archivo: **primero en la carpeta de la marca,
    después en el bucket**. Las dos, y en ese orden, porque resuelven cosas
    distintas. La carpeta viaja con el despliegue: la pista está el día que se
    despliega, sin un paso manual que alguien tiene que acordarse de hacer y
    cuyo olvido recién se descubre al montar un video ya pagado. El bucket deja
    agregar una pista sin desplegar nada.
    """
    banco = ficha.get("musica") or []
    clave = (pedida or "").strip()
    if clave.startswith("https://"):
        return clave
    if not clave or not any(p.get("clave") == clave for p in banco):
        # Una clave inventada no se convierte en silencio: se cae al banco. El
        # agente escribe el nombre de la pista de memoria y se equivoca.
        if not banco:
            return None
        clave = banco[0]["clave"]

    from . import config
    local = config.RAIZ / ".claude" / "skills" / cli.marca / "musica" / f"{clave}.mp3"
    if local.exists():
        return local.as_uri()
    return f"{cli.url.rstrip('/')}/storage/v1/object/public/disenos/musica/{clave}.mp3"


def rotulo(marca: str, fila: dict, destino: pathlib.Path) -> pathlib.Path:
    """El PNG transparente que se monta encima del clip.

    Es la plantilla `campana` en modo `sobre_video`, dibujada al tamaño del
    reel. O sea: **el rótulo de un reel se hace con el mismo molde que una
    pieza**, no con un dibujo aparte. Si mañana cambia la tipografía de la
    marca, cambia también acá y sin tocar este archivo.

    Dos detalles que sin ellos no funciona:

    · `.canvas` viene con `background:#FFFFFF` en la hoja de la marca —lo que
      corresponde para una pieza— así que hay que pisarlo. Sin eso el
      `omit_background` de Playwright no sirve de nada: el PNG sale con un
      rectángulo blanco de 1080×1920 y tapa el video entero.
    · Es **sync**. Playwright se niega a correr su API sync adentro de un loop
      de asyncio, y el ciclo del worker es async: hay que entrar por
      `asyncio.to_thread`, igual que el dibujo de plantillas.
    """
    import importlib
    import sys

    from . import config

    carpeta = config.RAIZ / ".claude" / "skills" / marca
    sys.path.insert(0, str(carpeta))
    sys.path.insert(0, str(config.RAIZ))
    modulo = importlib.import_module("marca")

    from motor import plantillas as mp
    from playwright.sync_api import sync_playwright

    plantillas = mp.cargar(carpeta, modulo)
    if "campana" not in plantillas:
        raise RuntimeError(
            f"la marca «{marca}» no tiene la plantilla `campana`, que es con la "
            f"que se dibuja el rótulo de los reels")

    html = plantillas["campana"]({
        "titulo": fila.get("titulo") or "",
        "kicker": fila.get("kicker") or "",
        "bajada": fila.get("bajada") or "",
        "sobre_video": True,
        "posicion": "arriba",
    }, "reel")
    html += "<style>.canvas{background:transparent !important}</style>"

    with sync_playwright() as p:
        nav = p.chromium.launch()
        try:
            pg = nav.new_page(viewport={"width": 1080, "height": 1920},
                              device_scale_factor=1)
            # `file://` y no `set_content` pelado: la plantilla pide las fuentes
            # y el logo por ruta relativa a la carpeta de la marca, y sin una
            # URL base el navegador no las encuentra — el rótulo sale con la
            # tipografía del sistema y nadie se entera hasta ver el reel.
            tmp = carpeta / f".rotulo-{fila['id']}.html"
            tmp.write_text(html, encoding="utf-8")
            try:
                pg.goto(tmp.as_uri())
                pg.wait_for_timeout(300)          # que terminen de cargar las fuentes
                pg.screenshot(path=str(destino), omit_background=True)
            finally:
                tmp.unlink(missing_ok=True)
        finally:
            nav.close()
    return destino


def atender(cli) -> int:
    """Los reels de esta corrida para este cliente. Devuelve cuántas filas movió.

    **Es sync y tiene que llamarse con `asyncio.to_thread`**, por Playwright.
    """
    ficha = _ficha(cli.marca)
    if not ficha:
        return 0
    return atender_todos(
        cli, ficha,
        lambda fila, destino: rotulo(cli.marca, fila, destino),
        cli.subir,
        lambda fila: musica_de(cli, ficha, fila.get("musica")))
