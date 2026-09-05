# -*- coding: utf-8 -*-
"""Plantillas que son datos, no código.

Una plantilla vive en una carpeta con dos archivos:

    plantillas/<id>/plantilla.html   el diseño, con {{ campos }}
    plantillas/<id>/plantilla.json   el contrato: formatos, medidas, campos, notas

`cargar(carpeta, marca)` devuelve un dict `{id: función(data, formato) -> html}`
con **la misma firma que las plantillas escritas en Python**. Por eso una marca
puede tener las dos cosas conviviendo y el resto del motor no se entera:

    PLANTILLAS = {"horarios": horarios}                     # las que son programas
    PLANTILLAS.update(plantillas.cargar(AQUI, sys.modules[__name__]))

## Por qué existe

Agregar o corregir una plantilla dejaba de ser trabajo de diseño y pasaba a ser
trabajo de despliegue. Con la plantilla como dato, se edita, se previsualiza y
se publica sin tocar código — y el contrato de campos alcanza para dos cosas al
mismo tiempo: el formulario que ve una persona y el catálogo que lee el agente.

## Lo que NO viene acá

Las plantillas que no son un diseño con variables sino un programa: `horarios`
elige cuerpo tipográfico y cantidad de columnas según cuántas horas entran,
`duelo` mide la foto y arma su propia estructura. Forzarlas a plantilla sería
inventar un lenguaje de programación adentro del HTML. Se quedan en Python, y
lo que tienen de reutilizable se sube a `motor/`.
"""
import json
import pathlib

import jinja2

from . import retoque as _retoque

from motor import legibilidad, silueta

CARPETA = "plantillas"

#: Los nombres que el motor ya usa al renderizar. Una marca que llame `c` o
#: `fmt` a un ayudante suyo pisaría la paleta o el formato y la plantilla
#: saldría mal sin error, así que esos no se toman del módulo de marca.
RESERVADAS = frozenset(("d", "m", "fmt", "t", "c", "ac", "raiz", "plan_titular"))
_ENTORNO = jinja2.Environment(
    # Crudo, como las f-strings de hoy: varios campos traen `<br>` a propósito
    # y los helpers devuelven HTML. Escapar acá rompería las 14 plantillas.
    # Lo que entra por un pedido de chat lo escapa quien arma el `data`.
    autoescape=False,
    undefined=jinja2.StrictUndefined,
    keep_trailing_newline=True,
)


class PlantillaIncompleta(Exception):
    pass


def _contratos(raiz: pathlib.Path):
    base = raiz / CARPETA
    if not base.is_dir():
        return {}
    salida = {}
    for carpeta in sorted(base.iterdir()):
        # Una carpeta que empieza con guión bajo es un borrador: alguien la
        # está escribiendo y todavía no la revisó nadie. El motor no la carga,
        # así que no puede salir en una pieza por accidente mientras se arma.
        # Es una regla de una línea que hace imposible un error que si no
        # dependería de acordarse.
        if carpeta.name.startswith("_") or not carpeta.is_dir():
            continue
        json_ = carpeta / "plantilla.json"
        html = carpeta / "plantilla.html"
        if not (json_.exists() and html.exists()):
            continue
        contrato = json.loads(json_.read_text(encoding="utf-8"))
        contrato["_html"] = html.read_text(encoding="utf-8")
        salida[contrato.get("id", carpeta.name)] = contrato
    return salida


def _completar(contrato, data):
    """Aplica los valores por defecto y falla claro si falta algo requerido."""
    d = dict(data or {})
    faltan = []
    for campo in contrato["campos"]:
        cid = campo["id"]
        vacio = cid not in d or d[cid] is None or d[cid] == ""
        if vacio:
            if "default" in campo:
                d[cid] = campo["default"]
            elif campo.get("requerido"):
                faltan.append(f"{cid} ({campo.get('etiqueta', '')})")
            else:
                d.setdefault(cid, "")
    if faltan:
        raise PlantillaIncompleta(
            f"la plantilla «{contrato['id']}» necesita:\n  · "
            + "\n  · ".join(faltan))
    return d


