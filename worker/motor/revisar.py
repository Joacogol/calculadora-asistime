"""Mirar la pieza terminada antes de entregarla.

── Por qué existe ──────────────────────────────────────────────────────────

Porque el motor sabe producir y no sabía si lo que produjo estaba bien.

El 1/9/2026 salieron cuatro piezas rotas y **las cuatro quedaron marcadas
«listo»**: un reel sin una sola pista de audio, un video estirado 33% de más
alto, un rótulo negro que tapaba el video en el medio, y un título que aparecía
recién al segundo. Ninguna dio error. Las cuatro las encontró una persona
mirando el archivo a mano.

En treinta días Boss pidió 76 piezas y 8 dieron error — un 10% que se ve. Las
que salen mal y se ven bien no las cuenta nadie, y son las peores: se publican.

Esto no reemplaza a alguien mirando la pieza. Lo que hace es que las fallas
BURDAS —las que se miden con un número y no admiten opinión— dejen de llegar al
feed sin que nadie las nombre.

── Tres reglas ─────────────────────────────────────────────────────────────

**1. No frena nada.** La pieza sale igual, siempre. En este punto el video ya
se generó y se pagó; retenerlo por un aviso cambia «una pieza con un problema»
por «ninguna pieza y la plata gastada». Lo que hace es ESCRIBIR lo que vio,
para que el chat lo diga antes de que alguien la suba.

**2. Sólo dice lo que puede medir.** Si el color de un titular queda feo, eso
es criterio y no va acá. Si el archivo no tiene audio, eso es un hecho. La
diferencia importa: una lista de avisos donde la mitad son opiniones se vuelve
ruido y se deja de leer a la tercera pieza.

**3. Si no puede medir, se calla.** Un `ffprobe` que no está, un archivo que no
se abre: eso NO es un problema de la pieza. Inventar un aviso cuando la
herramienta falló es peor que no revisar, porque enseña a desconfiar de los
avisos que sí valen.
"""
from __future__ import annotations

import json
import logging
import pathlib
import re
import subprocess

log = logging.getLogger(__name__)

#: Por debajo de esto un cuadro cuenta como negro. **No es cero, y ese fue el
#: primer error**: `YAVG` viene en la escala de video, donde el negro vale 16 y
#: no 0. Con el umbral en 12 nunca hubiera saltado nada — ni un rótulo opaco
#: tapando la pieza entera.
#:
#: Medido sobre los reels reales del 1/9/2026: un rótulo negro a pantalla
#: completa da 16 clavado; el fundido de salida pasa por 64, 40 y 16; la imagen
#: de verdad de esos cuatro videos nunca bajó de 82. Entre 16 y 82 no hay nada,
#: así que el umbral va cerca del piso: 20 deja pasar cualquier escena oscura
#: real y sigue atrapando el negro liso.
NEGRO = 20.0

#: Cuánto negro seguido es un problema. Un parpadeo de dos cuadros no se ve;
#: medio segundo en el medio de un reel de diez es un quinto de la pieza.
NEGRO_MAXIMO_SEG = 0.4

#: El fundido de salida es negro A PROPÓSITO —lo pone el montaje— así que el
#: último tramo no se mira. Es medio segundo de fundido más un margen.
FINAL_SIN_MIRAR_SEG = 0.9

#: Por debajo de esto la pista de audio existe pero no suena. Un reel con una
#: pista muda es lo mismo que uno sin pista, y desde afuera se ve mejor: hay
#: audio, dice el archivo.
SILENCIO_DB = -50.0


def _ejecutar(orden: list[str]) -> str | None:
    """La salida del comando, o None si no se pudo. Nunca levanta."""
    try:
        r = subprocess.run(orden, capture_output=True, text=True, timeout=120)
    except Exception as e:                                   # noqa: BLE001
        log.warning("no pude correr %s: %s", orden[0], e)
        return None
    return r.stdout if r.returncode == 0 else None


