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
import re
import subprocess
import tempfile
import urllib.error
import urllib.request

import requests

log = logging.getLogger(__name__)

API = "https://api.magnific.com/v1/ai/video"

#: Los modelos de video que sabemos pedir, con lo que cada uno cuesta y lo que
#: cada uno acepta. No son intercambiables: cambia el precio, cambian las
#: duraciones permitidas, cambia la forma del pedido y hasta cambia la URL para
#: preguntar cómo va. Por eso está todo junto en una tabla y no repartido.
#:
#: **Los precios se MIDIERON con `simulate_cost` el 26/8/2026**, en 9:16 con
#: efectos de sonido, y son lineales por segundo (se comprobó en 6, 10 y 15
#: segundos: 840, 1.400 y 2.100 en Mini 720p). Magnific no publica una tabla de
#: precios, así que esto queda viejo sin avisar el día que los cambie. Lo que
#: de verdad protege es el tope de créditos de la marca: aunque esta tabla
#: mienta, el gasto queda acotado.
#:
#: La diferencia entre Mini 2.0 y 2.5 es de tres veces por el mismo reel —1.400
#: contra 4.400 en diez segundos a 720p— y Magnific misma marca a Mini como su
#: mejor relación calidad/precio para clips de 4 a 15 segundos.
MODELOS = {
    "seedance-2-mini": {
        "nombre": "Seedance 2.0 Mini",
        "ruta": "seedance-2-mini-{res}",
        "ruta_estado": "seedance-2-mini",     # el estado NO lleva resolución
        "precio": {"480p": 70, "720p": 140},
        "duraciones": (5, 10),                # exactamente estas dos
        "multishot": False,                   # sólo un `prompt`, hasta 2000
        "referencias": True,
        "manda_el_audio": False,              # no acepta `no_music`
    },
    "seedance-2-5-pro": {
        "nombre": "Seedance 2.5",
        "ruta": "seedance-2-5-pro-{res}",
        "ruta_estado": "seedance-2-5-pro-{res}",
        "precio": {"480p": 200, "720p": 440, "1080p": 790},
        # 4 a 30 segundos, comprobado contra la API: acepta 30 y rechaza 3. Acá
        # decía 4–12 y estaba mal, copiado de un techo mío de otra parte del
        # código: un pedido de 15 segundos no se podía cumplir NUNCA, ni con el
        # tope de créditos por las nubes, porque la tabla mentía sobre lo que el
        # modelo sabe hacer. Los límites de un modelo se miden, no se suponen.
        "duraciones": tuple(range(4, 31)),
        "multishot": True,
        "referencias": True,
        "manda_el_audio": True,               # acepta `no_music`
    },
}

#: Lo que la persona pide en el chat, traducido a modelo y resolución.
#:
#: Son tres y no diez porque quien escribe en el chat no elige un modelo: dice
#: si esto es una prueba o si va a publicarse. Traducir eso es trabajo nuestro.
CALIDADES = {
    "borrador": ("seedance-2-mini", "480p"),
    "normal":   ("seedance-2-mini", "720p"),
    "maxima":   ("seedance-2-5-pro", "720p"),
}

#: Lo que se le pide a Magnific si la marca no dice otra cosa.
#:
#: `normal` es Mini 2.0 a 720p: 140 créditos por segundo. Magnific llama «720p»
#: al lado largo, así que el clip sale de 406×720 y hay que estirarlo a
#: 1080×1920 — 2,7 veces. En 480p serían 270×480, o sea 4 veces, y a esa altura
#: el video se ve blando; sirve para un borrador, no para publicar.
POR_DEFECTO = {"calidad": "normal", "duracion": 6, "relacion": "social_story_9_16"}

#: Lo que se acepta LEER de un pedido. No es lo que se va a hacer —eso lo
#: decide `_plan` con lo que el modelo y el tope permiten— es hasta dónde se
#: considera que un número es una duración y no otra cosa.
#:
#: Estaba en 4–12 y eso rompió un pedido real: alguien pidió 15 segundos, el 15
#: cayó afuera del rango, `duracion_pedida` devolvió None —que significa «no
#: dijo nada»— y el reel salió de 10 SIN UNA PALABRA de por qué. Un techo que
#: descarta callado es el mismo error que no leer la duración: la persona pidió
#: algo y el sistema hizo otra cosa sin avisar.
#:
#: Ahora el rango es amplio —Seedance 2.5 hace hasta 30— y lo que no entra ya
#: no se descarta: se recorta a lo posible y SE DICE.
DURACION_MINIMA, DURACION_MAXIMA = 3, 60