def _ayudas(marca, raiz):
    """Lo que una plantilla puede usar dentro del HTML.

    Todo lo que la marca ofrece y nada más: una plantilla no puede inventar un
    color ni una tipografía, compone con el vocabulario que ya existe. Eso es
    lo que la mantiene on-brand aunque la haya escrito alguien que nunca vio el
    manual.

    Los nombres salen del módulo de marca, no de una lista escrita acá. La
    lista fija llevaba los de Boss —`aros`, `blob`, `escudo`— y por eso una
    plantilla-dato de otra marca no podía usar su propio vocabulario: Clínica
    dibuja con `puntos`, `pastilla` y `sello`, y ninguno de los tres existía
    para el motor. Peor que no funcionar: fallaba en silencio, porque el
    `hasattr` los descartaba sin decir nada.

    La convención del proyecto alcanza para separarlos sin una lista: los
    ayudantes de dibujo son funciones en minúscula, y lo que va en MAYÚSCULA
    es registro o dato (`PLANTILLAS`, `FORMATOS`, `CATALOGO`, `PRESENTACION`).
    """
    ayudas = {n: getattr(marca, n) for n in dir(marca)
              if not n.startswith("_") and n.islower()
              and n not in RESERVADAS
              and callable(getattr(marca, n, None))}

    def _plan_titular(foto, acento, oscuro, zona,
                      objetivo_blanco=4.0, objetivo_acento=3.0):
        """Cuánto contraste hay en la franja donde cae el titular.

        Vive acá y no en la plantilla porque medir una foto le sirve a
        cualquier marca. La plantilla decide qué hacer con la respuesta; el
        motor la calcula. Las rutas del spec son relativas a la carpeta de la
        marca, así que se resuelven contra `raiz`.

        Los objetivos son parámetros porque cada marca elige su listón: Boss
        se conforma con 4,0 sobre blanco y Clínica pide 4,5. Los valores por
        defecto son los de `legibilidad.plan_titular`, así que una llamada que
        no los pasa —las de Boss— se comporta exactamente igual que antes.
        """
        ruta = pathlib.Path(foto)
        if not ruta.is_absolute():
            ruta = pathlib.Path(raiz) / ruta
        return legibilidad.plan_titular(str(ruta), acento, oscuro=oscuro,
                                        zona=tuple(zona),
                                        objetivo_blanco=objetivo_blanco,
                                        objetivo_acento=objetivo_acento)

    def _recortada(foto) -> bool:
        """¿Esta foto es un objeto recortado y no una foto de fondo?

        Lo necesita la plantilla para razonar bien: «hay foto, así que el texto
        va blanco y sin degradé» es correcto sobre una FOTO —el texto se apoya
        en ella— y es falso sobre un recorte, donde el texto se apoya en el
        fondo de la marca y el recorte está en otra parte de la pieza.

        El 5/9/2026 eso apagó el degradé de la palabra destacada en todas las
        piezas con Tony: el titular salía blanco entero sobre el fondo de
        impacto, que es justo donde el degradé azul→violeta luce.
        """
        if not foto:
            return False
        ruta = pathlib.Path(foto)
        if not ruta.is_absolute():
            ruta = pathlib.Path(raiz) / ruta
        return legibilidad.transparencia(ruta) >= legibilidad.RECORTE_MINIMO

    def _ocupa(foto, ancho, alto, zona, foco="50% 50%") -> float:
        """¿Cuánto de este rectángulo de la pieza tapa el sujeto recortado?

        La plantilla pregunta por la zona donde va a poner algo —el pie, el
        logo, un botón— y decide. El motor sólo mide: ver `motor/silueta.py`.

        Existe porque «ASISTIME.AI» salió cuatro veces escrito encima de la
        oreja de Tony. El guardián de contraste lo veía DESPUÉS de renderizar
        y avisaba; un diseñador no firma sobre el sujeto y después mide si se
        lee, mira dónde está el sujeto y firma en otro lado. Esto es lo que le
        faltaba ver a la plantilla para poder hacer lo mismo.
        """
        ruta = pathlib.Path(foto) if foto else None
        if ruta is not None and not ruta.is_absolute():
            ruta = pathlib.Path(raiz) / ruta
        return silueta.ocupacion(str(ruta) if ruta else "", int(ancho),
                                 int(alto), tuple(zona), foco or "50% 50%")

    ayudas["recortada"] = _recortada
    ayudas["ocupa"] = _ocupa
    ayudas["plan_titular"] = _plan_titular
    # El degradé que entrega el velo medido justo donde arranca el texto. Va
    # de la mano de `plan_titular` —uno mide y el otro dibuja lo medido— y es
    # igual de agnóstico de marca, así que vive en el mismo lugar.
    ayudas["degrade"] = legibilidad.degrade
    return ayudas


