# -*- coding: utf-8 -*-
"""Le pide al Agent SDK que diseñe la pieza usando el skill de la marca.

Qué marca es sale del pedido, no del código: cada cliente tiene su app y todas
escriben en la misma tabla. La columna `marca` la completa un trigger desde el
perfil del usuario, así que el frontend no puede pedir la marca de otro.
"""
import json
import logging
import re
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions

from . import config, manual

log = logging.getLogger(__name__)

PROMPT = """Sos el agente de contenidos de {marca_nombre}. Te llegó este pedido \
por el formulario.

PEDIDO
------
Lo que pidieron:
{texto}

Sede: {sede}
Formatos pedidos: {formatos}
Fotos que subió la persona: {fotos_subidas}
Fotos del banco que eligió la persona: {fotos_elegidas}
Logo de la empresa del convenio: {logo_socio}
Videos que subió la persona: {videos_subidos}
Para publicar el: {cuando}
Lo pidió: {quien}

DATOS QUE YA RESOLVÍ POR VOS
----------------------------
Marca: {marca_nombre}
Color de acento que corresponde: {acento}
Teléfono de esta sede: {contacto}{sede_extra}
{reglas_marca}
QUÉ TENÉS QUE HACER
-------------------
1. Leé el pedido e interpretá qué plantilla corresponde. Las plantillas de
   esta marca están listadas en su SKILL.md — usá una de ésas y ninguna otra.
   Si el pedido trae algo que la plantilla no tiene, no bajes el pedido: eso
   se resuelve con `retoque`, más abajo.
2. Sacá del texto libre todo lo que puedas: fechas, categorías, nombres,
   precios, urgencia. No inventes datos que no estén.
3. Generá la pieza en EXACTAMENTE los formatos pedidos arriba, ni más ni
   menos. Un archivo por formato.
4. Escribí en un solo `spec.json` TODOS los formatos pedidos y renderizalos de
   una, indicando la carpeta de salida como segundo argumento:

       python3 render.py spec.json {salida}
       python3 video.py guion.json {salida}     # sólo si el pedido lleva reel

   Van directo ahí: no hay que copiar nada desde `out/` después.

   **LEÉ LO QUE IMPRIME.** Además de los archivos, `render.py` te dice lo que
   midió. Una línea que empieza con `⚠` es un defecto medido en la imagen, no
   una sugerencia: corregí el spec y volvé a renderizar antes de seguir. La
   pieza sale igual si la ignorás, y ahí el defecto lo encuentra el cliente.
5. Escribí DOS archivos separados, y no mezcles lo que va en cada uno:

   {salida}/copy.txt  — SÓLO el texto del posteo, listo para copiar y pegar
     en Instagram, en uruguayo y con voseo. Nada más: ni encabezados, ni
     explicaciones, ni notas, ni el pedido que te hicieron. Este archivo se
     publica tal cual en la cuenta del cliente.
     (si el pedido es SÓLO una presentación PDF, en vez del copy de
     Instagram poné un resumen de dos o tres líneas para acompañar el envío
     del documento por mail o WhatsApp)

   {salida}/notas.txt — las decisiones que tomaste y lo que asumiste porque
     el pedido no lo aclaraba. Esto lo lee quien pidió la pieza, no el
     público.

   Van separados porque van a lugares distintos: el copy sale publicado y las
   notas quedan adentro. El 9/8/2026 estaban en el mismo archivo y las ocho
   notas de trabajo del diseñador terminaron públicas en el Instagram del
   club. Si dudás de dónde va algo: ¿lo leería un socio del club sin
   entender de qué hablás? Entonces va en notas.txt.

EL CAMINO CORTO
---------------
Para una placa, esto son cuatro pasos y no hace falta ninguno más:

  1. leer `referencias/fotos.json` y elegir foto + copiar su `foco`
  2. escribir un `spec.json` con un trabajo por formato pedido
  3. `python3 render.py spec.json {salida}`
  4. escribir `copy.txt` y `notas.txt`

Todo lo que necesitás saber está en el SKILL.md y en `fotos.json`. **No
explores la carpeta** buscando ejemplos ni leas los .py del motor salvo que
algo falle de verdad: cada lectura de más se vuelve a leer entera en todos los
turnos que siguen, y ahí es donde se va el costo de la pieza.

No hay nadie del otro lado para contestarte: no preguntes, decidí y dejá lo
que asumiste escrito en notas.txt.

REGLA DE ORO
------------
Generá una primera versión COMPLETA lo antes posible, y recién después
mejorala. Nunca termines sin haber dejado al menos un archivo en la carpeta
de salida.

Si buscás una foto que cumpla una condición y no la encontrás en dos intentos,
**dejá de buscar**: elegí la más cercana, generá la pieza, y explicá en
notas.txt qué pediste, qué usaste y qué foto haría falta sumar al banco. Una
pieza entregada con una foto que no es exactamente la pedida sirve; una pieza
que nunca se generó porque seguiste buscando no le sirve a nadie.

REGLAS
------
- **Un pedido a medida NO es un pedido imposible: para eso está `retoque`.**
  Cuando piden algo que la plantilla no tiene —«el título metido adentro de un
  recuadro tipo chimenea», «el número tachado», «una cinta en diagonal en la
  esquina»— **no lo bajes a lo más parecido ni escribas en notas.txt que el
  motor no lo puede hacer.** Sí lo puede: en el `data` de ese trabajo agregás
  `retoque` con un bloque de CSS escrito para ESA pieza.

      {{"plantilla": "titular", "formato": "vert", "data": {{
         "titulo": "Se viene el invierno",
         "kicker": "TEMPORADA",
         "retoque": ".disp{{color:#3B2412;padding:52px 46px;border:30px solid #8B3A1E;background:linear-gradient(180deg,#FFF0C4,#FFC46B,#FF7A2F)}}"
      }}}}

  Se aplica DESPUÉS de la hoja de la marca, así que pisa lo que la plantilla
  decidió — que es todo el punto. No se guarda en ningún lado: la pieza
  siguiente vuelve a salir como siempre.

  **Y después MIRÁ EL PNG.** Un retoque puede quedar tapado por el fondo de la
  plantilla, desbordar el texto o pisar el logo, y nada de eso se ve leyendo el
  CSS: se ve en la imagen. La primera vez que se usó, el marco estaba
  correctamente aplicado y no se veía: lo tapaba el fondo de la plantilla.

  Abrí el PNG de TODA pieza que lleve `retoque` o `dibujo` y contestate tres
  preguntas antes de escribir el copy. Son tres, son concretas, y si alguna da
  que sí se corrige el spec y se vuelve a renderizar:

  1. ¿Hay algo encima del logo, del pie o del titular?
  2. ¿Quedó un tercio de la pieza vacío mientras otro está amontonado?
  3. ¿El clima es el que pidieron? «Fiesta», «urgente» y «elegante» no se
     resuelven con el mismo fondo. Si pidieron energía, el fondo pleno o el
     degradé dicen más que el fondo claro, que es el de todos los días.

  Mirar una vez y corregir cuesta un turno. Entregar una pieza floja cuesta el
  pedido entero, porque lo vuelve a pedir una persona.

  Cuatro cosas que el retoque no puede, y te las rechaza con el motivo: cerrar
  `</style>`, traer una hoja o una imagen de internet —un SVG embebido en
  `data:` sí—, usar `position: fixed`, y pasar de 4.000 caracteres. Si te está
  quedando enorme, lo que hace falta es una plantilla y no un retoque.

  En un carrusel el retoque va en la diapositiva que lo necesita, no en todas.

  Y la pregunta que decide entre las dos puertas: **¿esto se va a volver a
  pedir?** Si sí, es una plantilla nueva. Si es de hoy, es un retoque.
- **Si el pedido tiene una FORMA que no existe, dibujala: `dibujo`.** El
  retoque pinta lo que ya está; no agrega una consola de DJ, una chimenea, una
  guirnalda ni una flecha. Para eso, en el mismo `data`, va `dibujo` con SVG:

      {{"plantilla": "titular", "formato": "story", "data": {{
         "titulo": "Mañana es VIERNES",
         "dibujo": [
           {{"clase": "consola",
            "svg": "<svg viewBox='0 0 1080 1920'><g transform='translate(180 1290)' fill='none' stroke='#FFF' stroke-width='7'><rect width='720' height='330' rx='26'/><circle cx='150' cy='120' r='78'/></g></svg>"}},
           {{"clase": "marco", "atras": true, "svg": "<svg viewBox='0 0 1080 1920'>...</svg>"}}
         ],
         "retoque": ".dibujo.consola{{opacity:.42}}"
      }}}}

  Cada capa cubre el lienzo entero y el SVG se estira a ese tamaño: **dibujá
  con un `viewBox` propio** y ubicá las cosas en esas coordenadas. Van encima
  de la plantilla; `"atras": true` la manda detrás del texto y delante del
  fondo, que es donde va un marco. La `clase` es para poder apuntarle desde el
  retoque —opacidad, color, posición— y esa es la división de trabajo: el
  `dibujo` pone las formas, el `retoque` las acomoda.

  Hasta 4 capas y 12.000 caracteres cada una. Se parsea como XML antes de
  entrar, así que **tiene que cerrar todas las etiquetas y tener una sola
  raíz `<svg>`**; y no entran `script`, `style`, `foreignObject` ni nada que
  venga de internet (un `data:` sí).

  **Para tocar el logo o el pie de la marca, usá sus variables.** El isotipo y
  el lockup salen con el tamaño del kit, y ese tamaño es el respaldo de una
  variable CSS. Si el pedido dice «el logo más grande», el retoque es:

      ".marca-iso{{--iso-ancho:110px;--iso-alto:110px}}"

  y para el lockup, `.marca-logo` con `--logo-ancho` y `--logo-alto`. Escribir
  `.marca-iso{{width:110px}}` NO funciona —el ancho va en el atributo `style` y
  le gana a cualquier clase— así que si usás eso vas a ver la pieza igual y
  vas a creer que la cambiaste. Pasó el 4/9/2026: el agente anotó que había
  agrandado el logo 1,8 veces y salió idéntico.

  **Los emojis del sistema no son un dibujo.** Se ven distinto en cada lado y
  en esta marca 🎵 sale azul marino: sobre un fondo azul desaparece. Si el
  pedido dice «emojis de música», lo que hace falta son notas dibujadas con la
  tinta de la marca, no el carácter.
- Usá el acento que te di arriba. No lo deduzcas de nuevo.
- {regla_telefono}
  Cuando el teléfono va, usá EXACTAMENTE el número de arriba, no lo deduzcas.
  Lo mismo vale para el copy de Instagram.
- Si falta un dato imprescindible y no lo podés inferir, generá igual la
  pieza con lo que tengas y dejá bien claro en notas.txt qué faltó.
- **Si la persona subió fotos, USÁ ESAS y ninguna del banco.** Las subió a
  propósito. El banco es para cuando no hay foto propia, no una alternativa a
  elegir. Como no tienen `foco` precalculado, generá la pieza, MIRÁ el PNG que
  salió, y si la cara del sujeto quedó cortada o chocando con el titular,
  corregí el `foco` y volvé a generar.
- **Si arriba dice que eligió fotos del banco, usá ESAS.** Son claves de
  `referencias/fotos.json`: buscá cada una ahí y sacá de la entrada la ruta del
  archivo y el `foco`. Las eligió mirándolas, así que no las cambies por otra
  que te parezca mejor. Si pidió más fotos de las que entran en la pieza, usá
  las primeras y decí en notas.txt cuáles quedaron afuera.

  **Y entonces la plantilla TIENE que llevar foto.** Elegir una plantilla sólo
  tipográfica cuando la persona eligió una foto no es «usar la foto y que no
  entre»: es ignorarla. Ya pasó, y el agente lo escribió en notas.txt como si
  fuera una decisión de diseño razonable. No lo es: la persona abrió el banco,
  miró las fotos y eligió una. Eso es una instrucción, no una sugerencia.
  Si te parece que la pieza queda mejor sin foto, **hacela igual con foto** y
  dejá tu opinión escrita en notas.txt. Quien pidió decide, vos ejecutás.

  Lo mismo vale cuando la persona SUBIÓ una foto: subirla es elegirla.
- **El banco tiene dos clases de foto y se usan distinto.** Las que vienen en
  el skill traen el `foco` ya resuelto: copialo y listo. Las que subió el
  cliente desde su app dicen `"origen": "banco del cliente"` y traen dos cosas
  más:
  · `archivo` — usá ESA ruta en el spec, no `assets/<clave>.jpg`.
  · `foco_confirmado` — dice si el encuadre está resuelto o es provisorio.

    **`true` → no mires nada.** Copiá el `foco` y seguí. Abrir el PNG para
    confirmar algo que ya está confirmado son dos turnos tirados, y en este
    sistema cada turno cuesta releer la conversación entera.

    **`false` → una sola vuelta de verificación, y guardás lo que aprendiste
    en UN comando:**

        python3 banco.py foco <clave> <formato> "50% 24%" \\
          --quien '{{"genero":"femenino","cantidad":"una persona","edad":"adulto","apariencia":"pelo oscuro atado; remera negra"}}'

    Generás, mirás el PNG UNA vez, y corrés eso: guarda el encuadre y la
    descripción de quién aparece de una sola pasada. La próxima pieza con esa
    foto ya no necesita ninguna de las dos cosas. Si el encuadre provisorio
    quedó bien, guardalo igual — confirmarlo vale tanto como corregirlo.

- **Si arriba hay un «Logo de la empresa del convenio», la pieza es un
  convenio.** Ese archivo es el logo de OTRA marca: va en el campo
  `logo_socio` de la plantilla `convenio` y en ningún otro lado. Nunca como
  foto de fondo, nunca estirado, nunca recortado — la plantilla ya lo encaja
  sola en su caja.
  Si el logo viene en blanco y no se ve sobre el fondo claro, generá igual la
  pieza y pedí en notas.txt la versión oscura o a color.
  Y si el pedido habla de un convenio pero NO subieron el logo, hacela con el
  logo nuestro solo y decilo en notas.txt: **no busques el logo por internet.**
- Si el pedido menciona una foto que no está en assets/, usá la del banco
  que mejor encaje y avisalo en notas.txt. Si la marca todavía no tiene banco
  —`referencias/fotos.json` vacío— **no inventes una ruta de archivo**: usá una
  plantilla sin foto y decilo en notas.txt.
- Si el pedido incluye un reel, el video es la pieza principal: apuntá a
  12 segundos, con el tramo más fuerte al principio y todo lo importante
  resuelto antes del segundo 8. La sección «Reels en video» del skill tiene
  las reglas y el porqué.
- **Si la persona subió videos, el reel se arma con ESOS clips.** Arriba, en
  «Videos que subió la persona», ya tenés el análisis hecho: duración,
  medidas, dónde cambia la toma, dónde hay silencio y dónde están los picos de
  audio. **No corras ffprobe ni ffmpeg para averiguar eso: ya está.**
  Lo que SÍ tenés que hacer es **abrir los cuadros con Read antes de elegir
  los cortes** — el nombre de cada uno trae el segundo. Sin mirarlos estás
  eligiendo a ciegas.
  Podés completar con fotos del banco si los clips no alcanzan, pero los clips
  subidos van sí o sí y son el material principal.

- **El reel se pide con un GUION DE EDICIÓN**, no con un spec del motor. Se
  escribe en tiempos del material original —`desde` y `hasta`— que es como
  pensás cuando mirás los cuadros:

      {{"nombre": "reel-torneo",
        "tramos": [
          {{"archivo": "clips/subidas/01-partido.mp4", "desde": 12.4, "hasta": 16.1}},
          {{"archivo": "clips/subidas/01-partido.mp4", "desde": 31.0, "hasta": 34.2,
           "velocidad": 0.5}}
        ],
        "musica": {{"archivo": "clips/subidas/03-pista.mp3", "volumen": 0.35}}}}

  Y se renderiza con `python3 video.py guion.json {salida}`.
  **Se valida antes de encodear**: si un tramo pide un segundo que no existe o
  el reel se pasa de 90 segundos, te lo dice en castellano y no gastás el
  encode. Los avisos que empiezan con ⚠ no frenan nada, pero leelos.

  **Los carteles NO son la frase que te dieron.** Quien pide te da una idea;
  vos la convertís en carteles de 2 a 4 palabras. Nunca el mismo texto en dos
  tramos seguidos, y no todos los tramos llevan texto — el punto se mira, no
  se lee. La sección «El texto en pantalla» del skill tiene los ejemplos.

  **Si la persona subió música, usá ESA** y no la cama del motor.

  Tres cosas que el guion resuelve y conviene usar:
  · **Cortá en los cortes de toma** que te di, no en el medio de una toma.
  · **Saltá los silencios**: es lo que más hace que un video de celular
    parezca editado.
  · `velocidad` menor a 1 es cámara lenta. Ese tramo va MUDO a propósito, así
    que no lo uses donde alguien habla.
- Si el pedido pide algo sobre QUIÉN aparece en la foto (jugadoras, chicos,
  grupo, gente en la tribuna), filtrá el banco por el campo `quien` de
  `referencias/fotos.json`. Si ninguna foto lo cumple, NO lo ignores en
  silencio: elegí la más cercana y escribilo en la sección
  notas.txt, diciendo qué foto haría falta sumar al banco.

Cuando termines, respondé sólo con una línea: LISTO seguido de un título
corto para la carpeta (máximo 6 palabras, sin barras ni dos puntos).
"""


VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}
# Un audio que sube la persona iba a `assets/subidas/` como si fuera una foto,
# y ahí el agente lo veía listado entre las imágenes y no lo usaba nunca. Va a
# la misma carpeta que los clips, que es donde el motor busca material de reel.
AUDIO_EXT = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac"}

MARCA_POR_DEFECTO = "boss-padel-disenos"


def _reglas_de_marca(marca: str) -> tuple[str, int | None]:
    """El manual que el club edita en Asistime, listo para el prompt.

    Va DESPUÉS de los datos resueltos y ANTES de las instrucciones, y dice
    explícitamente que manda sobre el SKILL.md. El orden no es decorativo: el
    skill trae reglas escritas hace meses y el manual trae la que el club
    escribió ayer. Cuando se contradicen, gana la de ayer — si no, el club
    edita el documento, ve que la pieza sale igual, y deja de confiar en el
    documento.

    Si no hay manual, devuelve la cadena vacía y el prompt queda como estaba.
    """
    texto, version = manual.leer(marca)
    if not texto:
        return "", None
    nombre = (_ficha(marca) or {}).get("nombre", marca)
    return (f"""
REGLAS DE ESTA MARCA — LAS ESCRIBE EL CLIENTE
---------------------------------------------
Esto lo mantiene {nombre} en Asistime y es lo más actualizado que hay.
**Cuando algo de acá contradiga al SKILL.md, mandá lo de acá.**

{texto}
""", version)


