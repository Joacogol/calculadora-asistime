# -*- coding: utf-8 -*-
"""El fotero: las cinco cosas que se le piden a una foto antes de una pieza.

## Por qué existe

El motor dibuja piezas con las fotos que le dan, y las fotos que le dan casi
nunca están como hacen falta. La de catálogo viene sobre fondo blanco —y la
plantilla `campana` tiene escrito que una foto así «obliga a un velo tan grande
que la pieza sale gris»—; la que manda el cliente por WhatsApp viene de 800
píxeles cuando la pieza se dibuja a 2160; y la horizontal que sirve para un post
no entra en un story sin comerse el producto.

Los cinco verbos salen de ahí, no de la lista de lo que la API sabe hacer:

    fondo     recorta el producto. El más pedido y el que arregla el velo gris.
    formato   estira la foto a otra proporción inventando lo que falta, en vez
              de recortar y perder el producto.
    tamano    agranda una foto chica.
    retoque   «sacale el cartel de oferta», «borrá la persona del fondo».
    escena    el producto en otro lado: una calle, una mesa, un pie.

`retoque` y `escena` son el mismo endpoint con distinto prompt. Están separados
igual porque el que escribe en el chat los piensa distinto, y porque `escena`
GENERA —puede deformar el producto— mientras `retoque` edita. Merecen avisos
distintos el día que salgan mal.

## Por qué pasa por el worker si una edición tarda segundos

Un reel tarda cuatro minutos y por eso no puede vivir adentro del turno del
agente. Una edición tarda segundos, así que ese argumento no aplica. Pasa por
acá igual, por dos razones propias:

· **La clave de Magnific vive en un solo lugar.** Ponerla también en las Edge
  Functions sería una segunda copia de una llave que puede vaciar la cuenta, y
  lejos de los topes de créditos que la cuidan.
· **El resultado caduca.** La URL que devuelve quitar-fondo vive CINCO minutos.
  Alguien tiene que bajarla y subirla al bucket enseguida; ese alguien ya
  existe y es este proceso.

## Los estados

    pendiente   → recién anotado por el agente
    trabajando  → pedido a Magnific; `tarea` tiene el id si es asíncrono
    listo       → el archivo está en el bucket, `url` lo apunta
    rechazado   → sale más caro que el tope; NO se pidió
    error       → algo falló; `notas` dice qué
"""
import io
import json
import logging
import os
import pathlib
import tempfile
import urllib.error
import urllib.parse
import urllib.request

import requests

log = logging.getLogger(__name__)

API = "https://api.magnific.com/v1/ai"

#: Lo que cuesta cada verbo, en créditos.
#:
#: **Los seis están MEDIDOS**, no estimados. Se midieron de la única forma que
#: vale: corriendo uno y mirando cuánto bajó el saldo de la cuenta. `fondo` el
#: 26/8/2026, `crear` el 27/8, y los otros cuatro el 28/8 — 40, 180, 100 y 100,
#: contra la cota de 300 que llevaban antes. Tres de los cuatro salían bastante
#: más baratos de lo que decía la cota.
#:
#: **Lo que NO se usó para esto**: el simulador del conector de Magnific. Sus
#: números son de otros endpoints con otros modelos que las rutas REST a las
#: que le pega el worker. Una cifra que parece medida y no lo está es peor que
#: una cota honesta — por eso estuvieron dos días en 300 en vez de tomar
#: prestado un número parecido.
#:
#: **`tamano` es el único que depende del tamaño.** Magnific lo cobra por
#: tramos: 90 el chico, 180 el mediano —el que se midió, con una foto de 1,9
#: megapíxeles—, 270 el grande y 1080 el enorme. Los 180 alcanzan porque este
#: verbo existe para agrandar fotos CHICAS; para que no se cuele una grande y
#: cueste 1080 sin que nadie lo estimara, `_cuerpo` la rechaza antes (ver
#: `MAX_MP_AGRANDAR`).
PRECIOS = {
    "fondo":   {"creditos": 3,   "medido": True},
    "crear":   {"creditos": 100, "medido": True},
    "formato": {"creditos": 40,  "medido": True},
    "tamano":  {"creditos": 180, "medido": True},
    "retoque": {"creditos": 100, "medido": True},
    "escena":  {"creditos": 100, "medido": True},
}

