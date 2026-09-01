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

from motor import legibilidad

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

    ayudas["plan_titular"] = _plan_titular
    # El degradé que entrega el velo medido justo donde arranca el texto. Va
    # de la mano de `plan_titular` —uno mide y el otro dibuja lo medido— y es
    # igual de agnóstico de marca, así que vive en el mismo lugar.
    ayudas["degrade"] = legibilidad.degrade
    return ayudas


def _pagina(marca, raiz, ayudas, contrato, compilada, data, fmt):
    """El HTML completo de una pieza. El único lugar donde se arma una."""
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
    return (f'<!doctype html><html><head><meta charset="utf-8">'
            f'<style>{marca.BASE_CSS}\n.canvas{{height:{m["alto"]}px}} '
            f'</style></head><body>\n'
            f'<div class="canvas">{cuerpo}</div></body></html>')


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

        dibujar.__name__ = contrato["id"]
        dibujar.__doc__ = contrato.get("descripcion", "")
        dibujar.contrato = contrato
        return dibujar

    return {cid: _hacer(c) for cid, c in contratos.items()}


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

CIERRE = """
---

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

## Un carrusel NO necesita una plantilla de carrusel

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

## El VIDEO ya se puede. No lo mandes a `avisar_cambio_motor`

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

## Y si necesita código

`avisar_cambio_motor` queda para lo que de verdad necesita código: un formato o
una medida que no existe, un carrusel que se encadene solo. **Ni el video, ni
el carrusel, ni la secuencia van acá: ésos ya se pueden.** Es la excepción, no
la salida fácil.
"""


def catalogo(raiz, escritas_en_python=()):
    """El catálogo de plantillas de una marca, generado de los contratos.

    Es la mitad del punto de todo esto: el mismo archivo que dibuja el
    formulario para una persona le describe la plantilla al agente. Una
    plantilla publicada queda disponible en la pieza siguiente sin que nadie
    actualice un texto a mano en otro lado.

    `notas` sale del contrato y se escribe a mano: los campos se declaran, el
    oficio se cuenta. Sin eso el catálogo pierde lo mejor del skill.
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
    partes.append(CIERRE.strip())
    return "\n".join(partes)