def _marca(pedido: dict) -> str:
    """Qué skill le toca a este pedido.

    Sale de la columna `marca`, que en la base la completa un trigger desde el
    perfil del usuario. No la manda el frontend: si la mandara, cualquiera
    podría pedir un diseño con la marca de otro cliente cambiando un campo en
    el navegador.
    """
    m = (pedido.get("marca") or "").strip()
    return m if m else MARCA_POR_DEFECTO


#: Los datos de la marca que van al prompt. Vive en `config` para que leerlos
#: no arrastre este módulo, que carga el SDK. Se re-exporta con el nombre de
#: siempre porque hay código que lo importa de acá.
_ficha = config.ficha_de_marca


def _analizar_clips(rutas: list[Path], base: Path) -> str:
    """Mira y escucha los clips que subió la persona, y lo cuenta en el prompt.

    Hasta acá el prompt le pedía al agente que sacara los cuadros él mismo con
    ffmpeg. Eso funcionaba, pero se pagaba dos veces: en turnos —cada llamada a
    ffmpeg es un turno, y el contexto entero se relee en el siguiente— y en
    criterio, porque el agente elegía los segundos a ojo y la mitad de los
    cuadros caían en partes muertas.

    Ahora lo hace el motor, una sola vez, eligiendo los momentos por donde el
    material cambia: justo después de un corte de toma y en los picos de audio.
    El agente recibe el resultado ya masticado y arranca decidiendo.
    """
    if not rutas:
        return "ninguno"
    from motor import analisis as _an

    destino = base / "clips/subidas/analisis"
    try:
        a = _an.analizar_varios(rutas, destino)
        _an.escribir(a, destino)
    except Exception as e:
        log.warning("no pude analizar los clips: %s", e)
        return ", ".join(f"clips/subidas/{r.name}" for r in rutas) + \
               " (no se pudieron analizar: miralos vos con ffprobe)"

    lineas = []
    for m in a["materiales"]:
        lineas.append(
            f"  · clips/subidas/{m['archivo']} — {m['duracion']}s · "
            f"{m['ancho']}x{m['alto']}{' vertical' if m['vertical'] else ' APAISADO'} · "
            f"{'con audio' if m['tiene_audio'] else 'MUDO'}")
        if m["cortes_de_toma"]:
            lineas.append(f"      cortes de toma: {_lista(m['cortes_de_toma'])}")
        if m["silencios"]:
            lineas.append(f"      silencios (sacalos): "
                          f"{', '.join(f'{x:.1f}-{y:.1f}' for x, y in m['silencios'][:8])}")
        if m["picos_de_audio"]:
            lineas.append(f"      picos de audio: {_lista(m['picos_de_audio'])}")

    cuadros = [f"clips/subidas/analisis/{c['archivo']}"
               for m in a["materiales"] for c in m["cuadros"]]
    if cuadros:
        lineas.append("")
        lineas.append("  CUADROS YA SACADOS PARA QUE LOS MIRES —abrilos con Read "
                      "ANTES de elegir los cortes. El nombre trae el segundo:")
        lineas += [f"      {c}" for c in cuadros]
    for av in a.get("avisos", []):
        lineas.append(f"  ⚠ {av}")
    return "\n" + "\n".join(lineas)


