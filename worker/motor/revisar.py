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

#: Los píxeles del filo del archivo que no se miran, porque ahí el detector de
#: bordes ve un salto que no dibujó nadie. Tres alcanzan.
MARCO = 3

#: Contraste mínimo entre una marca de la plantilla y lo que le quedó detrás.
#: 3:1 es el piso de la WCAG para texto grande, y todo lo que protegemos acá
#: —logo, titular, pie— es texto grande o un símbolo del tamaño de uno.
#:
#: Se mira como CAÍDA y no como valor absoluto: lo que se avisa es que el
#: dibujo empeoró algo que estaba bien. Una plantilla con poco contraste
#: propio es una decisión de la marca y no un defecto de esta pieza.
CONTRASTE_MINIMO = 3.0

#: Cuánto borde tiene que tocar una capa para que cuente como que llega ahí.
#: Treinta píxeles es más que un vértice y menos que cualquier franja.
BORDE_TOCADO = 30

#: Cuántos TRAZOS nuevos tiene que meter un dibujo en una franja insegura para
#: que valga avisar. Se cuentan bordes, no píxeles cambiados: un resplandor de
#: fondo cambia la franja entera sin agregar un solo trazo, y con la primera
#: versión de esta medida eso disparaba un aviso falso.
#:
#: Tres mil es una forma de verdad, no un asomo: el celular cortado del
#: 4/9/2026 metió mucho más que eso en los 250 px de abajo de una story, que es
#: donde Instagram pone la caja de responder.
EN_LA_FRANJA = 3000


def _tinta(im):
    """Máscara de lo que está DIBUJADO en la pieza: textos, logos, formas.

    Un degradé no es tinta aunque tenga color: cambia de a poco. Lo que se
    busca son los saltos bruscos, que es lo que hace una letra contra su
    fondo. Es la misma idea que usa cualquier detector de bordes y alcanza de
    sobra acá, donde no hay que reconocer nada: sólo saber dónde hay algo.
    """
    from PIL import ImageDraw, ImageFilter
    m = im.convert("L").filter(ImageFilter.FIND_EDGES).point(
        lambda v: 255 if v > BORDE else 0)
    # El detector de bordes dibuja un marco alrededor de TODA imagen: el filo
    # del archivo es el salto más grande que hay. Ese marco no es tinta de
    # nadie y son ~190 píxeles por zona, o sea que una zona vacía del borde
    # parecía tener contenido y cualquier dibujo que pasara por ahí «lo
    # tapaba». Dio un falso positivo en la primera prueba real.
    d = ImageDraw.Draw(m)
    d.rectangle([0, 0, m.width - 1, MARCO - 1], fill=0)
    d.rectangle([0, m.height - MARCO, m.width - 1, m.height - 1], fill=0)
    d.rectangle([0, 0, MARCO - 1, m.height - 1], fill=0)
    d.rectangle([m.width - MARCO, 0, m.width - 1, m.height - 1], fill=0)
    return m


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


def _luz(rgb) -> float:
    """Luminancia relativa de la WCAG. Es la que usa la fórmula de contraste."""
    def canal(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)


def _contraste(a: float, b: float) -> float:
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def _promedio(im, mascara) -> tuple | None:
    """El color promedio de los píxeles que la máscara deja pasar."""
    px, mp = im.load(), mascara.load()
    r = g = b = n = 0
    for y in range(im.height):
        for x in range(im.width):
            if mp[x, y]:
                c = px[x, y]
                r += c[0]; g += c[1]; b += c[2]; n += 1
    return (r / n, g / n, b / n) if n else None


def _contraste_de_zona(im, tinta, alrededor):
    """(luz de la marca, luz de lo que la rodea) en esta imagen."""
    a, b = _promedio(im, tinta), _promedio(im, alrededor)
    return (None if a is None else _luz(a)), (None if b is None else _luz(b))


