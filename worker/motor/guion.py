# -*- coding: utf-8 -*-
"""El guion de edición: lo que el agente escribe y el motor ejecuta.

## Por qué un contrato y no llamadas sueltas

Es la pieza más importante del editor de reels, y la que **no depende de
ffmpeg**. El agente no ejecuta cortes: escribe qué quiere. Si mañana el motor
cambia —otro encoder, un servicio de render, lo que sea— el guion sigue siendo
el mismo y no hay que reescribir nada del lado que decide.

Es el mismo patrón del `spec.json` de las placas, que ya lleva meses andando:
**el agente decide, el motor dibuja.**

## La forma

```json
{
  "tramos": [
    {"archivo": "clip1.mp4", "desde": 12.4, "hasta": 16.1},
    {"archivo": "clip1.mp4", "desde": 31.0, "hasta": 34.2, "velocidad": 0.5}
  ],
  "subtitulos": [
    {"texto": "No necesitás agendar", "desde": 0.0, "hasta": 1.8}
  ],
  "musica": {"archivo": "pista.mp3", "desde": 8.0, "volumen": 0.35,
             "bajar_con_voz": true},
  "tapa":   {"titulo": "Vení sin turno", "destacado": "en 1 hora"},
  "cierre": {"cta": "ESCRIBINOS", "tel": "092 566 967"}
}
```

Los tiempos de `tramos` son del **material original**. Los de `subtitulos` son
del **reel ya montado**, que es lo que la persona va a ver. Mezclarlos es el
error más fácil de cometer y el más difícil de ver en el código, así que el
validador chequea cada uno contra su propia escala.

## Por qué valida antes de renderizar

Un encode tarda minutos. Descubrir a los tres minutos que un tramo pedía el
segundo 40 de un clip que dura 30 es tirar esos tres minutos, y encima el error
que llega es de ffmpeg y no lo entiende nadie.

Se valida **todo junto y de una**: el validador junta TODOS los problemas y los
devuelve en una sola lista, en castellano. Si devolviera el primero, el agente
arreglaría uno por turno y cada turno cuesta.
"""
from pathlib import Path

# Los límites de Instagram para que un video entre en la pestaña de Reels.
MIN_REEL, MAX_REEL = 5.0, 90.0

# Menos de esto no es un corte, es un parpadeo: no da tiempo a entender qué se
# ve y el reel se siente nervioso. Sale de mirar cortes de 0,5s renderizados.
MIN_TRAMO = 0.8

# Fuera de este rango el video deja de leerse: muy lento se ve trabado, muy
# rápido no se entiende nada.
VEL_MIN, VEL_MAX = 0.25, 4.0

ANIMOS = ("club", "calmo", "tension")

MAX_SUBTITULO = 42        # caracteres por línea de subtítulo
MIN_SUBTITULO = 0.6       # segundos que necesita un subtítulo para leerse


class GuionInvalido(ValueError):
    """Todos los problemas del guion, juntos y en castellano."""

    def __init__(self, problemas):
        self.problemas = problemas
        super().__init__("El guion no se puede renderizar:\n  · "
                         + "\n  · ".join(problemas))


def duracion_tramo(t: dict) -> float:
    """Cuánto ocupa un tramo EN EL REEL, que no es lo mismo que en el original.

    Un tramo de 4 segundos a velocidad 0,5 dura 8 en el reel. Sin esto, un
    guion con cámara lenta se pasa de los 90 segundos sin que nadie lo note
    hasta que Instagram lo rechaza.
    """
    largo = float(t.get("hasta", 0)) - float(t.get("desde", 0))
    return largo / float(t.get("velocidad") or 1.0)