def _lista(xs, tope=10):
    xs = [f"{x:.1f}" for x in xs[:tope]]
    return ", ".join(xs) + ("…" if len(xs) == tope else "")


def _traer_adjuntos(pedido: dict, marca: str) -> tuple[str, str, str]:
    """Baja lo que subió la persona. Devuelve (fotos, videos, logo) para el prompt.

    Van a carpetas distintas porque el agente las usa distinto: las fotos a
    `assets/subidas/`, que es donde busca imágenes, y los clips a
    `clips/subidas/`, que es de donde arma los reels.

    Si un archivo falla, se sigue con el resto: mejor un reel con dos de los
    tres clips que ningún reel.
    """
    from .supa import bajar
    adj = pedido.get("adjuntos") or []
    base = config.RAIZ / ".claude/skills" / marca
    if not adj and not pedido.get("logo_socio"):
        return "ninguna", "ninguno", ""

    fotos, videos, audios = [], [], []
    rutas_video = []
    for i, a in enumerate(adj):
        url = a.get("url") if isinstance(a, dict) else a
        nombre = (a.get("nombre") if isinstance(a, dict) else None) or f"subida-{i+1}"
        # El índice adelante evita que dos nombres distintos colisionen al
        # limpiarlos: "foto ñandú.jpg" y "foto nandu.jpg" quedan iguales.
        nombre = f"{i+1:02d}-" + re.sub(r"[^A-Za-z0-9._-]", "-", nombre)
        ext = Path(nombre).suffix.lower()
        es_video, es_audio = ext in VIDEO_EXT, ext in AUDIO_EXT
        if es_video:
            carpeta, destino = "clips/subidas", videos
        elif es_audio:
            carpeta, destino = "clips/subidas", audios
        else:
            carpeta, destino = "assets/subidas", fotos
        try:
            bajar(url, base / carpeta / nombre)
            destino.append(f"{carpeta}/{nombre}")
            if es_video:
                rutas_video.append(base / carpeta / nombre)
        except Exception as e:
            log.warning("no pude bajar el adjunto %s: %s", nombre, e)

    # El logo del socio va a su propia carpeta, no a `assets/subidas/`. Es lo
    # que hace que el agente no tenga que adivinar: si está acá, es un logo, y
    # si es un logo, va en `logo_socio` de la plantilla `convenio` — nunca de
    # fondo ni como foto de la pieza.
    logo = pedido.get("logo_socio") or ""
    if logo:
        try:
            nombre = re.sub(r"[^A-Za-z0-9._-]", "-",
                            Path(logo.split("?")[0]).name) or "logo-socio"
            if not Path(nombre).suffix:
                nombre += ".png"
            bajar(logo, base / "assets/socios" / nombre)
            logo = f"assets/socios/{nombre}"
        except Exception as e:
            log.warning("no pude bajar el logo del socio: %s", e)
            logo = ""

    resumen = _analizar_clips(rutas_video, base)
    if audios:
        resumen += ("\n\n  MÚSICA QUE SUBIÓ LA PERSONA — usala en el guion con "
                    "`\"musica\": {\"archivo\": \"...\"}`:\n"
                    + "\n".join(f"      {a}" for a in audios))
    return (", ".join(fotos) or "ninguna", resumen, logo)