def _bordes_tocados(huella, ancho, alto) -> list[str]:
    """Qué bordes del lienzo toca el dibujo, con nombre."""
    px = huella.load()
    toca = []
    if sum(1 for y in range(alto) if px[0, y]) >= BORDE_TOCADO:
        toca.append("izquierdo")
    if sum(1 for y in range(alto) if px[ancho - 1, y]) >= BORDE_TOCADO:
        toca.append("derecho")
    if sum(1 for x in range(ancho) if px[x, 0]) >= BORDE_TOCADO:
        toca.append("de arriba")
    if sum(1 for x in range(ancho) if px[x, alto - 1]) >= BORDE_TOCADO:
        toca.append("de abajo")
    return toca


def revisar_dibujo(con: pathlib.Path, sin: pathlib.Path,
                   zonas: dict | None = None) -> list[str]:
    """Qué se comió el dibujo de una pieza a medida.

    La comparación es exacta porque la pieza se renderiza dos veces: con el
    dibujo y sin él. Lo que cambió entre las dos imágenes ES el dibujo, sin
    tener que adivinar dónde lo puso nadie ni qué plantilla se usó. Y lo que
    importa no es que el dibujo ocupe lugar —para eso está— sino **que tape lo
    que la plantilla ya había dibujado**: el logo, el titular, el pie.

    Una capa `atras` da cero por construcción: queda detrás del texto, así que
    los píxeles del texto no cambian. Eso no es una casualidad afortunada, es
    la razón por la que la medida sirve: distingue «cubre» de «está detrás».

    Se miden tres cosas, y las tres salieron de piezas reales del 3 y 4/9/2026:

    · **Qué tapó.** La consola de DJ que cruzaba el pie.
    · **Qué dejó ilegible.** Las cintas de obra que pasaban por detrás del
      logo y del pie: no tapaban nada —iban `atras`, así que la marca seguía
      ahí— pero blanco sobre rayas amarillas y negras no se lee. Tapar y
      arruinar son dos fallas distintas y hacían falta dos medidas.
    · **Si quedó cortado.** El megáfono que se salía por la derecha y se leía
      como una taza.
    · **Si cae donde Instagram tapa.** Un celular apoyado en el borde de abajo
      de una story queda debajo de la caja de respuesta. `zonas` son las
      franjas que la marca declara como intocables para ese formato.

    Esto es un hecho y no una opinión, que es la regla 2 del módulo. Si el
    dibujo quedó feo, desbalanceado o fuera de clima, eso lo tiene que ver
    alguien mirando; acá sólo se dice qué quedó tapado, qué quedó ilegible y
    qué quedó cortado.
    """
    problemas: list[str] = []
    try:
        from PIL import Image, ImageChops, ImageFilter
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

            # Lo que rodea a cada marca, para medirle el contraste: un anillo
            # de seis píxeles alrededor de la tinta y no el resto de la zona,
            # porque lo que hace ilegible una letra es lo que tiene PEGADO.
            gordo = antes.filter(ImageFilter.MaxFilter(13))
            alrededor = ImageChops.subtract(gordo, antes)

            cols, filas = ZONAS
            cw, ch = ancho // cols, alto // filas
            peor = (0.0, "", 0)
            ilegible = None
            for f in range(filas):
                for c in range(cols):
                    caja = (c * cw, f * ch, (c + 1) * cw, (f + 1) * ch)
                    hay = _cuantos(antes.crop(caja))
                    if hay < TINTA_MINIMA:
                        continue
                    comido = _cuantos(tapado.crop(caja))
                    parte = comido / hay
                    if parte > peor[0]:
                        peor = (parte, _donde(c, f), comido)

                    # Contraste antes y después, en la misma zona. Se avisa la
                    # CAÍDA: si la plantilla ya venía floja ahí, es una
                    # decisión de la marca y no la rompió este dibujo.
                    mt, ma = antes.crop(caja), alrededor.crop(caja)
                    if _cuantos(ma) < TINTA_MINIMA:
                        continue
                    t1, f1 = _contraste_de_zona(b.crop(caja), mt, ma)
                    t2, f2 = _contraste_de_zona(a.crop(caja), mt, ma)
                    if None in (t1, f1, t2, f2):
                        continue
                    c1, c2 = _contraste(t1, f1), _contraste(t2, f2)
                    if c1 >= CONTRASTE_MINIMO > c2:
                        if ilegible is None or c2 < ilegible[0]:
                            ilegible = (c2, c1, _donde(c, f))

            huella = ImageChops.difference(a, b).convert("L").point(
                lambda v: 255 if v > 10 else 0)
            toca = _bordes_tocados(huella, ancho, alto)

            # Lo que el dibujo METE en las franjas que Instagram tapa. Se mide
            # por trazos agregados —bordes que antes no estaban— y no por
            # píxeles cambiados, y esa distinción es la que hace que el aviso
            # sirva: una mancha de luz desenfocada de fondo cambia la franja
            # entera y no molesta a nadie; un teléfono agrega contornos. Con
            # píxeles cambiados avisaba de los dos.
            nueva_tinta = ImageChops.subtract(despues, antes)
            tapado_por_ig = []
            for lado, alto_franja in (("arriba", (zonas or {}).get("arriba")),
                                      ("abajo", (zonas or {}).get("abajo"))):
                if not alto_franja:
                    continue
                caja = ((0, 0, ancho, alto_franja) if lado == "arriba"
                        else (0, alto - alto_franja, ancho, alto))
                cuantos = _cuantos(nueva_tinta.crop(caja))
                if cuantos > EN_LA_FRANJA:
                    tapado_por_ig.append((lado, alto_franja, cuantos))
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

    if ilegible:
        c2, c1, donde = ilegible
        problemas.append(
            f"el dibujo dejó ilegible lo que hay {donde}: el contraste pasó de "
            f"{c1:.1f}:1 a {c2:.1f}:1. Estar por detrás no alcanza — el logo y "
            f"el pie necesitan un fondo tranquilo. Corré el dibujo, bajale la "
            f"opacidad, o dejale libre esa esquina")

    # Un dibujo que toca UN borde y no el de enfrente suele ser un objeto que
    # se salió del lienzo. El megáfono del 4/9/2026 tocaba sólo el derecho y
    # quedaba cortado; las cintas cruzaban la pieza y tocaban los dos, que es
    # lo que tiene que hacer una franja. La diferencia es medible y el aviso
    # dice las dos lecturas, porque las dos existen.
    for lado, alto_franja, cuantos in tapado_por_ig:
        problemas.append(
            f"el dibujo mete {cuantos // 1000}k trazos en los {alto_franja} px "
            f"de {lado}, que es donde Instagram pone {'el nombre de la cuenta' if lado == 'arriba' else 'la caja de responder'}. "
            f"Ahí no se ve: subilo o achicalo")

    for uno, otro in (("izquierdo", "derecho"), ("de arriba", "de abajo")):
        for a_, b_ in ((uno, otro), (otro, uno)):
            if a_ in toca and b_ not in toca:
                problemas.append(
                    f"el dibujo toca el borde {a_} y no el {b_}: si era un "
                    f"objeto entero, quedó cortado ahí. Si era una franja que "
                    f"cruza la pieza, está bien")
    return problemas


