# -*- coding: utf-8 -*-
"""El reelero: convierte una foto de producto en un reel de la marca.

## Por qué esto vive en el worker y no en una tool de Asistime

Una tool de `custom_code` se corta a los **5 segundos**. Generar el video tarda
**cuatro minutos**. No hay forma de que la tool haga el trabajo: se cortaría 235
segundos antes de que Magnific conteste.

Así que el reel sigue el mismo camino que ya sigue un diseño:

    el agente anota la fila  →  el worker la levanta y la trabaja

`crear_reel` escribe en `reels` y contesta en menos de un segundo. Este módulo
hace el resto.

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
import os
import pathlib
import subprocess
import tempfile
import urllib.request

import requests

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

#: Lo que se le pide a Magnific si la marca no dice otra cosa. 480p es
#: deliberado: a 8 segundos sale 1.600 contra 6.320 de 1080p, y la pieza se
#: escala después. Una marca que quiera más nitidez lo sube en su `marca.json`.
POR_DEFECTO = {"resolucion": "480p", "duracion": 8, "relacion": "social_story_9_16"}


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
    """
    filtro = [
        f"[0:v]scale=1080:1920:flags=lanczos,fade=t=out:st={dur-0.5:.2f}:d=0.5[base]",
        f"[1:v]format=rgba,fade=t=in:st=0.3:d=0.5:alpha=1,"
        f"fade=t=out:st={dur-0.8:.2f}:d=0.6:alpha=1[rot]",
        "[base][rot]overlay=0:0:shortest=1[vout]",
    ]
    orden = ["-i", str(clip), "-loop", "1", "-t", f"{dur+0.1:.2f}", "-i", str(rotulo)]
    if musica:
        orden += ["-i", str(musica)]
        filtro += [
            "[0:a]volume=0.28[amb]",
            f"[2:a]atrim=0:{dur:.2f},afade=t=in:st=0:d=0.3,"
            f"afade=t=out:st={dur-0.7:.2f}:d=0.7[mus]",
            "[mus][amb]amix=inputs=2:duration=first:dropout_transition=0,"
            "loudnorm=I=-14:TP=-1:LRA=11[aout]",
        ]
    else:
        filtro += ["[0:a]loudnorm=I=-14:TP=-1:LRA=11[aout]"]

    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *orden,
         "-filter_complex", ";".join(filtro),
         "-map", "[vout]", "-map", "[aout]",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-r", "24",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", str(salida)],
        check=True)
    return salida


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
                "select": "id,mensaje,foto,titulo,kicker,bajada,musica,"
                          "tarea,resolucion,duracion,clip_url,quien,metricas"})
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


def atender_todos(cli, ficha: dict, armar_rotulo, subir) -> int:
    """Un ciclo. Devuelve cuántas filas movió.

    `armar_rotulo(fila) -> Path` dibuja el PNG transparente con la plantilla
    `campana` en modo `sobre_video`. `subir(Path, nombre) -> url` lo sube al
    bucket. Los dos entran por parámetro y no por import para que este módulo
    se pueda probar sin levantar el motor entero.
    """
    tope_pieza = int(ficha.get("creditos_maximos") or 2000)
    tope_mes = int(ficha.get("creditos_maximos_mes") or 20000)
    res = ficha.get("resolucion") or POR_DEFECTO["resolucion"]
    dur = int(ficha.get("duracion") or POR_DEFECTO["duracion"])
    movidas = 0

    # --- a) recién anotados: ¿cuánto sale? ----------------------------------
    for fila in _pendientes(cli, "pendiente"):
        if not _tomar(cli, fila["id"], "pendiente", "estimando"):
            continue
        cuesta = precio(res, dur)
        ya = _gastado_este_mes(cli)
        if cuesta > tope_pieza:
            _marcar(cli, fila["id"], "rechazado", creditos_estimados=cuesta,
                    notas=f"{cuesta} créditos supera el tope por pieza ({tope_pieza}). "
                          f"Bajá la resolución o la duración en marca.json.")
        elif ya + cuesta > tope_mes:
            _marcar(cli, fila["id"], "rechazado", creditos_estimados=cuesta,
                    notas=f"este mes ya hay {ya} comprometidos y el tope es {tope_mes}.")
        else:
            tarea = pedir_clip({**fila, "foto_texto": fila.get("titulo") or "the product"},
                               {"resolucion": res, "duracion": dur})
            _marcar(cli, fila["id"], "generando", tarea=tarea, modelo="seedance-2-5-pro",
                    resolucion=res, duracion=dur, creditos_estimados=cuesta)
        movidas += 1

    # --- b) pedidos a Magnific: ¿ya está? -----------------------------------
    # NO se vuelve a pedir: se pregunta por la tarea que ya existe. Es la
    # diferencia entre cobrar una vez y cobrar una vez por minuto.
    for fila in _pendientes(cli, "generando"):
        if not fila.get("tarea"):
            _marcar(cli, fila["id"], "error", notas="quedó en generando sin id de tarea")
            continue
        estado, url = estado_clip(fila["tarea"], fila.get("resolucion") or res)
        if estado in ("FAILED", "ERROR"):
            _marcar(cli, fila["id"], "error", notas=f"Magnific devolvió {estado}")
            movidas += 1
        elif estado == "COMPLETED" and url:
            _marcar(cli, fila["id"], "montando", clip_url=url)
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
                rotulo = armar_rotulo(fila)
                musica = None
                if fila.get("musica"):
                    musica = bajar(fila["musica"], t / "musica.mp3")
                final = montar(clip, rotulo, musica, t / "reel.mp4",
                               float(fila.get("duracion") or dur))
                _marcar(cli, fila["id"], "listo",
                        url=subir(final, f"reels/{fila['id']}.mp4"),
                        creditos_gastados=fila.get("creditos_estimados"))
            except Exception as e:                       # noqa: BLE001
                _marcar(cli, fila["id"], "error", notas=f"al montar: {e}")
        movidas += 1

    return movidas
