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

    t, db = energia_audio(ruta)
    mudos = silencios(t, db, umbral_db=umbral_db, minimo=minimo)

    tramos, cursor = [], desde
    for a, b in mudos:
        if b <= desde or a >= fin:
            continue
        a, b = max(a, desde), min(b, fin)
        if a - cursor >= min_tramo:
            tramos.append((round(max(desde, cursor - aire), 2),
                           round(min(fin, a + aire), 2)))
        cursor = max(cursor, b)
    if fin - cursor >= min_tramo:
        tramos.append((round(max(desde, cursor - aire), 2), round(fin, 2)))

    # ── que el primer y el último borde no partan una palabra ──
    #
    # Está medido en un video real: la palabra «Una» arranca en 1,74 pero el
    # ataque es tan suave que la energía dice silencio hasta 2,25. Con
    # cualquier `aire` razonable el corte cae adentro y el reel empieza con
    # media sílaba — justo la primera, que es la que engancha o no. Subir el
    # `aire` no lo arregla: con 0,45 s seguía mordiendo y ya casi no recortaba.
    #
    # **Sólo los bordes de afuera, y eso es deliberado.** La primera versión
    # protegía TODOS los cortes y el resultado fue peor: de seis tramos quedaron
    # dos y el recorte bajó de 4,6 s a 2,4. La causa es la trampa que el propio
    # pack de JordiGPT advierte —Whisper ESTIRA las palabras sobre las pausas—,
    # así que sus bordes dicen que dos frases separadas por un silencio real son
    # una sola palabra larga. Adentro manda la energía, que para eso se mide;
    # en las puntas manda la transcripción, que es donde la energía falla porque
    # el que habla entra y sale bajito.
    if palabras and tramos:
        primera = min((w["desde"] for w in palabras), default=None)
        ultima = max((w["hasta"] for w in palabras), default=None)
        a0, b0 = tramos[0]
        if primera is not None and primera < a0:
            tramos[0] = (round(max(desde, primera - 0.06), 2), b0)
        aN, bN = tramos[-1]
        if ultima is not None and ultima > bN:
            tramos[-1] = (aN, round(min(fin, ultima + 0.06), 2))
    return tramos
