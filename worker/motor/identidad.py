# -*- coding: utf-8 -*-
"""Una marca hecha sólo de datos, vista desde el motor.

── Qué resuelve ───────────────────────────────────────────────────────────

Que dar de alta un cliente no requiera escribir Python. Antes del 2/9/2026 una
marca eran 300 a 450 líneas propias —colores, hoja de estilo, logo, once
ayudantes de dibujo— más su `marca.py` enchufándolas al motor. Ahora una marca
es:

    .claude/skills/<marca>/
      marca.json          ← con un bloque «identidad»: colores, formatos,
                             tipografías, logos, componentes, y lo del reel
      estilo.css          ← las clases que usan sus plantillas
      fonts/  assets/     ← los archivos que la identidad nombra
      plantillas/<id>/    ← plantilla.json + plantilla.html, como siempre
      marca.py            ← tres líneas: `from motor.identidad import cargar`

`cargar(carpeta)` lee eso y devuelve un objeto que cumple `motor.contrato`
—`C`, `FORMATOS`, `BASE_CSS`, `PLANTILLAS`, `logo`— con los ayudantes de
`motor.componentes` ya atados a los tokens de la marca. Para el resto del
motor es indistinguible de un `marca.py` escrito a mano: se comprobó con
Stadium comparando las 20 salidas byte a byte.

── El bloque «identidad» de marca.json ───────────────────────────────────

    "identidad": {
      "colores":  {"naranja": "#FF6600", "tinta": "#222222", …},
      "roles":    {"acento": "naranja", "claro": "blanco", "tinta": "tinta"},
      "formatos": {"post": [1080, 1080], "story": [1080, 1920], …},
      "tipografias": [{"familia": "Arch", "archivo": "fonts/Archivo-var.ttf",
                       "pesos": "100 900"}],
      "logo": {"archivo": "assets/logo.svg", "ratio": 8.207, "ancho": 300},
      "iso":  {"archivo": "assets/iso.svg",  "ratio": 1.236, "alto": 96},
      "componentes": {"barra": {"texto": "stadium.com.uy"}},
      "paletas": {…}, "voces": {…}, "zonas_seguras": {…},
      "acento_por_defecto": "naranja",
      "reel": {"tipografias": ["Montserrat-Black.ttf", "Montserrat-SemiBold.ttf"],
               "animo_musica": "club", "acento": "naranja"},
      "carrusel": {"color_cromo": "tinta", "fuente_cromo": "'Arch',sans-serif",
                   "fuente_texto": "'Arch',sans-serif"},
      "vocabulario": "Hablamos de …"
    }

Un color se nombra por su nombre («naranja») en todos lados; el motor lo
resuelve. Un valor que empieza con `$` dentro de las paletas es también un
nombre de color.

Lo que una marca NO puede hacer como datos: `DIAPOS` —los cuerpos de un
carrusel— y `PRESENTACION`. Todavía son Python. Una marca que los tenga los
declara en su `marca.py` al lado del `cargar`, y pisan a los del motor.
"""
from __future__ import annotations

import json
import pathlib
import types

from motor import componentes, plantillas as _plantillas


class IdentidadIncompleta(Exception):
    pass


class Identidad:
    """Los tokens de la marca, leídos de `marca.json`."""

    def __init__(self, carpeta: pathlib.Path, datos: dict, ficha: dict):
        self.carpeta = carpeta
        falta = [k for k in ("colores", "formatos", "tipografias", "logo")
                 if not datos.get(k)]
        if falta:
            raise IdentidadIncompleta(
                f"a la identidad de «{carpeta.name}» le falta: {', '.join(falta)}")
        self.C = dict(datos["colores"])
        self.roles = {"acento": None, "claro": None, "tinta": None,
                      **(datos.get("roles") or {})}
        for rol, nombre in self.roles.items():
            if nombre is None or nombre not in self.C:
                raise IdentidadIncompleta(
                    f"«{carpeta.name}»: el rol «{rol}» tiene que nombrar un "
                    f"color de `colores`; llegó {nombre!r}")
        self.FORMATOS = {k: tuple(v) for k, v in datos["formatos"].items()}
        self.tipografias = datos["tipografias"]
        self.logo = datos["logo"]
        self.iso = datos.get("iso")
        self.componentes = datos.get("componentes") or {}
        self.web = ficha.get("web") or ""
        self.VOCES = datos.get("voces") or {}
        self.PALETAS = {n: {k: self._resolver(v) for k, v in p.items()}
                        for n, p in (datos.get("paletas") or {}).items()}
        self.ZONAS_SEGURAS = datos.get("zonas_seguras") or None
        self.acento_por_defecto = datos.get("acento_por_defecto") or self.roles["acento"]
        self.reel = datos.get("reel") or {}
        self.carrusel = datos.get("carrusel") or {}
        self.vocabulario = datos.get("vocabulario") or ""
        self.nombre = ficha.get("nombre") or carpeta.name

    def _resolver(self, v):
        if isinstance(v, str) and v.startswith("$"):
            nombre = v[1:]
            if nombre not in self.C:
                raise IdentidadIncompleta(f"«{v}» no es un color de esta marca")
            return self.C[nombre]
        return v

    def archivo_texto(self, relativo: str) -> str:
        ruta = self.carpeta / relativo
        if not ruta.exists():
            raise IdentidadIncompleta(
                f"«{self.carpeta.name}» nombra {relativo} y no está")
        return ruta.read_text(encoding="utf-8")

    # ── Lo que el contrato pide como texto ────────────────────────────────
    @property
    def FONT_CSS(self) -> str:
        lineas = [f"@font-face{{font-family:'{t['familia']}';src:url('{t['archivo']}');"
                  f"font-weight:{t['pesos']}}}" for t in self.tipografias]
        return "\n" + "\n".join(lineas) + "\n"

    @property
    def BASE_CSS(self) -> str:
        estilo = self.carpeta / "estilo.css"
        if not estilo.exists():
            raise IdentidadIncompleta(f"«{self.carpeta.name}» no tiene estilo.css")
        return self.FONT_CSS + "\n" + estilo.read_text(encoding="utf-8")


