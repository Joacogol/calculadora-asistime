"""Cambiarle cosas a un reel ya armado, sin rehacerlo.

Este módulo existe por una asimetría que tardó en verse: **acertar es caro y
corregir tendría que ser barato, y era al revés.**

Armar un reel con subtítulos automáticos cuesta escuchar el audio entero,
partirlo en frases que respiren, medir dónde hay silencio y escribir un hook.
Cuando de veintidós frases hay dos mal transcritas, lo único que hacía falta
era cambiar dos textos. Pero como el motor tiraba lo que había resuelto, la
única salida era rehacerlo entero: volver a escuchar —y volver a equivocarse
igual, porque el modelo es determinista con el mismo audio— y de paso tirar las
veinte frases que estaban bien.

Con el guion armado guardado (ver `motor.video.desde_guion`), corregir es
editar un JSON. Este módulo es esa edición, y lo que aporta no son los cambios
de texto —eso es un `replace`— sino **los cambios de estructura**.

## Por qué sacar un tramo no es sacar un tramo

Los subtítulos viven en el reloj del REEL, no en el del clip. Si el reel tiene
diez tramos y se saca el tercero, todo lo que venía después se adelanta lo que
duraba ése. Borrar el tramo y nada más deja veintidós frases apareciendo tarde,
cada vez más desfasadas hasta el final: el reel sale peor que antes de
corregirlo, y el que pidió el cambio no tiene forma de saber por qué.

Así que acá, cuando se toca la estructura, las frases se recalculan: cada una
se ata al tramo donde suena, y viaja con él. Las que sonaban en un tramo que ya
no está se van con él, porque son lo que se dijo en un pedazo que se sacó.
"""
from __future__ import annotations

import copy
import logging

from .guion import duracion_tramo

log = logging.getLogger(__name__)


class CambioImposible(Exception):
    """Lo pedido no se puede hacer sobre este reel, y se dice por qué.

    Se avisa ANTES de dibujar. Un pedido que no se puede cumplir tiene que
    fallar en el segundo cero con una frase en castellano, no a los dos minutos
    con un video mal hecho.
    """


def _texto(v) -> str:
    return str(v if v is not None else "").strip()


def _indices(pedidos, cuantos: int, que: str) -> list[int]:
    """Convierte números de 1 a N —como los ve la persona— en índices reales."""
    fuera = [n for n in pedidos if not isinstance(n, int) or not 1 <= n <= cuantos]
    if fuera:
        cuales = ", ".join(str(n) for n in fuera)
        raise CambioImposible(
            f"no existe {que} número {cuales}: este reel tiene {cuantos}, "
            f"del 1 al {cuantos}")
    return [n - 1 for n in pedidos]


def _reemplazar(texto: str, pares: list[dict]) -> str:
    for p in pares:
        de, a = _texto(p.get("de")), _texto(p.get("a"))
        if de:
            texto = texto.replace(de, a)
    return texto


def _reubicar(armado: dict, orden: list[int]) -> dict:
    """Rearma el guion con los tramos en `orden` (índices), moviendo las frases.

    `orden` puede dejar tramos afuera: eso es sacarlos.

    La cuenta es simple y hay que hacerla igual. Cada tramo ocupa un pedazo del
    reloj del reel; una frase pertenece al tramo donde cae su punto medio —el
    medio y no el principio, porque una frase puede empezar un pelo antes del
    corte y sonar entera en el tramo siguiente—; y al reordenar, la frase se
    mueve con su tramo conservando el lugar que tenía adentro.
    """
    tramos = armado.get("tramos") or []
    duras = [duracion_tramo(t) for t in tramos]

    # Dónde empieza cada tramo en el reel de ahora.
    arranca, suma = [], 0.0
    for d in duras:
        arranca.append(suma)
        suma += d

    # Cada frase, atada a su tramo y al lugar que ocupa adentro.
    atadas: dict[int, list[dict]] = {i: [] for i in range(len(tramos))}
    huerfanas = 0
    for s in (armado.get("subtitulos") or []):
        desde, hasta = float(s["desde"]), float(s["hasta"])
        medio = (desde + hasta) / 2
        cual = None
        for i, (a, d) in enumerate(zip(arranca, duras)):
            if a <= medio < a + d:
                cual = i
                break
        if cual is None:                       # cae en la placa de cierre, o después
            huerfanas += 1
            continue
        atadas[cual].append({**s,
                             "desde": desde - arranca[cual],
                             "hasta": hasta - arranca[cual]})
    if huerfanas:
        log.info("%d frases quedaban fuera de todo tramo y no se remapean", huerfanas)

    # Y se rearma con el orden nuevo.
    nuevos, frases, reloj = [], [], 0.0
    for i in orden:
        nuevos.append(tramos[i])
        for s in atadas[i]:
            frases.append({**s,
                           "desde": round(reloj + s["desde"], 3),
                           "hasta": round(reloj + s["hasta"], 3)})
        reloj += duras[i]

    return {**armado, "tramos": nuevos, "subtitulos": frases}


