"""Prueba el revisor de piezas contra fallas fabricadas a propósito.

    python3 herramientas/probar-revisor.py

── Por qué se fabrican los casos ───────────────────────────────────────────

El revisor nació de cuatro piezas rotas de verdad, y contra esas cuatro se
midió antes de escribir esta prueba. Pero esos archivos son de un pedido
puntual y no viven en el repo: una prueba que dependa de ellos no la puede
correr nadie más. Así que acá cada falla se FABRICA con ffmpeg, y los números
que se esperan son los que dieron los archivos de verdad.

Lo medido sobre los reels reales del 1/9/2026, que es de dónde salen los
umbrales:

    v50/final.mp4      1080×1920, sin pista de audio     → mudo
    v5e/pieza.mp4      1080×1920, sin pista de audio     → mudo
    encuadre-fal.mp4   1080×1920, audio a −22,2 dB       → nada que decir
    vfal/fal.mp4       768×1024                          → mal encuadrado
    rótulo negro       16 clavado durante 2,7 s          → negro en el medio
    fundido de salida  pasa por 64, 40 y 16              → nada que decir
    imagen de verdad   nunca bajó de 82                  → nada que decir
    5 placas del carr. desvío entre 14,9 y 50,3          → nada que decir

El caso que más importa es el ÚLTIMO de la lista de video: el fundido final
es negro a propósito. Si el revisor lo confunde con una falla, avisa en todas
las piezas, y un aviso que aparece siempre se deja de leer. Por eso hay dos
pruebas de negro y una es que NO diga nada.
"""
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from motor.revisar import en_una_linea, revisar_imagen, revisar_video  # noqa: E402

fallos = 0


def ok(cond, que, detalle=None):
    global fallos
    if cond:
        print("  ✓", que)
    else:
        fallos += 1
        print("  ✗", que, "" if detalle is None else repr(detalle))


def ffmpeg(*args):
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, args)],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("ffmpeg falló: " + r.stderr[-800:])


def dice(problemas, palabra):
    """Si alguno de los avisos habla de eso."""
    return any(palabra in p for p in problemas)


tmp = pathlib.Path(tempfile.mkdtemp(prefix="revisor-"))

# ── El material ──────────────────────────────────────────────────────────
#
# Una pieza sana: 1080×1920, diez segundos, con imagen que se mueve y con
# sonido. Todo lo demás son variantes rotas de ésta, así que si el revisor
# habla de la sana, está hablando de más.
sana = tmp / "sana.mp4"
ffmpeg("-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30:duration=10",
       "-f", "lavfi", "-i", "sine=frequency=440:duration=10",
       "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
       "-c:a", "aac", "-shortest", sana)

muda = tmp / "muda.mp4"
ffmpeg("-i", sana, "-an", "-c:v", "copy", muda)

silenciosa = tmp / "silenciosa.mp4"
ffmpeg("-i", sana, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
       "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
       "-shortest", silenciosa)

chica = tmp / "768x1024.mp4"
ffmpeg("-i", sana, "-vf", "scale=768:1024", "-c:v", "libx264",
       "-preset", "ultrafast", "-crf", "30", "-c:a", "copy", chica)

# Un rótulo opaco tapando el video entero, que es exactamente lo que pasó.
rotulo = tmp / "rotulo.mp4"
ffmpeg("-i", sana, "-vf",
       "drawbox=x=0:y=0:w=1080:h=1920:color=black@1:t=fill:"
       "enable='between(t,4,6.5)'",
       "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
       "-c:a", "copy", rotulo)

# El fundido de salida que pone el montaje. Es negro y es correcto.
fundido = tmp / "fundido.mp4"
ffmpeg("-i", sana, "-vf", "fade=t=out:st=9.5:d=0.5",
       "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
       "-c:a", "copy", fundido)

print("\n■ Una pieza sana no da nada que decir")
#
# Esta es la prueba que sostiene a todas las demás. Un revisor que avisa de
# algo en cada pieza es ruido, y el ruido se ignora entero: se pierden también
# los avisos que valían.
ok(revisar_video(sana) == [], "callado", revisar_video(sana))

print("\n■ El reel mudo — la falla que motivó todo")
#
# El 1/9/2026 salió un reel sin una sola pista de audio y quedó marcado
# «listo». No dio ningún error: el archivo existía, duraba lo que tenía que
# durar y pesaba lo que tenía que pesar.
p = revisar_video(muda)
ok(dice(p, "SIN SONIDO"), "lo dice", p)
ok(len(p) == 1, "y no dice nada más", p)

print("\n■ Una pista muda es peor que ninguna")
#
# Desde afuera se ve mejor —el archivo declara que tiene audio— así que es
# más difícil de encontrar mirando.
p = revisar_video(silenciosa)
ok(dice(p, "silencio"), "lo dice", p)