def _cuerpo(marca, raiz, ayudas, contrato, compilada, data, fmt):
    """El HTML de ADENTRO del lienzo, y las medidas con las que se dibujó.

    Es lo que comparten una placa y una diapositiva de carrusel: la placa lo
    envuelve en su propia página (`_pagina`); el carrusel lo pone dentro de la
    suya, con el índice y las flechas encima (`motor.carrusel`).
    """
    if fmt not in contrato["medidas"]:
        raise PlantillaIncompleta(
            f"la plantilla «{contrato.get('id', '?')}» no tiene formato "
            f"«{fmt}». Tiene: {', '.join(contrato['medidas'])}")
    d = _completar(contrato, data)
    m = contrato["medidas"][fmt]
    cuerpo = compilada.render(
        d=d, m=m, fmt=fmt, t=contrato,
        c=marca.C,
        # El acento por defecto lo pone la marca, no el motor. Estaba escrito
        # `"lima"` acá —el verde de Boss—, y como ninguno de sus doce contratos
        # lo declara, los doce dependían de esa constante. Para Clínica habría
        # sido un KeyError en la primera pieza: su paleta no tiene «lima».
        ac=marca.C[d.get("acento") or contrato.get("acento_por_defecto")
                   or marca.ACENTO_POR_DEFECTO],
        raiz=str(raiz),
        **ayudas)
    return cuerpo, m


def _css_recorte(raiz, data) -> str:
    """Un objeto recortado no se recorta: se coloca.

    `.bg` lleva `object-fit: cover` en la hoja de todas las marcas, y es lo
    correcto para una foto: llena el lienzo y lo que sobra se va. Aplicado a un
    PNG sin fondo es exactamente lo contrario de lo que haría cualquiera: lo
    agranda hasta llenar y le corta lo que no entra.

    El 4/9/2026 se pidió cuatro veces «la jirafa de Tony en la parte inferior
    mirando hacia arriba» y salieron cuatro cabezas gigantes cortadas al medio.
    Con `contain` la figura entra entera y el `foco` de la foto decide contra
    qué borde se apoya — que es la posición inline de la plantilla y le gana a
    esta regla, así que sigue mandando la foto.

    Se decide midiendo el archivo, no por un campo que alguien tiene que
    acordarse de poner.
    """
    foto = (data or {}).get("foto")
    if not foto:
        return ""
    ruta = pathlib.Path(foto)
    if not ruta.is_absolute():
        ruta = pathlib.Path(raiz) / ruta
    if legibilidad.transparencia(ruta) < legibilidad.RECORTE_MINIMO:
        return ""
    return ".bg{object-fit:contain}"


def _pagina(marca, raiz, ayudas, contrato, compilada, data, fmt):
    """El HTML completo de una pieza. El único lugar donde se arma una.

    Por eso el retoque se inyecta acá y en ningún otro lado: una pieza a
    medida no es un camino aparte del normal, es el camino normal con un
    bloque de estilo más y, si hace falta, una capa dibujada.
    Ver `motor/retoque.py`.
    """
    cuerpo, m = _cuerpo(marca, raiz, ayudas, contrato, compilada, data, fmt)
    # El orden de las tres hojas es la regla entera: la marca pone la base,
    # las capas dibujadas se acomodan encima, y el retoque va último porque
    # tiene que poder pisar a las dos —mover una capa o recolorearla es
    # justamente su trabajo.
    css_capas, capas = _retoque.dibujos(data)
    extra = _retoque.hoja(data)
    # El recorte va DESPUÉS de la hoja de la marca —para pisar su `cover`— y
    # antes del retoque, que tiene que poder pisarlo a él.
    recorte = _css_recorte(raiz, data)
    return (f'<!doctype html><html><head><meta charset="utf-8">'
            f'<style>{marca.BASE_CSS}\n.canvas{{height:{m["alto"]}px}} '
            f'{recorte}{css_capas}{extra}</style></head><body>\n'
            f'<div class="canvas">{cuerpo}{capas}</div></body></html>')


def cargar(raiz, marca):
    """Las plantillas-dato de una marca, como funciones(data, formato) -> html.

    `raiz` es la carpeta de la marca; `marca` el módulo que expone C, FORMATOS,
    BASE_CSS y los helpers gráficos (logo, aros, blob).
    """
    raiz = pathlib.Path(raiz)
    contratos = _contratos(raiz)
    if not contratos:
        return {}

    ayudas = _ayudas(marca, raiz)

    def _hacer(contrato):
        compilada = _ENTORNO.from_string(contrato["_html"])

        def dibujar(data, fmt="post"):
            return _pagina(marca, raiz, ayudas, contrato, compilada, data, fmt)

        def cuerpo(data, fmt="post"):
            return _cuerpo(marca, raiz, ayudas, contrato, compilada, data, fmt)[0]

        dibujar.__name__ = contrato["id"]
        dibujar.__doc__ = contrato.get("descripcion", "")
        dibujar.contrato = contrato
        dibujar.cuerpo = cuerpo
        return dibujar

    return {cid: _hacer(c) for cid, c in contratos.items()}