def _modelo(pedido: dict) -> str:
    """Qué modelo le toca a este pedido.

    Una placa es trabajo acotado: elegir plantilla, sacar fechas y categorías
    de un texto corto, copiar un `foco` que ya está resuelto en `fotos.json`.
    Un reel y una presentación no: hay que decidir qué tramo de qué clip, con
    qué ritmo, o cómo se estructura un argumento en ocho slides. Ahí la
    diferencia entre modelos se nota en la pieza; en una placa no.
    """
    pedidos = set(pedido.get("formatos") or [])
    return (config.MODELO_COMPLEJO
            if pedidos & config.FORMATOS_COMPLEJOS
            else config.MODELO_SIMPLE)


def _metricas(res, modelo: str = "") -> dict:
    """Lo que costó generar la pieza, sacado del ResultMessage del SDK.

    Se guarda para poder mostrarlo en la plataforma. El dato que más importa
    es `costo_usd`: los tokens son difíciles de interpretar, los centavos no.

    Ojo con la lectura de caché: va a ser el número más grande de todos y eso
    está bien. El skill entero —manual, plantillas, banco de fotos— se le manda
    al modelo en cada corrida, pero a partir de la segunda se lee de caché a una
    fracción del precio. Un número de caché alto significa que el sistema está
    reusando bien, no que esté gastando de más.
    """
    if res is None:
        return {}
    u = res.usage or {}
    return {
        "version": config.VERSION,
        "modelo": modelo,
        "costo_usd": round(res.total_cost_usd or 0.0, 5),
        "tokens_entrada": u.get("input_tokens", 0),
        "tokens_salida": u.get("output_tokens", 0),
        "cache_lectura": u.get("cache_read_input_tokens", 0),
        "cache_escritura": u.get("cache_creation_input_tokens", 0),
        "turnos": res.num_turns,
        "segundos": round((res.duration_ms or 0) / 1000, 1),
        "segundos_modelo": round((res.duration_api_ms or 0) / 1000, 1),
    }