def duracion_final(guion: dict, con_tapas: float = 0.0) -> float:
    return round(sum(duracion_tramo(t) for t in guion.get("tramos") or []) + con_tapas, 2)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def verificar(guion: dict, materiales: dict, tapas_seg: float = 0.0) -> list[str]:
    """Revisa el guion contra el material real. Devuelve los avisos.

    `materiales` es `{nombre_de_archivo: duracion_en_segundos}` — sale derecho
    del análisis. Lo que está mal levanta `GuionInvalido`; lo que se puede
    renderizar pero probablemente no convenga vuelve como aviso.
    """
    problemas, avisos = [], []

    if not isinstance(guion, dict):
        raise GuionInvalido(["El guion tiene que ser un objeto JSON."])

    tramos = guion.get("tramos")
    if not isinstance(tramos, list) or not tramos:
        raise GuionInvalido(["El guion no tiene ningún tramo: sin tramos no hay reel."])

    # ── los tramos ──
    for i, t in enumerate(tramos, 1):
        if not isinstance(t, dict):
            problemas.append(f"Tramo {i}: tiene que ser un objeto con archivo, desde y hasta.")
            continue
        arch = (t.get("archivo") or "").strip()
        desde, hasta = _num(t.get("desde")), _num(t.get("hasta"))
        vel = _num(t.get("velocidad") or 1.0)

        if not arch:
            problemas.append(f"Tramo {i}: le falta el archivo.")
        elif arch not in materiales:
            cerca = ", ".join(sorted(materiales)) or "ninguno"
            problemas.append(
                f"Tramo {i}: pide «{arch}», que no está entre los archivos "
                f"subidos ({cerca}).")
        if desde is None or hasta is None:
            problemas.append(f"Tramo {i}: «desde» y «hasta» tienen que ser números.")
            continue
        if desde < 0:
            problemas.append(f"Tramo {i}: «desde» no puede ser negativo.")
        if hasta <= desde:
            problemas.append(
                f"Tramo {i}: «hasta» ({hasta}) tiene que ser mayor que «desde» ({desde}).")
            continue
        if arch in materiales:
            dur = materiales[arch]
            if hasta > dur + 0.05:
                problemas.append(
                    f"Tramo {i}: pide hasta el segundo {hasta:.1f} pero "
                    f"«{arch}» dura {dur:.1f}.")
        if vel is None or not (VEL_MIN <= vel <= VEL_MAX):
            problemas.append(
                f"Tramo {i}: velocidad {t.get('velocidad')} fuera de rango "
                f"({VEL_MIN} a {VEL_MAX}).")
        elif duracion_tramo(t) < MIN_TRAMO:
            avisos.append(
                f"Tramo {i}: dura {duracion_tramo(t):.2f}s en el reel. Menos de "
                f"{MIN_TRAMO}s no es un corte, es un parpadeo.")

    # ── los rótulos, mirados como conjunto ──
    #
    # Estas dos revisiones existen por una pieza real: el mismo texto aparecía
    # en cuatro tramos seguidos, así que la animación de entrada se repetía
    # cuatro veces y el reel se sentía trabado. Y los textos eran la frase que
    # había escrito la persona, copiada tal cual.
    previo_txt = None
    for i, tr in enumerate(tramos, 1):
        txt = (tr.get("texto") or "").strip()
        if not txt:
            previo_txt = None
            continue
        if txt.lower() == (previo_txt or "").lower():
            avisos.append(
                f"Tramo {i}: repite el rótulo «{txt[:28]}» del tramo anterior. "
                f"La animación de entrada vuelve a correr y se siente trabado — "
                f"si el texto tiene que quedarse, alargá el tramo en vez de "
                f"repetirlo.")
        palabras = len(txt.split())
        if palabras > 5:
            avisos.append(
                f"Tramo {i}: el rótulo «{txt[:34]}» tiene {palabras} palabras. "
                f"Un rótulo de reel son 2 a 4: no es un subtítulo, es un cartel.")
        previo_txt = txt

    if problemas:
        raise GuionInvalido(problemas)

    # ── el largo total ──
    total = duracion_final(guion, tapas_seg)
    if total < MIN_REEL:
        problemas.append(
            f"El reel dura {total:.1f}s y el mínimo de Instagram es {MIN_REEL:.0f}s.")
    if total > MAX_REEL:
        problemas.append(
            f"El reel dura {total:.1f}s. Pasado de {MAX_REEL:.0f}s no entra en la "
            f"pestaña de Reels: sacá o acortá tramos.")

    # ── los subtítulos, que van en la escala del reel montado ──
    subs = guion.get("subtitulos") or []
    # «auto» es «transcribí el audio y armalos vos». Se resuelve en
    # `video.desde_guion`, ANTES de validar, así que si llegó hasta acá como
    # texto es porque no había nada que transcribir — y eso no es un error:
    # un peloteo de pádel no tiene voz y el reel sale igual, sin subtítulos.
    if isinstance(subs, str):
        subs = []
    if not isinstance(subs, list):
        problemas.append("«subtitulos» tiene que ser una lista, o «auto» para "
                         "sacarlos del audio.")
        subs = []
    previo = None
    for i, s in enumerate(sorted(
            [x for x in subs if isinstance(x, dict)],
            key=lambda x: _num(x.get("desde")) or 0), 1):
        texto = (s.get("texto") or "").strip()
        desde, hasta = _num(s.get("desde")), _num(s.get("hasta"))
        if not texto:
            problemas.append(f"Subtítulo {i}: está vacío.")
        if desde is None or hasta is None or hasta <= desde:
            problemas.append(f"Subtítulo {i} («{texto[:24]}»): los tiempos están mal.")
            continue
        if hasta > total + 0.05:
            problemas.append(
                f"Subtítulo {i} («{texto[:24]}»): termina en {hasta:.1f}s pero el "
                f"reel dura {total:.1f}s. Los tiempos de los subtítulos son del "
                f"reel montado, no del video original.")
        if hasta - desde < MIN_SUBTITULO:
            avisos.append(
                f"Subtítulo {i} («{texto[:24]}»): {hasta - desde:.1f}s no alcanzan "
                f"para leerlo.")
        if len(texto) > MAX_SUBTITULO:
            avisos.append(
                f"Subtítulo {i}: {len(texto)} caracteres. Más de {MAX_SUBTITULO} "
                f"no entran en una línea y se parte solo.")
        if previo is not None and desde < previo - 0.05:
            avisos.append(f"Subtítulo {i} («{texto[:24]}»): se pisa con el anterior.")
        previo = hasta

    # ── la música ──
    mus = guion.get("musica")
    if mus:
        if not isinstance(mus, dict):
            problemas.append("«musica» tiene que ser un objeto.")
        else:
            arch = (mus.get("archivo") or "").strip()
            # Sin archivo NO es un error: es la cama sintetizada del motor, que
            # es lo normal. `archivo` sólo se usa cuando la persona subió una
            # pista propia.
            if arch and arch not in materiales:
                problemas.append(
                    f"La música pide «{arch}», que no está entre los archivos subidos.")
            vol = _num(mus.get("volumen") if mus.get("volumen") is not None else 0.35)
            if vol is None or not (0.0 <= vol <= 1.0):
                problemas.append(f"Volumen de la música fuera de rango: {mus.get('volumen')}.")
            animo = (mus.get("animo") or "").strip()
            if animo and animo not in ANIMOS:
                problemas.append(
                    f"Ánimo de música desconocido: «{animo}». Los que hay son "
                    f"{', '.join(ANIMOS)}.")
            bpm = _num(mus.get("bpm")) if mus.get("bpm") is not None else None
            if bpm is not None and not (60 <= bpm <= 160):
                problemas.append(f"BPM fuera de rango: {mus.get('bpm')} (60 a 160).")
            if vol is not None and 0 <= vol <= 1 and vol > 0.6 and subs:
                # Con alguien hablando, la música arriba de 0,6 tapa la voz. No
                # es un error —hay reels sin voz donde 0,8 está bien— pero si
                # el guion trae subtítulos es que alguien habla.
                avisos.append(
                    f"La música va a {vol:.2f} y el reel tiene subtítulos: por "
                    f"encima de 0,60 la música tapa la voz.")

    if problemas:
        raise GuionInvalido(problemas)
    return avisos


