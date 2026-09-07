# -*- coding: utf-8 -*-
"""Encuadre por planos: que el recorte vertical vaya a donde están las caras.

## El problema

Un video de gente hablando se filma apaisado. Para hacerlo reel se recorta a
vertical, y hasta el 2/9/2026 ese recorte se quedaba SIEMPRE en el centro.
En un primer plano de podcast la cara suele estar a un lado —al 67 % del
ancho en el clip con que se midió esto— y el centro la parte al medio. En un
plano de dos, el centro deja afuera justo a quien habla.

## Lo que se decidió, y con qué datos

Se midieron tres formas de saber a dónde mirar, sobre el mismo clip:

* **Detectar caras localmente** (YuNet, un modelo de 230 KB que corre en CPU):
  posición con precisión de píxel, cinco veces por segundo, gratis. Es lo que
  se usa.
* **Movimiento de la boca para saber quién habla**: no distingue. Gestos y
  tamaño de cara contaminan la señal; en el plano de dos eligió al que no
  hablaba.
* **Gemini agéntico**: acierta la posición de las caras (±3 %) y los cortes de
  cámara, pero puso hablando dos segundos a una persona que no estaba en el
  plano. Sus números sirven; su relato de quién habla, no.

Por eso la regla no intenta adivinar quién habla. Divide el tramo en PLANOS
—cambia el conjunto de caras, cambia el plano; así se detectan los cortes de
cámara que el material ya trae— y por plano decide:

* **una cara** → el recorte se centra en ella;
* **varias caras** → el recorte se ABRE hasta que entren todas (bandas
  desenfocadas arriba y abajo, lo que el motor ya sabe hacer). Nunca deja
  afuera al que habla, que es lo que importa;
* **no entran ni abriendo** → la cara más grande, que es la más cerca de la
  cámara.

Un plano corto —una reacción de dos segundos— es un plano igual: se fusiona
con el vecino sólo si el encuadre del vecino ya lo contiene. Absorberlo a
ciegas fue el error de la primera versión: dejó dos segundos de una cara
cortada por el borde.

## Cómo entra al motor

Devuelve SUB-TRAMOS: el mismo material, partido donde cambia el plano, con
`foco_x` y `recorte` en cada pedazo. Son campos que `motor/video.py` ya
entendía. No se toca ffmpeg ni el render; y si OpenCV o el modelo no están,
o no aparece ninguna cara, los tramos salen como entraron y el reel sale
como hasta hoy. Un reel con el encuadre viejo es peor que uno con el nuevo,
y muchísimo mejor que ninguno.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

AQUI = Path(__file__).resolve().parent
MODELO = AQUI / "assets" / "face_detection_yunet_2023mar.onnx"

#: Cuadros por segundo que se miran. Cinco alcanzan para ver un corte de
#: cámara y sobran para una cara que no se mueve; a 640 px de ancho el
#: detector tarda unos 10 ms por cuadro.
FPS = 5
ANCHO_ANALISIS = 640

#: El recorte por defecto del motor: 9:16 a toda altura de la fuente.
RECORTE_BASE = 1080 / 1920
#: Hasta dónde se abre para que entren varias caras. 1:1 es el look de las
#: bandas desenfocadas que ya usan los reels del club; más abierto queda una
#: tirita en el medio.
RECORTE_MAXIMO = 1.0
#: Cuánto aire se deja a cada lado de una cara, en anchos de cara.
AIRE = 0.9
#: Un cambio de caras tiene que sostenerse esto para ser un plano y no un
#: parpadeo del detector.
PERSISTENCIA = 3
#: Un plano más corto que esto se fusiona con el vecino si el vecino ya lo
#: encuadra bien.
PLANO_CORTO = 1.5
#: Dos caras a menos de esto de distancia (fracción del ancho) son la misma
#: persona en cuadros distintos.
MISMA_PERSONA = 0.12


def disponible() -> bool:
    """¿Se puede encuadrar? OpenCV instalado y el modelo en su lugar."""
    if not MODELO.exists():
        return False
    try:
        import cv2  # noqa: F401
        return hasattr(cv2, "FaceDetectorYN")
    except Exception:                                        # noqa: BLE001
        return False


# ═══ 1. Ver: las caras de cada cuadro ═══════════════════════════════════════

def caras_de(video, desde: float, hasta: float, ancho_fuente: int, alto_fuente: int
             ) -> list[list[tuple[float, float]]]:
    """Por cuadro muestreado, las caras como (centro_x, ancho), en fracción del ancho.

    Los cuadros salen de ffmpeg ya achicados y en crudo, sin escribir archivos:
    para esto no hace falta más resolución, y decodificar una vez a 640 px es
    más barato que sacar imágenes y volver a leerlas.
    """
    import numpy as np
    import cv2
    w = ANCHO_ANALISIS
    h = int(round(alto_fuente * w / ancho_fuente / 2) * 2)
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{desde:.3f}", "-t", f"{hasta - desde:.3f}",
         "-i", str(video), "-vf", f"fps={FPS},scale={w}:{h}",
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
        capture_output=True, timeout=600)
    n = len(r.stdout) // (w * h * 3)
    if n == 0:
        return []
    cuadros = np.frombuffer(r.stdout[: n * w * h * 3], np.uint8).reshape(n, h, w, 3)
    det = cv2.FaceDetectorYN.create(str(MODELO), "", (w, h), score_threshold=0.6)
    salida = []
    for img in cuadros:
        _, c = det.detect(img)
        salida.append([((f[0] + f[2] / 2) / w, f[2] / w) for f in (c if c is not None else [])])
    return salida


# ═══ 2. Entender: planos y personas ═════════════════════════════════════════

def _firma(caras: list[tuple[float, float]]) -> tuple:
    return tuple(sorted(round(cx, 1) for cx, _ in caras))


def planos(caras: list[list[tuple[float, float]]]) -> list[tuple[int, int]]:
    """Índices (desde, hasta) de cada plano: cambia el conjunto de caras y se sostiene."""
    n = len(caras)
    if n == 0:
        return []
    salida, ini, actual = [], 0, _firma(caras[0])
    i = 1
    while i < n:
        f = _firma(caras[i])
        if f != actual and all(_firma(caras[j]) == f for j in range(i, min(i + PERSISTENCIA, n))):
            salida.append((ini, i))
            ini, actual = i, f
        i += 1
    salida.append((ini, n))
    return salida


def personas(caras: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    """Las personas de un plano: grupos estables de caras, como (centro_x, ancho)."""
    import numpy as np
    todas = sorted((cx, w) for cuadro in caras for cx, w in cuadro)
    grupos: list[list[tuple[float, float]]] = []
    for cx, w in todas:
        if grupos and abs(cx - grupos[-1][-1][0]) < MISMA_PERSONA:
            grupos[-1].append((cx, w))
        else:
            grupos.append([(cx, w)])
    minimo = max(1, int(0.4 * len(caras)))
    return [(float(np.median([c for c, _ in g])), float(np.median([w for _, w in g])))
            for g in grupos if len(g) >= minimo]


# ═══ 3. Decidir: foco y recorte de cada plano ═══════════════════════════════

def _ancho_recorte(recorte: float, ancho: int, alto: int) -> float:
    """Qué fracción del ancho de la fuente ocupa un recorte de esa proporción."""
    return min(1.0, recorte * alto / ancho)


def _foco(centro: float, ancho_recorte: float) -> float:
    """`foco_x` del motor: posición del recorte dentro del margen que sobra, 0..1."""
    if ancho_recorte >= 1.0:
        return 0.5
    return min(1.0, max(0.0, (centro - ancho_recorte / 2) / (1 - ancho_recorte)))


def decidir(gente: list[tuple[float, float]], ancho: int, alto: int) -> tuple[float, float, str]:
    """(foco_x, recorte, motivo) para un plano con esas personas."""
    if not gente:
        return 0.5, RECORTE_BASE, "sin caras"
    if len(gente) == 1:
        cx, _ = gente[0]
        return _foco(cx, _ancho_recorte(RECORTE_BASE, ancho, alto)), RECORTE_BASE, f"una cara en x={cx:.2f}"
    izq = min(cx - w * AIRE for cx, w in gente)
    der = max(cx + w * AIRE for cx, w in gente)
    if der - izq <= _ancho_recorte(RECORTE_MAXIMO, ancho, alto):
        recorte = max(RECORTE_BASE, min(RECORTE_MAXIMO, (der - izq) * ancho / alto))
        return (_foco((izq + der) / 2, _ancho_recorte(recorte, ancho, alto)), round(recorte, 3),
                f"{len(gente)} caras, entran todas")
    cx, _ = max(gente, key=lambda p: p[1])
    return (_foco(cx, _ancho_recorte(RECORTE_BASE, ancho, alto)), RECORTE_BASE,
            f"{len(gente)} caras, no entran: la más grande en x={cx:.2f}")


def _ventana(s: dict, ancho: int, alto: int) -> tuple[float, float]:
    cw = _ancho_recorte(s["recorte"], ancho, alto)
    x0 = (1 - cw) * s["foco_x"]
    return x0, x0 + cw


def _contiene(a: dict, b: dict, ancho: int, alto: int) -> bool:
    ia, fa = _ventana(a, ancho, alto)
    ib, fb = _ventana(b, ancho, alto)
    return ia - 0.03 <= ib and fb <= fa + 0.03


def fusionar(subs: list[dict], ancho: int, alto: int) -> list[dict]:
    """Vecinos con el mismo encuadre se juntan; un plano corto sólo si el vecino lo contiene."""
    salida: list[dict] = []
    for s in subs:
        if salida and abs(salida[-1]["foco_x"] - s["foco_x"]) < 0.05 \
                and abs(salida[-1]["recorte"] - s["recorte"]) < 0.02:
            salida[-1]["hasta"] = s["hasta"]
            continue
        if salida and s["hasta"] - s["desde"] < PLANO_CORTO and _contiene(salida[-1], s, ancho, alto):
            salida[-1]["hasta"] = s["hasta"]
            continue
        salida.append(dict(s))
    return salida


def subtramos(caras: list[list[tuple[float, float]]], desde: float, hasta: float,
              ancho: int, alto: int) -> list[dict]:
    """De las caras por cuadro a los sub-tramos, en tiempo del material original."""
    if not caras:
        return []
    subs = []
    for a, b in planos(caras):
        foco, recorte, motivo = decidir(personas(caras[a:b]), ancho, alto)
        subs.append({"desde": desde + a / FPS, "hasta": desde + b / FPS,
                     "foco_x": round(foco, 3), "recorte": recorte, "motivo": motivo})
    subs = fusionar(subs, ancho, alto)
    # el último termina exactamente donde terminaba el tramo, no en un múltiplo del muestreo
    subs[-1]["hasta"] = hasta
    subs[0]["desde"] = desde
    return [{**s, "desde": round(s["desde"], 3), "hasta": round(s["hasta"], 3)} for s in subs]


# ═══ 4. Aplicar a un guion ══════════════════════════════════════════════════

def aplicar(tramos: list[dict], base) -> tuple[list[dict], list[str]]:
    """Los tramos del guion, partidos por plano y con su encuadre. Y los avisos.

    Sólo toca los tramos apaisados que no traen ya un `foco_x` o un `recorte`
    escritos a mano: si alguien miró el material y dijo dónde encuadrar, eso
    manda. Todo lo demás del tramo (velocidad, audio, lo que sea) se copia
    a cada pedazo.
    """
    if not disponible():
        return tramos, ["encuadre automático no disponible (falta OpenCV o el modelo): sale centrado"]
    from . import analisis
    base = Path(base)
    salida, avisos, fichas = [], [], {}
    for t in tramos:
        arch = (t.get("archivo") or "").strip()
        ruta = base / arch
        if not arch or not ruta.exists() or t.get("tipo") == "placa" \
                or "foco_x" in t or "recorte" in t or t.get("encuadre") == "marco":
            salida.append(t)
            continue
        if arch not in fichas:
            try:
                fichas[arch] = analisis.sondear(ruta)
            except Exception as e:                           # noqa: BLE001
                log.warning("encuadre: no pude medir %s (%s)", arch, e)
                fichas[arch] = None
        ficha = fichas[arch]
        if not ficha or not ficha.get("ancho") or ficha["ancho"] <= ficha["alto"]:
            salida.append(t)                                 # vertical o cuadrado: nada que encuadrar
            continue
        desde = float(t.get("desde", 0))
        hasta = float(t.get("hasta", desde))
        if hasta - desde <= 0:
            salida.append(t)
            continue
        try:
            caras = caras_de(ruta, desde, hasta, int(ficha["ancho"]), int(ficha["alto"]))
        except Exception as e:                               # noqa: BLE001
            log.warning("encuadre: no pude mirar %s (%s); sale centrado", arch, e)
            avisos.append(f"no pude mirar las caras de {arch}: sale centrado")
            salida.append(t)
            continue
        subs = subtramos(caras, desde, hasta, int(ficha["ancho"]), int(ficha["alto"]))
        if not subs or all(s["motivo"] == "sin caras" for s in subs):
            salida.append(t)
            continue
        for s in subs:
            pedazo = {k: v for k, v in t.items()}
            pedazo.update({"desde": s["desde"], "hasta": s["hasta"],
                           "foco_x": s["foco_x"], "recorte": s["recorte"]})
            salida.append(pedazo)
        log.info("encuadre de %s %.1f–%.1f: %s", arch, desde, hasta,
                 " · ".join(f"{s['desde']:.1f}-{s['hasta']:.1f} {s['motivo']}" for s in subs))
    return salida, avisos
