# -*- coding: utf-8 -*-
"""Lo que se DICE en un clip, con el tiempo de cada palabra.

Es la única pieza del motor que escucha. `analisis.py` mide **cuánto** sonido
hay —silencios, picos— y eso sirve para elegir dónde cortar; acá se saca
**qué** se dice, que es otra cosa y sirve para los subtítulos.

## Whisper local, no una API

Corre adentro del worker con `faster-whisper`. No se paga por minuto y no sale
ningún audio de clientes hacia afuera, que para una clínica no es un detalle
menor. Lo que cuesta es CPU: medido acá con el modelo `small` en 4 núcleos,
12 segundos de voz se transcriben en 3,7 — unas 3,3 veces más rápido que
tiempo real. Un reel de 60 segundos son unos 20 de transcripción.

## Las cuatro trampas, que no descubrimos nosotros

Vienen del pack de edición de reels de JordiGPT (21/8/2026), donde están
documentadas después de sufrirlas en reels publicados. Se anotan acá porque
son exactamente el tipo de error que sale bien en la prueba y mal en producción:

1. **Nunca un modelo `.en` con audio en español.** No lo transcribe: lo
   TRADUCE al inglés. Por eso `IDIOMA` es explícito y el modelo nunca lleva
   sufijo.
2. **Nunca cortar por los huecos entre palabras de Whisper.** Whisper estira
   las palabras sobre las pausas, así que su idea de dónde termina una frase no
   es la real. Para cortar está la energía de audio, que ya mide `analisis.py`.
   Acá el tiempo de Whisper se usa para MOSTRAR texto, nunca para cortar video.
3. **Whisper deriva en un audio largo con pausas.** El pack transcribe cada
   corte por separado. Nosotros transcribimos cada CLIP ORIGINAL entero y
   mapeamos, que es equivalente para el problema —el original es audio continuo
   sin pegar, que es de donde viene la deriva— y encima transcribe una sola vez
   un clip que aparece en tres tramos.
4. **Los nombres propios salen mal.** Medido: «Boss Padel» salió «vos panel».
   Se arregla pasándole el vocabulario de la marca como pista, y con eso salió
   bien. Por eso `vocabulario` no es opcional en la práctica: sin él, el nombre
   del cliente aparece mal escrito en su propio reel.
"""
import logging
import os
import re
import time
from pathlib import Path

log = logging.getLogger(__name__)

#: Cuál modelo. Se puede cambiar sin tocar código con `WHISPER_MODELO`.
#:
#: Esto decía `small`, después `medium`, y cada vez el comentario juraba que el
#: siguiente «no valía la pena». **Las dos veces fue falso al medirlo.**
#:
#: · `small` → `medium` (1/9/2026, tres clips de Boss): `small` inventaba
#:   («futbol es un superpoder», una frase que nadie dijo); `medium` no dejó
#:   ni un error.
#: · `medium` → `large-v3` (3/9/2026, dos clips de Asistime con gente
#:   hablándose encima): `medium` escribió «¿Te la presto?» por «¿Te la
#:   prestó?», «Vi lo que me gustaste» por «Vi lo que me mostraste» y «No
#:   está, es que la pego» por «Ahí no está la pelota, la que la pegó». Son
#:   errores de sentido, no de ortografía, y en un subtítulo se leen. Con
#:   `large-v3` más el filtro de voz (abajo) no queda ninguno.
#:
#: Lo que cuesta, medido sobre los mismos dos clips (27 s y 46 s):
#:
#:   | | transcribir | pesa |
#:   |---|---|---|
#:   | `medium` int8   | 25 s + 47 s | 1,5 GB |
#:   | `large-v3` int8 | 40 s + 70 s | 3,1 GB |
#:
#: Un 60 % más de tiempo en la transcripción, que es una parte del montaje y
#: no la más larga. El job tiene 8 GiB y 8 núcleos, así que entra con aire.
#:
#: **Se intentó una vez y hubo que volver atrás el mismo día**, y conviene que
#: quede escrito. Se puso `medium` sin tocar nada más y un reel que tardaba
#: 1 m 23 s pasó de largo los ocho minutos. La medición de calidad era buena;
#: lo que no se midió es si el modelo ENTRABA: en Cloud Run el disco del
#: contenedor **es memoria**, así que un modelo que no está horneado en la
#: imagen se baja en cada corrida y se lo cuenta al job. Por eso cambiar el
#: modelo son TRES lugares y no uno: acá, el `Dockerfile` (que lo hornea) y
#: `desplegar-chat.sh` (que fija `WHISPER_MODELO`). `_cargar()` avisa en el
#: log si el modelo tuvo que bajarse.
#:
#: Si algo sale mal se vuelve sin tocar código: `WHISPER_MODELO=medium`.
MODELO = os.environ.get("WHISPER_MODELO", "large-v3")

