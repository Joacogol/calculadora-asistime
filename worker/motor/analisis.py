# -*- coding: utf-8 -*-
"""Mirar y escuchar el material antes de editarlo.

## Por qué existe

Hasta acá el agente escribía el guion de un reel **a ciegas**: recibía un
archivo de video y no tenía forma de saber qué había adentro ni en qué segundo.
Editar bien es decidir qué momento importa, y eso no se puede decidir sin ver.

Este módulo no edita nada. Mide, y deja el resultado en un JSON y en un puñado
de cuadros que el agente puede abrir. Después el agente escribe el guion
—`motor/guion.py`— y recién ahí el motor de video ejecuta.

    material  →  ANÁLISIS  →  el agente escribe el GUION  →  MOTOR  →  reel
                (medir)          (decidir)                  (dibujar)

## Lo que mide, y por qué eso y no otra cosa

- **La ficha del archivo.** Duración, medidas, fps, si trae audio. Sin esto no
  se puede ni validar un guion.
- **Los cortes de toma.** Dónde cambia la escena. Marca los límites naturales:
  cortar en medio de una toma se nota, cortar donde ya había un corte no.
- **La energía del audio.** De la misma curva salen dos cosas opuestas y las
  dos importan: los **silencios** —lo que hay que sacar, y es lo que más hace
  que un video de celular parezca editado— y los **picos**, que casi siempre
  son el momento bueno: el golpe, la risa, el «mirá esto».

## Los cuadros son caros: por eso se eligen

Un cuadro que el agente mira cuesta del orden de 1.200 tokens. Sesenta cuadros
de un video de un minuto costarían más que todo el resto del diseño junto.

Se muestrean **como máximo 15**, y no repartidos parejo: se priorizan los que
caen justo después de un corte de toma y en los picos de audio. Un cuadro
elegido vale más que diez al azar — al azar, la mitad caen en transiciones y en
partes muertas.
"""
import json
import logging
import math
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

TIEMPO = 240          # segundos de tope para cada llamada a ffmpeg

# Material más largo que esto no se analiza entero: se avisa y se recorta. El
# worker corre con 2 CPU y 30 minutos de tope por tarea; un archivo de media
# hora se come la corrida y mata también los diseños de los demás clientes.
MAX_ENTRADA = 300.0   # 5 minutos

MAX_CUADROS = 15
ANCHO_CUADRO = 480


class SinFFmpeg(RuntimeError):
    pass


def _exe(nombre: str) -> str:
    ruta = shutil.which(nombre)
    if not ruta:
        raise SinFFmpeg(f"falta {nombre} en el contenedor")
    return ruta


def _correr(args: list[str], tiempo=TIEMPO) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=tiempo)


# ────────────────────────────────────────────────────────────────── LA FICHA

def sondear(ruta) -> dict:
    """Los datos duros del archivo. Es lo primero y lo más barato."""
    ruta = Path(ruta)
    r = _correr([_exe("ffprobe"), "-v", "error", "-print_format", "json",
                 "-show_format", "-show_streams", str(ruta)], tiempo=60)
    if r.returncode != 0:
        raise RuntimeError(f"no pude leer «{ruta.name}»: {r.stderr[:200]}")
    d = json.loads(r.stdout or "{}")
    fmt = d.get("format", {})
    video = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not video:
        raise RuntimeError(f"«{ruta.name}» no tiene pista de video")

    ancho, alto = int(video.get("width", 0)), int(video.get("height", 0))
    # La rotación de los celulares viene en metadatos, no en las medidas: un
    # video filmado vertical con un iPhone se reporta 1920×1080 con rotate=-90.
    # Sin esto, el sistema cree que es apaisado y lo recorta al revés.
    giro = 0
    for lado in (video.get("side_data_list") or []):
        if "rotation" in lado:
            giro = int(abs(float(lado["rotation"]))) % 180
    if giro == 90:
        ancho, alto = alto, ancho

    fps = 0.0
    try:
        num, den = (video.get("avg_frame_rate") or "0/1").split("/")
        fps = round(float(num) / float(den), 2) if float(den) else 0.0
    except Exception:
        pass

    dur = float(fmt.get("duration") or video.get("duration") or 0.0)
    return {
        "archivo": ruta.name,
        "duracion": round(dur, 2),
        "ancho": ancho, "alto": alto,
        "proporcion": round(ancho / alto, 3) if alto else 0,
        "vertical": alto >= ancho,
        "fps": fps,
        "codec": video.get("codec_name", ""),
        "tiene_audio": bool(audio),
        "codec_audio": (audio or {}).get("codec_name", ""),
        "peso_mb": round(int(fmt.get("size") or 0) / 1048576, 1),
        "muy_largo": dur > MAX_ENTRADA,
    }