def _ficha(video: pathlib.Path) -> dict | None:
    salida = _ejecutar([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_streams", "-show_format", str(video)])
    if not salida:
        return None
    try:
        return json.loads(salida)
    except json.JSONDecodeError:
        return None


def _brillos(video: pathlib.Path, cada: int = 4) -> list[float] | None:
    """El brillo medio de un cuadro de cada `cada`, en orden."""
    salida = _ejecutar([
        "ffprobe", "-v", "error", "-f", "lavfi",
        "-i", f"movie={video},select='not(mod(n\\,{cada}))',signalstats",
        "-show_entries", "frame_tags=lavfi.signalstats.YAVG",
        "-of", "csv=p=0"])
    if salida is None:
        return None
    valores = []
    for linea in salida.split():
        for trozo in linea.split(","):
            try:
                valores.append(float(trozo))
            except ValueError:
                pass
    return valores or None


def _volumen(video: pathlib.Path) -> float | None:
    """El volumen medio en dB, o None si no hay pista o no se pudo medir."""
    try:
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-i", str(video),
             "-af", "volumedetect", "-f", "null", "/dev/null"],
            capture_output=True, text=True, timeout=120)
    except Exception:                                        # noqa: BLE001
        return None
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else None


def revisar_video(video: pathlib.Path, *,
                  ancho: int | None = 1080, alto: int | None = 1920,
                  con_audio: bool = True,
                  duracion: float | None = None) -> list[str]:
    """Qué tiene de malo esta pieza de video. Lista vacía = nada que decir.

    Cada expectativa se puede apagar, y no es por comodidad: un aviso falso
    cuesta más que un aviso que falta. A la tercera pieza que avisa algo que
    no es cierto, se dejan de leer todos.

    `ancho=None` para el material crudo, que sale con la medida que le dio el
    proveedor —fal devuelve 768×1024— y no con una que nosotros hayamos
    pedido: ahí no hay nada contra qué comparar.

    `con_audio=False` para lo que se entrega mudo a propósito.
    """
    problemas: list[str] = []
    ficha = _ficha(video)
    if not ficha:
        return problemas                                     # regla 3

    pistas = ficha.get("streams") or []
    v = next((s for s in pistas if s.get("codec_type") == "video"), None)
    a = next((s for s in pistas if s.get("codec_type") == "audio"), None)

    if not v:
        return ["el archivo no tiene imagen"]

    # ── La forma ────────────────────────────────────────────────────────
    #
    # Se compara con lo que la pieza DIJO que iba a ser, no con lo que parece
    # razonable. Un video de fal sale en 768×1024 y es correcto como material;
    # lo que está mal es entregarlo como reel sin encuadrarlo.
    if ancho and alto and (v.get("width"), v.get("height")) != (ancho, alto):
        problemas.append(
            f"salió en {v.get('width')}×{v.get('height')} y una pieza de "
            f"este tipo va en {ancho}×{alto}: si se sube así, se ve estirada "
            f"o cortada")

    # ── El sonido ───────────────────────────────────────────────────────
    if con_audio:
        if not a:
            problemas.append(
                "salió SIN SONIDO, sin ninguna pista de audio. En el feed un "
                "video mudo no se lee como una decisión: se lee como que algo "
                "se rompió")
        else:
            vol = _volumen(video)
            if vol is not None and vol < SILENCIO_DB:
                problemas.append(
                    f"tiene pista de audio pero está en silencio ({vol:.0f} dB): "
                    f"desde afuera se ve peor que no tener ninguna, porque el "
                    f"archivo dice que sí tiene")

    # ── El negro en el medio ────────────────────────────────────────────
    #
    # El caso que motivó todo: un rótulo opaco tapando el video entero durante
    # varios segundos. El archivo pesaba lo mismo, duraba lo mismo y no daba
    # ningún error.
    brillos = _brillos(video)
    dur = float(ficha.get("format", {}).get("duration") or 0) or duracion
    if brillos and dur and len(brillos) > 4:
        seg_por_muestra = dur / len(brillos)
        # El fundido final es negro a propósito: no se mira.
        mirar = max(1, len(brillos) - int(FINAL_SIN_MIRAR_SEG / seg_por_muestra))
        corrida = mayor = 0
        for y in brillos[:mirar]:
            corrida = corrida + 1 if y < NEGRO else 0
            mayor = max(mayor, corrida)
        negro = mayor * seg_por_muestra
        if negro > NEGRO_MAXIMO_SEG:
            problemas.append(
                f"hay {negro:.1f} segundos en negro en el medio del video, "
                f"tapando lo que se está mostrando")

    return problemas