def como_diapositivas(marca, mapa: dict):
    """`DIAPOS` para una marca de datos: cada tipo de diapositiva, dibujado
    con una de sus plantillas.

    `mapa` es `tipo → id de plantilla`, y sale de `identidad.carrusel.diapos`
    en el marca.json. Hasta el 3/9/2026 un carrusel exigía escribir Python
    —`DIAPOS` era «una de las dos únicas cosas de una marca que todavía son
    código»— y una marca de datos se quedaba sin carruseles. Pero una
    diapositiva es la misma placa de siempre, en el mismo lienzo, con el
    índice encima: no había nada que programar, sólo que enchufar.

    Cada función devuelta cumple la firma de `DIAPOS`: `(data, w, h, acento)
    → html del cuerpo`. El formato se deduce del lienzo —(1080, 1350) es
    `vert`— porque `motor.carrusel` fija UNA proporción para todo el
    carrusel y la manda como medidas, no como nombre. El acento llega como
    color ya resuelto y las plantillas lo esperan como nombre, así que no se
    le pasa: cada plantilla usa el suyo por defecto.

    Devuelve también, como atributo `cromo`, la función que dice de qué color
    van el índice y las flechas sobre cada diapositiva. Lo declara el
    contrato de la plantilla en `cromo`: un nombre de color, o un diccionario
    `valor de estilo → color` con `*` como defecto. Sin eso el índice sale
    del `COLOR_CROMO` de la marca, que sobre una diapositiva oscura no se ve.
    """
    faltan = sorted({pid for pid in mapa.values() if pid not in marca.PLANTILLAS})
    if faltan:
        raise PlantillaIncompleta(
            "el carrusel de esta marca nombra plantillas que no tiene: "
            + ", ".join(faltan))
    for tipo in ("portada", "cierre"):
        if tipo not in mapa:
            raise PlantillaIncompleta(
                f"el carrusel de esta marca necesita la diapositiva «{tipo}»: "
                "un carrusel siempre abre y cierra igual")

    def formato_de(contrato, w, h):
        for nombre, medida in marca.FORMATOS.items():
            if tuple(medida) == (w, h) and nombre in contrato["medidas"]:
                return nombre
        raise PlantillaIncompleta(
            f"la plantilla «{contrato['id']}» no tiene un formato de {w}×{h}")

    def datos_de(s):
        # `tipo` y `cromo` son del carrusel, no de la plantilla; y un `acento`
        # que no sea un nombre de color de la marca es el hex que resolvió el
        # motor, que la plantilla no sabría leer. `responder` sí pasa: la
        # última story de una secuencia lleva la caja de respuesta encima del
        # margen inferior y la plantilla tiene que dejarle el lugar. Y
        # `en_carrusel` le dice que el índice del motor va a ocupar la esquina
        # inferior izquierda, donde una placa suelta firma con la web.
        d = {k: v for k, v in s.items() if k not in ("tipo", "cromo")}
        if "acento" in d and d["acento"] not in marca.C:
            d.pop("acento")
        d["en_carrusel"] = True
        return d

    def hacer(pid):
        fn = marca.PLANTILLAS[pid]

        def diapo(s, w, h, ac):
            return fn.cuerpo(datos_de(s), formato_de(fn.contrato, w, h))
        diapo.__name__ = f"diapo_{pid}"
        return diapo

    diapos = {tipo: hacer(pid) for tipo, pid in mapa.items()}

    def cromo(tipo, s):
        contrato = marca.PLANTILLAS[mapa[tipo]].contrato if tipo in mapa else None
        regla = (contrato or {}).get("cromo")
        if not regla:
            return None
        if isinstance(regla, dict):
            estilo = _completar(contrato, datos_de(s)).get("estilo")
            regla = regla.get(str(estilo)) or regla.get("*")
        return marca.C.get(regla, regla) if regla else None

    cromo.__name__ = "cromo_diapo"
    return diapos, cromo


def compilar(marca, raiz, contrato, html, data, fmt="post"):
    """El HTML de una pieza a partir de una plantilla que todavía no se guardó.

    Es lo que usa el estudio para previsualizar. Pasa por exactamente el mismo
    camino que una plantilla publicada —misma hoja de estilo, mismos helpers,
    mismos valores por defecto, mismas medidas— y eso no es una coincidencia
    que haya que mantener: es la misma función.

    Un preview que dibuja por otro lado deja de servir para decidir. Se ve bien
    en el editor y sale distinto en la pieza, y a partir de ahí nadie confía en
    lo que ve.
    """
    raiz = pathlib.Path(raiz)
    return _pagina(marca, raiz, _ayudas(marca, raiz), contrato,
                   _ENTORNO.from_string(html), data, fmt)


