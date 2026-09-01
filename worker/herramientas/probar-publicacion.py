#!/usr/bin/env python3
"""Prueba que una foto no se dé por perdida porque Instagram tardó un segundo.

    python3 herramientas/probar-publicacion.py

No toca Instagram ni la base: los dos están de mentira acá adentro. Corre en
menos de un segundo y da siempre lo mismo.

## Por qué existe

El 1/9/2026 se pidió publicar una placa de Clínica Preventiva y volvió un error
en portugués: «A mídia não está pronta para ser publicada. Aguarde um momento.»
La pieza estaba bien, la cuenta estaba bien y el pie de foto estaba escrito. Lo
único que pasó es que Meta todavía estaba terminando de procesarla.

Eran dos errores encimados, y por eso hacen falta dos pruebas:

1. **No se le preguntaba si estaba lista.** El worker esperaba a que el
   contenedor dijera FINISHED sólo para los videos. Una foto se publicaba
   derecho, porque una foto está lista al instante — y es verdad casi siempre,
   que es la clase de «casi siempre» que falla un martes cualquiera.
2. **Y cuando Meta avisó, se lo tomó como definitivo.** El mensaje dice
   textualmente «aguarde un momento» y el posteo se marcó `error`, que es el
   estado del que no se vuelve. Con reintentar alcanzaba.

El primero es la causa; el segundo es lo que convirtió una demora de un segundo
en un posteo perdido. Arreglar uno solo dejaría la mitad del agujero abierto.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import instagram as I                                # noqa: E402
from app import publicador                                    # noqa: E402
from app.instagram import _traducir                           # noqa: E402

# `esperar` duerme entre pregunta y pregunta, que es lo correcto contra Meta y
# una pérdida de tiempo contra un Instagram de mentira. Se anula acá y no
# adentro de `esperar` para no cambiar el código que se está probando.
I.time.sleep = lambda _s: None


class ClienteFalso:
    """Lo mínimo de `supa.Cliente` que toca `procesar`: tomar y marcar."""

    marca = "clinica"

    def __init__(self):
        self.estado = "programado"
        self.campos: dict = {}

    def tomar_publicacion(self, *_a, **_k):
        return True

    def marcar_publicacion(self, _id, estado, **campos):
        self.estado = estado
        self.campos.update(campos)


class InstagramFalso:
    """Un Instagram de mentira que se comporta como el de verdad en lo que importa.

    Lo importante es que **rechaza publicar un contenedor que todavía no está
    listo**, con el mismo código con el que lo rechaza Meta. Sin eso, esta
    prueba no prueba nada: la primera versión dejaba publicar siempre, así que
    pasaba igual contra el código que ni preguntaba si la foto estaba lista.
    Un Instagram de mentira más amable que el de verdad convierte la prueba en
    un adorno.
    """

    def __init__(self, estados, al_publicar=None):
        #: Qué devuelve `estado()` en cada llamada sucesiva.
        self.estados = list(estados)
        #: Un error puesto a mano, para los casos que no son sobre la espera.
        self.al_publicar = al_publicar
        self.listo = False
        self.publicaciones = 0

    def estado(self, _contenedor):
        code = self.estados.pop(0) if self.estados else "FINISHED"
        self.listo = self.listo or code == "FINISHED"
        return code, ""

    # `esperar` es el de verdad: es justamente lo que se está probando.
    esperar = publicador.Instagram.esperar

    def publicar(self, _contenedor):
        self.publicaciones += 1
        if self.al_publicar:
            raise self.al_publicar
        if not self.listo:
            raise _traducir({"code": 9007, "error_subcode": 2207027,
                             "error_user_msg": "A mídia não está pronta para "
                                               "ser publicada."})
        return "17900000000000000"

    def permalink(self, _media):
        return "https://www.instagram.com/p/Dxxxxxxxxxx/"


def _fila():
    # Con `contenedor` ya puesto se saltea el armado de la pieza, que baja
    # archivos y habla con el Storage. Lo que se prueba está después de eso.
    return {"id": "63f9c45a", "tipo": "post", "estado": "subiendo",
            "contenedor": "18000000000000000", "intentos": 0, "esperas": 0,
            "urls": ["https://ejemplo/placa.jpg"]}


def main() -> int:
    fallas = []

    # ── 1 · la foto que todavía se está procesando ────────────────────────
    #
    # Meta contesta IN_PROGRESS dos veces y después FINISHED. Antes del arreglo
    # no se preguntaba nada: se publicaba de una y Meta rechazaba.
    cli, ig = ClienteFalso(), InstagramFalso(["IN_PROGRESS", "IN_PROGRESS",
                                              "FINISHED"])
    publicador.procesar(cli, ig, _fila())
    if cli.estado != "publicado":
        fallas.append(
            f"✗ la foto quedó en «{cli.estado}» en vez de publicarse.\n"
            f"  Es el error del 1/9: no se espera a que Meta termine de "
            f"procesar una foto, sólo un video.")
    else:
        print("✓ espera a que la foto esté lista y recién ahí la publica")

    # ── 2 · y si igual la agarra a mitad de camino, se reintenta ──────────
    #
    # Entre preguntar y publicar hay una carrera que ninguna espera cierra. El
    # código 9007 dice «esperá un momento»: es lo más temporal que existe, y
    # marcarlo `error` es tirar un posteo que iba a salir bien solo.
    # El error se arma con `_traducir`, que es quien decide si algo se
    # reintenta. Escribirlo a mano acá probaría lo que yo creo que decide, no
    # lo que decide.
    cli, ig = ClienteFalso(), InstagramFalso(["FINISHED"])
    ig.al_publicar = _traducir({"code": 9007, "error_subcode": 2207027,
                                "error_user_msg": "A mídia não está pronta "
                                                  "para ser publicada."})
    publicador.procesar(cli, ig, _fila())
    if cli.estado != "programado":
        fallas.append(
            f"✗ Instagram dijo «esperá un momento» y el posteo quedó en "
            f"«{cli.estado}».\n  Un error que pide esperar se reintenta; "
            f"«error» es el estado del que no se vuelve.")
    else:
        print("✓ un «todavía no está lista» de Meta se reintenta, no se pierde")

    # ── 3 · y lo que SÍ está mal se sigue dando por perdido ───────────────
    #
    # Sin esto, la prueba pasaría con un publicador que reintenta todo para
    # siempre y nunca le avisa a nadie que la pieza no se puede publicar.
    cli, ig = ClienteFalso(), InstagramFalso(["FINISHED"])
    ig.al_publicar = _traducir(
        {"code": 100, "error_subcode": 2207009,
         "error_user_msg": "Aspect ratio no soportado"})
    publicador.procesar(cli, ig, _fila())
    if cli.estado != "error":
        fallas.append(
            f"✗ una proporción que Instagram no acepta quedó en «{cli.estado}»: "
            f"eso no se arregla reintentando, hay que avisarlo.")
    else:
        print("✓ un rechazo de verdad se sigue informando como error")

    if fallas:
        print("\n" + "\n".join(fallas))
        return 1
    print("\npublicación OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