def _piezas(salida: Path) -> list[Path]:
    """Los archivos que cuentan como pieza entregable.

    Un pedido de sólo PDF no deja ningún PNG: si midiéramos el éxito contando
    imágenes, una presentación correcta se marcaría como error.
    """
    return (list(salida.glob("*.png")) + list(salida.glob("*.pdf"))
            + list(salida.glob("*.mp4")))


async def _correr(prompt: str, modelo: str, salida: Path,
                  marca: str = MARCA_POR_DEFECTO) -> tuple[str, dict]:
    """Una pasada del agente. Devuelve (último texto, métricas)."""
    opciones = ClaudeAgentOptions(
        cwd=str(config.RAIZ),
        model=modelo,
        setting_sources=["project"],
        skills=[marca],
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Skill"],
        permission_mode="dontAsk",
        max_turns=80,
        # El SDK lee la salida del CLI mensaje por mensaje y corta con
        # «JSON message exceeded maximum buffer size» si uno solo pasa el
        # tope, que por defecto es 1 MB. Un `Read` de una pieza terminada
        # manda el PNG entero en base64: nuestras stories pesan entre 0,9 y
        # 1,7 MB, o sea 1,2 a 2,3 MB en base64. Todas las corridas del
        # 2 y 3/9/2026 que miraron el PNG murieron ahí. El tope alto no
        # gasta memoria por sí solo: es hasta cuánto se permite acumular.
        max_buffer_size=32 * 1024 * 1024,
    )

    log.info("arranco con %s · marca %s", modelo, marca)
    ultimo, resultado, corto = "", None, ""
    herramientas: dict[str, int] = {}
    try:
        async for msg in query(prompt=prompt, options=opciones):
            # El ResultMessage llega al final y trae el costo y los tokens.
            if type(msg).__name__ == "ResultMessage":
                resultado = msg
                continue
            _contar_herramientas(msg, herramientas)
            texto = _texto(msg)
            if texto:
                ultimo = texto
                log.info("agente: %s", texto[:300])
    except Exception as e:
        # El agente puede cortar con error habiendo dejado las piezas hechas.
        # Preferimos entregar lo que haya antes que descartar todo el trabajo.
        corto = f"{type(e).__name__}: {e}"
        log.warning("el agente corto con error (%s); reviso si dejo archivos", e)

    # Si el agente se cortó no hay ResultMessage y `_metricas` devuelve {}, que
    # es indistinguible de una pieza cargada a mano. Pasó con la story del
    # viernes del 3/9/2026: la pieza salió sin copy ni notas y las métricas no
    # decían nada, así que el fallo fue invisible. Ahora la corrida cortada deja
    # su rastro aunque no haya métricas.
    met = _metricas(resultado, modelo)
    if corto:
        met["corto"] = corto[:300]
        met.setdefault("version", config.VERSION)
        met.setdefault("modelo", modelo)
    if met:
        met["herramientas"] = herramientas
    if "costo_usd" in met:
        log.info("%s · US$%.4f · %d turnos · %d tokens de salida · %ds",
                 modelo, met["costo_usd"], met["turnos"],
                 met["tokens_salida"], met["segundos"])
    if herramientas:
        log.info("herramientas: %s", ", ".join(
            f"{k}×{v}" for k, v in sorted(
                herramientas.items(), key=lambda x: -x[1])))
    return ultimo, met