#: Lo que va antes y después de la lista, en el documento que lee el agente.
#: Vive acá y no escrito a mano en Asistime porque el documento se regenera
#: entero en cada despliegue: lo que se edite allá se pierde en el siguiente.
ENCABEZADO = """
Las plantillas que el motor sabe dibujar. **Este documento no se edita a mano:**
lo genera el motor desde el contrato de cada plantilla y lo republica solo.

Cada plantilla dice sus **campos**. Los marcados con `?` son opcionales: si van
vacíos, el bloque que los contiene desaparece entero, rótulo incluido. Los que
no tienen `?` son obligatorios y el motor rechaza la pieza sin ellos.

---
"""

#: El catálogo termina siempre igual, salvo por el bloque del carrusel que
#: va justo en el medio — y por eso son dos y no uno. Pegados en ese orden
#: dan el texto de siempre, carácter por carácter: mover ese bloque al final
#: le cambiaría el documento a Boss y a Clínica sin motivo, y además dejaría
#: la última línea contra el `---` del cierre, que en markdown convierte esa
#: línea en un título.
CIERRE_ANTES = """
---

## Un pedido a medida que vale para ESA pieza: `retoque`

Antes de fundar una plantilla, mirá si lo que piden es de una sola vez. «Que
el texto tenga un recuadro tipo chimenea», «que el número salga tachado»,
«ponele una cinta en diagonal en la esquina»: eso no es una plantilla nueva,
es la de siempre con algo encima.

Para eso, en el `data` de ese trabajo agregás `retoque` con un bloque de CSS
escrito para esa pieza:

```json
{"plantilla": "titular", "formato": "vert", "data": {
   "titulo": "Se viene el invierno",
   "retoque": ".disp{border:14px solid #B45309;border-radius:22px;padding:36px 40px;box-shadow:inset 0 0 0 6px #FDE68A}"
}}
```

Se aplica DESPUÉS de la hoja de la marca, así que pisa lo que la plantilla
decidió. No se guarda en ningún lado: la pieza siguiente vuelve a salir como
siempre.

**Cuándo NO es un retoque.** Si lo mismo se va a pedir de nuevo —es un tipo de
pieza, no un capricho de hoy— entonces sí es `crear_plantilla`. La pregunta es
«¿esto lo vuelvo a necesitar?». Y si el retoque te está quedando enorme,
también: más de un par de reglas es una plantilla que no se quiso escribir.

**Cuatro cosas que el retoque no puede hacer** y te las va a rechazar con el
motivo: cerrar la etiqueta `</style>`, traer una hoja o una imagen de internet
—un SVG embebido en `data:` sí—, usar `position: fixed`, y pasar de cuatro mil
caracteres.

**Y una que sí puede y por eso hay que mirarla:** un retoque puede tapar el
logo, correr el pie o desbordar el texto. Ninguna validación lo distingue de
un pedido legítimo. Así que una pieza con retoque **se mira antes de
entregarla** — y si algo quedó pisado, se corrige y se vuelve a renderizar.

En un carrusel el retoque va en la diapositiva que lo necesita, no en el
carrusel entero.

## Y si lo que falta es una FORMA: `dibujo`

El retoque pinta lo que la plantilla ya dibujó. No agrega una consola de DJ,
una chimenea ni una guirnalda de notas: con CSS se cambia el aspecto de algo
que existe, no se inventan trazos. Para eso, en el mismo `data`, va `dibujo`
con SVG:

```json
{"plantilla": "titular", "formato": "story", "data": {
   "titulo": "Mañana es VIERNES",
   "dibujo": [
     {"clase": "consola", "svg": "<svg viewBox='0 0 1080 1920'>…</svg>"},
     {"clase": "marco", "atras": true, "svg": "<svg viewBox='0 0 1080 1920'>…</svg>"}
   ],
   "retoque": ".dibujo.consola{opacity:.42}"
}}
```

Cada capa cubre el lienzo entero y el SVG se estira a ese tamaño, así que
conviene un `viewBox` propio: se dibuja en esas coordenadas y sale igual en
cualquier formato. Va encima de la plantilla, salvo `"atras": true`, que la
manda detrás del texto y delante del fondo — que es donde va un marco. La
`clase` sirve para apuntarle desde el retoque, y ahí está la división: el
dibujo pone las formas y el retoque las acomoda.

Hasta 4 capas y 12.000 caracteres cada una. Se parsea como XML antes de
entrar, así que tiene que cerrar todas sus etiquetas y tener una sola raíz
`<svg>`; y no entran `script`, `style`, `foreignObject` ni nada traído de
internet.

**Y no entra TEXTO: `text`, `tspan` y `textPath` se rechazan.** El texto de
una pieza lo pone la plantilla, con la tipografía de la marca, y sobre él
corren tres mediciones que un texto dibujado apaga sin avisar: el que lo
achica si no entra en el lienzo, el que avisa si algo le queda encima al logo
o al pie, y el que avisa si se mezclaron alineaciones. Para MOVER o AGRANDAR
un titular está el `retoque`, no el dibujo.

Un dibujo puede traer una foto adentro **cuando la foto va DENTRO DE UNA
FORMA**: `<image href="assets/subidas/01-foto.jpg" …/>`, con las rutas
relativas a la carpeta de la marca. Eso es lo que permite «la captura adentro
de un teléfono» o «la foto en un recuadro con sombra», que la plantilla no sabe
hacer.

**Pero la foto principal de la pieza va en `foto`, nunca adentro de un
`dibujo`.** Es la diferencia entre una foto que está adentro de algo dibujado y
una foto que ES la pieza. Metida en un dibujo se apagan, sin que nada falle,
las cuatro cosas que el motor sabe hacer con una foto: encuadrarla con
`contain` para que un recorte no salga cortado, medir el velo, usar el `foco`
que el banco ya tiene guardado para ese archivo, y avisar si la firma de la
marca queda apoyada sobre el sujeto.

Y para ubicarla no hace falta calcular nada: **`foco` es la posición dentro del
lienzo**. `"50% 100%"` la apoya en el borde de abajo —que es lo que se pide
cuando alguien dice «que arranque desde abajo, sin espacio»—, `"50% 0%"` arriba,
`"50% 50%"` centrada. El 5/9/2026 se pidió cuatro veces «Tony pegado al borde
inferior» y las cuatro se resolvió con un `<image>` en un dibujo, con `x`, `y`,
`width` y `height` calculados a mano — y las cuatro quedó flotando. El `foco`
de esa foto en el banco ya decía `50% 100%`.

**Una captura de pantalla no es una foto.** Recortada y con velo no se lee.
Va como objeto, entera y grande, nunca de fondo completo.

**Los emojis del sistema no son un dibujo.** Se ven distinto en cada
dispositivo y su color no es el de ninguna marca.

**El logo y el pie se tocan por sus variables.** El tamaño de la firma sale
del kit y viaja como respaldo de una variable CSS, así que para agrandarla el
retoque es `.marca-iso{--iso-ancho:110px;--iso-alto:110px}` —y `.marca-logo`
con `--logo-ancho`/`--logo-alto` para el lockup. Poner `width` directamente no
hace nada: el ancho va en el atributo `style` del elemento y le gana a
cualquier clase.

## Si falta una plantilla

No improvises con la más parecida y no digas que no se puede: **armala**. Con
`crear_plantilla` se encarga un molde nuevo — contá qué pieza tiene que
permitir hacer, qué datos lleva cada vez, y si hay alguna de esta lista
parecida, en qué tiene que ser distinta.

Tarda unos cinco minutos y lo que vuelve es un **borrador con su preview**:
existe y se puede ver, pero las piezas no lo usan hasta que alguien lo publica.
Mostráselo a la persona, y recién si le gusta, `publicar_plantilla`.

## Si una de esta lista está mal

Cuando lo que piden es cambiar una que ya existe —«el título de esa plantilla
se ve chico», «que muestre también la dirección»— usá **la misma
`crear_plantilla`, pero con `corrige`** y el id de esa plantilla, tal cual
figura arriba.

Es la diferencia entre corregir la plantilla que se está usando y reemplazarla
por otra parecida. Rehaciéndola se pierden los campos que alguien ya venía
mandando y las decisiones que nadie escribió. Además sale en la mitad del
tiempo.

En `mensaje` va **sólo qué hay que cambiar**, con las palabras de la persona.
No repitas para qué sirve la plantilla: eso ya está.

Lo que vuelve es otra vez un borrador, y vale lo mismo: **la plantilla que se
usa hoy no cambió** hasta que alguien publique la versión nueva.

"""