#: Qué le pide cada verbo a Magnific.
#:
#: `sync` es la diferencia que más se nota en el código: quitar fondo contesta
#: con el resultado en la misma llamada, y los otros cuatro devuelven un id de
#: tarea que hay que ir a preguntar. Los dos caminos existen porque la API es
#: así, no porque nos guste.
VERBOS = {
    "crear": {
        "ruta": "text-to-image/seedream-v5-pro",
        "sync": False,
        "modelo": "seedream-v5-pro",
        "que_hace": "inventa una foto nueva a partir de una descripción",
        # El único verbo que NO parte de una foto. Todo lo demás en este módulo
        # supone que hay una imagen de entrada, así que la excepción se declara
        # acá y se lee de un lugar en vez de repetirse en cada `if`.
        "sin_foto": True,
    },
    "fondo": {
        "ruta": "beta/remove-background",
        "sync": True,
        "formulario": True,      # esta ruta NO lee JSON
        "modelo": "remove-background",
        "que_hace": "recorta el producto y deja el fondo transparente",
    },
    "formato": {
        "ruta": "image-expand/seedream-v4-5",
        "sync": False,
        "modelo": "seedream-v4-5-expand",
        "que_hace": "estira la foto a otra proporción inventando los bordes",
    },
    "tamano": {
        "ruta": "image-upscaler-precision-v2",
        "sync": False,
        "modelo": "upscaler-precision-v2",
        "que_hace": "agranda la foto sin que se vea blanda",
    },
    "retoque": {
        "ruta": "text-to-image/seedream-v5-pro-edit",
        "sync": False,
        "modelo": "seedream-v5-pro-edit",
        "que_hace": "saca o cambia algo puntual de la foto",
    },
    "escena": {
        "ruta": "text-to-image/seedream-v5-pro-edit",
        "sync": False,
        "modelo": "seedream-v5-pro-edit",
        "que_hace": "pone el producto en otro lugar",
    },
}

#: Las proporciones a las que se puede llevar una foto, con los nombres que ya
#: usan las plantillas. No es una lista nueva: es la misma de `marca.FORMATOS`,
#: escrita acá porque este módulo se prueba sin levantar el motor.
PROPORCIONES = {"post": 1 / 1, "vert": 4 / 5, "story": 9 / 16, "reel": 9 / 16}

#: Cómo se llaman nuestras proporciones del lado de Magnific, para `crear`.
#:
#: `vert` es el único que no tiene equivalente: nuestras piezas verticales son
#: 4:5 y el modelo no lo ofrece, así que va a 3:4, que es un poco más alto. La
#: pieza recorta unos píxeles arriba y abajo — preferible a generar un 1:1 y
#: estirarlo.
RELACIONES = {
    "post":  "square_1_1",
    "vert":  "traditional_3_4",
    "story": "social_story_9_16",
    "reel":  "social_story_9_16",
}

#: Hasta qué tamaño tiene sentido agrandar una foto — y hasta dónde sale barato.
#:
#: Las dos cosas van juntas y por eso hay un solo número. Agrandar una foto que
#: ya es grande no arregla nada: la pieza se dibuja a 2160 y con 4 megapíxeles
#: ya sobra. Y del lado del precio, Magnific cobra `tamano` por tramos y el
#: salto de arriba es feo — 1080 créditos contra los 180 del tramo mediano.
#:
#: Cortando acá pasan las dos cosas: no se agranda lo que no hace falta, y el
#: precio estimado (180) no se puede quedar corto contra el real.
MAX_MP_AGRANDAR = 4.0

#: Lo máximo que la API deja agregar de un lado al expandir.
MAX_EXPANSION = 2048


def precio(verbo: str) -> int:
    return PRECIOS.get(verbo, {"creditos": max(p["creditos"] for p in PRECIOS.values())})["creditos"]


def _clave() -> str:
    c = (os.environ.get("MAGNIFIC_CLAVE") or "").strip()
    if not c:
        raise RuntimeError("falta MAGNIFIC_CLAVE en el entorno del job")
    return c