def revisar_imagen(imagen: pathlib.Path, *,
                   ancho: int | None = None,
                   alto: int | None = None) -> list[str]:
    """Qué tiene de malo esta placa. Lista vacía = nada que decir.

    Dos cosas nada más, y las dos son hechos: que mida lo que tiene que medir,
    y que no sea un rectángulo de un solo color. Lo segundo es el modo de falla
    de un render que salió mal —la plantilla no cargó, la foto no llegó— y el
    archivo igual existe, pesa poco y nadie lo mira hasta que está publicado.

    La medida se compara sólo si se dice cuál era. Un diseño sale en 1080×1350,
    en 1080×1920 o en 1080×1080 según lo que se haya pedido, y comparar contra
    una medida inventada daría un aviso falso en dos de cada tres piezas.
    """
    problemas: list[str] = []
    try:
        from PIL import Image, ImageStat
    except Exception:                                        # noqa: BLE001
        return problemas                                     # regla 3

    try:
        with Image.open(imagen) as im:
            medidas = im.size
            gris = im.convert("L")
            desvio = ImageStat.Stat(gris).stddev[0]
    except Exception as e:                                   # noqa: BLE001
        log.warning("no pude abrir %s: %s", imagen, e)
        return problemas

    if ancho and alto and medidas != (ancho, alto):
        problemas.append(
            f"salió en {medidas[0]}×{medidas[1]} y tenía que salir en "
            f"{ancho}×{alto}")

    # Un desvío casi nulo quiere decir que todos los píxeles son parecidos: no
    # hay foto, ni texto, ni logo. Es un rectángulo. El umbral es bajo a
    # propósito —una placa tipográfica sobre negro tiene poco contraste global
    # y es legítima— así que esto sólo salta con una pieza de verdad vacía.
    if desvio < 3.0:
        problemas.append(
            "la placa salió prácticamente vacía: es casi un rectángulo de un "
            "solo color, sin foto ni texto visible")

    return problemas


#: Cuánta tinta puede tapar un dibujo DENTRO DE UNA ZONA antes de que sea un
#: problema. Se mide por zona y no sobre la pieza entera, y esa fue la primera
#: versión y estaba mal: la consola de DJ que cruzaba el pie de la story del
#: 3/9/2026 tapaba el 0,4% de la tinta total —nada— porque el titular aporta
#: miles de píxeles y el pie unos cientos. Mirado por zona, la misma consola
#: tapa el 12% del pie. El defecto era local y la medida tenía que serlo.
#:
#: Medido sobre esa pieza: la consola que cruza el pie hace desaparecer el 10%
#: de las marcas del pie; unas notas sueltas en el fondo, 0%; y un recuadro
#: puesto ATRÁS del titular, también 0%. Entre 0 y 10 no hay nada, así que el
#: umbral va cómodo en el medio.
TAPADO_MAXIMO = 0.05

#: Cuántos píxeles de tinta necesita una zona para que valga la pena juzgarla.
#: Una zona casi vacía da porcentajes enormes con cuatro píxeles.
TINTA_MINIMA = 150

#: Y cuántos tiene que tapar, en absoluto. Evita que el borde suavizado de una
#: forma que apenas roza una letra cuente como que la tapó.
TAPADO_MINIMO = 40

#: En cuántas zonas se parte la pieza. Seis por diez sobre 1080×1920 son
#: recuadros de 180×192: del tamaño de un logo o de una línea de pie, que es la
#: escala de lo que se quiere proteger.
ZONAS = (6, 10)

#: Debajo de esto un píxel no es un trazo sino fondo. Los degradados de marca
#: cambian de a poco entre píxel y píxel; una letra o un logo saltan de golpe.
BORDE = 28


def _tinta(im):
    """Máscara de lo que está DIBUJADO en la pieza: textos, logos, formas.

    Un degradé no es tinta aunque tenga color: cambia de a poco. Lo que se
    busca son los saltos bruscos, que es lo que hace una letra contra su
    fondo. Es la misma idea que usa cualquier detector de bordes y alcanza de
    sobra acá, donde no hay que reconocer nada: sólo saber dónde hay algo.
    """
    from PIL import ImageFilter
    return im.convert("L").filter(ImageFilter.FIND_EDGES).point(
        lambda v: 255 if v > BORDE else 0)