def normalizar(guion: dict) -> dict:
    """Completa lo que falta con los valores por defecto."""
    g = dict(guion)
    g["tramos"] = [{**t, "velocidad": float(t.get("velocidad") or 1.0)}
                   for t in (g.get("tramos") or [])]
    g["subtitulos"] = sorted(
        [dict(s) for s in (g.get("subtitulos") or []) if isinstance(s, dict)],
        key=lambda s: _num(s.get("desde")) or 0)
    if g.get("musica"):
        m = dict(g["musica"])
        m.setdefault("desde", 0.0)
        m.setdefault("volumen", 0.35)
        m.setdefault("bajar_con_voz", True)
        g["musica"] = m
    return g


def desde_analisis(analisis: dict) -> dict:
    """El `{archivo: duracion}` que necesita `verificar()`, sacado del análisis."""
    return {m["archivo"]: m["duracion"] for m in analisis.get("materiales", [])
            if m.get("archivo")}


def resumen(guion: dict, tapas_seg: float = 0.0) -> str:
    """Una línea para el log y para `copy.txt`."""
    g = normalizar(guion)
    n = len(g["tramos"])
    return (f"{n} tramo{'s' if n != 1 else ''} · "
            f"{duracion_final(g, tapas_seg):.1f}s · "
            f"{len(g['subtitulos'])} subtítulos · "
            f"música: {'sí' if g.get('musica') else 'no'}")