# ─────────────────────────────────────────────────────── LOS CORTES DE TOMA

# El umbral empezó en 0,30, que es el valor que se recomienda en general, y en
# material de club **se comía la mitad de los cortes**. Medido sobre un video de
# cinco tomas de cancha, los cuatro cortes reales puntuaron 0,494 · 0,320 ·
# 0,289 · 0,195: con 0,30 aparecían dos.
#
# No es un defecto del filtro, es el material: en un club todas las tomas son la
# misma cancha, la misma luz y los mismos colores, así que dos tomas distintas
# se parecen mucho más que en un video cualquiera. El puntaje mide cuánto cambia
# la imagen, y acá cambia poco aunque el plano sea otro.
UMBRAL_CORTE = 0.15

# Dos cortes a menos de esto son casi siempre el mismo corte contado dos veces,
# o un temblor de cámara. Se queda el de puntaje más alto.
SEPARACION_CORTES = 0.40


def cortes_de_toma(ruta, umbral: float = UMBRAL_CORTE,
                   tope: float = MAX_ENTRADA) -> list[float]:
    """Segundos donde cambia la escena.

    Son los límites naturales del material: cortar en medio de una toma se
    nota, cortar donde el video ya cambiaba no.

    Se analiza a 240 px de ancho a propósito. La detección compara cuánto
    cambia un cuadro respecto del anterior, y eso no necesita resolución;
    bajarla hace que un video de tres minutos se analice en segundos.
    """
    r = _correr([
        _exe("ffmpeg"), "-v", "info", "-t", str(tope), "-i", str(ruta),
        "-vf", (f"scale=240:-2,select='gt(scene,{umbral})',"
                f"metadata=print:file=-"),
        "-an", "-f", "null", "-",
    ])
    # Se leen tiempo y puntaje juntos: el puntaje es lo que permite quedarse con
    # el corte más fuerte cuando aparecen dos pegados.
    candidatos, ahora = [], None
    for linea in ((r.stdout or "") + "\n" + (r.stderr or "")).splitlines():
        if "pts_time:" in linea:
            try:
                ahora = float(linea.split("pts_time:")[1].split()[0])
            except (ValueError, IndexError):
                ahora = None
        elif "scene_score=" in linea and ahora is not None:
            try:
                candidatos.append((round(ahora, 2), float(linea.split("scene_score=")[1])))
            except ValueError:
                pass
            ahora = None

    salida = []
    for t_, s in sorted(set(candidatos), key=lambda x: -x[1]):
        if all(abs(t_ - u) >= SEPARACION_CORTES for u in salida):
            salida.append(t_)
    return sorted(salida)


# ─────────────────────────────────────────────────────── LA ENERGÍA DEL AUDIO