#: Filtro de voz antes de transcribir. Whisper decodifica en ventanas de 30 s
#: y una ventana con silencio largo o música lo tienta a inventar; el VAD
#: (Silero, viene con faster-whisper) le saca los tramos sin voz y él vuelve a
#: poner los tiempos en el reloj original. Medido el 3/9/2026 sobre `medium`
#: solo: con el filtro arregló «Vi lo que me gustaste» → «mostraste» sin
#: cambiar de modelo. Se apaga con `WHISPER_VAD=0`.
VAD = os.environ.get("WHISPER_VAD", "1") != "0"

#: Nivelar el volumen antes de transcribir. Los videos de teléfono traen a
#: uno que habla cerca y a otro que contesta desde lejos; nivelados, el de
#: lejos deja de perder palabras. Es un `loudnorm` de ffmpeg sobre una copia
#: mono a 16 kHz, que es exactamente lo que Whisper hace adentro con el
#: archivo antes de escucharlo, así que no cuesta una pasada extra de verdad.
#: Se apaga con `WHISPER_NIVELAR=0`.
NIVELAR = os.environ.get("WHISPER_NIVELAR", "1") != "0"

#: Nunca con sufijo `.en`. Ver la trampa 1.
IDIOMA = os.environ.get("WHISPER_IDIOMA", "es")

#: Cuánto silencio entre dos palabras corta una frase. Menos que esto es la
#: respiración normal de alguien hablando, no un final.
PAUSA = 0.55

#: Los mismos números que valida `guion.py`, para que un subtítulo automático
#: no pueda salir peor que uno escrito a mano.
MAX_CARACTERES = 42
MIN_SEGUNDOS = 0.6
MAX_SEGUNDOS = 3.2

_modelo = None

#: La transcripción de un clip, para no pagarla dos veces: la usan los
#: subtítulos y también el corte de silencios, que la necesita para no partir
#: una palabra al medio.
_dicho: dict = {}


#: A partir de acá, cargar el modelo tardó tanto que seguro se bajó de
#: internet en vez de leerse del disco del contenedor.
AVISO_CARGA = 20.0


def _cargar():
    """El modelo, una sola vez por proceso.

    Horneado en la imagen tarda unos segundos. Si NO está horneado se baja de
    HuggingFace **en cada corrida** —el contenedor es efímero— y ahí no sólo
    tarda: en Cloud Run el disco del contenedor es memoria, así que un modelo
    de 1,5 GB se come 1,5 GiB del límite del job antes de empezar a trabajar.

    Eso pasó el 1/9/2026 y no dejó ningún rastro: el reel simplemente no
    terminaba nunca. Por eso ahora se mide y se avisa. Un aviso en el log no
    arregla nada, pero convierte «se colgó» en «se está bajando el modelo».
    """
    global _modelo
    if _modelo is None:
        from faster_whisper import WhisperModel
        log.info("cargando el modelo de transcripción %s", MODELO)
        t0 = time.monotonic()
        _modelo = WhisperModel(MODELO, device="cpu", compute_type="int8")
        tardo = time.monotonic() - t0
        if tardo > AVISO_CARGA:
            log.warning(
                "el modelo %s tardó %.0fs en cargar: casi seguro NO está "
                "horneado en la imagen y se bajó de internet. Se va a bajar "
                "otra vez en cada corrida, y en Cloud Run ocupa memoria del "
                "job. Ver la sección del Dockerfile en DESPLEGAR.md",
                MODELO, tardo)
        else:
            log.info("modelo %s listo en %.1fs", MODELO, tardo)
    return _modelo