def _pedir(ruta: str, cuerpo: dict | None = None, metodo: str = "POST",
           formulario: bool = False) -> dict:
    """Una llamada a Magnific, con el cuerpo en el formato que pide CADA ruta.

    `formulario=True` manda `application/x-www-form-urlencoded` en vez de JSON, y
    hace falta de verdad: `beta/remove-background` NO lee JSON. Contra un cuerpo
    JSON perfecto contesta *«Either image_url or image_file is required»* —
    exactamente el mismo error que contra un cuerpo vacío—, así que el mensaje
    manda a revisar la URL de la foto, que está bien, en vez del formato del
    pedido, que es lo que falla. Costó un pedido real para verlo.

    Y los errores traen el CUERPO de la respuesta, no sólo el código. Sin esto,
    una fila terminaba en `error` con la nota «HTTP Error 400: Bad Request», que
    no dice nada: hay que reproducir la llamada a mano para enterarse de algo. El
    cuerpo, en ese mismo caso, decía exactamente qué faltaba.
    """
    if cuerpo is None:
        datos, tipo = None, "application/json"
    elif formulario:
        datos = urllib.parse.urlencode(cuerpo).encode()
        tipo = "application/x-www-form-urlencoded"
    else:
        datos, tipo = json.dumps(cuerpo).encode(), "application/json"

    pedido = urllib.request.Request(
        f"{API}/{ruta}", data=datos, method=metodo,
        headers={"x-magnific-api-key": _clave(), "Content-Type": tipo})
    try:
        with urllib.request.urlopen(pedido, timeout=90) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detalle = ""
        try:
            detalle = e.read().decode("utf-8", "replace")[:300]
        except Exception:                                        # noqa: BLE001
            pass
        raise RuntimeError(
            f"Magnific contestó {e.code} en {ruta}"
            + (f": {detalle}" if detalle else "")) from None


# ═══ 1. Pedir la edición ═════════════════════════════════════════════════════

def medidas(url: str) -> tuple[int, int]:
    """El ancho y el alto de una foto, sin bajarla entera si se puede evitar.

    Hace falta sólo para `formato`: expandir se pide en PÍXELES por lado, no en
    proporciones, así que sin las medidas de la original no hay forma de saber
    cuántos agregar.
    """
    from PIL import Image
    with urllib.request.urlopen(url, timeout=60) as r:
        return Image.open(io.BytesIO(r.read())).size