def _sede(marca: str, ficha: dict, sede: str) -> dict:
    """Los datos de una sede: su contacto y su acento.

    `sedes` va como diccionario `nombre → {contacto, acento, extra}`, y una
    marca sin locales igual tiene una: la marca entera.

    Lo que se valida acá es la FORMA, porque el `marca.json` lo escribe una
    persona y el error no se ve hasta cuatro minutos después. El 2/9/2026
    Asistime lo tenía como lista —`["Todas"]`, que se lee perfectamente
    razonable— y el diseño murió con «'list' object has no attribute 'get'»:
    un mensaje que no nombra ni la marca ni el campo, en un pedido que ya
    había esperado su turno en la cola.

    No frena la pieza. Lo único que se pierde es el contacto y el acento de
    la sede, y una pieza sin teléfono es muchísimo mejor que ninguna pieza.
    """
    sedes = ficha.get("sedes") or {}
    if not isinstance(sedes, dict):
        log.warning(
            "%s: `sedes` es %s y tiene que ser un diccionario "
            "`nombre → {contacto, acento}`. Sigo sin datos de sede.",
            marca, type(sedes).__name__)
        return {}
    datos = sedes.get(sede) or sedes.get(ficha.get("sede_por_defecto", "")) or {}
    if not isinstance(datos, dict):
        log.warning("%s: la sede «%s» no es un diccionario. Sigo sin sus datos.",
                     marca, sede)
        return {}
    return datos


async def disenar(pedido: dict, salida: Path) -> tuple[bool, str, dict]:
    """Genera las piezas. Devuelve (ok, titulo, metricas)."""
    salida.mkdir(parents=True, exist_ok=True)
    marca = _marca(pedido)
    ficha = _ficha(marca)
    sede = pedido.get("sede") or ficha.get("sede_por_defecto", "")
    datos = _sede(marca, ficha, sede)

    _subidas = _traer_adjuntos(pedido, marca)
    reglas, version_manual = _reglas_de_marca(marca)
    prompt = PROMPT.format(
        texto=pedido["texto"], sede=sede, cuando=pedido["cuando"],
        quien=pedido["quien"], formatos=_formatos(pedido.get("formatos")),
        fotos_subidas=_subidas[0], videos_subidos=_subidas[1],
        fotos_elegidas=", ".join(pedido.get("fotos_elegidas") or []) or "ninguna",
        logo_socio=_subidas[2] or "ninguno",
        marca_nombre=ficha.get("nombre", marca),
        contacto=datos.get("contacto", ""),
        sede_extra=("\n" + datos["extra"]) if datos.get("extra") else "",
        acento=datos.get("acento", ""),
        reglas_marca=reglas,
        regla_telefono=ficha.get(
            "regla_telefono",
            "Poné el teléfono sólo si el pedido lo pide."),
        salida=salida,
    )

    modelo = _modelo(pedido)
    ultimo, met = await _correr(prompt, modelo, salida, marca)

    # La red del modelo barato: si no dejó ninguna pieza, se rehace una sola
    # vez con el caro antes de darla por perdida. Un reintento cuesta menos que
    # un pedido que vuelve como error y hay que volver a escribir a mano.
    if not _piezas(salida) and modelo != config.MODELO_COMPLEJO:
        log.warning("%s no dejó ninguna pieza; reintento con %s",
                    modelo, config.MODELO_COMPLEJO)
        ultimo2, met2 = await _correr(prompt, config.MODELO_COMPLEJO, salida, marca)
        if met2:
            # El costo del intento fallido igual se pagó: se suma, si no el
            # promedio del mes miente justo en los casos que salen caros.
            met2["costo_usd"] = round((met2.get("costo_usd") or 0)
                                      + (met.get("costo_usd") or 0), 5)
            met2["reintento"] = True
            met2["modelo_previo"] = modelo
            met, ultimo = met2, ultimo2 or ultimo

    # Con qué versión del manual se hizo esta pieza. Es una línea y evita una
    # investigación entera: cuando el club diga «desde ayer salen mal», la
    # respuesta está en comparar este número entre una pieza buena y una mala,
    # en vez de deducir qué cambió.
    if version_manual is not None and isinstance(met, dict):
        met["manual"] = version_manual

    titulo = _titulo(ultimo) or "Pieza"
    generadas = _piezas(salida)
    if not generadas:
        log.error("el agente no generó ninguna pieza para la fila %s", pedido["fila"])
        return False, titulo, met
    log.info("fila %s -> %d archivos", pedido["fila"], len(generadas))
    return True, titulo, met