def palabras(ruta, vocabulario: str = "") -> list[dict]:
    """Cada palabra con su segundo de entrada y de salida, en tiempo del clip.

    `vocabulario` son los nombres propios de la marca, separados por comas. No
    es un adorno: ver la trampa 4.

    Si el clip no tiene voz —o no tiene audio— devuelve una lista vacía. Eso NO
    es un error: un peloteo de pádel no tiene nada que subtitular y el reel
    tiene que salir igual.
    """
    llave = (str(ruta), vocabulario)
    if llave in _dicho:
        return _dicho[llave]
    limpio = None
    try:
        limpio = _nivelado(ruta) if NIVELAR else None
        # `beam_size` 5 es el que trae faster-whisper; va explícito porque es
        # el que se midió. La temperatura se deja con su escalera por defecto
        # (0 → 1.0): sólo sube cuando la decodificación a 0 falla, así que en
        # audio normal es idéntica a fijarla en 0 —que fue lo medido— y en
        # audio difícil evita que el modelo se quede repitiendo una frase.
        segmentos, _ = _cargar().transcribe(
            str(limpio or ruta), language=IDIOMA, word_timestamps=True,
            initial_prompt=vocabulario or None,
            vad_filter=VAD, beam_size=5)
        _dicho[llave] = [{"texto": w.word.strip(),
                          "desde": float(w.start), "hasta": float(w.end)}
                         for s in segmentos for w in (s.words or []) if w.word.strip()]
        return _dicho[llave]
    except Exception as e:                                   # noqa: BLE001
        log.warning("no pude transcribir %s: %s", ruta, e)
        _dicho[llave] = []
        return []
    finally:
        if limpio:
            limpio.unlink(missing_ok=True)


def _nivelado(ruta):
    """Una copia del audio, mono a 16 kHz y con el volumen nivelado.

    Devuelve la ruta del archivo temporal —quien la pide la borra— o `None`
    si ffmpeg no pudo: en ese caso se transcribe el original, que es lo que
    se hacía antes. Nivelar es una mejora, no una condición.
    """
    import subprocess
    import tempfile
    fd, tmp = tempfile.mkstemp(suffix=".wav", prefix="habla-")
    os.close(fd)
    salida = Path(tmp)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(ruta), "-vn",
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ac", "1", "-ar", "16000",
         str(salida)], capture_output=True, text=True)
    if r.returncode != 0 or not salida.exists() or salida.stat().st_size < 1000:
        log.warning("no pude nivelar el audio de %s, va el original: %s",
                    ruta, (r.stderr or "").strip()[-200:])
        salida.unlink(missing_ok=True)
        return None
    return salida


#: Palabras con las que una línea de subtítulo NO puede terminar.
#:
#: Son las que no significan nada solas: artículos, preposiciones,
#: conjunciones, posesivos. Dejarlas colgando al final de la línea obliga a
#: leer el renglón siguiente para entender el primero, y en un reel —donde el
#: texto está en pantalla dos segundos— eso se paga caro.
#:
#: Salió de mirar un reel real: «creamos el / primer agente y», «tenemos
#: disponibles que en / realidad es». Las dos líneas cortan justo donde la
#: frase todavía no dijo nada.
DEBILES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "lo", "al", "del",
    "de", "a", "ante", "bajo", "con", "contra", "desde", "en", "entre", "hacia",
    "hasta", "para", "por", "según", "sin", "sobre", "tras", "durante",
    "y", "e", "o", "u", "ni", "que", "qué", "como", "cómo", "cuando", "cuándo",
    "donde", "dónde", "porque", "pero", "aunque", "si", "sí", "más", "muy",
    "mi", "tu", "su", "mis", "tus", "sus", "nuestro", "nuestra", "este", "esta",
    "ese", "esa", "aquel", "se", "me", "te", "nos", "les", "le",
}


def _peso(palabra: str) -> int:
    """Cuánto molesta cortar DESPUÉS de esta palabra. Menos es mejor."""
    limpia = palabra.lower().strip(" ,.;:¿?¡!\"'()")
    if limpia.endswith((".", "?", "!")) or palabra.rstrip().endswith((".", "?", "!")):
        return 0                      # final de oración: el mejor corte posible
    if palabra.rstrip().endswith(","):
        return 1                      # una coma es una pausa de verdad
    if limpia in DEBILES:
        return 9                      # deja el renglón sin decir nada
    return 3