print("\n■ Un video que se entrega mudo a propósito no se marca")
ok(revisar_video(muda, con_audio=False) == [],
   "con con_audio=False se calla", revisar_video(muda, con_audio=False))

print("\n■ El video de fal, entregado como pieza")
#
# fal devuelve 768×1024 y eso está BIEN como material. Lo que está mal es
# subirlo así: en el feed se ve estirado o cortado. Por eso el mismo archivo
# da un aviso como pieza y ninguno como material.
p = revisar_video(chica)
ok(dice(p, "768×1024"), "avisa el encuadre como pieza", p)
ok(revisar_video(chica, ancho=768, alto=1024) == [],
   "y no avisa nada como material",
   revisar_video(chica, ancho=768, alto=1024))

print("\n■ El rótulo negro tapando el video")
p = revisar_video(rotulo)
ok(dice(p, "en negro"), "lo encuentra", p)
ok(any("2." in x or "3." in x for x in p if "en negro" in x),
   "y dice cuántos segundos", p)

print("\n■ El fundido de salida NO es una falla")
#
# El caso que hace la diferencia entre un revisor que se lee y uno que se
# ignora. El fundido es negro, dura medio segundo y lo pone el montaje.
ok(revisar_video(fundido) == [], "no dice nada", revisar_video(fundido))

print("\n■ Si no puede medir, se calla")
#
# Regla 3. Un archivo que no se abre no es un problema DE LA PIEZA, y un
# aviso inventado enseña a desconfiar de los que sí valen.
ok(revisar_video(tmp / "no-existe.mp4") == [], "un archivo que no está")
(tmp / "basura.mp4").write_bytes(b"esto no es un video")
ok(revisar_video(tmp / "basura.mp4") == [], "un archivo que no es video")

# ── Las placas ───────────────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw
except ImportError:
    print("\n(sin Pillow: no se prueban las placas)")
else:
    import random
    random.seed(7)

    # Una placa con foto y texto: mucha variación de brillo, como las cinco
    # del carrusel de verdad (desvío entre 14,9 y 50,3).
    llena = Image.new("RGB", (1080, 1350))
    px = llena.load()
    for y in range(0, 1350, 3):
        for x in range(0, 1080, 3):
            v = random.randint(0, 255)
            for dy in range(3):
                for dx in range(3):
                    if y + dy < 1350 and x + dx < 1080:
                        px[x + dx, y + dy] = (v, v, v)
    llena_p = tmp / "llena.png"
    llena.save(llena_p)

    # Una placa que salió vacía: la plantilla no cargó, la foto no llegó, y
    # el archivo igual existe. Nadie la mira hasta que está publicada.
    vacia_p = tmp / "vacia.png"
    Image.new("RGB", (1080, 1350), (11, 11, 13)).save(vacia_p)

    # Una placa tipográfica sobre negro: poco color, mucho contraste. Es
    # legítima y no se marca.
    tipo = Image.new("RGB", (1080, 1350), (11, 11, 13))
    ImageDraw.Draw(tipo).rectangle([80, 600, 1000, 760], fill=(240, 240, 240))
    tipo_p = tmp / "tipografica.png"
    tipo.save(tipo_p)

    print("\n■ Una placa con foto y texto no da nada que decir")
    ok(revisar_imagen(llena_p, ancho=1080, alto=1350) == [],
       "callado", revisar_imagen(llena_p, ancho=1080, alto=1350))

    print("\n■ Una placa vacía es un rectángulo de un color")
    p = revisar_imagen(vacia_p, ancho=1080, alto=1350)
    ok(dice(p, "vacía"), "lo dice", p)

    print("\n■ Una placa tipográfica sobre negro es legítima")
    ok(revisar_imagen(tipo_p, ancho=1080, alto=1350) == [],
       "no se marca", revisar_imagen(tipo_p, ancho=1080, alto=1350))

    print("\n■ Una placa con la medida cambiada")
    p = revisar_imagen(llena_p, ancho=1080, alto=1920)
    ok(dice(p, "1080×1350"), "dice la que salió y la que iba", p)

    print("\n■ Una imagen que no se abre")
    (tmp / "basura.png").write_bytes(b"tampoco es una imagen")
    ok(revisar_imagen(tmp / "basura.png", ancho=1080, alto=1350) == [],
       "se calla")

print("\n■ Cómo se escribe en la fila")
ok(en_una_linea([]) == "", "sin problemas no escribe nada", en_una_linea([]))
linea = en_una_linea(["uno", "dos"])
ok(linea.startswith("revisión de la pieza —") and " · " in linea,
   "y con problemas queda en una sola línea", linea)

subprocess.run(["rm", "-rf", str(tmp)])
print(f"\n✗ {fallos} fallo(s)\n" if fallos else "\n✓ todo bien\n")
sys.exit(1 if fallos else 0)