# Los chips del chat de Lovable, traducidos a lo que entiende render.py.
MEDIDAS = {
    "post": "post (1080x1080, cuadrado)",
    "vertical": "vert (1080x1350, vertical de feed)",
    "vert": "vert (1080x1350, vertical de feed)",
    "story": "story (1080x1920)",
    # OJO: `reel` es la TAPA (una imagen fija) y `video` es el reel de verdad
    # (un mp4). Son dos cosas distintas y el chip del chat también. Si se les
    # da la misma clave, Python se queda con la última y la tapa de reel
    # empieza a devolver un video sin que nadie se entere.
    "reel": "tapa de reel (1080x1920, una imagen fija)",
    "pdf": "presentación PDF (16:9, un archivo .pdf con varios slides)",
    "video": "reel en video (1080x1920 vertical, un .mp4 de unos 12 segundos)",
    # OJO con este: durante un tiempo decía «usá la plantilla `carrusel`» a
    # secas, y eso convertía el chip en una orden. El 8/8/2026 se pidieron los
    # horarios libres marcando este chip y salieron carruseles de cinco
    # diapositivas, aun con `horarios` ya desplegada: el agente estaba
    # obedeciendo esta línea. El chip elige un FORMATO —varias imágenes que se
    # leen deslizando—, no una plantilla.
    "carrusel": ("carrusel de feed (3 a 6 imágenes encadenadas que se leen "
                 "deslizando, TODAS en 1080x1350 salvo que pidan cuadrado). "
                 "Normalmente se arma con la plantilla `carrusel`, pero si el "
                 "contenido tiene una plantilla propia —por ejemplo horarios "
                 "libres, que van en `horarios`— usá esa, una imagen por "
                 "bloque, y decilo en notas.txt"),
    "secuencia": ("secuencia de 3 stories (1080x1920 cada una, se ven una "
                  "atrás de otra; usá la plantilla `secuencia`)"),
}


def _formatos(elegidos) -> str:
    """La persona marca los chips; el agente tiene que respetarlos."""
    pedidos = [f for f in (elegidos or []) if f in MEDIDAS]
    if not pedidos:
        pedidos = ["post"]
    return " · ".join(MEDIDAS[f] for f in pedidos)


def _contar_herramientas(msg, cuenta: dict) -> None:
    """Cuenta qué herramienta usó el agente en cada turno.

    Existe porque el costo de una pieza es casi lineal en la cantidad de
    turnos —el contexto entero se relee en cada uno— y hasta acá sabíamos
    CUÁNTOS turnos hubo pero no en qué se fueron. Una pieza de Clínica pasó de
    15 a 27 turnos y de US$ 0,34 a 0,62 sin que nadie pudiera decir en qué.

    Un `Read` de un PNG y un `Bash` que renderiza cuestan lo mismo en turnos y
    cosas muy distintas en contexto: la imagen se queda adentro de la
    conversación hasta el final. Sin este desglose, optimizar es adivinar.

    Se guarda en `metricas` de cada diseño: `{"Bash": 9, "Read": 6, ...}`.
    """
    contenido = getattr(msg, "content", None)
    if not isinstance(contenido, list):
        return
    for b in contenido:
        # El SDK puede cambiar los nombres de clase; el pato importa más.
        nombre = getattr(b, "name", None)
        if nombre and type(b).__name__.lower().startswith("tooluse"):
            cuenta[str(nombre)] = cuenta.get(str(nombre), 0) + 1


def _texto(msg) -> str:
    contenido = getattr(msg, "content", None)
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        partes = [getattr(b, "text", "") for b in contenido]
        return " ".join(p for p in partes if p)
    return ""


def _titulo(texto: str) -> str:
    m = re.search(r"LISTO[:\s]+(.+)", texto)
    if not m:
        return ""
    limpio = re.sub(r"[\\/:*?\"<>|]", " ", m.group(1)).strip()
    return " ".join(limpio.split()[:6])