# ═══════════════════════════════════════════════════════════════════════════
#  Del guion al spec del motor
#
#  El guion habla en «desde/hasta del material original», que es como piensa
#  quien edita. El motor de video piensa en «desde + cuánto dura en el reel».
#  La traducción vive acá, en un solo lugar, para que el agente nunca tenga que
#  saber cómo espera los datos ffmpeg.
# ═══════════════════════════════════════════════════════════════════════════

def a_spec(guion: dict, nombre: str, carpeta=None, sonido: dict | None = None) -> dict:
    """El `spec` que entiende `motor.video.reel()`.

    `carpeta` es dónde están los archivos que subió la persona. Se resuelve
    acá y no en el guion: el agente escribe nombres de archivo, no rutas, y así
    el mismo guion sirve aunque el material se mueva de lugar.
    """
    g = normalizar(guion)
    base = Path(carpeta) if carpeta else None

    tramos = []
    for t in g["tramos"]:
        arch = t["archivo"]
        ruta = str((base / arch)) if base else arch
        tramos.append({
            "tipo": "video",
            "archivo": ruta,
            "desde": round(float(t["desde"]), 3),
            # El motor razona en duración final; el guion en punto de entrada y
            # de salida del original. Esta línea es toda la traducción.
            "dura": round(duracion_tramo(t), 3),
            "velocidad": t["velocidad"],
        })
        for campo in ("texto", "emoji", "pos", "cuerpo", "recorte", "foco_x",
                      "audio", "estilo", "encuadre", "fondo"):
            if campo in t:
                tramos[-1][campo] = t[campo]

    son = dict(sonido or {})
    # Los efectos se piden con `efectos: true` en el guion. Ver la nota en
    # `video._mezclar` sobre por qué ya no vienen solos.
    if g.get("efectos") is not None:
        son["efectos"] = bool(g.get("efectos"))
    mus = g.get("musica")
    if mus:
        son["musica"] = True
        son["vol_musica"] = float(mus.get("volumen", 0.35))
        if mus.get("animo"):
            son["animo"] = mus["animo"]
        if mus.get("bpm"):
            son["bpm"] = int(mus["bpm"])
        if base and mus.get("archivo"):
            son["archivo_musica"] = str(base / mus["archivo"])

    # Los subtítulos van en la escala del reel montado, así que pasan tal cual:
    # no hay nada que traducir. Estuvieron declarados en el contrato y
    # validados desde el primer día, pero esta línea no existía y el spec salía
    # sin ellos — el agente escribía subtítulos, el validador los aceptaba y no
    # aparecían en el video, sin ningún error que lo explicara.
    subs = [{"texto": str(x["texto"]).strip(),
             "desde": round(float(x["desde"]), 3),
             "hasta": round(float(x["hasta"]), 3)}
            for x in (g.get("subtitulos") or [])
            if isinstance(x, dict)
            if str(x.get("texto") or "").strip()
            and x.get("desde") is not None and x.get("hasta") is not None]

    return {"nombre": nombre, "tramos": tramos, "sonido": son,
            "subtitulos": subs}
