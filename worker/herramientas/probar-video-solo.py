#!/usr/bin/env python3
"""¿Un pedido de VIDEO entrega el archivo y no una pieza?

    python3 herramientas/probar-video-solo.py

Corre el tramo final de `atender_todos` —el que agarra los clips ya generados
y decide qué hacer con ellos— con un Supabase de mentira y un `montar` espía.
Lo que se mide no es que no reviente: es **qué queda escrito en la fila** y
**si se llamó a montar**.

Las dos cosas importan por separado:

· que quede `clip_url` y NO `url`, porque `url` es la señal de «hay una pieza
  terminada, se puede publicar» y acá no la hay;
· que `montar` no se llame, porque montar es lo que le pone encima el título
  que nadie pidió — y de paso son treinta segundos de ffmpeg por un archivo
  que ya estaba listo.

Y al revés: un pedido normal tiene que seguir montando. Una prueba que sólo
mira el caso nuevo deja pasar el día en que el caso nuevo se come al viejo.

Se corre sola en `desplegar-chat.sh`.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import reelero                                        # noqa: E402

fallos = 0


def ok(condicion, que, detalle=None):
    global fallos
    if condicion:
        print("  ✓", que)
    else:
        fallos += 1
        print("  ✗", que, "" if detalle is None else repr(detalle))


class ClienteFalso:
    """Guarda lo que se le escribe a cada fila. Eso es lo que mira la prueba."""

    marca = "prueba"

    def __init__(self, filas):
        self.filas = {f["id"]: f for f in filas}
        self.escrito = {}


def correr(fila):
    """Pasa una sola fila por el tramo de montaje y devuelve qué se escribió."""
    cli = ClienteFalso([fila])
    espia = {"monto": False, "subido": []}

    def _pendientes(c, estado, limite=3):
        return [f for f in cli.filas.values() if f["estado"] == estado]

    def _marcar(c, rid, estado, **campos):
        cli.escrito[rid] = {"estado": estado, **campos}

    def bajar(url, destino):
        destino.write_bytes(b"no importa el contenido")
        return destino

    def montar(*a, **k):
        espia["monto"] = True
        salida = a[3]
        salida.write_bytes(b"la pieza")
        return salida

    def subir(archivo, ruta):
        espia["subido"].append(ruta)
        return f"https://bucket/{ruta}"

    viejo = {n: getattr(reelero, n) for n in ("_pendientes", "_marcar", "bajar", "montar")}
    reelero._pendientes, reelero._marcar = _pendientes, _marcar
    reelero.bajar, reelero.montar = bajar, montar
    try:
        reelero.atender_todos(
            cli, {"calidad": "normal", "duracion": 10},
            armar_rotulo=lambda f, d: (d.write_bytes(b"png"), d)[1],
            subir=subir,
            musica_de_fila=lambda f: None)
    finally:
        for n, v in viejo.items():
            setattr(reelero, n, v)
    return cli.escrito.get(fila["id"], {}), espia


BASE = {
    "id": "abc", "estado": "montando", "modelo": "seedance-2-mini",
    "resolucion": "720p", "duracion": 10, "creditos_estimados": 1400,
    "clip_url": "https://cdn.proveedor/firmado.mp4", "titulo": "Un título",
}

print("\n■ Se pidió el VIDEO: se entrega el archivo")
escrito, espia = correr({**BASE, "metricas": {"pieza": "video", "proveedor": "fal"}})
ok(escrito.get("estado") == "listo", "queda listo", escrito.get("estado"))
ok(escrito.get("clip_url", "").endswith("abc-crudo.mp4"),
   "con el archivo guardado en NUESTRO bucket", escrito.get("clip_url"))
ok("url" not in escrito,
   "y sin `url`: no hay ninguna pieza terminada que publicar", escrito)
ok(not espia["monto"], "no se montó nada encima")
ok(espia["subido"] == ["reels/abc-crudo.mp4"], "se subió un solo archivo", espia["subido"])
ok(escrito.get("creditos_gastados") == 1400, "y se anotó lo que costó", escrito)

print("\n■ Se pidió la PIEZA: sigue armándose como siempre")
escrito, espia = correr({**BASE, "metricas": {"proveedor": "magnific"}})
ok(escrito.get("estado") == "listo", "queda listo", escrito.get("estado"))
ok(espia["monto"], "se montó")
ok(escrito.get("url", "").endswith("abc.mp4"), "y hay pieza para publicar", escrito.get("url"))
ok(escrito.get("clip_url", "").endswith("abc-crudo.mp4"),
   "con el crudo guardado igual, para poder reusarlo", escrito.get("clip_url"))

print("\n■ Una fila sin `metricas` es una pieza, como siempre fue")
escrito, espia = correr({**BASE, "metricas": None})
ok(espia["monto"] and escrito.get("url"), "se monta", escrito.get("url"))

print("\n■ Eligió un proveedor que el motor no tiene prendido")
#
# Antes esta fila se quedaba callada en «pendiente» para siempre, que estaba
# bien mientras el proveedor lo ponía la marca: el día que llegara el secreto
# salía sola. Desde que la persona elige en el chat, ese silencio es una
# trampa — eligió, espera, y nadie le dice que ese video no va a llegar nunca.
import os                                                      # noqa: E402

# Ninguna de las dos claves: así ninguna fila de estas llega a pedirle un video
# a nadie, que es justo lo que se está probando.
os.environ.pop("FAL_CLAVE", None)
os.environ.pop("MAGNIFIC_CLAVE", None)

escrito, _ = correr({**BASE, "id": "sinclave", "estado": "pendiente",
                     "metricas": {"proveedor": "fal"}})
notas = escrito.get("notas", "")
ok(escrito.get("estado") == "rechazado", "se rechaza en vez de colgarse", escrito.get("estado"))
ok("no se gastó nada" in notas.lower(), "diciendo que no se gastó nada", notas)
ok("Magnific" in notas, "y ofreciendo el otro sistema", notas)

print("\n■ Pero si el proveedor lo puso la marca, sigue esperando callado")
escrito, _ = correr({**BASE, "id": "sinclave2", "estado": "pendiente",
                     "metricas": {}})
ok(escrito == {}, "no se toca la fila: sale sola cuando llegue el secreto", escrito)

print(f"\n✗ {fallos} fallo(s)\n" if fallos else "\n✓ todo bien\n")
sys.exit(1 if fallos else 0)