def _cuantos(mascara) -> int:
    return sum(mascara.point(lambda v: 1 if v else 0).convert("L").getdata())


def _donde(col: int, fila: int) -> str:
    """La zona en castellano: «abajo a la izquierda»."""
    cols, filas = ZONAS
    vertical = ("arriba" if fila < filas / 3 else
                "abajo" if fila >= filas * 2 / 3 else "en el medio")
    lado = ("a la izquierda" if col < cols / 3 else
            "a la derecha" if col >= cols * 2 / 3 else "al centro")
    return f"{vertical} {lado}"


def revisar_dibujo(con: pathlib.Path, sin: pathlib.Path) -> list[str]:
    """Qué se comió el dibujo de una pieza a medida.

    La comparación es exacta porque la pieza se renderiza dos veces: con el
    dibujo y sin él. Lo que cambió entre las dos imágenes ES el dibujo, sin
    tener que adivinar dónde lo puso nadie ni qué plantilla se usó. Y lo que
    importa no es que el dibujo ocupe lugar —para eso está— sino **que tape lo
    que la plantilla ya había dibujado**: el logo, el titular, el pie.

    Una capa `atras` da cero por construcción: queda detrás del texto, así que
    los píxeles del texto no cambian. Eso no es una casualidad afortunada, es
    la razón por la que la medida sirve: distingue «cubre» de «está detrás».

    Esto es un hecho y no una opinión, que es la regla 2 del módulo. Si el
    dibujo quedó feo, desbalanceado o fuera de clima, eso lo tiene que ver
    alguien mirando; acá sólo se dice qué quedó tapado.
    """
    problemas: list[str] = []
    try:
        from PIL import Image, ImageChops
    except Exception:                                        # noqa: BLE001
        return problemas                                     # regla 3
    try:
        with Image.open(con) as a, Image.open(sin) as b:
            a, b = a.convert("RGB"), b.convert("RGB")
            if a.size != b.size:
                return problemas
            ancho, alto = a.size
            # Lo que estaba dibujado y ya no está. La primera versión medía
            # «dónde cambió la imagen», y daba falso positivo con las capas de
            # atrás: un recuadro traslúcido detrás del titular cambia el fondo
            # que rodea cada letra, y el borde de la letra cambia con él,
            # aunque la letra siga perfectamente visible. Lo que importa no es
            # si algo cambió alrededor de la marca sino si la marca DESAPARECIÓ.
            antes, despues = _tinta(b), _tinta(a)
            tinta = antes
            tapado = ImageChops.subtract(antes, despues)

            cols, filas = ZONAS
            cw, ch = ancho // cols, alto // filas
            peor = (0.0, "", 0)
            for f in range(filas):
                for c in range(cols):
                    caja = (c * cw, f * ch, (c + 1) * cw, (f + 1) * ch)
                    hay = _cuantos(tinta.crop(caja))
                    if hay < TINTA_MINIMA:
                        continue
                    comido = _cuantos(tapado.crop(caja))
                    parte = comido / hay
                    if parte > peor[0]:
                        peor = (parte, _donde(c, f), comido)
    except Exception as e:                                   # noqa: BLE001
        log.warning("no pude comparar %s con %s: %s", con, sin, e)
        return problemas

    parte, donde, comido = peor
    if parte > TAPADO_MAXIMO and comido >= TAPADO_MINIMO:
        problemas.append(
            f"el dibujo tapa {parte * 100:.0f}% de lo que la plantilla había "
            f"dibujado {donde} — puede ser el logo, el pie o el titular. "
            f"Corrélo, achicalo, o poné esa capa con \"atras\": true para que "
            f"pase por detrás")
    return problemas


def en_una_linea(problemas: list[str]) -> str:
    """Los avisos juntos, para escribirlos en `notas` de la fila.

    Con mayúscula al principio y separados por ` · `: es el mismo formato que
    ya usan los otros avisos del motor, y el chat los lee tal cual.
    """
    if not problemas:
        return ""
    return "revisión de la pieza — " + " · ".join(problemas)