def bordes(ancho: int, alto: int, formato: str) -> dict:
    """Cuántos píxeles agregar de cada lado para llegar a la proporción pedida.

    Se agrega SIEMPRE y no se recorta nunca, que es la única razón por la que
    esto existe: recortar una foto horizontal a 9:16 se come el producto, y el
    producto es lo único que no se puede perder.

    Reparte parejo entre los dos lados. Podría ser más listo —bajar más arriba
    que abajo cuando el producto está centrado— pero eso necesita saber dónde
    está el producto, y equivocarse ahí es peor que quedar simétrico.
    """
    objetivo = PROPORCIONES.get(formato)
    if not objetivo:
        raise ValueError(
            f"no sé qué proporción es «{formato}». Las que sé: "
            f"{', '.join(PROPORCIONES)}")
    lados = {"left": 0, "right": 0, "top": 0, "bottom": 0}
    actual = ancho / alto
    if actual > objetivo:                      # muy ancha: hay que hacerla alta
        falta = round(ancho / objetivo) - alto
        lados["top"] = lados["bottom"] = min(falta // 2, MAX_EXPANSION)
    elif actual < objetivo:                    # muy alta: hay que ensancharla
        falta = round(alto * objetivo) - ancho
        lados["left"] = lados["right"] = min(falta // 2, MAX_EXPANSION)
    return lados


def _cuerpo(fila: dict) -> dict:
    """El pedido que le corresponde a este verbo. Cada uno es distinto."""
    verbo, foto = fila["verbo"], fila.get("foto")
    if verbo == "crear":
        instruccion = (fila.get("instruccion") or "").strip()
        if not instruccion:
            raise ValueError(
                "«crear» necesita la descripción de la foto. Sin eso no hay "
                "nada que generar.")
        cuerpo = {"prompt": _prompt("crear", instruccion), "resolution": "2k"}
        rel = RELACIONES.get(fila.get("formato") or "")
        if rel:
            cuerpo["aspect_ratio"] = rel
        return cuerpo
    if verbo == "fondo":
        return {"image_url": foto}
    if verbo == "tamano":
        ancho, alto = medidas(foto)
        mp = (ancho * alto) / 1_000_000
        if mp > MAX_MP_AGRANDAR:
            raise ValueError(
                f"esta foto ya mide {ancho}x{alto} ({mp:.1f} megapíxeles) y las "
                f"piezas se dibujan a 2160: agrandarla no cambiaría nada y "
                f"costaría varias veces más. Usala como está.")
        return {"image": foto}
    if verbo == "formato":
        ancho, alto = medidas(foto)
        lados = bordes(ancho, alto, fila.get("formato") or "story")
        if not any(lados.values()):
            raise ValueError(
                f"la foto ya está en {fila.get('formato')}: no hay nada que "
                f"expandir. Usá la original.")
        return {"image": foto, **lados}
    if verbo in ("retoque", "escena"):
        instruccion = (fila.get("instruccion") or "").strip()
        if not instruccion:
            raise ValueError(
                f"«{verbo}» necesita que le digan qué hacer. Sin instrucción no "
                f"hay nada que pedirle al modelo.")
        return {"prompt": _prompt(verbo, instruccion),
                "reference_images": [foto]}
    raise ValueError(f"no sé hacer «{verbo}». Sé: {', '.join(VERBOS)}")


def _prompt(verbo: str, instruccion: str) -> str:
    """Lo que se le dice al modelo, con la regla del producto pegada atrás.

    La regla no es adorno y no se puede sacar: se midió con los reels que
    pidiéndole al modelo que MANIPULE el producto lo deforma —la caña alta de
    una zapatilla desapareció y la suela cambió de color—. Acá el riesgo es el
    mismo y peor, porque el resultado se publica como si fuera una foto del
    producto de verdad.

    La instrucción va **tal cual la escribió la persona**, en castellano, aunque
    la regla vaya en inglés y aunque el modelo responda algo mejor en inglés.
    Traducirla necesitaría una llamada a un modelo por cada edición —para una
    operación que sale 3 créditos y tarda segundos— y sobre todo pondría en el
    medio algo que puede entender mal lo que pidieron. Una traducción torcida
    de «sacale el cartel» es peor que un prompt mezclado.
    """
    # `crear` no tiene producto que cuidar: parte de la nada. Lo que sí tiene
    # es el riesgo contrario — que la imagen salga con carteles, logos o marcas
    # inventadas y termine publicada como si fuera el local de verdad. Un texto
    # falso en la fachada de una clínica no es un detalle estético.
    if verbo == "crear":
        return (f"{instruccion.strip()}. Photorealistic, natural light, clean "
                f"composition. No text, no letters, no logos, no signage, no "
                f"watermarks anywhere in the image. Do not depict real brands.")

    regla = ("Keep the product exactly as it is: same shape, same colors, same "
             "materials, same logos and text on it. Do not redesign it, do not "
             "change its proportions, do not add or remove parts of it.")
    if verbo == "escena":
        return (f"{instruccion.strip()}. Photorealistic, natural light. {regla}")
    return f"{instruccion.strip()}. {regla}"


def pedir(fila: dict) -> tuple[str | None, str | None]:
    """Le pide la edición a Magnific.

    Devuelve `(tarea, url_lista)`. Uno de los dos es None y cuál depende del
    verbo: `fondo` contesta con el resultado ahí mismo, los otros cuatro con un
    id para ir a preguntar después.
    """
    v = VERBOS[fila["verbo"]]
    r = _pedir(v["ruta"], _cuerpo(fila), formulario=v.get("formulario", False))
    if v["sync"]:
        # La respuesta trae varias resoluciones. Se toma la grande: las piezas
        # se dibujan a 2160 y el `preview` viene a 0,25 megapíxeles, que es
        # menos de lo que ya tenía la foto original.
        url = r.get("high_resolution") or r.get("url")
        if not url:
            raise RuntimeError(f"quitar fondo no devolvió una imagen: {r}")
        return None, url
    d = r.get("data") or r
    tarea = d.get("task_id") or d.get("id")
    if not tarea:
        raise RuntimeError(f"no vino el id de la tarea: {r}")
    return tarea, None


def estado(fila: dict) -> tuple[str, str | None]:
    """`(estado, url)` de una tarea asíncrona."""
    v = VERBOS[fila["verbo"]]
    d = _pedir(f"{v['ruta']}/{fila['tarea']}", metodo="GET")
    d = d.get("data") or d
    est = str(d.get("status") or "").upper()
    urls = d.get("generated") or d.get("images") or []
    url = d.get("url") or (urls[0] if urls else None)
    if isinstance(url, dict):
        url = url.get("url")
    return est, url


def bajar(url: str, destino: pathlib.Path) -> pathlib.Path:
    with urllib.request.urlopen(url, timeout=180) as r, open(destino, "wb") as f:
        f.write(r.read())
    return destino


# ═══ 2. El ciclo ═════════════════════════════════════════════════════════════

def _pendientes(cli, est: str, limite: int = 5) -> list[dict]:
    r = requests.get(
        cli._url("fotos_editadas"), headers=cli._cab(), timeout=30,
        params={"estado": f"eq.{est}", "order": "creado_en.asc",
                "limit": str(limite),
                "select": "id,creado_en,actualizado_en,verbo,foto,instruccion,"
                          "formato,tarea,modelo,quien,creditos_estimados"})
    if r.status_code in (400, 404):
        return []                    # esta base todavía no tiene la tabla
    r.raise_for_status()
    return r.json()


def _tomar(cli, rid: str, de: str, a: str) -> bool:
    """Igual que en los reels: el filtro por el estado viejo va en el PATCH.

    Dos worker vivos a la vez leerían la misma fila y los dos pedirían la misma
    edición, cobrada dos veces. Con el filtro, el segundo recibe cero filas.
    """
    r = requests.patch(
        cli._url("fotos_editadas"),
        headers={**cli._cab(), "Prefer": "return=representation"},
        params={"id": f"eq.{rid}", "estado": f"eq.{de}"},
        data=json.dumps({"estado": a}), timeout=30)
    r.raise_for_status()
    return bool(r.json())


def _marcar(cli, rid: str, est: str, **campos):
    requests.patch(
        cli._url("fotos_editadas"), headers=cli._cab(),
        params={"id": f"eq.{rid}"},
        data=json.dumps({"estado": est, **campos}), timeout=30).raise_for_status()


def _gastado_este_mes(cli) -> int:
    from datetime import datetime, timezone
    desde = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0,
                                               microsecond=0).isoformat()
    r = requests.get(cli._url("fotos_editadas"), headers=cli._cab(), timeout=30,
                     params={"creado_en": f"gte.{desde}",
                             "estado": "not.in.(rechazado,error)",
                             "select": "creditos_estimados"})
    if r.status_code in (400, 404):
        return 0
    return sum((f.get("creditos_estimados") or 0) for f in r.json())


#: Cuánto se le aguanta a una tarea antes de darla por perdida. Una edición
#: tarda segundos; diez minutos es mucho más que de sobra.
TOPE_TRABAJANDO = 10 * 60


def _colgada(fila: dict) -> bool:
    """Igual que en los reels, y contra `actualizado_en` por la misma razón:
    lo que se acota es la espera a Magnific, no la vida del pedido."""
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
    return (datetime.now(timezone.utc) - cuando).total_seconds() > TOPE_TRABAJANDO


def _guardar(cli, fila: dict, url: str, subir) -> str:
    """Baja el resultado y lo sube al bucket. Devuelve la URL definitiva.

    Esto no es un paso administrativo: **la URL de Magnific caduca**. La de
    quitar fondo vive cinco minutos. Guardar la de ellos en la base sería
    guardar un enlace roto que funciona el tiempo justo para que la prueba
    salga bien y falle con el primer cliente.
    """
    ext = ".png" if fila["verbo"] == "fondo" else ".jpg"
    with tempfile.TemporaryDirectory() as tmp:
        local = bajar(url, pathlib.Path(tmp) / f"foto{ext}")
        return subir(local, f"editadas/{fila['id']}{ext}")


def atender_todos(cli, ficha: dict, subir) -> int:
    """Un ciclo. Devuelve cuántas filas movió.

    `subir(Path, nombre) -> url` entra por parámetro y no por import para que
    este módulo se pueda probar sin levantar el motor entero.
    """
    tope_pieza = int(ficha.get("creditos_maximos") or 600)
    tope_mes = int(ficha.get("creditos_maximos_mes") or 5000)
    movidas = 0

    # --- a) recién anotados ------------------------------------------------
    nuevos = _pendientes(cli, "pendiente")

    # La clave se mira ANTES de tocar una fila. Si faltara, el pedido quedaría
    # trabado en `trabajando`, que nadie vuelve a levantar; así se queda quieto
    # en `pendiente` y sale solo en la primera corrida después del secreto.
    if nuevos and not (os.environ.get("MAGNIFIC_CLAVE") or "").strip():
        log.warning("[%s] %d foto(s) esperando: falta MAGNIFIC_CLAVE en el job",
                    getattr(cli, "marca", "?"), len(nuevos))
        nuevos = []

    for fila in nuevos:
        verbo = fila.get("verbo")
        if verbo not in VERBOS:
            _marcar(cli, fila["id"], "error",
                    notas=f"no sé hacer «{verbo}». Sé: {', '.join(VERBOS)}")
            movidas += 1
            continue

        cuesta = precio(verbo)
        ya = _gastado_este_mes(cli)
        if cuesta > tope_pieza:
            _marcar(cli, fila["id"], "rechazado", creditos_estimados=cuesta,
                    notas=f"«{verbo}» sale {cuesta} créditos y el tope por pieza "
                          f"es {tope_pieza}.")
            movidas += 1
            continue
        if ya + cuesta > tope_mes:
            _marcar(cli, fila["id"], "rechazado", creditos_estimados=cuesta,
                    notas=f"este mes ya hay {ya} créditos de fotos comprometidos "
                          f"y el tope es {tope_mes}.")
            movidas += 1
            continue

        if not _tomar(cli, fila["id"], "pendiente", "trabajando"):
            continue
        try:
            tarea, url = pedir(fila)
            if url:
                # Sync: ya está. Se baja y se sube en la misma corrida porque
                # la URL de Magnific caduca a los cinco minutos.
                _marcar(cli, fila["id"], "listo",
                        url=_guardar(cli, fila, url, subir),
                        modelo=VERBOS[verbo]["modelo"],
                        creditos_estimados=cuesta, creditos_gastados=cuesta)
            else:
                _marcar(cli, fila["id"], "trabajando", tarea=tarea,
                        modelo=VERBOS[verbo]["modelo"], creditos_estimados=cuesta)
        except Exception as e:                                   # noqa: BLE001
            # A `error` y no de vuelta a la cola: si el pedido se cortó por
            # timeout puede haber salido igual del otro lado, y reintentar lo
            # cobraría dos veces.
            log.exception("[%s] falló la foto %s", getattr(cli, "marca", "?"),
                          fila["id"])
            _marcar(cli, fila["id"], "error", notas=str(e)[:400])
        movidas += 1

    # --- b) las asíncronas: ¿ya están? -------------------------------------
    for fila in _pendientes(cli, "trabajando"):
        if not fila.get("tarea"):
            # Sin tarea no hay a quién preguntarle. Pasa si el worker murió
            # entre el `_tomar` y el `_marcar`.
            if _colgada(fila):
                _marcar(cli, fila["id"], "error",
                        notas="quedó trabajando sin id de tarea")
                movidas += 1
            continue
        try:
            est, url = estado(fila)
        except Exception as e:                                   # noqa: BLE001
            # Preguntar no cobra, así que un fallo acá no mata la fila: se
            # vuelve a preguntar el minuto que viene. El try está para que una
            # tarea rota no se lleve puesto el resto de la corrida.
            log.warning("[%s] no pude preguntar por la foto %s: %s",
                        getattr(cli, "marca", "?"), fila["id"], e)
            if _colgada(fila):
                _marcar(cli, fila["id"], "error", notas=f"sin respuesta: {e}")
                movidas += 1
            continue

        if est in ("COMPLETED", "SUCCESS", "SUCCEEDED", "DONE") and url:
            try:
                _marcar(cli, fila["id"], "listo",
                        url=_guardar(cli, fila, url, subir),
                        creditos_gastados=fila.get("creditos_estimados"))
            except Exception as e:                               # noqa: BLE001
                log.exception("[%s] no pude guardar la foto %s",
                              getattr(cli, "marca", "?"), fila["id"])
                _marcar(cli, fila["id"], "error", notas=f"al guardar: {e}")
            movidas += 1
        elif est in ("FAILED", "ERROR"):
            _marcar(cli, fila["id"], "error", notas=f"Magnific devolvió {est}")
            movidas += 1
        elif _colgada(fila):
            _marcar(cli, fila["id"], "error",
                    notas=f"lleva más de {TOPE_TRABAJANDO // 60} minutos en "
                          f"«{est or 'sin estado'}»")
            movidas += 1

    return movidas


# ═══ 3. El enganche con el worker ════════════════════════════════════════════

def _ficha(marca: str) -> dict:
    """El bloque `fotos` del `marca.json`, o vacío si la marca no lo tiene.

    Vacío quiere decir que esta marca no edita fotos, y con eso alcanza para no
    tocarle la cola. Boss y Clínica no lo tienen.
    """
    from .disenador import _ficha as ficha_de_marca
    return (ficha_de_marca(marca) or {}).get("fotos") or {}


def atender(cli) -> int:
    ficha = _ficha(cli.marca)
    if not ficha:
        return 0
    return atender_todos(cli, ficha, cli.subir)
