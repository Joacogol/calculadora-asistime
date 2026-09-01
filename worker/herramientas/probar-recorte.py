#!/usr/bin/env python3
"""Prueba que el recorte de tiempos muertos no se coma lo que se dice.

    python3 herramientas/probar-recorte.py

Se arma un audio de laboratorio con ffmpeg, así la prueba corre en segundos, no
depende de ningún material y da siempre el mismo resultado.

## Por qué existe

El 31/8/2026 salió un reel donde alguien pregunta «¿qué superpoder elegirías?»
y la respuesta no está. No se cortó mal por un decimal: **desaparecieron seis
segundos y medio con nueve palabras adentro**, y el video quedó con la pregunta
hecha y el remate colgando.

La causa no fue la que parecía. La primera lectura fue que la respuesta se
había dicho más flojo y la energía no la había oído; medida, se oye igual de
fuerte que todo lo demás. Lo que pasó es más sutil: Bruno contesta a las
corridas —pregunta, respuesta, repregunta— con pausas cortas en el medio, así
que quedaron **cinco islas de habla de unos 0,75 s cada una**. El mínimo para
que un pedazo cuente como tramo era 0,8 s. Ninguna llegaba, así que se
descartaron las cinco: cada descarte defendible por separado, y el conjunto un
desastre.

Por eso el libreto de abajo son ráfagas cortas y no bloques largos. Un audio de
laboratorio con dos segundos seguidos de habla **no reproduce este error** —se
probó, y pasaba también con el código roto—, y un test que no falla contra el
bug que dice cubrir es peor que no tener test.

Esta prueba fija las dos mitades del contrato, que tiran para lados opuestos:

1. **Nunca se pierde una palabra**, ni aunque venga en ráfagas más cortas que
   el mínimo de un tramo.
2. **Se sigue recortando** el silencio de verdad — si no, la prueba pasaría
   trivialmente con un recorte que no recorta nada.
"""
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from motor import analisis as A                              # noqa: E402

#: El libreto del audio de laboratorio: (desde, hasta, volumen en dB, qué es).
#:
#: El medio es el caso de Bruno: cuatro ráfagas de 0,7 s separadas por pausas
#: de 0,6 s. Cada ráfaga sola es más corta que `min_tramo`; juntas son un
#: diálogo entero. A los costados van dos bloques largos, para que el recorte
#: tenga algo obvio que conservar, y dos silencios de verdad de dos segundos,
#: que son lo que sí se tiene que ir.
LIBRETO = [
    (0.0,  2.0,  -8,  "bloque largo", True),
    (2.0,  4.0, -90,  "silencio de verdad", False),
    (4.0,  4.7,  -8,  "ráfaga corta", True),
    (4.7,  5.3, -90,  "pausa de diálogo", False),
    (5.3,  6.0,  -8,  "ráfaga corta", True),
    (6.0,  6.6, -90,  "pausa de diálogo", False),
    (6.6,  7.3,  -8,  "ráfaga corta", True),
    (7.3,  7.9, -90,  "pausa de diálogo", False),
    (7.9,  8.6,  -8,  "ráfaga corta", True),
    (8.6, 10.6, -90,  "silencio de verdad", False),
    (10.6, 12.6, -8,  "bloque largo", True),
]


def _armar(destino: pathlib.Path) -> None:
    partes, filtros, etiquetas = [], [], []
    for i, (a, b, vol, _, _) in enumerate(LIBRETO):
        partes += ["-f", "lavfi", "-t", f"{b - a}",
                   "-i", f"sine=frequency={220 + i * 40}:sample_rate=48000"]
        filtros.append(f"[{i}:a]volume={vol}dB[a{i}]")
        etiquetas.append(f"[a{i}]")
    cadena = ";".join(filtros) + ";" + "".join(etiquetas) + \
        f"concat=n={len(LIBRETO)}:v=0:a=1[out]"
    largo = LIBRETO[-1][1]
    # Lleva una pista de video negra porque `sondear` mide videos, no audios
    # sueltos: es un módulo de reels. Pesa nada y ahorra un caso especial.
    subprocess.run(["ffmpeg", "-v", "error", "-y", *partes,
                    "-f", "lavfi", "-t", str(largo),
                    "-i", "color=c=black:s=64x64:r=10",
                    "-filter_complex", cadena,
                    "-map", "[out]", "-map", f"{len(LIBRETO)}:v",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", str(destino)], check=True)


def _palabras():
    """Lo que «dijo» la transcripción: una palabra cada medio segundo."""
    ps = []
    for a, b, _, _, hay_voz in LIBRETO:
        if not hay_voz:
            continue
        t = a
        while t + 0.3 <= b:
            ps.append({"texto": f"p{len(ps)}", "desde": round(t, 2),
                       "hasta": round(t + 0.3, 2)})
            t += 0.35
    return ps


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        audio = pathlib.Path(tmp) / "laboratorio.mp4"
        _armar(audio)
        ps = _palabras()
        tramos = A.tramos_hablados(audio, palabras=ps)

        print("audio de laboratorio:")
        for a, b, vol, que, _ in LIBRETO:
            print(f"  {a:4.1f}–{b:4.1f}s  {vol:>4} dB  {que}")
        print("\nse queda:", " · ".join(f"{a:.2f}–{b:.2f}" for a, b in tramos))

        fallas = []

        # ── 1 · ninguna palabra puede desaparecer ────────────────────────
        perdidas = [p["texto"] for p in ps
                    if not any(a <= (p["desde"] + p["hasta"]) / 2 <= b
                               for a, b in tramos)]
        if perdidas:
            fallas.append(
                f"✗ se perdieron {len(perdidas)} palabras: {' '.join(perdidas)}\n"
                f"  Es el error del 31/8: se descartaron ráfagas de habla por "
                f"ser más cortas que `min_tramo`, una por una.")
        else:
            print(f"\n✓ las {len(ps)} palabras siguen estando, incluidas las "
                  f"de las ráfagas más cortas que el mínimo de un tramo")

        # ── 2 · y el silencio de verdad se sigue yendo ───────────────────
        #
        # Sin esto la prueba pasaría con un recorte que no recorta: la forma
        # más fácil de no perder una palabra es no cortar nunca.
        for a, b, _, que, hay_voz in LIBRETO:
            if hay_voz or que != "silencio de verdad":
                continue
            medio = (a + b) / 2
            if any(x <= medio <= y for x, y in tramos):
                fallas.append(
                    f"✗ el {que} de {a:.0f}–{b:.0f}s quedó adentro: el recorte "
                    f"dejó de recortar")
        if not any(f.startswith("✗ el silencio") for f in fallas):
            print("✓ los dos silencios de verdad se recortaron")

        if fallas:
            print("\n" + "\n".join(fallas))
            return 1
        print("\nrecorte OK")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