CIERRE_DESPUES = """## El VIDEO ya se puede. No lo mandes a `avisar_cambio_motor`

Se dice acá, en positivo y con todas las letras, porque este documento se lee
como si mandara sobre todo lo demás — y **una versión vieja de este mismo
párrafo decía que el video necesitaba código**. El 1/9/2026 alguien pidió un
video de una paleta creciendo como un árbol; el agente leyó eso, contestó que
no se podía y anotó un pedido de cambio de motor. Una hora antes el sistema
había hecho exactamente ese video.

Lo que se puede hoy:

- **`crear_video`** — genera el VIDEO y te da el archivo, sin título ni música
  encima. Es lo que se usa cuando piden «un video» a secas, o cuando lo quieren
  ver antes de decidir qué decirle arriba.
- **`crear_reel`** — genera la PIEZA terminada: el mismo video pero ya con el
  título y la música de la marca, listo para subir.
- **`montar_reel`** — editar videos que ya existen: unirlos, sacarles los
  tiempos muertos, subtitularlos. No cuesta créditos.
- **`ver_reel` + `retocar_reel`** — corregir un reel que ya salió sin rehacerlo.

### Un archivo y una pieza no son lo mismo

Es la misma diferencia que ya existe entre `crear_foto` (un archivo) y
`crear_diseno` (una pieza), y vale igual para el video. Quien va a editar el
video después no quiere un título encima; quien lo va a publicar tal cual, sí.
Si el pedido no lo aclara, preguntá — son dos cosas distintas y cuestan lo
mismo.

Y lo que las une: **un video generado se puede convertir en pieza sin volver a
pagarlo.** `estado_reel` devuelve el archivo crudo, y `montar_reel` lo toma
como un clip más. Así que «hacemos el video, lo miramos, y después le ponemos
el texto» es un camino de verdad, no una promesa: el título se cambia todas las
veces que haga falta y sólo se paga la generación una vez.

### Con qué sistema se genera lo elige quien paga

Hay dos —Magnific y fal.ai— y no son intercambiables: cambian el precio, la
duración máxima y la moneda. Por eso un pedido de video **no arranca hasta que
la persona elija**: la herramienta te devuelve las dos opciones con su precio y
su duración, se las mostrás, y recién con la respuesta volvés a llamar. No
elijas vos y no supongas «el de siempre»: es su plata.

**Y no digas un precio de memoria.** Ni «son 1.400 créditos» ni ningún otro
número antes de llamar a la herramienta. Lo que sale depende del sistema, de la
duración y de la calidad: por fal, cinco segundos son US$ 0,40; por Magnific,
diez segundos son 1.400 créditos. Son la misma pieza y no se parecen.

El precio que vale es el que devuelve la herramienta, y viene con la unidad al
lado. Un número dicho de memoria envejece sin que nadie se entere, y sobre un
precio equivocado la persona toma una decisión que no habría tomado. Si todavía
no llamaste, decí que vas a consultar el precio — no lo estimes.

## Y si necesita código

{codigo}
"""