def frases(pals: list[dict]) -> list[dict]:
    """Agrupa palabras en frases que entren en pantalla y se alcancen a leer.

    Dos pasos, y el orden es lo que evita el defecto obvio:

    **Primero se parte donde la persona hizo punto** —un signo de final o una
    pausa larga—. Ahí el corte no se nota porque coincide con el habla.

    **Después, un bloque que no entra se reparte PAREJO**, no se llena hasta el
    tope y se deja el resto. Llenar hasta el tope fue la primera versión y se
    veía enseguida qué estaba mal: «...y ropa» / «deportiva.» — una palabra
    sola colgada en pantalla. Repartir en partes iguales no deja huérfanas
    porque no hay sobra, y de paso las líneas quedan del mismo largo, que se
    lee mejor.
    """
    if not pals:
        return []

    # ── 1. bloques: donde termina una idea ──
    #
    # Una pausa larga NO siempre es el final de una idea: también es alguien
    # buscando la palabra. Si la última palabra dicha no dice nada sola —«la»,
    # «de», «que»: la lista `DEBILES`— el corte se saltea y las dos partes van
    # juntas. Medido el 3/9/2026 sobre el reel de Bauti: entre «¡Opa! La» y
    # «pelota» hay un segundo y medio de duda, y el subtítulo salía partido
    # ahí, con un renglón terminado en «La». Se lee dos veces.
    #
    # Con signo de final sí se corta, aunque la palabra esté en la lista: «Sí.»
    # es una frase entera y «si» está en DEBILES por el condicional.
    def _corta_aca(anterior, siguiente):
        texto = anterior["texto"].rstrip()
        if texto.endswith((".", "?", "!", "…")):
            return True
        if siguiente["desde"] - anterior["hasta"] < PAUSA:
            return False
        return _peso(texto) < 9

    bloques, actual = [], []
    for p in pals:
        if actual and _corta_aca(actual[-1], p):
            bloques.append(actual)
            actual = []
        actual.append(p)
    if actual:
        bloques.append(actual)

    # ── 2. repartir cada bloque en partes parejas ──
    def armar(grupo):
        texto = " ".join(x["texto"] for x in grupo)
        texto = re.sub(r"\s+([,.;:!?])", r"\1", texto).strip()
        return {"texto": texto, "desde": round(grupo[0]["desde"], 3),
                "hasta": round(grupo[-1]["hasta"], 3)}

    salida = []
    for b in bloques:
        largo = len(" ".join(x["texto"] for x in b))
        dur = b[-1]["hasta"] - b[0]["desde"]
        partes = max(1, -(-largo // MAX_CARACTERES), int(dur // MAX_SEGUNDOS) + 1)
        if partes == 1:
            salida.append(armar(b))
            continue
        # Dónde cortar: cerca del reparto parejo, pero corriéndose hasta tres
        # palabras para no terminar un renglón en «el», «de» o «que».
        #
        # El equilibrio importa —dos líneas de largo muy distinto se leen
        # peor— así que alejarse del punto ideal también pesa. Gana el corte
        # que minimiza las dos cosas juntas.
        n = len(b)
        cortes = [0]
        for i in range(1, partes):
            ideal = round(n * i / partes)
            mejor, mejor_costo = ideal, None
            for cand in range(max(cortes[-1] + 1, ideal - 3),
                              min(n - (partes - i), ideal + 3) + 1):
                costo = _peso(b[cand - 1]["texto"]) + abs(cand - ideal)
                if mejor_costo is None or costo < mejor_costo:
                    mejor, mejor_costo = cand, costo
            cortes.append(mejor)
        cortes.append(n)
        for i in range(partes):
            trozo = b[cortes[i]:cortes[i + 1]]
            if trozo:
                salida.append(armar(trozo))

    # Correrse para no cortar en «el» puede dejar una línea por encima del
    # largo, y el reparto en partes iguales no lo garantiza tampoco: una parte
    # con palabras largas se pasa aunque tenga la misma cantidad. Salía «que
    # quiera un diseño genérico que diga feliz» — 44 caracteres.
    #
    # Se parte al medio, y esta vez sin buscar el corte lindo: acá ya se agotó
    # la elegancia y lo que importa es que entre. Una línea que se pasa la
    # parte el navegador donde le queda cómodo, que es peor.
    def _partir(f):
        if len(f["texto"]) <= MAX_CARACTERES:
            return [f]
        pal = f["texto"].split()
        if len(pal) < 2:
            return [f]
        m = len(pal) // 2
        # El tiempo se reparte por cantidad de letras y no de palabras: es más
        # cerca de cuánto tarda alguien en decirlas.
        izq, der = " ".join(pal[:m]), " ".join(pal[m:])
        corte = f["desde"] + (f["hasta"] - f["desde"]) * len(izq) / len(f["texto"])
        return _partir({"texto": izq, "desde": f["desde"], "hasta": round(corte, 3)}) + \
               _partir({"texto": der, "desde": round(corte, 3), "hasta": f["hasta"]})

    salida = [x for f in salida for x in _partir(f)]

    salida.sort(key=lambda f: f["desde"])

    # Una frase demasiado corta no se lee. Se estira hacia adelante hasta el
    # mínimo, sin pisar a la siguiente: es preferible que quede un instante de
    # más en pantalla a que parpadee.
    for i, f in enumerate(salida):
        if f["hasta"] - f["desde"] < MIN_SEGUNDOS:
            tope = salida[i + 1]["desde"] if i + 1 < len(salida) else f["hasta"] + 1
            f["hasta"] = round(min(f["desde"] + MIN_SEGUNDOS,
                                   max(tope - 0.05, f["hasta"])), 3)
    return salida


def para_guion(guion: dict, base, vocabulario: str = "") -> list[dict]:
    """Los subtítulos de un guion entero, ya en la escala del REEL MONTADO.

    Acá vive la traducción entre los dos relojes, que es lo que el contrato del
    guion advierte que es el error más fácil de cometer: los tramos hablan en
    segundos del material original y los subtítulos en segundos del reel.

    La cuenta por tramo es: se toman las palabras que caen adentro del recorte,
    se les resta el `desde` del tramo, se dividen por la velocidad —un tramo en
    cámara lenta dura el doble, así que sus palabras también— y se les suma lo
    que ya duraba el reel antes de este tramo.

    Una frase no cruza de un tramo al siguiente. Podría, pero dos tramos no son
    necesariamente contiguos en el original: una frase a caballo diría algo que
    en el reel nunca se escucha entero.
    """
    base = Path(base)
    cache: dict[str, list[dict]] = {}
    subs, offset = [], 0.0

    for t in (guion.get("tramos") or []):
        arch = (t.get("archivo") or "").strip()
        desde = float(t.get("desde", 0))
        hasta = float(t.get("hasta", desde))
        vel = float(t.get("velocidad", 1) or 1)
        dura = max(0.0, (hasta - desde) / vel)

        if arch and t.get("audio", True):
            if arch not in cache:
                ruta = base / arch
                cache[arch] = palabras(ruta, vocabulario) if ruta.exists() else []
            dentro = [{"texto": p["texto"],
                       "desde": offset + (p["desde"] - desde) / vel,
                       "hasta": offset + (min(p["hasta"], hasta) - desde) / vel}
                      for p in cache[arch]
                      if p["desde"] >= desde - 0.02 and p["desde"] < hasta]
            subs += frases(dentro)

        offset += dura

    # ── Nada termina después del reel ──
    #
    # `frases()` estira una frase corta hacia adelante para que se pueda leer,
    # y a la ÚLTIMA no la frena nadie: se pasa del final del tramo. Con un
    # solo tramo casi nunca se nota; con el último tramo de un montaje, el
    # subtítulo termina después de que el reel terminó, el validador lo
    # rechaza y el reel entero muere. Pasó el 2/9/2026: «termina en 26.1s
    # pero el reel dura 25.6s». Acá `offset` ya es lo que dura el reel.
    subs = [{**s, "hasta": min(s["hasta"], round(offset, 3))}
            for s in subs if s["desde"] < offset]
    subs = [s for s in subs if s["hasta"] > s["desde"]]
    subs.sort(key=lambda s: s["desde"])

    # ── las frases sueltas se juntan con una vecina ──
    #
    # Una frase de una o dos palabras cortas —«acá», «bueno»— no alcanza a
    # leerse y parpadea. Se prueba con la anterior y, si no entra, con la
    # siguiente: juntar sólo hacia atrás dejaba huérfanas justo en los
    # empalmes entre clips, que es donde más aparecen.
    # Pero nunca hacia atrás por encima de un punto. «Vi lo que me mostraste.
    # Panchi,» salió así el 2/9/2026: «Panchi,» era corta, entraba, y se pegó a
    # la frase anterior aunque ésta ya había terminado —y además era otra
    # persona hablando—. Si la anterior cerró la oración, la corta va con la
    # siguiente, que es a la que pertenece.
    def _cerrada(f):
        return f["texto"].rstrip().endswith((".", "?", "!", "…"))
    juntadas: list[dict] = []
    i = 0
    while i < len(subs):
        f = subs[i]
        corta = len(f["texto"]) <= 8
        if corta and juntadas and not _cerrada(juntadas[-1]) and \
                len(juntadas[-1]["texto"]) + 1 + len(f["texto"]) <= MAX_CARACTERES:
            juntadas[-1]["texto"] += " " + f["texto"]
            juntadas[-1]["hasta"] = max(juntadas[-1]["hasta"], f["hasta"])
        elif corta and i + 1 < len(subs) and \
                len(f["texto"]) + 1 + len(subs[i + 1]["texto"]) <= MAX_CARACTERES:
            sig = subs[i + 1]
            juntadas.append({"texto": f["texto"] + " " + sig["texto"],
                             "desde": f["desde"], "hasta": sig["hasta"]})
            i += 1
        else:
            juntadas.append(dict(f))
        i += 1

    # ── y recién ahora, que no haya dos en pantalla a la vez ──
    #
    # Va ÚLTIMO a propósito: juntar frases mueve los tiempos, así que limpiar
    # las superposiciones antes deja pasar las que el juntado crea después.
    # Ese fue el orden de la primera versión y por eso quedaba «Acá» pisando a
    # la frase siguiente.
    #
    # El estirón que `frases()` le da a una frase corta mira sólo dentro de su
    # propio tramo, así que la última frase de un tramo se estira por encima de
    # la primera del siguiente. Es un empalme que ninguna de las dos partes ve,
    # y dos textos superpuestos es el peor defecto posible: no se lee ninguno.
    for a, b in zip(juntadas, juntadas[1:]):
        if a["hasta"] > b["desde"] - 0.04:
            a["hasta"] = round(max(a["desde"] + 0.25, b["desde"] - 0.04), 3)
    return juntadas


def en_frase(palabras) -> str:
    """Una lista de términos, convertida en una oración normal.

    Ver `vocabulario_de`: al modelo no se le puede pasar una lista.
    """
    ps = [str(p).strip() for p in palabras if str(p or "").strip()]
    if not ps:
        return ""
    if len(ps) == 1:
        return f"Se escribe {ps[0]}."
    return "Se escriben " + ", ".join(ps[:-1]) + " y " + ps[-1] + "."


def vocabulario_de(marca) -> str:
    """El contexto que se le da al modelo ANTES de escuchar. **En prosa.**

    `initial_prompt` no es una lista de palabras clave: es «el texto que venía
    justo antes de esto». El modelo lo lee y copia su ESTILO — puntuación
    incluida.

    Eso se midió y sorprende. Con una lista separada por comas —que es como
    estaba escrito acá— el modelo empezó a escribir sin signos: «cual
    elegirías?», «Para ir a donde?». Le habíamos enseñado, sin querer, que en
    este texto no se abren interrogaciones. En un subtítulo eso se ve.

    Escrito como una frase normal, con sus signos, la puntuación sale perfecta
    y los nombres propios se siguen escribiendo bien. Por eso `VOCABULARIO` es
    una frase y no una lista, y por eso lo que se agrega acá también lo es.
    """
    voc = getattr(marca, "VOCABULARIO", "") or ""
    if not isinstance(voc, str):        # una lista, de cuando esto era otra cosa
        voc = en_frase(voc)
    voc = voc.strip()
    nombre = (getattr(marca, "NOMBRE", "") or "").strip()
    if nombre and nombre.lower() not in voc.lower():
        voc = (f"Esto es material de {nombre}. " + voc).strip()
    return voc


def hook_de(texto: str, marca: str = "") -> str:
    """Una frase de enganche para los primeros segundos, escrita por Claude.

    Los tres primeros segundos deciden si alguien sigue mirando, y el arranque
    natural de casi todo el material crudo es el peor posible: «bueno, en este
    video les voy a mostrar…». Eso ANUNCIA en vez de mostrar, y anunciar es lo
    que hace que el dedo siga de largo.

    Se le pasa lo que se dice en el video —ya transcrito— y devuelve una línea.
    Corta y en mayúsculas la pone la plantilla; acá sólo importa que diga algo.

    Si falla devuelve cadena vacía, y el reel sale sin hook. Un reel sin hook
    es peor que uno con hook, pero infinitamente mejor que ningún reel: esto no
    puede tumbar un montaje que ya está hecho.
    """
    texto = (texto or "").strip()
    if len(texto) < 20:
        return ""
    try:
        import asyncio
        from claude_agent_sdk import ClaudeAgentOptions, query
    except Exception:                                        # noqa: BLE001
        log.warning("no está el SDK de Claude: el reel va sin hook")
        return ""

    prompt = (
        "Escribí el texto de enganche para los primeros 3 segundos de un reel "
        "vertical de Instagram" + (f" de {marca}" if marca else "") + ".\n\n"
        "Esto es lo que se dice en el video:\n\n" + texto[:2500] + "\n\n"
        "Reglas:\n"
        "· Máximo 8 palabras. Se lee en un segundo y medio.\n"
        "· Que diga LO CONCRETO que el video muestra, no que lo anuncie. "
        "«En este video te muestro cómo hacer X» está mal; «X en 30 segundos» "
        "está bien.\n"
        "· Tiene que salir del TEMA PRINCIPAL, no de cualquier momento "
        "llamativo. Si en el video algo falla o sale mal, eso NO va en el hook "
        "salvo que el video sea justamente sobre eso: es un momento "
        "incidental, y el titular de una pieza no lidera con un tropiezo.\n"
        "· Castellano rioplatense, sin signos de admiración ni emojis.\n"
        "· Nada de clickbait ni promesas que el video no cumple.\n"
        "· Contestá SÓLO la frase, sin comillas ni explicación.")

    try:
        async def _pedir() -> str:
            t = ""
            async for msg in query(prompt=prompt, options=ClaudeAgentOptions(
                    allowed_tools=[], max_turns=1, permission_mode="dontAsk")):
                for bloque in getattr(msg, "content", None) or []:
                    x = getattr(bloque, "text", None)
                    if x:
                        t += x
            return t
        # `asyncio.run` y no `await`, por la misma razón que en `reelero`: esto
        # corre adentro del hilo que abre `to_thread`, sin loop propio.
        linea = asyncio.run(_pedir()).strip().strip('"«»').split("\n")[0]
    except Exception as e:                                   # noqa: BLE001
        log.warning("no pude escribir el hook: %s", e)
        return ""

    return _recortar_hook(linea)


def _recortar_hook(linea: str, tope: int = 10) -> str:
    """Acorta un hook largo SIN dejarlo colgado a mitad de frase.

    La primera versión cortaba en la palabra número diez y listo, y salió
    «Un cliente le pide un diseño a la IA de». Terminar en «de» es peor que no
    tener hook: la frase promete algo que nunca dice, y encima queda como un
    error del sistema a la vista de todos.

    El orden es: primero probar si hay una coma antes del tope —una coma es un
    final legítimo—, y si no, retroceder mientras la última palabra no diga
    nada por sí sola. Es la misma lista `DEBILES` que usan los subtítulos: si
    una palabra no puede cerrar un renglón, tampoco puede cerrar un titular.
    """
    linea = (linea or "").strip(" .,:;·-–—")
    pal = linea.split()
    if len(pal) <= tope:
        return _sin_cola_debil(linea)

    # ¿Hay una coma dentro del tope? Ahí termina una idea.
    for i in range(min(tope, len(pal)) - 1, 1, -1):
        if pal[i].endswith(","):
            return " ".join(pal[:i + 1]).strip(" ,")
    return _sin_cola_debil(" ".join(pal[:tope]))


def _sin_cola_debil(linea: str) -> str:
    """Saca del final las palabras que no dicen nada solas."""
    pal = linea.split()
    while len(pal) > 3 and pal[-1].lower().strip(" ,.;:") in DEBILES:
        pal.pop()
    return " ".join(pal).strip(" .,:;")


def elegir_tramos(tramos: list[dict], objetivo: float, marca: str = "") -> list[int]:
    """Cuáles tramos entran para llegar a un largo objetivo. Devuelve índices.

    **Sólo corre si alguien pidió un largo.** Sin `duracion_objetivo` el motor
    conserva todo lo que se dijo, y eso es deliberado: descartar material de un
    cliente sin que nadie lo haya pedido es una decisión editorial que un motor
    no debería tomar solo. Un reel largo se puede acortar; una frase que el
    sistema tiró en silencio no se recupera.

    Cuando SÍ se pide, el criterio es el que falta en todo lo demás que hace
    este módulo: sacar los silencios no convierte una grabación cruda en un
    reel, porque el silencio no es lo único que sobra. Acá se lee lo que se
    dice en cada tramo y se elige qué entra, conservando el orden — reordenar
    una explicación la rompe.

    Si falla, devuelve todos: un reel largo es peor que uno bien editado, y
    muchísimo mejor que ninguno.
    """
    todos = list(range(len(tramos)))
    total = sum(float(t.get("dura") or 0) for t in tramos)
    if not tramos or objetivo <= 0 or total <= objetivo:
        return todos
    try:
        import asyncio
        import json as _json
        from claude_agent_sdk import ClaudeAgentOptions, query
    except Exception:                                        # noqa: BLE001
        return todos

    lista = "\n".join(
        f"{i}. ({float(t.get('dura') or 0):.1f}s) {t.get('texto', '').strip() or '[sin voz]'}"
        for i, t in enumerate(tramos))
    prompt = (
        "Estás editando un reel vertical de Instagram"
        + (f" de {marca}" if marca else "") + ". Estos son los tramos "
        "disponibles, con su duración y lo que se dice en cada uno:\n\n"
        + lista + f"\n\nEl reel entero dura {total:.0f}s y tiene que quedar en "
        f"unos {objetivo:.0f}s, así que sobra material.\n\n"
        "Ordená TODOS los tramos de más a menos importante: primero el que no "
        "puede faltar, último el que menos se extraña. No calcules duraciones "
        "ni recortes la lista — tienen que estar todos, ordenados.\n\n"
        "Criterios:\n"
        "· Lo que engancha y lo que explica el punto principal va primero.\n"
        "· Lo que se repite, lo que titubea y lo que no aporta va último.\n"
        "· Un tramo sin voz va último salvo que sea la única imagen de algo.\n\n"
        'Contestá SÓLO un JSON así: {"orden": [0, 3, 1, 2]}')

    try:
        async def _pedir() -> str:
            t = ""
            async for msg in query(prompt=prompt, options=ClaudeAgentOptions(
                    allowed_tools=[], max_turns=1, permission_mode="dontAsk")):
                for bloque in getattr(msg, "content", None) or []:
                    x = getattr(bloque, "text", None)
                    if x:
                        t += x
            return t
        crudo = asyncio.run(_pedir())
        i, j = crudo.index("{"), crudo.rindex("}")
        orden = [int(x) for x in _json.loads(crudo[i:j + 1]).get("orden") or []]
    except Exception as e:                                   # noqa: BLE001
        log.warning("no pude ordenar los tramos, van todos: %s", e)
        return todos

    # ── la cuenta la hace el código ──
    #
    # La primera versión le pedía al modelo que eligiera los tramos Y que la
    # suma diera el objetivo. Le pedí 28 segundos y devolvió 50: elegir bien y
    # sumar bien son dos habilidades distintas y se las estaba pidiendo juntas.
    #
    # Ahora el modelo hace sólo lo que sabe hacer —decidir qué vale más— y el
    # presupuesto lo llena el código, de arriba hacia abajo. El largo queda
    # garantizado por construcción.
    orden = [i for i in dict.fromkeys(orden) if 0 <= i < len(tramos)]
    orden += [i for i in todos if i not in orden]     # por si olvidó alguno

    elegidos, suma = [], 0.0
    for i in orden:
        d = float(tramos[i].get("dura") or 0)
        if not elegidos or suma + d <= objetivo:
            elegidos.append(i)
            suma += d
    elegidos = sorted(elegidos)                       # se muestran en su orden
    if not elegidos:
        return todos
    log.info("de %d tramos entran %d (objetivo %.0fs)",
             len(tramos), len(elegidos), objetivo)
    return elegidos
