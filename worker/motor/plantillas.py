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
    """
    ayudas = {n: getattr(marca, n)
              for n in ("logo", "aros", "blob", "escudo", "marco", "cinta")
              if hasattr(marca, n)}

    def _plan_titular(foto, acento, oscuro, zona):
        """Cuánto contraste hay en la franja donde cae el titular.

        Vive acá y no en la plantilla porque medir una foto le sirve a
        cualquier marca. La plantilla decide qué hacer con la respuesta; el
        motor la calcula. Las rutas del spec son relativas a la carpeta de la
        marca, así que se resuelven contra `raiz`.
        """
        ruta = pathlib.Path(foto)
        if not ruta.is_absolute():
            ruta = pathlib.Path(raiz) / ruta
        return legibilidad.plan_titular(str(ruta), acento, oscuro=oscuro,
                                        zona=tuple(zona))

    ayudas["plan_titular"] = _plan_titular
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
        ac=marca.C[d.get("acento") or contrato.get("acento_por_defecto", "lima")],
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

`avisar_cambio_motor` queda para lo que de verdad necesita código: el video,
los efectos, un formato que no existe, la estructura del carrusel. Es la
excepción, no la salida fácil.
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