#: Lo que se dice del carrusel y la secuencia — SÓLO si la marca los sabe
#: hacer. Un carrusel se arma encadenando diapositivas, y eso necesita `DIAPOS`
#: en la marca: Boss y Clínica lo tienen, Stadium y Asistime no.
#:
#: Antes esto iba en el CIERRE, o sea en el catálogo de TODAS las marcas. El
#: 2/9/2026, al dar de alta a Asistime, el catálogo le prometía carruseles a
#: una marca cuyo motor los rechaza. Es la peor forma del error: el agente lee
#: que se puede, lo ofrece, y la pieza falla cuatro minutos después con un
#: mensaje que él no puede explicar. Un catálogo que promete de más es peor que
#: uno corto.
CARRUSEL = """## Un carrusel NO necesita una plantilla de carrusel

Esta lista son las plantillas de UNA pieza. `carrusel` y `secuencia` no están
—ni tienen que estar— porque **son formatos, no plantillas**: los arma el motor
encadenando diapositivas, con la portada y el cierre que ya tiene la marca.

Se piden como cualquier otro formato, en `formatos` de `crear_diseno`:

- **`carrusel`** — de 3 a 6 imágenes para el feed, que se leen deslizando.
- **`secuencia`** — 3 stories que se ven una atrás de otra.

Contá en `mensaje` qué va en cada diapositiva, en orden. Eso alcanza.

**No armes una plantilla nueva para hacer un carrusel.** Es el error que da
esta lista si se la lee sola: como no aparece `carrusel`, parece que falta.
Pasó el 28/8/2026 — se pidió un carrusel de seis diapositivas para un servicio
y el agente ofreció construir un molde que no hacía falta.

Una plantilla se arma cuando falta un TIPO DE PIEZA, no cuando falta un
formato.

"""

#: El último párrafo, en sus dos versiones. Para una marca sin `DIAPOS` el
#: carrusel SÍ es un pedido de cambio de motor —es exactamente lo que le
#: falta—, así que el ejemplo cambia de lado en vez de desaparecer.
CODIGO_CON_CARRUSEL = """\
`avisar_cambio_motor` queda para lo que de verdad necesita código: un formato o
una medida que no existe, un carrusel que se encadene solo. **Ni el video, ni
el carrusel, ni la secuencia van acá: ésos ya se pueden.** Es la excepción, no
la salida fácil."""

