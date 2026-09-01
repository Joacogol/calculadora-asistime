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

    # ── El falso desconfía, como la base de verdad ────────────────────────
    #
    # `creditos_estimados`, `creditos_gastados` y `duracion` son columnas
    # ENTERAS. Un falso que acepta cualquier cosa deja pasar exactamente el
    # error que costó un video: el 1/9/2026 el primer pedido a fal escribió
    # `0.40` —dólares— en una columna de créditos enteros, PostgREST contestó
    # 400, y el id de la tarea se perdió con la excepción. fal ya tenía el
    # video pedido.
    #
    # Una prueba que no puede fallar no prueba nada, así que acá el falso
    # rechaza lo mismo que rechaza Postgres.
    ENTERAS = ("creditos_estimados", "creditos_gastados", "duracion")

    def _marcar(c, rid, estado, **campos):
        for col in ENTERAS:
            v = campos.get(col)
            if v is None or isinstance(v, bool):
                continue
            if not isinstance(v, int):
                raise AssertionError(
                    f"la columna «{col}» es entera y le escribieron {v!r} "
                    f"({type(v).__name__}). Esto en producción es un 400.")
        # Un PATCH pisa los campos que trae y deja los otros, como el de verdad.
        cli.escrito.setdefault(rid, {})
        cli.escrito[rid].update({"estado": estado, **campos})

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

# ═══ El tramo que pide el video: qué se anota y de qué tipo ═════════════════
#
# Es el que rompió el 1/9. Se corre con `pedir_clip` y el guionista falsos —no
# se le pide nada a ningún proveedor ni a ningún modelo de texto— y lo que se
# mira es qué queda escrito y en qué columna.

def pedir(fila, prov):
    """Pasa una fila nueva por el tramo de estimar y pedir."""
    cli = ClienteFalso([fila])
    pedidos = []

    def _pendientes(c, estado, limite=3):
        return [f for f in cli.filas.values() if f["estado"] == estado]

    def _tomar(c, rid, de, a):
        cli.filas[rid]["estado"] = a
        return True

    ENTERAS = ("creditos_estimados", "creditos_gastados", "duracion")

    def _marcar(c, rid, estado, **campos):
        for col in ENTERAS:
            v = campos.get(col)
            if v is None or isinstance(v, bool):
                continue
            if not isinstance(v, int):
                raise AssertionError(
                    f"la columna «{col}» es entera y le escribieron {v!r}")
        cli.escrito.setdefault(rid, {})
        cli.escrito[rid].update({"estado": estado, **campos})
        cli.filas[rid].update({"estado": estado, **campos})

    def pedir_clip(f, plan, planos):
        pedidos.append(plan)
        return "tarea-de-mentira"

    viejo = {n: getattr(reelero, n)
             for n in ("_pendientes", "_marcar", "_tomar", "pedir_clip",
                       "guionar", "_planos", "estado_clip")}
    reelero._pendientes, reelero._marcar = _pendientes, _marcar
    reelero._tomar, reelero.pedir_clip = _tomar, pedir_clip
    # Sin esto la misma corrida sigue de largo y le pregunta a los proveedores
    # DE VERDAD por una tarea inventada. Una prueba que sale a la red no es una
    # prueba: falla cuando no hay internet y pasa cuando no debería.
    reelero.estado_clip = lambda tarea, modelo, res: ("PROCESSING", None)
    reelero.guionar = lambda f, d: {"calidad": "normal", "planos": []}
    reelero._planos = lambda f, d: [{"prompt": "un plano", "duration": d}]
    try:
        reelero.atender_todos(
            cli, {"calidad": "normal", "duracion": 5, "proveedor": prov},
            armar_rotulo=lambda f, d: None, subir=lambda a, r: "https://x",
            musica_de_fila=lambda f: None)
    finally:
        for n, v in viejo.items():
            setattr(reelero, n, v)
    return cli.escrito.get(fila["id"], {}), pedidos


os.environ["MAGNIFIC_CLAVE"] = "de-mentira"
os.environ["FAL_CLAVE"] = "de-mentira"

NUEVA = {"id": "nueva", "estado": "pendiente", "mensaje": "un video de 5 segundos",
         "foto": "https://x/f.jpg"}

print("\n■ Un pedido a fal se cobra en dólares, y los dólares no son créditos")
escrito, pedidos = pedir({**NUEVA, "metricas": {"proveedor": "fal"}}, "fal")
ok(pedidos and pedidos[0]["modelo"] == "h3-max", "se le pide a h3-max", pedidos)
ok(escrito.get("tarea") == "tarea-de-mentira", "queda el id de la tarea", escrito.get("tarea"))
ok(escrito.get("modelo") == "h3-max",
   "y el modelo, que es con lo que después se sabe a quién preguntarle", escrito.get("modelo"))
ok("creditos_estimados" not in escrito,
   "NO se escriben dólares en la columna de créditos", escrito.get("creditos_estimados"))
costo = (escrito.get("metricas") or {}).get("costo") or {}
ok(costo.get("moneda") == "usd" and abs(costo.get("monto", 0) - 0.40) < 1e-9,
   "el gasto queda anotado con su unidad al lado", costo)

print("\n■ Y uno a Magnific sigue contándose en créditos enteros")
escrito, pedidos = pedir({**NUEVA, "metricas": {"proveedor": "magnific"}}, "magnific")
ok(pedidos and pedidos[0]["modelo"] == "seedance-2-mini", "se le pide a Seedance", pedidos)
ok(escrito.get("creditos_estimados") == 700, "700 créditos por 5 segundos", escrito.get("creditos_estimados"))
costo = (escrito.get("metricas") or {}).get("costo") or {}
ok(costo.get("moneda") == "creditos", "y también con su unidad", costo)

print(f"\n✗ {fallos} fallo(s)\n" if fallos else "\n✓ todo bien\n")
sys.exit(1 if fallos else 0)