_SEGUNDOS = re.compile(
    r"(?:de\s+)?(\d{1,2})\s*(?:segundos?|seg\b|s\b)", re.IGNORECASE)


def ficha_modelo(modelo: str) -> dict:
    return MODELOS.get(modelo) or MODELOS["seedance-2-5-pro"]


def precio(modelo: str, resolucion: str, duracion: int) -> int:
    """Lo que va a salir este video, antes de pedirlo.

    Si no conoce la combinación devuelve el precio más caro que conoce, no cero.
    Un precio desconocido que se estima en cero pasa cualquier tope y se entera
    con la factura.
    """
    tabla = ficha_modelo(modelo)["precio"]
    return tabla.get(resolucion, max(tabla.values())) * duracion


def duracion_valida(modelo: str, pedida: int) -> int:
    """La duración más cercana a la pedida que el modelo acepta de verdad.

    Mini 2.0 sólo hace 5 o 10 segundos —el resto la API los rechaza con un
    error de validación—, y 2.5 va de 4 en adelante. Pedir 7 en Mini no es un
    video de 7 segundos: es un 400 y un pedido perdido.
    """
    permitidas = ficha_modelo(modelo)["duraciones"]
    if pedida in permitidas:
        return pedida
    return min(permitidas, key=lambda d: (abs(d - pedida), d))