CODIGO_SIN_CARRUSEL = """\
`avisar_cambio_motor` queda para lo que de verdad necesita código: un formato o
una medida que no existe, o el carrusel — esta marca todavía no lo sabe armar y
es un pedido válido. **El video no va acá: ése ya se puede.** Es la excepción,
no la salida fácil."""


#: Lo que se agrega al párrafo del carrusel cuando la marca es de datos y sus
#: diapositivas son sus propias plantillas: el agente tiene que saber qué
#: tipos puede pedir y con qué campos.
DIAPOS_DE_DATOS = """### Las diapositivas de esta marca

Cada diapositiva de un carrusel o una secuencia se dibuja con una plantilla de
la lista de arriba y lleva **los campos de esa plantilla**. El `tipo` de la
diapositiva elige cuál:

{lista}

`portada` y `cierre` abren y cierran siempre. `cuadro` es el defecto de una
secuencia de stories. Una diapositiva con foto lleva su `foto` como cualquier
placa.

"""


PALETAS = """
## Los fondos de esta marca, y para qué es cada uno

El campo `estilo` de una plantilla elige el fondo. **Elegí por para qué es la
pieza, no por cómo se llama el fondo.**

Se dice acá porque el 5/9/2026 costó dos días de piezas equivocadas: el agente
leyó «degrade» y entendió «el degradé de la marca», así que lo usó para una
pieza de expectativa — y el fondo que la marca reconoce como suyo se llamaba
«oscuro», que sonaba a otra cosa. Las dos veces eligió por el nombre, porque
era lo único que tenía para elegir.

{lista}
"""


def _paletas(marca) -> str:
    """Qué fondos tiene la marca y cuándo va cada uno.

    Una paleta sin `cuando` no se cuenta: mejor que el agente no la conozca a
    que la elija adivinando por el nombre, que es exactamente lo que salió mal.
    """
    filas = []
    for nombre, pal in (getattr(marca, "PALETAS", None) or {}).items():
        cuando = (pal or {}).get("cuando")
        if cuando:
            filas.append(f"- **`{nombre}`** — {cuando}")
    return PALETAS.format(lista="\n".join(filas)) if filas else ""


def catalogo(raiz, escritas_en_python=(), con_carrusel=True, diapos=None,
             marca=None):
    """El catálogo de plantillas de una marca, generado de los contratos.

    Es la mitad del punto de todo esto: el mismo archivo que dibuja el
    formulario para una persona le describe la plantilla al agente. Una
    plantilla publicada queda disponible en la pieza siguiente sin que nadie
    actualice un texto a mano en otro lado.

    `notas` sale del contrato y se escribe a mano: los campos se declaran, el
    oficio se cuenta. Sin eso el catálogo pierde lo mejor del skill.

    `con_carrusel` decide si el catálogo cuenta que se pueden pedir carruseles
    y secuencias. Es `False` para una marca sin `DIAPOS`: el motor los rechaza,
    y prometerlos hace que el agente los ofrezca y la pieza falle después.
    """
    partes = [ENCABEZADO.strip()]
    for cid, c in sorted(_contratos(pathlib.Path(raiz)).items()):
        campos = []
        for campo in c["campos"]:
            marca_ = "" if campo.get("requerido") else "?"
            campos.append(f"{campo['id']}{marca_}")
        partes.append(
            f"### `{cid}` — {c.get('descripcion', '')}\n"
            f"**Cuándo:** {c.get('cuando_usarla', '—')}\n"
            f"**Formatos:** {', '.join(c['medidas'])}\n"
            f"**Campos:** {', '.join(campos)}  ·  `?` = opcional\n"
            + (f"\n{c['notas'].strip()}\n" if c.get("notas") else ""))
    for nombre in escritas_en_python:
        partes.append(
            f"### `{nombre}`\nEscrita en Python — no se edita desde el estudio. "
            f"Ver el SKILL.md.\n")
    carrusel = CARRUSEL if con_carrusel else ""
    if con_carrusel and diapos:
        lista = "\n".join(f"- `{tipo}` → plantilla `{pid}`"
                          for tipo, pid in diapos.items())
        carrusel += DIAPOS_DE_DATOS.format(lista=lista)
    paletas = _paletas(marca)
    if paletas:
        partes.append(paletas.strip())
    cierre = (CIERRE_ANTES + carrusel + CIERRE_DESPUES)
    cierre = cierre.replace(
        "{codigo}", CODIGO_CON_CARRUSEL if con_carrusel else CODIGO_SIN_CARRUSEL)
    partes.append(cierre.strip())
    return "\n".join(partes)
