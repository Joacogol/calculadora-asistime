#!/usr/bin/env python3
"""Mete la precarga del modelo de transcripción en el Dockerfile del worker.

    python3 herramientas/hornear-modelo.py

## Por qué esto es un script y no una instrucción

El `Dockerfile` **no está en este repo**: vive sólo en `~/worker`, así que la
línea que hace falta estuvo escrita en `DESPLEGAR.md` desde el principio, para
pegarla a mano. El 1/9/2026 se descubrió que nunca se había pegado: el modelo
se venía bajando de HuggingFace en cada corrida desde siempre.

Con `small` eso costaba 464 MB y unos segundos — molesto, invisible, nadie lo
notó. Con `medium` son 1,5 GB, y en Cloud Run **el disco del contenedor es
memoria**: esos 1,5 GB salen del límite del job antes de empezar a trabajar.
Sumados a los 2,1 GiB del modelo cargado no entraban en los 4 GiB que había, y
el reel se colgaba sin escribir un error en ningún lado.

Una instrucción que hay que acordarse de seguir no es una instrucción, es una
apuesta. Ésta se perdió durante semanas sin que nadie se enterara. Por eso
ahora es un comando que se corre y dice qué hizo.

Es idempotente: si ya está, no toca nada y lo dice.
"""
import pathlib
import shutil
import sys

#: Va ANTES de `COPY . .` a propósito. Docker invalida todas las capas que
#: siguen a una que cambió; puesto después del código, cada cambio de una línea
#: de Python volvería a bajar 1,5 GB al construir la imagen.
BLOQUE = '''# Precarga el modelo de transcripción. El contenedor es efímero: sin esto el
# modelo se baja de HuggingFace en CADA corrida. Con `medium` son 1,5 GB, y en
# Cloud Run el disco del contenedor ES MEMORIA, así que sin esta línea el job
# se queda sin memoria en vez de tardar un poco más.
#
# `HF_HOME` explícito no es adorno: sin él la caché queda en el $HOME del
# usuario que corrió el RUN, y si el job corre con otro usuario no la puede
# leer — se baja igual y no se entera nadie.
ENV HF_HOME=/opt/modelos
RUN python -c "from faster_whisper import WhisperModel; \\
      WhisperModel('medium', device='cpu', compute_type='int8')" \\
    && chmod -R a+rX /opt/modelos

'''


def main() -> int:
    ruta = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                        else pathlib.Path.home() / "worker" / "Dockerfile")
    if not ruta.exists():
        print(f"✗ No encuentro {ruta}")
        print("  Si tu worker está en otro lado, pasale la ruta:")
        print("    python3 herramientas/hornear-modelo.py /ruta/al/Dockerfile")
        return 1

    texto = ruta.read_text()
    if "WhisperModel" in texto:
        print("✓ El Dockerfile ya precarga el modelo. No toco nada.")
        for n, l in enumerate(texto.splitlines(), 1):
            if "WhisperModel" in l:
                print(f"   línea {n}: {l.strip()}")
        return 0

    lineas = texto.splitlines(keepends=True)
    donde = next((i for i, l in enumerate(lineas) if l.strip() == "COPY . ."), None)
    if donde is None:
        # No se inventa un lugar: el bloque necesita que `faster-whisper` ya
        # esté instalado, y eso lo garantiza el orden del archivo, no el azar.
        print("✗ No encontré la línea «COPY . .» en el Dockerfile, que es")
        print("  donde tiene que ir justo antes. No lo toco.")
        return 1

    shutil.copy(ruta, str(ruta) + ".antes")
    lineas.insert(donde, BLOQUE)
    ruta.write_text("".join(lineas))
    print(f"✓ Listo: la precarga de `medium` quedó antes de la línea {donde + 1}.")
    print(f"  Copia de seguridad en {ruta}.antes")
    print()
    print("  Ahora desplegá:  cd ~/worker && ./desplegar-chat.sh")
    print("  Ese build va a tardar más que de costumbre —una sola vez—,")
    print("  porque la imagen se lleva el modelo adentro.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
