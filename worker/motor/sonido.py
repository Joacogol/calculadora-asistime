# -*- coding: utf-8 -*-
"""Efectos y música sintetizados para los reels de Boss Padel.

Todo se genera con matemática, no se descarga nada. Dos motivos: no hay
licencia que pedir ni riesgo de que Instagram silencie el reel, y los sonidos
salen a medida — el golpe dura exactamente lo que dura el corte.

Los efectos son cuatro y alcanzan para todo:
  whoosh    ruido filtrado que barre de agudo a grave — acompaña un corte
  pop       seno corto con caída rápida — entra un rótulo o un emoticón
  impacto   sinusoide que cae de 120 a 45 Hz — le da peso al corte
  riser     ruido que sube en tono y volumen — anuncia el cierre

La música es una cama, no un tema: bombo en cada pulso, palmas en 2 y 4,
hi-hat en las corcheas, un bajo y un punteo. Suena a base programada porque
lo es, pero marca el pulso y llena el silencio.

    python3 sonido.py            # genera todo en assets/sfx/
"""
import subprocess
import wave
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent
SFX = RAIZ / "assets" / "sfx"
SR = 48000


def _guardar(nombre: str, x: np.ndarray) -> Path:
    """Normaliza, aplica un fundido mínimo en los bordes y escribe el WAV.

    El fundido de 3 ms en cada punta no es un capricho: una onda que arranca o
    corta en un valor distinto de cero produce un chasquido audible.
    """
    SFX.mkdir(parents=True, exist_ok=True)
    x = np.asarray(x, dtype=np.float64)
    pico = np.max(np.abs(x)) or 1.0
    x = x / pico * 0.92
    n = int(SR * 0.003)
    if len(x) > 2 * n:
        x[:n] *= np.linspace(0, 1, n)
        x[-n:] *= np.linspace(1, 0, n)
    ruta = SFX / f"{nombre}.wav"
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    return ruta


def _t(dur):
    return np.linspace(0, dur, int(SR * dur), endpoint=False)


def _pasabajos(x, corte, veces=2):
    """Filtro de un polo aplicado varias veces. Con uno solo casi no se nota."""
    a = np.exp(-2 * np.pi * corte / SR)
    for _ in range(veces):
        y = np.empty_like(x)
        acum = 0.0
        for i, v in enumerate(x):
            acum = (1 - a) * v + a * acum
            y[i] = acum
        x = y
    return x


def _pasaaltos(x, corte, veces=1):
    return x - _pasabajos(x, corte, veces)


# ── efectos ───────────────────────────────────────────────────────────────

def whoosh(dur=0.32):
    t = _t(dur)
    ruido = np.random.RandomState(7).normal(0, 1, len(t))
    # el corte del filtro barre de 6 kHz a 400 Hz: eso es lo que se oye como
    # un objeto que pasa de largo
    env = np.exp(-t * 7)
    x = _pasabajos(ruido, 2600, 2) * env
    x += _pasaaltos(ruido, 4000, 1) * np.exp(-t * 16) * 0.5
    return x * np.sin(np.pi * t / dur) ** 0.6


def pop(dur=0.13, base=880):
    """El sonido del rótulo cuando entra.

    **Era un beep** —tres senoidales a 880 Hz con caída rápida— y por eso
    sonaba a alarma de microondas. Un tono con altura definida suena a aviso;
    el oído lo lee como «pasó algo que tenés que atender», no como «entró un
    texto».

    Lo que usan hoy los cortes deportivos es un **transitorio sin altura**: un
    golpecito de ruido filtrado, muy corto, con un poco de cuerpo abajo. No
    canta ninguna nota, así que nunca desafina contra la música, y desaparece
    debajo de la voz en vez de competir con ella.

    No copié ningún sonido de los que circulan —no se puede y no hace falta—:
    esto es la MISMA construcción, sintetizada.
    """
    t = _t(dur)
    r = np.random.default_rng(7)

    # El chasquido: ruido en la zona de los 2-5 kHz, que es donde el oído
    # detecta el ataque, con una caída de 90 —dura 30 milisegundos.
    chasquido = _pasaaltos(_pasabajos(r.normal(0, 1, len(t)), 5200), 1400)
    chasquido *= np.exp(-t * 90)

    # El cuerpo: un golpe grave cortísimo que baja de tono. Es lo que hace que
    # se sienta un «toc» y no un «ts». Sin esto el sonido queda anémico en el
    # parlante de un celular.
    cuerpo = np.sin(2 * np.pi * (190 * np.exp(-t * 26)) * t) * np.exp(-t * 46)

    x = chasquido * 0.85 + cuerpo * 0.55
    pico = np.max(np.abs(x)) or 1.0
    return x / pico