def cargar(archivo_marca) -> types.SimpleNamespace:
    """El módulo de marca, armado a partir de la carpeta de `marca.py`.

    Se llama desde el `marca.py` de tres líneas de cada marca:

        from motor.identidad import cargar
        globals().update(vars(cargar(__file__)))

    Devuelve un espacio de nombres con todo lo que el contrato y el resto del
    motor esperan: mayúsculas para datos y registros, minúsculas para los
    ayudantes de dibujo —que es la convención con la que `plantillas._ayudas`
    los reconoce sin lista—.
    """
    carpeta = pathlib.Path(archivo_marca).resolve()
    if carpeta.is_file():
        carpeta = carpeta.parent
    ficha = json.loads((carpeta / "marca.json").read_text(encoding="utf-8"))
    datos = ficha.get("identidad")
    if not datos:
        raise IdentidadIncompleta(
            f"el marca.json de «{carpeta.name}» no tiene el bloque «identidad»")
    ident = Identidad(carpeta, datos, ficha)

    m = types.SimpleNamespace()
    m.__name__ = carpeta.name
    m.AQUI = carpeta
    m.NOMBRE = ident.nombre
    m.C = ident.C
    m.FORMATOS = ident.FORMATOS
    m.FONT_CSS = ident.FONT_CSS
    m.BASE_CSS = ident.BASE_CSS
    m.VOCES = ident.VOCES
    m.PALETAS = ident.PALETAS
    m.ZONAS_SEGURAS = ident.ZONAS_SEGURAS or componentes.ZONAS_SEGURAS
    m.ACENTO_POR_DEFECTO = ident.acento_por_defecto
    m.VOCABULARIO = ident.vocabulario

    # Los ayudantes, atados a esta marca. Sólo los que la identidad puede
    # dibujar: sin isotipo declarado no hay `iso`, y una plantilla que lo
    # llame falla con nombre —StrictUndefined— en vez de dibujar nada.
    for nombre, fabrica in componentes.TODOS.items():
        fn = fabrica(ident)
        if fn is not None:
            fn.__name__ = nombre
            setattr(m, nombre, fn)

    # El reel y el carrusel: los mismos nombres que leía `reelero`, con los
    # colores ya resueltos.
    r = ident.reel
    if r.get("tipografias"):
        m.TIPO_REEL = tuple(r["tipografias"])
    m.ANIMO_MUSICA = r.get("animo_musica", "club")
    m.ACENTO_REEL = ident.C[r.get("acento", ident.roles["acento"])]
    cr = ident.carrusel
    m.COLOR_CROMO = ident.C[cr["color_cromo"]] if cr.get("color_cromo") else ident.C[ident.roles["claro"]]
    if cr.get("fuente_cromo"):
        m.FUENTE_CROMO = cr["fuente_cromo"]
    if cr.get("fuente_texto"):
        m.FUENTE_TEXTO = cr["fuente_texto"]

    # Las plantillas, todas como datos: no queda ninguna escrita en Python.
    m.PLANTILLAS = _plantillas.cargar(carpeta, m)
    m.ESCRITAS_EN_PYTHON = ()
    # El catálogo cuenta lo del carrusel sólo si la marca lo sabe hacer. Una
    # marca de datos no tiene `DIAPOS` salvo que su `marca.py` lo agregue al
    # lado del `cargar`, así que se mira sobre el módulo ya armado y no acá.
    m.CATALOGO = lambda: _plantillas.catalogo(
        carpeta, (), con_carrusel=hasattr(m, "DIAPOS"))
    return m