# ── Cómo quedó compuesta ───────────────────────────────────────────────────
#
# Esto NO son avisos y por eso no llevan ⚠. Una pieza con un tercio vacío puede
# estar perfecta —Asistime es una marca aireada y el vacío es parte del kit— y
# marcarlo como defecto sería opinar, que es lo que la regla 2 prohíbe.
#
# Lo que se dice acá son HECHOS sobre la composición, para que quien la armó
# pueda juzgarla. La diferencia importa: un defecto se corrige, un hecho se
# mira. El 4/9/2026 una pieza salió con el 41% de la tinta arriba, el 3% en el
# medio y el 56% abajo —un agujero de 500 px entre el título y el teléfono— y
# nadie lo vio, porque el agente no tenía forma de saberlo sin mirar de verdad.

#: Por debajo de esta densidad, una fila de píxeles está vacía. Es relativa a
#: la fila más cargada de la pieza: un titular gigante y una línea de pie no se
#: pueden comparar contra el mismo número absoluto.
FILA_VACIA = 0.02

#: Un hueco más chico que esto es aire normal entre bloques, no un agujero.
HUECO_MINIMO = 0.12


def composicion(pieza: pathlib.Path,
                sin_dibujo: pathlib.Path | None = None) -> list[str]:
    """Los hechos de la composición: dónde está el peso y dónde el vacío.

    Se mide sobre la tinta —lo que está dibujado— y no sobre el color, porque
    un fondo degradado ocupa el lienzo entero sin componer nada.
    """
    lineas: list[str] = []
    try:
        from PIL import Image, ImageChops
    except Exception:                                        # noqa: BLE001
        return lineas                                        # regla 3
    try:
        with Image.open(pieza) as im:
            im = im.convert("RGB")
            ancho, alto = im.size
            tinta = _tinta(im)
            filas = [_cuantos(tinta.crop((0, y, ancho, y + 1)))
                     for y in range(alto)]
    except Exception as e:                                   # noqa: BLE001
        log.warning("no pude medir la composición de %s: %s", pieza, e)
        return lineas

    total = sum(filas)
    if not total:
        return lineas

    # 1 · Dónde está el peso, en tercios.
    t = alto // 3
    partes = [sum(filas[:t]), sum(filas[t:2 * t]), sum(filas[2 * t:])]
    lineas.append("la tinta se reparte {}% arriba · {}% medio · {}% abajo"
                  .format(*[round(p * 100 / total) for p in partes]))

    # 2 · El hueco más grande. No es «cuánto vacío hay» sino «dónde está TODO
    #     junto»: dos franjas de 10% repartidas no molestan; una de 28% en el
    #     medio parte la pieza en dos.
    piso = max(filas) * FILA_VACIA
    mejor, largo, desde = 0, 0, 0
    for y, v in enumerate(filas):
        if v <= piso:
            largo += 1
            if largo > mejor:
                mejor, desde = largo, y - largo + 1
        else:
            largo = 0
    if mejor > alto * HUECO_MINIMO:
        centro = (desde + mejor / 2) / alto
        donde = ("arriba" if centro < 0.34 else
                 "abajo" if centro > 0.66 else "en el medio")
        lineas.append(f"hay una franja vacía de {round(mejor * 100 / alto)}% "
                      f"del alto {donde}")

    # 3 · El objeto dibujado: cuánto ocupa y si apoya en un borde. Sin el
    #     segundo render no se sabe cuál es el objeto, así que es opcional.
    #
    #     Se mide por TRAZOS agregados y no por píxeles cambiados, por lo
    #     mismo que la franja de Instagram: una mancha de luz de fondo cambia
    #     el lienzo entero, y con píxeles cambiados «lo dibujado» daba
    #     siempre 100% del ancho y tocando los cuatro bordes. Lo que ocupa
    #     lugar en una composición es lo que tiene forma.
    if sin_dibujo:
        try:
            with Image.open(pieza) as a, Image.open(sin_dibujo) as b:
                a, b = a.convert("RGB"), b.convert("RGB")
                if a.size == b.size:
                    caja = ImageChops.subtract(_tinta(a), _tinta(b)).getbbox()
                    if caja:
                        x0, y0, x1, y1 = caja
                        # El filo se descuenta: `_tinta` borra MARCO píxeles
                        # de cada lado, así que un objeto pegado al borde
                        # termina justo adentro de ese recorte. Sin esto, el
                        # celular cortado del 4/9/2026 decía «no toca ningún
                        # borde» mientras el aviso decía lo contrario.
                        filo = MARCO + 2
                        pegado = [n for n, cond in
                                  (("arriba", y0 <= filo),
                                   ("abajo", y1 >= alto - filo),
                                   ("la izquierda", x0 <= filo),
                                   ("la derecha", x1 >= ancho - filo)) if cond]
                        cola = (" y llega al borde de " + " y ".join(pegado)
                                if pegado else " y no toca ningún borde")
                        lineas.append(
                            f"lo dibujado ocupa {round((y1 - y0) * 100 / alto)}% "
                            f"del alto y {round((x1 - x0) * 100 / ancho)}% "
                            f"del ancho{cola}")
        except Exception as e:                               # noqa: BLE001
            log.warning("no pude medir el objeto de %s: %s", pieza, e)
    return lineas


def en_una_linea(problemas: list[str]) -> str:
    """Los avisos juntos, para escribirlos en `notas` de la fila.

    Con mayúscula al principio y separados por ` · `: es el mismo formato que
    ya usan los otros avisos del motor, y el chat los lee tal cual.
    """
    if not problemas:
        return ""
    return "revisión de la pieza — " + " · ".join(problemas)