def impacto(dur=0.42):
    t = _t(dur)
    # la frecuencia cae de 120 a 45 Hz: el barrido es lo que da la sensación
    # de golpe en vez de un simple tono grave
    f = 45 + 75 * np.exp(-t * 22)
    fase = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(fase) * np.exp(-t * 8)
    click = np.random.RandomState(3).normal(0, 1, len(t)) * np.exp(-t * 180) * 0.35
    return x + _pasaaltos(click, 2000)


def riser(dur=1.4):
    t = _t(dur)
    ruido = np.random.RandomState(11).normal(0, 1, len(t))
    x = _pasaaltos(ruido, 500, 1) * (t / dur) ** 2
    f = 200 * (1 + 6 * (t / dur) ** 2)
    x += np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / dur) ** 3 * 0.5
    return x


# ── música ────────────────────────────────────────────────────────────────

def _bombo(dur=0.30):
    t = _t(dur)
    f = 45 + 85 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)


def _palma(dur=0.22):
    t = _t(dur)
    r = np.random.RandomState(5).normal(0, 1, len(t))
    x = _pasaaltos(_pasabajos(r, 4200, 1), 1100, 1)
    # tres golpes muy juntos: es lo que distingue una palmada de un ruido seco
    env = np.exp(-t * 26)
    for retardo in (0.008, 0.015):
        d = int(retardo * SR)
        env[d:] += np.exp(-t[:-d] * 26) * 0.55
    return x * env


def _hat(dur=0.07):
    t = _t(dur)
    r = np.random.RandomState(9).normal(0, 1, len(t))
    return _pasaaltos(r, 7000, 1) * np.exp(-t * 90)


def _bajo(nota_hz, dur):
    t = _t(dur)
    # sierra suavizada: cuerpo grave sin quedar en un seno soso
    x = 2 * (t * nota_hz - np.floor(0.5 + t * nota_hz))
    x = _pasabajos(x, 320, 2)
    env = np.minimum(1, t * 60) * np.exp(-t * 2.2)
    return x * env


def _punteo(nota_hz, dur):
    t = _t(dur)
    x = np.sin(2 * np.pi * nota_hz * t) + 0.4 * np.sin(2 * np.pi * nota_hz * 2 * t)
    return x * np.exp(-t * 7) * np.minimum(1, t * 200)


# Las notas que usan los ánimos. Si agregás una progresión con una nota que no
# esté acá, `musica()` explota con un KeyError — pasó al sumar el ánimo
# «tension», que trae si bemol y si natural.
NOTA = {"A2": 110.0, "C3": 130.81, "D3": 146.83, "F3": 174.61, "G3": 196.0,
        "A3": 220.0, "B3": 246.94, "C4": 261.63, "D4": 293.66, "E4": 329.63,
        "F4": 349.23, "G4": 392.0, "A4": 440.0}


# Los ánimos de la cama musical.
#
# Existen porque la misma música no le sirve a todas las marcas. La progresión
# original —La menor, con palmas y bombo a negras— suena a club de noche, que
# es exactamente Boss Padel. Puesta abajo de un reel de una clínica de salud
# laboral suena a promoción de gimnasio, y desafina con todo lo demás de la
# marca.
#
# `progresion`  los acordes, en orden, un compás cada uno
# `palmas`      la palma en los tiempos 2 y 4: es lo que da la sensación de
#               pista de baile. Sin ella la cama acompaña en vez de empujar
# `punteo`      volumen del arpegio; 0 lo apaga
# `vol`         volumen general de la cama
ANIMOS = {
    # Boss Padel: enérgico sin ser alegre. Negro, lima, de noche.
    "club": {
        "progresion": [("A2", ["A3", "C4", "E4"]), ("F3", ["A3", "C4", "F3"]),
                       ("C3", ["C4", "E4", "G4"]), ("G3", ["D4", "G4", "A4"])],
        "palmas": True, "punteo": 0.22, "vol": 1.0, "bpm": 100,
    },
    # Clínica Preventiva y cualquier marca de servicio: mayor, sin palmas,
    # más lento. Acompaña y no compite con una voz.
    "calmo": {
        "progresion": [("C3", ["C4", "E4", "G4"]), ("A2", ["A3", "C4", "E4"]),
                       ("F3", ["F3", "A3", "C4"]), ("G3", ["G3", "B3", "D4"])],
        "palmas": False, "punteo": 0.16, "vol": 0.85, "bpm": 84,
    },
    # Para cuentas regresivas y anuncios: tensión que empuja hacia adelante.
    "tension": {
        "progresion": [("A2", ["A3", "C4", "E4"]), ("A2", ["A3", "D4", "F4"]),
                       ("F3", ["A3", "C4", "F4"]), ("G3", ["B3", "D4", "G4"])],
        "palmas": True, "punteo": 0.12, "vol": 1.0, "bpm": 112,
    },
}


