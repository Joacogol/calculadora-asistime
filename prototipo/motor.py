# -*- coding: utf-8 -*-
"""Motor de plantillas: interpreta plantillas que son DATOS, no código.

Una plantilla es una carpeta con dos archivos:

    plantillas/<id>/plantilla.html   el diseño, con {{ campos }}
    plantillas/<id>/plantilla.json   el contrato: formatos, medidas y campos

El motor no sabe nada de ninguna plantilla en particular. Agregar una es
crear una carpeta; no se toca este archivo ni se despliega nada.
"""
import json
import pathlib

import jinja2

from brand import C, FONT_CSS, LOGO_CSS, FORMATOS, logo, aros, blob

ROOT = pathlib.Path(__file__).parent
DIR_PLANTILLAS = ROOT / "plantillas"
BASE_CSS = FONT_CSS + LOGO_CSS + (ROOT / "marca" / "base.css").read_text(encoding="utf-8")


def cargar(id_plantilla):
    """Devuelve (contrato, html) de una plantilla."""
    carpeta = DIR_PLANTILLAS / id_plantilla
    contrato = json.loads((carpeta / "plantilla.json").read_text(encoding="utf-8"))
    html = (carpeta / "plantilla.html").read_text(encoding="utf-8")
    return contrato, html


def listar():
    """Todas las plantillas disponibles, leídas del disco."""
    return sorted(p.name for p in DIR_PLANTILLAS.iterdir() if (p / "plantilla.json").exists())


def _completar(contrato, data):
    """Aplica valores por defecto y avisa si falta algo requerido."""
    d = dict(data)
    faltan = []
    for campo in contrato["campos"]:
        if campo["id"] not in d or d[campo["id"]] in (None, ""):
            if "default" in campo:
                d[campo["id"]] = campo["default"]
            elif campo.get("requerido"):
                faltan.append(campo["id"])
    if faltan:
        raise ValueError(
            f"La plantilla '{contrato['id']}' necesita: {', '.join(faltan)}"
        )
    return d


def componer(id_plantilla, data, fmt="post"):
    """Devuelve el HTML completo de una pieza, listo para renderizar."""
    contrato, plantilla_html = cargar(id_plantilla)

    if fmt not in contrato["formatos"]:
        raise ValueError(
            f"La plantilla '{id_plantilla}' no tiene formato '{fmt}'. "
            f"Tiene: {', '.join(contrato['formatos'])}"
        )

    d = _completar(contrato, data)
    m = contrato["medidas"][fmt]

    # autoescape=False replica el comportamiento de hoy: los campos entran
    # crudos y algunos traen <br> a propósito. Cuando el estudio deje que
    # un dato venga de un pedido de chat, esto pasa a escaparse y los
    # saltos de línea se declaran como campo "texto_multilinea".
    entorno = jinja2.Environment(autoescape=False, undefined=jinja2.StrictUndefined)
    cuerpo = entorno.from_string(plantilla_html).render(
        d=d,
        m=m,
        c=C,
        ac=C[d.get("acento", "blanco")],
        fmt=fmt,
        logo=logo,
        aros=aros,
        blob=blob,
    )

    return (
        f'<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}\n'
        f'.canvas{{height:{m["alto"]}px}} </style></head><body>\n'
        f'<div class="canvas">{cuerpo}</div></body></html>'
    )


def catalogo():
    """El catálogo que lee el diseñador-IA. Se genera solo desde los contratos.

    Es el punto de todo esto: cuando alguien crea una plantilla en el estudio,
    el agente la conoce en la pieza siguiente, sin que nadie le explique nada.
    """
    lineas = []
    for id_plantilla in listar():
        contrato, _ = cargar(id_plantilla)
        campos = ", ".join(
            c["id"] + ("" if c.get("requerido") else "?") for c in contrato["campos"]
        )
        lineas.append(
            f"- **{contrato['id']}** — {contrato['descripcion']}\n"
            f"  · Cuándo: {contrato.get('cuando_usarla', '—')}\n"
            f"  · Formatos: {', '.join(contrato['formatos'])}\n"
            f"  · Campos: {campos}"
        )
    return "\n".join(lineas)