def retocar(armado: dict, cambios: dict) -> tuple[dict, list[str]]:
    """El guion armado con los cambios aplicados, y qué se hizo, en castellano.

    Los cambios se aplican en un orden pensado, no en el que vengan:

    1. **Reemplazos de texto**, que valen para todas las frases a la vez.
    2. **Frases por número**, que son más específicas y por eso pisan lo
       anterior: si alguien reemplaza una palabra Y además reescribe la frase 4
       entera, lo que quiso decir de la 4 es lo segundo.
    3. **Hook y cierre.**
    4. **Estructura** (sacar tramos, reordenar), al final y sola, porque es la
       única que mueve los tiempos: hacerla antes obligaría a renumerar las
       frases en el medio y a que quien pide el cambio adivine con qué
       numeración le estamos hablando.
    """
    g = copy.deepcopy(armado)
    subs = list(g.get("subtitulos") or [])
    hecho: list[str] = []

    # ── 1 · reemplazos que valen para todo el reel ────────────────────────
    pares = [p for p in (cambios.get("reemplazar") or [])
             if isinstance(p, dict) and _texto(p.get("de"))]
    if pares:
        tocadas = 0
        for s in subs:
            antes = s.get("texto", "")
            s["texto"] = _reemplazar(antes, pares)
            tocadas += s["texto"] != antes
        # El hook y el cierre también se escriben con las mismas palabras: si
        # el club se llama «Boss Padel», se llama así en los tres lados.
        otros = []
        for campo, como in (("hook", "el hook"), ("cierre", "el cierre")):
            if isinstance(g.get(campo), str):
                antes = g[campo]
                g[campo] = _reemplazar(antes, pares)
                if g[campo] != antes:
                    otros.append(como)
        cuales = ", ".join(f"«{_texto(p['de'])}» → «{_texto(p.get('a'))}»" for p in pares)

        # Se cuenta TODO lo que cambió, no sólo las frases. Contar de menos
        # sería peor que no contar: el mensaje diría «no cambió nada» cuando
        # cambió el hook, y quien lo lea va a creer que el sistema le mintió.
        donde = []
        if tocadas:
            donde.append(f"{tocadas} {'frase' if tocadas == 1 else 'frases'}")
        donde += otros
        if donde:
            hecho.append(f"{cuales} (en {', '.join(donde)})")
        else:
            # Y si de verdad no cambió nada, también se dice. Si no, la persona
            # ve «listo», el error sigue ahí, y no entiende por qué.
            hecho.append(f"{cuales} — no lo encontré en ningún lado, "
                         f"no cambió nada")

    # ── 2 · frases por número ─────────────────────────────────────────────
    porcion = [x for x in (cambios.get("subtitulos") or []) if isinstance(x, dict)]
    if porcion:
        idx = _indices([x.get("n") for x in porcion], len(subs), "la frase")
        borrar = set()
        for i, x in zip(idx, porcion):
            nuevo = _texto(x.get("texto"))
            if nuevo:
                subs[i] = {**subs[i], "texto": nuevo}
                hecho.append(f"frase {i+1}: «{nuevo}»")
            else:
                # Texto vacío es «sacá esta frase». Es lo que uno espera al
                # borrar el contenido de un renglón.
                borrar.add(i)
                hecho.append(f"frase {i+1}: sacada")
        subs = [s for i, s in enumerate(subs) if i not in borrar]

    g["subtitulos"] = subs

    # ── 3 · hook y cierre ─────────────────────────────────────────────────
    for campo, como in (("hook", "el hook"), ("cierre", "la placa de cierre")):
        if campo in cambios:
            nuevo = _texto(cambios[campo])
            g[campo] = nuevo
            hecho.append(f"{como}: «{nuevo}»" if nuevo else f"{como}: sacada")

    # ── 4 · estructura ────────────────────────────────────────────────────
    tramos = g.get("tramos") or []
    quitar = _indices(list(cambios.get("quitar") or []), len(tramos), "el tramo")
    orden_pedido = cambios.get("orden")
    if orden_pedido:
        orden = _indices(list(orden_pedido), len(tramos), "el tramo")
        if len(set(orden)) != len(orden):
            raise CambioImposible(
                "el orden repite algún tramo: cada uno tiene que aparecer una "
                "sola vez")
    else:
        orden = list(range(len(tramos)))

    orden = [i for i in orden if i not in set(quitar)]
    if not orden:
        raise CambioImposible(
            "así no queda ningún tramo y un reel sin video no es un reel")

    if orden != list(range(len(tramos))):
        antes = len(g.get("subtitulos") or [])
        g = _reubicar(g, orden)
        if quitar:
            hecho.append("saqué " + ("el tramo " if len(quitar) == 1 else "los tramos ")
                         + ", ".join(str(i + 1) for i in sorted(quitar)))
        if orden_pedido:
            hecho.append("cambié el orden de los tramos")
        perdidas = antes - len(g.get("subtitulos") or [])
        if perdidas > 0:
            hecho.append(f"se fueron {perdidas} "
                         f"{'frase' if perdidas == 1 else 'frases'} "
                         f"que sonaban en lo que sacaste")

    if not hecho:
        raise CambioImposible(
            "no me pediste ningún cambio que pueda hacer sobre este reel")
    return g, hecho