def energia_audio(ruta, paso: float = 0.25, tope: float = MAX_ENTRADA):
    """(tiempos, dB) — cuánto sonido hay en cada tramito.

    Se decodifica a mono 8 kHz crudo y se calcula acá con numpy, en vez de
    pedirle el dato a un filtro de ffmpeg. Es más código pero el resultado es
    un array y no un texto que hay que parsear, y de un array salen los
    silencios y los picos con dos líneas.
    """
    try:
        import numpy as np
    except ImportError:
        return [], []

    r = subprocess.run(
        [_exe("ffmpeg"), "-v", "error", "-t", str(tope), "-i", str(ruta),
         "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
        capture_output=True, timeout=TIEMPO)
    if r.returncode != 0 or not r.stdout:
        return [], []

    muestras = np.frombuffer(r.stdout, dtype="<i2").astype("float32") / 32768.0
    n = max(1, int(8000 * paso))
    sobran = len(muestras) % n
    if sobran:
        muestras = muestras[:-sobran]
    if not len(muestras):
        return [], []
    bloques = muestras.reshape(-1, n)
    rms = np.sqrt((bloques ** 2).mean(axis=1))
    # −90 dB es el piso: un bloque en silencio absoluto daría log(0).
    db = 20 * np.log10(np.maximum(rms, 1e-5))
    tiempos = [round(i * paso, 2) for i in range(len(db))]
    return tiempos, [round(float(x), 1) for x in db]


def silencios(tiempos, db, umbral_db: float = -50.0, minimo: float = 0.35):
    """Los tramos callados que conviene sacar.

    El umbral es relativo al material, no absoluto: una grabación de celular en
    una recepción tiene un piso de ruido mucho más alto que un estudio.

    **Se toma la MEDIANA menos 12 dB.** La primera versión usaba el percentil 20
    más 6 dB y fue un error de razonamiento: si el video es ambiente parejo con
    unos pocos golpes fuertes —o sea, cualquier video de club— el percentil 20
    cae encima del ambiente y el umbral queda POR ARRIBA de él. Medido: marcaba
    el **94% del video como silencio**. Con la mediana menos 12 dB, el mismo
    video da 15%, que es exactamente el tramo que estaba mudo de verdad.

    La mediana es «el nivel normal de ESTE video»; 12 dB por debajo es
    «notoriamente más callado que lo normal», que es lo que queríamos decir
    desde el principio.
    """
    if not db:
        return []
    try:
        import numpy as np
        piso = float(np.median(db)) - 12.0
    except ImportError:
        piso = umbral_db
    umbral = max(min(piso, -25.0), -70.0)

    paso = (tiempos[1] - tiempos[0]) if len(tiempos) > 1 else 0.25
    fuera, ini = [], None
    for t, v in zip(tiempos, db):
        if v < umbral and ini is None:
            ini = t
        elif v >= umbral and ini is not None:
            if t - ini >= minimo:
                fuera.append((ini, round(t, 2)))
            ini = None
    if ini is not None and tiempos[-1] + paso - ini >= minimo:
        fuera.append((ini, round(tiempos[-1] + paso, 2)))
    return fuera


def picos(tiempos, db, cuantos: int = 8, separacion: float = 1.5):
    """Los momentos más sonoros, separados entre sí.

    Sin la separación mínima, los ocho picos caen todos dentro del mismo
    segundo y medio: son ocho vistas del mismo instante y no sirven de nada.
    """
    if not db:
        return []
    orden = sorted(range(len(db)), key=lambda i: db[i], reverse=True)
    elegidos = []
    for i in orden:
        t = tiempos[i]
        if all(abs(t - u) >= separacion for u in elegidos):
            elegidos.append(t)
        if len(elegidos) >= cuantos:
            break
    return sorted(elegidos)


# ───────────────────────────────────────────────────────────────── CUADROS

def momentos_interesantes(ficha: dict, cortes, altos, cuantos=MAX_CUADROS):
    """Qué segundos vale la pena mirar.

    El orden importa: primero lo que el material ya señala como distinto
    —arranques de toma y picos de sonido—, y sólo si sobran lugares se rellena
    parejo. Al revés, la mitad de los cuadros caen en partes muertas.
    """
    dur = ficha.get("duracion") or 0
    if dur <= 0:
        return []
    tope = min(dur, MAX_ENTRADA)
    salida = []

    def sumar(t, separacion=0.9):
        t = round(min(max(t, 0.05), tope - 0.05), 2)
        if t > 0 and all(abs(t - u) >= separacion for u in salida):
            salida.append(t)

    # Medio segundo después del corte: justo en el corte suele haber un cuadro
    # de transición o movido, que es el peor para entender qué se ve.
    for t in cortes:
        if len(salida) >= cuantos:
            break
        sumar(t + 0.5)

    # Y el FINAL de las tomas largas.
    #
    # Esto salió de una prueba que salió mal: el cuadro del segundo 7,50 se veía
    # perfecto, se cortó de 7,3 a 9,6, y en el reel la jugadora aparecía sin
    # cabeza. La toma se cerraba mientras corría y el cuadro no lo mostraba.
    #
    # **Un cuadro es un instante, no la toma.** En una toma de cinco segundos con
    # movimiento, el principio y el final pueden ser encuadres distintos. Con un
    # cuadro de cada punta, quien decide ve las dos y puede cortar donde sirve.
    limites = sorted(set([0.0] + list(cortes) + [tope]))
    for ini, fin in zip(limites, limites[1:]):
        if len(salida) >= cuantos:
            break
        if fin - ini >= 4.0:
            sumar(fin - 0.6)
    for t in altos:
        if len(salida) >= cuantos:
            break
        sumar(t)
    if len(salida) < cuantos:
        faltan = cuantos - len(salida)
        for i in range(faltan):
            sumar(tope * (i + 0.5) / faltan)
    return sorted(salida)[:cuantos]


def sacar_cuadros(ruta, momentos, destino: Path, ancho=ANCHO_CUADRO) -> list[dict]:
    """Un JPEG por momento. Devuelve la lista con su segundo, para el agente."""
    destino.mkdir(parents=True, exist_ok=True)
    base = Path(ruta).stem[:24]
    hechos = []
    for i, t in enumerate(momentos):
        salida = destino / f"{base}-{i:02d}-{t:06.2f}s.jpg"
        # -ss ANTES de -i es el salto rápido: ffmpeg va directo al keyframe más
        # cercano en vez de decodificar todo el video hasta ese punto.
        r = _correr([_exe("ffmpeg"), "-v", "error", "-ss", f"{t:.2f}",
                     "-i", str(ruta), "-frames:v", "1",
                     "-vf", f"scale={ancho}:-2", "-q:v", "5",
                     "-y", str(salida)], tiempo=60)
        if r.returncode == 0 and salida.exists():
            hechos.append({"segundo": t, "archivo": salida.name})
        else:
            log.warning("no pude sacar el cuadro de %.2fs de %s", t, base)
    return hechos


# ───────────────────────────────────────────────────────────────── EL TODO

def analizar(ruta, destino, cuantos_cuadros=MAX_CUADROS) -> dict:
    """Todo lo de arriba sobre un archivo, más los cuadros en `destino`."""
    ruta = Path(ruta)
    destino = Path(destino)
    ficha = sondear(ruta)

    avisos = []
    if ficha["muy_largo"]:
        avisos.append(
            f"El archivo dura {ficha['duracion']:.0f}s y sólo se analizan los "
            f"primeros {MAX_ENTRADA:.0f}. Para el resto hay que recortarlo antes.")
    if not ficha["tiene_audio"]:
        avisos.append("No trae audio: no hay silencios ni picos que detectar.")
    if not ficha["vertical"]:
        avisos.append(
            f"Está apaisado ({ficha['ancho']}×{ficha['alto']}). Para el reel se "
            f"recorta a 9:16, así que lo de los costados se pierde.")

    cortes = cortes_de_toma(ruta)
    tiempos, db = energia_audio(ruta) if ficha["tiene_audio"] else ([], [])
    callados = silencios(tiempos, db)
    altos = picos(tiempos, db)

    momentos = momentos_interesantes(ficha, cortes, altos, cuantos_cuadros)
    cuadros = sacar_cuadros(ruta, momentos, destino)

    hablado = None
    if ficha["duracion"] and callados:
        mudo = sum(b - a for a, b in callados)
        hablado = round(100 * (1 - mudo / min(ficha["duracion"], MAX_ENTRADA)))

    return {
        **ficha,
        "avisos": avisos,
        "cortes_de_toma": cortes,
        "silencios": [[a, b] for a, b in callados],
        "picos_de_audio": altos,
        "porcentaje_con_sonido": hablado,
        "cuadros": cuadros,
    }


def analizar_varios(rutas, destino, presupuesto=MAX_CUADROS) -> dict:
    """Varios archivos, repartiendo el presupuesto de cuadros entre todos.

    El reparto es lo que evita el costo que asusta: con cinco clips, sin
    presupuesto común serían 75 cuadros y el análisis saldría más caro que el
    diseño entero.
    """
    rutas = [Path(r) for r in rutas]
    if not rutas:
        return {"materiales": [], "avisos": ["No hay ningún archivo para analizar."]}
    por_archivo = max(3, presupuesto // len(rutas))

    materiales, avisos = [], []
    for r in rutas:
        try:
            a = analizar(r, destino, por_archivo)
            materiales.append(a)
            avisos += [f"{r.name}: {x}" for x in a["avisos"]]
        except Exception as e:
            log.exception("no pude analizar %s", r.name)
            avisos.append(f"{r.name}: no se pudo analizar — {e}")

    total = round(sum(m["duracion"] for m in materiales), 2)
    return {
        "materiales": materiales,
        "duracion_total": total,
        "cuadros_totales": sum(len(m["cuadros"]) for m in materiales),
        "avisos": avisos,
    }


def escribir(analisis: dict, destino: Path) -> Path:
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / "analisis.json"
    ruta.write_text(json.dumps(analisis, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    return ruta


def _restar(intervalos, quitar):
    """Lo que queda de `intervalos` después de sacarles `quitar`."""
    salida = []
    for a, b in intervalos:
        pedazos = [(a, b)]
        for x, y in quitar:
            siguientes = []
            for p, q in pedazos:
                if y <= p or x >= q:
                    siguientes.append((p, q))
                    continue
                if x > p:
                    siguientes.append((p, x))
                if y < q:
                    siguientes.append((y, q))
            pedazos = siguientes
        salida += pedazos
    return salida


def _juntar(intervalos, pegue: float = 0.0):
    """Los mismos intervalos, ordenados y sin superposiciones."""
    juntos = []
    for a, b in sorted(intervalos):
        if juntos and a <= juntos[-1][1] + pegue:
            juntos[-1] = (juntos[-1][0], max(juntos[-1][1], b))
        else:
            juntos.append((a, b))
    return juntos


def tramos_hablados(ruta, umbral_db: float = -42.0, minimo: float = 0.45,
                    aire: float = 0.12, min_tramo: float = 0.8,
                    desde: float = 0.0, hasta: float | None = None,
                    palabras: list[dict] | None = None) -> list[tuple]:
    """Los pedazos donde alguien habla, salteando los tiempos muertos.

    Es el complemento de `silencios()`: donde no hay silencio, hay algo que
    decir. Sirve para lo que en edición se llama «sacar los tiempos muertos»,
    que es la diferencia entre un video de 23 segundos y uno de 17 que se ve
    mucho mejor.

    **Se corta por ENERGÍA y no por los tiempos de la transcripción**, y esa
    diferencia importa: Whisper estira las palabras sobre las pausas, así que
    su idea de dónde termina una frase no coincide con dónde la persona se
    calló de verdad. Cortar por ahí parte palabras al medio. Está documentado
    en el pack de edición de reels de JordiGPT como una de sus trampas, y
    coincide con lo que este módulo ya medía.

    `aire` es lo que se deja a cada lado del habla. Sin eso el corte queda
    pegado a la primera sílaba y suena mordido; con 0,12 s la palabra respira y
    el tiempo muerto igual se va.

    `min_tramo` descarta las esquirlas: medio segundo de audio suelto entre dos
    silencios casi nunca es una palabra, es un ruido, y como tramo de video es
    un parpadeo.
    """
    ficha = sondear(ruta)
    fin = float(hasta if hasta is not None else ficha.get("duracion") or 0)
    if fin <= desde:
        return []
    if not ficha.get("tiene_audio"):
        return [(desde, fin)]

    # ── Un clip donde NADIE habla no se recorta ──────────────────────────
    #
    # «Sacar los tiempos muertos» es una operación sobre gente hablando: el
    # tiempo muerto es la pausa entre dos frases. En un clip sin una sola
    # palabra no hay pausas, hay PLANO — y lo que la energía llama silencio es
    # el ambiente, que es justamente lo que se quería filmar.
    #
    # Medido sobre un video generado por IA de 10,08 s: sin esta guarda el
    # recorte se comía los primeros 0,88 s, porque el arranque es más callado.
    # Ahí no se ahorró tiempo muerto: se tiró un segundo de un video que se
    # pagó, y en un clip generado **cada cuadro se pagó**.
    #
    # `palabras=None` es «no se transcribió» y no dice nada; `[]` es «se
    # escuchó y no se dijo una palabra», que es lo que decide.
    if palabras is not None and not palabras:
        return [(desde, fin)]

    t, db = energia_audio(ruta)
    mudos = silencios(t, db, umbral_db=umbral_db, minimo=minimo)

    # ── tiempo muerto que la energía no oye ──
    #
    # Medido en un video real: entre «acá» y «Y» hay 1,6 s en los que no se
    # dice nada, pero hay sonido —una respiración, un «eeeh», la sala— y la
    # energía no lo marca como silencio. Ese hueco sobrevivía al recorte y era
    # exactamente lo que se sentía como tiempo muerto al mirar el reel.
    #
    # Dos medidas distintas, dos definiciones de vacío: **callado** es lo que
    # oye la energía, **muerto** es que no se diga nada. Un reel hablado se
    # edita por lo segundo. Se cortan los dos.
    #
    # El final de cada palabra se toma como el arranque más una ventana, y no
    # como el `end` que declara Whisper, porque ese `end` está estirado hasta
    # la palabra siguiente: usarlo tal cual diría que nunca hay huecos.
    if palabras and len(palabras) > 1:
        # ── dónde termina de verdad cada palabra ──
        #
        # Whisper dice que «gustaría» dura 2,24 s: estira el final hasta la
        # palabra siguiente. Hasta acá eso se compensaba con una ventana fija
        # de 0,75 s, que es una estimación —y una estimación conservadora
        # obliga a dejar mucho aire, que es por qué el recorte sacaba 6,8 s de
        # 71 y el reel quedaba larguísimo.
        #
        # Pero el dato existe y ya se estaba midiendo para otra cosa: la
        # ENERGÍA dice exactamente cuándo la voz se apagó. Whisper sabe QUÉ se
        # dice y CUÁNDO empieza; la energía sabe cuándo termina. Cruzarlas da
        # el final real de cada palabra, y con un final real ya no hace falta
        # dejar aire de más «por las dudas».
        #
        # Se mide con paso fino: a 0,25 s —el paso que usa el resto del
        # módulo— el error es del mismo tamaño que una sílaba.
        tf, dbf = energia_audio(ruta, paso=0.06)
        piso = umbral_db

        #: Cuántas muestras seguidas por encima del umbral hacen falta para
        #: decir «acá todavía se está hablando». Tres, o sea 0,18 s.
        #:
        #: Una sola no alcanza, y eso era el bug: la primera versión buscaba el
        #: último instante por encima del umbral y devolvía casi siempre el
        #: final del hueco, porque en el medio del silencio hay chasquidos —una
        #: tecla, una silla, un click— que pasan el umbral por una muestra. Con
        #: eso el recorte no sacaba nada: medido, 71 s quedaban en 64,2 con la
        #: medición de energía y sin ella, exactamente igual.
        #:
        #: Una sílaba dura más de 0,18 s. Un chasquido, no.
        SEGUIDAS = 3

        def _fin_real(desde_p: float, tope_p: float) -> float:
            """El último instante en que se estaba hablando de verdad.

            Se recorre al revés y se busca una RACHA por encima del umbral, no
            una muestra suelta.
            """
            muestras = [(x, y) for x, y in zip(tf, dbf) if desde_p <= x <= tope_p]
            corridos = 0
            for x, y in reversed(muestras):
                if y > piso:
                    corridos += 1
                    if corridos >= SEGUIDAS:
                        return x + SEGUIDAS * 0.06
                else:
                    corridos = 0
            return desde_p

        VENTANA = 0.75
        # Sólo huecos GRANDES, y dejando aire generoso a los dos lados.
        #
        # Esto se calibró tres veces contra el mismo video y las tres primeras
        # se comieron «Y me gustaría». La razón de fondo es que el `end` de
        # Whisper no sirve para decidir dónde termina una palabra —viene
        # estirado— y `desde + VENTANA` es una estimación, no una medición. Con
        # márgenes de 0,10 s esa estimación se lleva la última sílaba.
        #
        # Así que el criterio final no es «apretar lo más posible» sino «cortar
        # sólo lo que es indudable»: un hueco de menos de 0,9 s no se toca, y
        # del que sí se toca se dejan 0,35 s a cada lado. Se recorta menos, y a
        # cambio no hay ninguna forma de que se pierda una palabra.
        #
        # Lo que se recorta igual es lo que se ve: el hueco de 2,8 s entre dos
        # frases, que es el que se siente como tiempo muerto. Los de medio
        # segundo son la respiración de alguien hablando y sacarlos hace que
        # suene atropellado.
        # Con el final medido en vez de estimado, los dos números se pueden
        # apretar: un hueco de medio segundo ya se corta, y el aire baja a
        # 0,18 s. Antes eran 0,90 y 0,35 y no era exceso de prudencia —era lo
        # que costaba no saber dónde terminaba la palabra—.
        HUECO_MINIMO = 0.50
        AIRE = 0.18

        # Dónde termina de verdad CADA palabra, calculado una sola vez. Sirve
        # para dos cosas distintas y opuestas: para saber dónde hay hueco que
        # cortar, y para saber qué no se puede cortar nunca.
        finales = []
        for i, w in enumerate(palabras):
            tope = palabras[i + 1]["desde"] if i + 1 < len(palabras) else fin
            c = min(_fin_real(w["desde"], tope), w["desde"] + VENTANA * 2)
            finales.append(max(c, w["desde"] + 0.10))

        for i, (w, sig) in enumerate(zip(palabras, palabras[1:])):
            if sig["desde"] - finales[i] >= HUECO_MINIMO:
                mudos.append((finales[i] + AIRE, sig["desde"] - AIRE))
        mudos = _juntar(mudos)

        # ── ningún corte puede COMERSE una palabra ────────────────────────
        #
        # Ésta es la regla que faltaba, y su ausencia arruinó un reel el
        # 31/8/2026. En el clip de Bruno la respuesta —«eh, por volar»— se
        # dijo más lejos del micrófono que la pregunta, así que su energía
        # quedó por debajo del umbral y `silencios()` marcó seis segundos y
        # medio como callados. El reel salió con la pregunta hecha, la
        # respuesta borrada y el remate colgando: técnicamente prolijo y sin
        # sentido.
        #
        # El error de fondo estaba en cómo se usaban las palabras. Servían
        # para AGREGAR cortes —los huecos que la energía no oye— y para que un
        # corte no partiera una palabra por la mitad. Pero nada impedía que un
        # corte se tragara palabras ENTERAS: si ninguna caía justo sobre el
        # borde, los dos bordes parecían limpios y nueve palabras desaparecían
        # en el medio sin que nada lo notara.
        #
        # Así que acá las palabras dejan de ser sólo un cortador y pasan a ser
        # un VETO: se le resta a los silencios todo lo que sea habla. La
        # energía sigue proponiendo dónde cortar; la transcripción tiene la
        # última palabra sobre dónde NO.
        #
        # Lo que queda afuera de este veto es lo único que no se puede
        # arreglar acá: una palabra que la transcripción tampoco escuchó. Para
        # eso está el retoque, que deja sacar o rehacer un tramo a mano.
        RESPIRO = 0.06
        habla = _juntar([(w["desde"] - RESPIRO, finales[i] + RESPIRO)
                         for i, w in enumerate(palabras)])
        # Después de sacarle el habla, un silencio puede quedar partido en
        # pedacitos. Los cortos no se cortan: un tijeretazo de dos décimas no
        # se siente como que sacaron un tiempo muerto, se siente como que el
        # video se trabó.
        mudos = [(a, b) for a, b in _restar(mudos, habla) if b - a >= minimo]

    # `min_tramo` descarta las esquirlas — pero NUNCA si adentro hay una
    # palabra.
    #
    # **Esto fue lo que arruinó el reel del 31/8/2026, y no lo que parecía.**
    # La primera lectura fue que la respuesta de Bruno se había dicho más
    # flojo que la pregunta y la energía no la había oído. Falso: medida, se
    # oye a −28 dB, igual que todo lo demás.
    #
    # Lo que pasó es más sutil. Bruno contesta a las corridas —pregunta,
    # respuesta, repregunta— con pausas cortas en el medio, así que quedaron
    # cinco islas de habla de unos 0,75 s cada una. `min_tramo` vale 0,8. Cada
    # isla, por sí sola, no llegaba al mínimo, así que se descartaron **las
    # cinco**: seis segundos y medio de diálogo desaparecieron uno por uno,
    # cada descarte defendible y el conjunto un desastre.
    #
    # La regla estaba pensada para basura —medio segundo de audio suelto entre
    # dos silencios casi nunca es una palabra— y el error fue no darle una
    # excepción para cuando SÍ lo es. Si adentro hay una palabra, el tramo
    # entra aunque sea corto: un parpadeo de video es un problema estético, y
    # perder lo que alguien dijo es un problema de otra categoría.
    arranques = [w["desde"] for w in (palabras or [])]

    def _vale(a: float, b: float) -> bool:
        return (b - a >= min_tramo) or any(a <= x <= b for x in arranques)

    tramos, cursor = [], desde
    for a, b in mudos:
        if b <= desde or a >= fin:
            continue
        a, b = max(a, desde), min(b, fin)
        if _vale(cursor, a):
            tramos.append((round(max(desde, cursor - aire), 2),
                           round(min(fin, a + aire), 2)))
        cursor = max(cursor, b)
    if _vale(cursor, fin):
        tramos.append((round(max(desde, cursor - aire), 2), round(fin, 2)))

    # ── que ningún corte parta una palabra ──
    #
    # Se usa el ARRANQUE de cada palabra y no su final, y ahí está toda la
    # gracia. La trampa que el pack de JordiGPT documenta es que Whisper
    # ESTIRA las palabras sobre las pausas: su `end` se va hasta donde empieza
    # la siguiente, así que dos frases separadas por un silencio real parecen
    # una sola palabra larga. Protegiendo por el `end` se juntaba todo — medido:
    # de seis tramos quedaban dos y el recorte caía de 4,2 s a 2,4.
    #
    # El `start`, en cambio, es preciso: es el instante en que se oye la
    # palabra. Así que lo que se protege es una ventana desde el arranque —lo
    # que dura la palabra, con un tope— y no el hueco inventado que viene
    # después. Adentro de esa ventana no puede caer un corte; fuera, manda la
    # energía, que es la que sabe dónde hay silencio de verdad.
    #
    # El tope existe porque una palabra estirada puede declarar dos segundos de
    # duración: sin él volveríamos a proteger la pausa entera. 0,75 s salió de
    # medir: con 0,60 el recorte se comía «Y me gustaría» —una palabra de tres
    # sílabas dura más que eso— y con 0,90 ya no recortaba lo suficiente.
    if palabras and tramos:
        VENTANA = 0.75

        def protegida(x):
            """El arranque de la palabra que este instante estaría partiendo."""
            for w in palabras:
                fin_real = min(w["hasta"], w["desde"] + VENTANA)
                if w["desde"] < x < fin_real:
                    return w["desde"], fin_real
            return None

        ajustados = []
        for a, b in tramos:
            p = protegida(a)
            if p:
                a = p[0] - 0.04
            p = protegida(b)
            if p:
                b = p[1] + 0.04
            ajustados.append((round(max(desde, a), 2), round(min(fin, b), 2)))

        # La primera palabra merece un trato aparte: el que habla entra bajito
        # y la energía no la oye. Medido en un video real, «Una» arranca en
        # 1,74 y la energía decía silencio hasta 2,25.
        primera = min((w["desde"] for w in palabras), default=None)
        if primera is not None and ajustados and primera < ajustados[0][0]:
            ajustados[0] = (round(max(desde, primera - 0.06), 2), ajustados[0][1])
        ultima = max((w["hasta"] for w in palabras), default=None)
        if ultima is not None and ajustados and ultima > ajustados[-1][1]:
            ajustados[-1] = (ajustados[-1][0], round(min(fin, ultima + 0.06), 2))

        # Estirar puede haber pegado dos tramos: se juntan, porque cortar y
        # volver a entrar en el mismo lugar se ve como un salto.
        tramos = []
        for a, b in ajustados:
            if tramos and a <= tramos[-1][1] + 0.05:
                tramos[-1] = (tramos[-1][0], max(tramos[-1][1], b))
            else:
                tramos.append((a, b))
    return tramos
