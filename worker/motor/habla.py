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
from pathlib import Path

log = logging.getLogger(__name__)

#: Cuál modelo. `small` es el punto de equilibrio medido: `tiny` y `base`
#: pierden acentos y números —que en un reel son el precio y el horario— y
#: `medium` es tres veces más lento por una mejora que no se nota en frases
#: cortas. Se puede cambiar sin tocar código con `WHISPER_MODELO`.
MODELO = os.environ.get("WHISPER_MODELO", "small")

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


def _cargar():
    """El modelo, una sola vez por proceso. Cargarlo son unos 9 segundos."""
    global _modelo
    if _modelo is None:
        from faster_whisper import WhisperModel
        log.info("cargando el modelo de transcripción %s", MODELO)
        _modelo = WhisperModel(MODELO, device="cpu", compute_type="int8")
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
    try:
        segmentos, _ = _cargar().transcribe(
            str(ruta), language=IDIOMA, word_timestamps=True,
            initial_prompt=vocabulario or None)
        _dicho[llave] = [{"texto": w.word.strip(),
                          "desde": float(w.start), "hasta": float(w.end)}
                         for s in segmentos for w in (s.words or []) if w.word.strip()]
        return _dicho[llave]
    except Exception as e:                                   # noqa: BLE001
        log.warning("no pude transcribir %s: %s", ruta, e)
        _dicho[llave] = []
        return []


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
    bloques, actual = [], []
    for p in pals:
        if actual and (p["desde"] - actual[-1]["hasta"] >= PAUSA
                       or actual[-1]["texto"].endswith((".", "?", "!", "…"))):
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
        # Reparto por cantidad de palabras: es lo que mantiene las líneas
        # parecidas sin tener que medir cada corte.
        n = len(b)
        cortes = [round(n * i / partes) for i in range(partes + 1)]
        for i in range(partes):
            trozo = b[cortes[i]:cortes[i + 1]]
            if trozo:
                salida.append(armar(trozo))

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

    return [s for s in subs if s["hasta"] > s["desde"]]


def vocabulario_de(marca) -> str:
    """Los nombres propios de la marca, para que Whisper no los escriba mal.

    Sale del módulo de la marca, así que cada cliente aporta el suyo sin que
    nadie mantenga una lista aparte.
    """
    partes = [getattr(marca, "NOMBRE", "") or ""]
    partes += list(getattr(marca, "VOCABULARIO", ()) or ())
    return ", ".join(p for p in partes if p).strip(", ")