def musica(dur_total: float, bpm: int | None = None, animo: str = "club") -> Path:
    """Cama rítmica sintetizada. Devuelve la ruta del WAV.

    **Se genera, no se descarga.** Eso no es una curiosidad técnica: es lo que
    permite incrustar la música en el archivo y publicar por la API de
    Instagram sin ningún problema de licencia. La biblioteca musical de
    Instagram no se puede usar por API, así que el audio tiene que ir adentro
    del mp4 — y si va adentro, tiene que ser nuestro.
    """
    cfg = ANIMOS.get(animo) or ANIMOS["club"]
    bpm = int(bpm or cfg["bpm"])
    pulso = 60.0 / bpm
    n = int(SR * (dur_total + 1.0))
    pista = np.zeros(n)

    def poner(x, t0, vol=1.0):
        i = int(t0 * SR)
        j = min(n, i + len(x))
        if i < n:
            pista[i:j] += x[: j - i] * vol

    progresion = cfg["progresion"]
    compas = pulso * 4
    total_compases = int(dur_total / compas) + 2

    b, p, h = _bombo(), _palma(), _hat()
    for c in range(total_compases):
        t0 = c * compas
        raiz, acorde = progresion[c % len(progresion)]
        poner(_bajo(NOTA[raiz], compas * 0.9), t0, 0.55)
        for k in range(4):
            poner(b, t0 + k * pulso, 0.95)
            poner(h, t0 + k * pulso + pulso / 2, 0.30)
            if cfg["palmas"] and k % 2 == 1:
                poner(p, t0 + k * pulso, 0.45)
        # el punteo entra recién en el segundo compás y deja el primero
        # respirando; si suena desde el arranque, satura
        if c % 2 == 1 and cfg["punteo"]:
            for k, nota in enumerate(acorde):
                poner(_punteo(NOTA[nota], pulso * 1.2), t0 + k * pulso, cfg["punteo"])

    pista = pista[: int(SR * dur_total)] * cfg["vol"]
    pista *= np.minimum(1, np.arange(len(pista)) / (SR * 0.6))          # entra
    salida = np.minimum(1, np.arange(len(pista))[::-1] / (SR * 1.2))     # sale
    return _guardar(f"musica-{animo}", pista * salida)


EFECTOS = {"whoosh": whoosh, "pop": pop, "impacto": impacto, "riser": riser}


def pista_efectos(eventos: list[tuple[float, str, float]], dur_total: float) -> Path:
    """Arma UNA pista con todos los efectos ya colocados en su lugar.

    La alternativa era pasarle a ffmpeg cada efecto como una entrada aparte y
    retrasarlo con `adelay`, pero un reel de veinte segundos tiene quince o
    veinte efectos: quince entradas, quince `asplit`, quince retardos. Sumarlos
    acá es una línea de numpy y deja el comando de ffmpeg con tres entradas.
    """
    n = int(SR * (dur_total + 0.5))
    pista = np.zeros(n)
    cache = {}
    for t0, tipo, vol in eventos:
        if tipo not in cache:
            cache[tipo] = EFECTOS[tipo]()
        x = cache[tipo]
        i = max(0, int(t0 * SR))
        j = min(n, i + len(x))
        if i < n:
            pista[i:j] += x[: j - i] * vol
    return _guardar("efectos", pista[: int(SR * dur_total)])


def generar_efectos() -> dict:
    return {n: _guardar(n, f()) for n, f in EFECTOS.items()}


if __name__ == "__main__":
    for n, r in generar_efectos().items():
        print(f"  {n:9} {r.stat().st_size/1024:6.1f} KB")
    r = musica(18.0)
    print(f"  {'musica':9} {r.stat().st_size/1024:6.1f} KB")