def duracion_pedida(mensaje: str | None) -> int | None:
    """Los segundos que pidió la persona, si los dijo.

    «Un reel de 10 segundos» es un pedido, no un comentario, y hasta el
    26/8/2026 el worker lo ignoraba: sacaba la duración del `marca.json` y
    hacía seis segundos siempre. Se pidieron diez dos veces seguidas y salieron
    seis las dos veces, sin una palabra que dijera por qué.

    Es una expresión regular y no una pregunta al modelo a propósito: «10
    segundos» escrito en castellano no tiene ambigüedad que valga una llamada.
    Si no encuentra nada, devuelve None y manda el default de la marca.

    **Lo que encuentra lo devuelve aunque sea imposible.** Si alguien pide 15
    segundos y ningún modelo llega, eso lo resuelve `_plan` —recorta y lo
    escribe en `notas`—; devolver None acá lo convertiría en «no pidió nada» y
    la persona nunca se enteraría. El rango sólo descarta lo que claramente no
    es una duración de reel, no lo que es difícil de cumplir.
    """
    m = _SEGUNDOS.search(mensaje or "")
    if not m:
        return None
    n = int(m.group(1))
    return n if DURACION_MINIMA <= n <= DURACION_MAXIMA else None


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
    """Una llamada a Magnific, con el CUERPO del error cuando falla.

    Sin esto, un pedido rechazado deja la nota «HTTP Error 400: Bad Request», que
    no dice nada y obliga a reproducir la llamada a mano para enterarse de algo.
    El cuerpo de la respuesta dice qué campo falta o qué valor no acepta — que es
    justo lo que hay que leer cuando la fila ya está en `error` y el video, si
    salió, ya se pagó.
    """
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pedido = urllib.request.Request(
        f"{API}/{ruta}", data=datos, method=metodo,
        headers={"x-magnific-api-key": _clave(),
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(pedido, timeout=60) as r:
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


# ═══ 1. Pedir el video ═══════════════════════════════════════════════════════

def pedir_clip(fila: dict, plan: dict, planos: list[dict]) -> str:
    """Le pide el video a Magnific y devuelve el id de tarea.

    Manda la foto en `reference_images` y no en `image`. La diferencia importa:
    con `image` el video ARRANCA de esa foto y sigue desde ahí, y una foto de
    catálogo sobre fondo blanco da un reel sobre fondo blanco. Como referencia,
    en cambio, la foto le dice al modelo CÓMO ES el producto y lo deja componer
    una escena. El producto se mantiene y el fondo es de verdad.

    Los planos van en `multishot` **cuando el modelo lo acepta**. 2.5 lo acepta;
    Mini 2.0 no —su API sólo toma un `prompt` de hasta 2.000 caracteres— y ahí
    los mismos planos se pliegan a un párrafo numerado. No es lo mismo: separar
    los tiempos da más control y se midió que con un solo plano el modelo se
    saltea la mitad de lo pedido. Numerarlos es lo más parecido que se puede
    hacer sin el campo.
    """
    m = ficha_modelo(plan["modelo"])
    cuerpo = {
        "duration": plan["duracion"],
        "aspect_ratio": POR_DEFECTO["relacion"],
        "sound_effects": True,
    }
    if m["referencias"]:
        cuerpo["reference_images"] = [fila["foto"]]
    if m["manda_el_audio"]:
        # La música la pone el worker desde el banco de la marca: es más barata
        # (una pista se genera una vez y se reusa en todos los reels) y sobre
        # todo es SIEMPRE la misma, que es lo que hace que una cuenta suene a
        # una cuenta y no a veinte piezas sueltas. El modelo que no acepta este
        # campo puede meter música propia, y de eso se entera el montaje.
        cuerpo["no_music"] = True

    if m["multishot"]:
        cuerpo["prompt"] = fila["mensaje"]
        cuerpo["multishot"] = planos
    else:
        cuerpo["prompt"] = _un_solo_prompt(planos)
    return _pedir(m["ruta"].format(res=plan["resolucion"]), cuerpo)["data"]["task_id"]


def _un_solo_prompt(planos: list[dict], tope: int = 1990) -> str:
    """Los planos plegados en un párrafo, para el modelo que no tiene multishot.

    Va numerado y con los segundos de cada tiempo adelante. Es la forma que más
    se parece a una lista de planos dentro de un campo de texto: el modelo lee
    un orden, no una sola escena promediada.

    El recorte al final no es decorativo: Mini corta en 2.000 caracteres y un
    prompt más largo se rechaza entero. Se recorta el ÚLTIMO plano, que es el
    que menos se nota, en vez de dejar que la API tire el pedido.
    """
    partes = [f"Shot {i} ({p['duration']}s): {p['prompt']}"
              for i, p in enumerate(planos, 1)]
    texto = " ".join(partes)
    return texto if len(texto) <= tope else texto[:tope].rsplit(" ", 1)[0]


GUION = """Escribí la lista de planos de un reel vertical de {dur} segundos.

Lo que pidió la persona, textual:
\"\"\"{pedido}\"\"\"

El producto es: {producto}. Va aparte como imagen de referencia, así que no
hace falta describirlo en detalle: alcanza con nombrarlo.

Reglas:

1. Si la persona describió una escena, ESA es la escena. Seguila. No la
   cambies por algo más seguro ni más publicitario.
2. Si sólo pidió "un reel con este producto" sin decir qué pasa, usá esta
   estructura de retail: el producto quieto con la cámara acercándose muy
   despacio, después una persona que entra al cuadro al lado del producto, y
   al final alguien de espaldas caminando en la calle usándolo.
3. El producto tiene que quedar reconocible y sin deformarse: misma forma,
   mismos colores, mismos detalles. Una escena rara —el producto gigante,
   alguien que cae adentro— está PERMITIDA si la pidieron; lo que no se vale
   es que el producto cambie de forma o que unas manos lo estrujen.
4. Nada de texto, letras ni carteles en el video. El texto lo pone el rótulo
   después, encima.
5. Escribí los planos EN INGLÉS. El modelo responde mejor.
6. Entre dos y tres planos, y las duraciones tienen que sumar exactamente
   {dur}.

Y decidí la calidad, que es lo que va a costar:

· `borrador` — si la persona dice que es una prueba, un boceto, "a ver cómo
  queda", o pide algo rápido o barato.
· `normal` — el default. Cualquier pedido de trabajo sin más aclaración.
· `maxima` — sólo si dice que es para publicar, que tiene que quedar
  impecable, que es para una campaña, o pide expresamente la mejor calidad.

Ante la duda, `normal`: cuesta tres veces menos que `maxima` y es la que se
usa todos los días.

Contestá SÓLO el JSON, sin explicar nada y sin ```:

{{"calidad": "normal", "planos": [{{"prompt": "...", "duration": 3}}, {{"prompt": "...", "duration": 3}}]}}
"""


def guionar(fila: dict, dur: int) -> dict | None:
    """`{calidad, planos}` a partir de lo que pidió la persona. None si no se pudo.

    Esto existe porque durante un tiempo NO existió, y el efecto fue el peor
    posible: silencioso. `_planos` armaba siempre los mismos tres tiempos de
    retail y se mandaban en `multishot`, que pesa mucho más que el `prompt`.
    Así que alguien pedía «una persona cae del cielo y aterriza adentro del
    zapato», pagaba 2.640 créditos, y recibía un reel de catálogo correcto y
    completamente ajeno a lo que había pedido. Sin un error en ningún lado.

    La estructura de retail no se tira —sigue siendo el mejor default y está
    escrita en el prompt—, pero pasa a ser lo que se hace CUANDO NO PIDIERON
    OTRA COSA, que es muy distinto de lo único que se puede hacer.

    Es un solo turno y sin herramientas: no es un agente trabajando, es una
    traducción de un pedido en castellano a una lista de planos. Al lado de los
    2.640 créditos del video, lo que cuesta no se mide.

    Si falla, devuelve None y el que llama se queda con `_planos`. Preferimos
    un reel genérico antes que ningún reel.
    """
    pedido = (fila.get("mensaje") or "").strip()
    if not pedido:
        return None
    try:
        import asyncio

        from claude_agent_sdk import ClaudeAgentOptions, query

        prompt = GUION.format(dur=dur, pedido=pedido[:2000],
                              producto=fila.get("foto_texto") or "the product")

        async def _pedir_guion() -> str:
            texto = ""
            async for msg in query(prompt=prompt, options=ClaudeAgentOptions(
                    allowed_tools=[], max_turns=1, permission_mode="dontAsk")):
                for bloque in getattr(msg, "content", None) or []:
                    t = getattr(bloque, "text", None)
                    if t:
                        texto += t
            return texto

        # `asyncio.run` y no `await`: esta función corre adentro del hilo que
        # `chat.py` abre con `to_thread`, o sea que no hay loop andando acá.
        crudo = asyncio.run(_pedir_guion())
    except Exception as e:                                   # noqa: BLE001
        log.warning("no pude armar el guión, uso los planos por defecto: %s", e)
        return None

    # El modelo puede envolver el JSON en ``` o en una frase. Se recorta a la
    # primera llave y a la última, que es más robusto que pedir por favor.
    try:
        i, j = crudo.index("{"), crudo.rindex("}")
        d = json.loads(crudo[i:j + 1])
        planos = [{"prompt": str(p["prompt"]), "duration": int(p["duration"])}
                  for p in (d.get("planos") or [])
                  if p.get("prompt") and p.get("duration")]
        calidad = str(d.get("calidad") or "").strip().lower()
    except Exception as e:                                   # noqa: BLE001
        log.warning("el guión no vino como JSON, uso los planos por defecto: %s", e)
        return None
    if not planos:
        return None
    # Una calidad inventada no elige un modelo carísimo por accidente: cae al
    # default, que es el barato.
    if calidad not in CALIDADES:
        calidad = POR_DEFECTO["calidad"]

    # Las duraciones tienen que sumar `dur` exactamente o Magnific rechaza el
    # pedido. El sobrante o el faltante va al último plano, que es el que menos
    # sufre un segundo de más o de menos.
    total = sum(p["duration"] for p in planos)
    if total != dur:
        planos[-1]["duration"] += dur - total
    if planos[-1]["duration"] < 1:
        return None
    log.info("guión %s de %d planos: %s", calidad, len(planos),
             " | ".join(f"{p['duration']}s {p['prompt'][:50]}" for p in planos))
    return {"calidad": calidad, "planos": planos}


def _planos(fila: dict, dur: int) -> list[dict]:
    """Los tres tiempos de un reel de producto, repartidos en `dur` segundos.

    Es el DEFAULT, no la ley: se usa cuando `guionar` no pudo armar el guión a
    partir de lo que pidió la persona. Lo de abajo sigue valiendo como consejo
    y por eso está también escrito en el prompt de `guionar`.

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


def estado_clip(tarea: str, modelo: str, resolucion: str) -> tuple[str, str | None]:
    """`(estado, url)` de una tarea. La URL vive 24 horas: hay que bajarla ya.

    La ruta para preguntar NO es la misma que para pedir, y no es igual en todos
    los modelos: 2.5 la lleva con resolución y Mini 2.0 sin ella. Preguntar por
    la ruta equivocada da 404, o sea «no existe» para una tarea que existe y se
    está generando — y el reel se daría por perdido con el video ya pagado.
    """
    ruta = ficha_modelo(modelo)["ruta_estado"].format(res=resolucion)
    d = _pedir(f"{ruta}/{tarea}", metodo="GET")["data"]
    urls = d.get("generated") or []
    return d.get("status", "").upper(), (urls[0] if urls else None)


# ═══ 2. Montar la pieza ══════════════════════════════════════════════════════

def montar(clip: pathlib.Path, rotulo: pathlib.Path | None, musica: pathlib.Path | None,
           salida: pathlib.Path, dur: float, usar_ambiente: bool = True) -> pathlib.Path:
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
    # `usar_ambiente=False` cuando el modelo no acepta que le pidan silencio: el
    # clip puede venir con MÚSICA propia, y mezclarla debajo de la nuestra no da
    # ambiente, da dos canciones a la vez. Con 2.5 se pide `no_music` y lo que
    # queda es sonido de ambiente de verdad, que sí suma.
    ambiente = usar_ambiente and _tiene_audio(clip)
    filtro = [f"[0:v]scale=1080:1920:flags=lanczos,"
              f"fade=t=out:st={dur-0.5:.2f}:d=0.5[vout]"]
    orden = ["-i", str(clip)]
    # El índice de la música depende de si hay rótulo, porque el rótulo es una
    # entrada más. Se lleva en una variable en vez de escribir `[2:a]` a mano:
    # el número escrito a mano fue correcto mientras el rótulo era obligatorio
    # y habría apuntado al video el día que dejó de serlo.
    i_musica = 1
    if rotulo:
        filtro[0] = filtro[0].replace("[vout]", "[base]")
        filtro += [
            f"[1:v]format=rgba,fade=t=in:st=0.3:d=0.5:alpha=1,"
            f"fade=t=out:st={dur-0.8:.2f}:d=0.6:alpha=1[rot]",
            "[base][rot]overlay=0:0:shortest=1[vout]",
        ]
        orden += ["-loop", "1", "-t", f"{dur+0.1:.2f}", "-i", str(rotulo)]
        i_musica = 2
    if musica:
        orden += ["-i", str(musica)]
        filtro.append(
            f"[{i_musica}:a]atrim=0:{dur:.2f},afade=t=in:st=0:d=0.3,"
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
                          "kicker,bajada,musica,tarea,modelo,resolucion,"
                          "duracion,clip_url,quien,metricas,creditos_estimados"})
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


def _plan(calidad: str, dur_pedida: int, tope_pieza: int) -> tuple[dict | None, str]:
    """Qué modelo, qué resolución y cuántos segundos, dentro del tope.

    Devuelve `(plan, aviso)`. El aviso es para la persona: si acá se cambió
    algo de lo que pidió, tiene que poder leer qué y por qué. Un pedido que
    sale distinto sin decir nada es peor que un pedido rechazado.

    En vez de ir recortando de a poco, se arman TODAS las combinaciones que el
    tope paga y se elige la mejor. Recortar por pasos parece más simple y se
    equivoca: probando calidad por calidad dentro de cada duración, un pedido
    de 12 segundos en calidad máxima con tope 4.500 salía en calidad normal de
    10 —porque «normal» se probaba antes de bajar a 10 segundos— cuando la
    máxima de 10 costaba 4.400 y entraba igual. Con las combinaciones a la
    vista eso no puede pasar.

    El criterio, en este orden:

    1. **La duración manda.** Gana la que más se acerca a lo pedido. Un video
       de cuatro segundos donde se pidieron diez se nota de lejos; el cambio de
       modelo, mucho menos. Puede pasarse de lo pedido si es lo más cercano que
       el modelo hace —Mini sólo hace 5 o 10, así que ocho segundos salen de
       diez— siempre que el tope lo pague.
    2. **Después la calidad**, y nunca por encima de la pedida: nadie quiere
       descubrir que su borrador salió en calidad máxima.
    """
    orden = ["maxima", "normal", "borrador"]
    if calidad not in orden:
        calidad = POR_DEFECTO["calidad"]
    candidatas = orden[orden.index(calidad):]

    opciones = []
    for rango, c in enumerate(candidatas):
        modelo, res = CALIDADES[c]
        for dur in ficha_modelo(modelo)["duraciones"]:
            cuesta = precio(modelo, res, dur)
            if cuesta <= tope_pieza:
                opciones.append((abs(dur - dur_pedida), rango, dur, c, modelo,
                                 res, cuesta))
    if not opciones:
        barato_m, barato_r = CALIDADES[candidatas[-1]]
        barato_d = min(ficha_modelo(barato_m)["duraciones"])
        return None, (f"ni el reel más barato ({barato_d}s en {barato_r}, "
                      f"{precio(barato_m, barato_r, barato_d)} créditos) entra "
                      f"en el tope por pieza ({tope_pieza}). Subilo en marca.json.")

    _, _, dur, c, modelo, res, cuesta = min(opciones)
    avisos = []
    if c != calidad:
        avisos.append(f"lo bajé a calidad {c} para que entrara en el tope de "
                      f"{tope_pieza} créditos")
    if dur != dur_pedida:
        avisos.append(f"pediste {dur_pedida} segundos y sale de {dur}: es lo "
                      f"que hace {ficha_modelo(modelo)['nombre']}")
    return ({"modelo": modelo, "resolucion": res, "duracion": dur,
             "creditos": cuesta, "calidad": c}, " · ".join(avisos))


def _ajustar(planos: list[dict], dur: int) -> list[dict]:
    """Que los planos sumen exactamente los segundos del video.

    El guión se escribe para la duración PEDIDA y el modelo puede hacer otra
    —Mini sólo hace 5 o 10—, así que las dos casi nunca coinciden. Un multishot
    que suma distinto que `duration` no es un video más largo ni más corto: es
    un pedido que Magnific rechaza.
    """
    planos = [dict(p) for p in planos]
    total = sum(p["duration"] for p in planos)
    if total == dur or not planos:
        return planos
    # Se reparte proporcionalmente y el resto va al último, que es el plano que
    # menos sufre un segundo de más o de menos.
    for p in planos:
        p["duration"] = max(1, round(p["duration"] * dur / total))
    planos[-1]["duration"] += dur - sum(p["duration"] for p in planos)
    if planos[-1]["duration"] < 1:
        # Con muy pocos segundos y muchos planos no hay reparto posible: se
        # quedan los que entren.
        planos = planos[:dur]
        for i, p in enumerate(planos):
            p["duration"] = 1
        planos[-1]["duration"] += dur - len(planos)
    return planos


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
    # todo se rechaza y nadie entiende por qué.
    tope_pieza = int(ficha.get("creditos_maximos") or 4500)
    tope_mes = int(ficha.get("creditos_maximos_mes") or 20000)
    dur = int(ficha.get("duracion") or POR_DEFECTO["duracion"])
    # La calidad por defecto de la marca. Es el 90% de los reels: acá es donde
    # está la plata, no en la excepción que pide calidad máxima.
    calidad_marca = ficha.get("calidad") or POR_DEFECTO["calidad"]
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
            con_foto = {**fila, "foto_texto": fila.get("titulo") or "the product"}
            dur_pedida = duracion_pedida(fila.get("mensaje")) or dur

            # El guión sale ANTES de elegir modelo, porque de ahí sale también
            # la calidad: la misma lectura del pedido que decide los planos
            # decide si esto es una prueba o algo para publicar. Una sola
            # llamada, no dos.
            guion = ((fila.get("metricas") or {}).get("guion")
                     or guionar(con_foto, dur_pedida) or {})
            calidad = guion.get("calidad") or calidad_marca
            planos = guion.get("planos") or _planos(con_foto, dur_pedida)

            plan, aviso = _plan(calidad, dur_pedida, tope_pieza)
            if not plan:
                _marcar(cli, fila["id"], "rechazado", notas=aviso)
                movidas += 1
                continue

            # Los planos se rearman si el modelo recortó la duración, o suman
            # otra cosa que el video y el modelo se queda con lo primero.
            planos = _ajustar(planos, plan["duracion"])
            cuesta = plan["creditos"]

            ya = _gastado_este_mes(cli)
            if ya + cuesta > tope_mes:
                _marcar(cli, fila["id"], "rechazado", creditos_estimados=cuesta,
                        notas=f"este reel sale {cuesta} créditos, este mes ya hay "
                              f"{ya} comprometidos y el tope mensual es {tope_mes}.")
            else:
                tarea = pedir_clip(con_foto, plan, planos)
                _marcar(cli, fila["id"], "generando", tarea=tarea,
                        modelo=plan["modelo"], resolucion=plan["resolucion"],
                        duracion=plan["duracion"], creditos_estimados=cuesta,
                        **({"notas": aviso} if aviso else {}))
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
            estado, url = estado_clip(
                fila["tarea"], fila.get("modelo") or "seedance-2-5-pro",
                fila.get("resolucion") or "720p")
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

                # El rótulo va en su propio try por la misma razón que la
                # música: acá el video YA está generado y pagado. Que el texto
                # no se pueda dibujar es un problema; perder por eso un clip de
                # 4.400 créditos es otro mucho más caro. Sale sin rótulo y la
                # nota dice por qué.
                rotulo = falta_rotulo = None
                try:
                    rotulo = armar_rotulo(fila, t / "rotulo.png")
                except Exception as e:                       # noqa: BLE001
                    falta_rotulo = f"sin rótulo: {e}"
                    log.exception("[%s] no pude dibujar el rótulo del reel %s",
                                  getattr(cli, "marca", "?"), fila["id"])
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
                               float(fila.get("duracion") or dur),
                               usar_ambiente=ficha_modelo(
                                   fila.get("modelo") or "").get("manda_el_audio", True))
                aviso = " · ".join(x for x in (falta_rotulo, falta_musica) if x)
                _marcar(cli, fila["id"], "listo",
                        url=subir(final, f"reels/{fila['id']}.mp4"),
                        creditos_gastados=fila.get("creditos_estimados"),
                        **({"notas": aviso} if aviso else {}))
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


def rotulo(marca: str, fila: dict, destino: pathlib.Path) -> pathlib.Path | None:
    """El PNG transparente que se monta encima del clip. None si no hay qué decir.

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

    Y el título: `campana` lo declara `requerido`, así que una fila sin título
    no dibuja, revienta. Eso costó un video pagado —4.400 créditos, el
    26/8/2026—: el clip estaba listo y el montaje murió pidiendo un campo. Por
    eso acá el texto se busca en los tres campos y no sólo en `titulo`: si el
    agente escribió la frase en la bajada, esa frase es el título del rótulo.
    Y si no escribió ninguno, se devuelve None y el reel sale sin rótulo, que
    es infinitamente mejor que no salir.
    """
    import importlib
    import sys

    from . import config

    # El primero que tenga texto manda. El orden es el de importancia visual,
    # no el del contrato.
    texto = next((t for t in (fila.get("titulo"), fila.get("kicker"),
                              fila.get("bajada")) if (t or "").strip()), "")
    if not texto:
        log.info("el reel %s no trae texto: va sin rótulo", fila.get("id"))
        return None

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

    datos = {"titulo": texto, "sobre_video": True, "posicion": "arriba"}
    # El kicker y la bajada sólo entran si no fueron ELLOS los que hicieron de
    # título: si no, la misma frase saldría dos veces en la pieza.
    for campo in ("kicker", "bajada"):
        valor = (fila.get(campo) or "").strip()
        if valor and valor != texto:
            datos[campo] = valor
    html = plantillas["campana"](datos, "reel")
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
