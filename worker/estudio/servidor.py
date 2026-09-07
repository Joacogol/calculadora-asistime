# -*- coding: utf-8 -*-
"""El estudio: donde un diseñador crea plantillas y las corrige.

    python3 -m estudio.servidor boss-padel-disenos          # http://localhost:8080

## Por qué vive al lado del worker y no en otra app

Porque el preview tiene que renderizar con **el motor de producción**. Mismo
Chromium, mismas tipografías instaladas, mismo tamaño de canvas, misma hoja de
estilo de la marca. Cualquier preview que dibuje por otro lado se ve bien en el
editor y sale distinto en la pieza — y a partir de ahí nadie vuelve a confiar en
lo que ve, que es lo único que hace que un editor sirva.

No es una promesa: `motor.plantillas.compilar()` es literalmente la misma
función que arma la pieza final. El único paso que no comparten es que acá el
PNG vuelve por HTTP en vez de subirse a Supabase.

## Una marca por proceso

Igual que el render. Dos marcas tienen archivos con el mismo nombre —`brand.py`,
`templates.py`— y no pueden convivir importadas en el mismo proceso. Para
atender a dos clientes se levantan dos procesos, que además es lo que uno quiere
si algún día hay que darle acceso al diseñador de un cliente y no al del otro.

## Lo que el estudio NO hace

No borra plantillas y no toca el disco. Publica en la base del cliente, y el
worker las baja al skill en la corrida siguiente. Que el estudio escribiera
directo en el disco del contenedor sería escribir en una copia que se pierde en
el próximo despliegue.
"""
import json
import logging
import os
import pathlib
import queue
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

log = logging.getLogger("estudio")

AQUI = pathlib.Path(__file__).resolve().parent
FORMATO_POR_DEFECTO = "post"


# ── La marca ──────────────────────────────────────────────────────────────

def cargar_marca(nombre: str):
    carpeta = RAIZ / ".claude" / "skills" / nombre
    if not carpeta.is_dir():
        raise SystemExit(f"no existe la marca «{nombre}» en .claude/skills/")
    from motor.cargador import cargar_marca
    return cargar_marca(carpeta), carpeta


# ── Datos de ejemplo ──────────────────────────────────────────────────────
# Una plantilla vacía no se puede previsualizar, y pedirle al diseñador que
# invente doce campos antes de ver nada es la forma más rápida de que cierre la
# pestaña. El contrato ya dice qué es cada campo: alcanza para llenarlo.

_MUESTRA = {
    "texto": "Texto de ejemplo",
    "texto_largo": ("Un párrafo de ejemplo, lo bastante largo como para que se "
                    "vea cómo cae el texto cuando el contenido no es corto."),
    "color": "",
    "si_no": True,
}


def _una_foto(carpeta: pathlib.Path) -> str:
    fotos = sorted((carpeta / "assets").glob("*.jpg"))
    return f"assets/{fotos[0].name}" if fotos else ""


def ejemplo(contrato: dict, carpeta: pathlib.Path) -> dict:
    """Datos con los que la plantilla se ve, sin que nadie escriba nada."""
    d = {}
    for campo in contrato.get("campos", []):
        cid, tipo = campo["id"], campo.get("tipo", "texto")
        if "ejemplo" in campo:
            d[cid] = campo["ejemplo"]
        elif tipo == "imagen":
            d[cid] = _una_foto(carpeta)
        elif tipo == "opcion":
            d[cid] = campo.get("default", (campo.get("opciones") or [""])[0])
        elif tipo == "lista":
            cols = campo.get("columnas") or [{"id": "texto"}]
            d[cid] = [[c.get("etiqueta", c["id"]) for c in cols] for _ in range(3)]
        elif "default" in campo:
            # Un campo cuyo default es vacío se muestra vacío, aunque el
            # preview quede con un hueco. `contacto` en `torneo` es justo eso:
            # la marca dice que el teléfono NO va salvo que lo pidan, y un
            # preview que lo inventa enseña lo contrario de lo que hay que
            # aprender.
            d[cid] = campo["default"]
        elif campo.get("requerido"):
            d[cid] = _MUESTRA.get(tipo, "Texto de ejemplo")
        else:
            d[cid] = ""
    return d


# ── El estudio ────────────────────────────────────────────────────────────

class _Taller(threading.Thread):
    """El navegador, en su propio hilo, atendiendo capturas de a una.

    Playwright sync ata el navegador al hilo que lo creó y falla con
    «Cannot switch to a different thread» si lo toca otro. Un candado no
    alcanza: el problema no es que entren dos a la vez, es que entre *otro*.
    El servidor atiende cada pedido en un hilo distinto, así que el navegador
    tiene que vivir en uno solo y recibir trabajo por una cola.

    Y de paso sale gratis lo que el candado buscaba: las capturas se hacen de a
    una y en orden.
    """

    def __init__(self, marca, carpeta: pathlib.Path):
        super().__init__(daemon=True, name="taller")
        self.marca, self.carpeta = marca, carpeta
        self.cola: queue.Queue = queue.Queue()
        self.listo = threading.Event()
        self.falla: Exception | None = None

    def run(self):
        from playwright.sync_api import sync_playwright
        from motor.render import Render
        try:
            with sync_playwright() as pw:
                navegador = pw.chromium.launch()
                pagina = navegador.new_page(
                    viewport={"width": 1080, "height": 1080},
                    device_scale_factor=1)
                # El mismo Render que usa la corrida: los efectos
                # atmosféricos, el recorte del `.canvas` y la espera de las
                # tipografías salen de ahí y no de una copia parecida.
                render = Render(self.marca, self.carpeta)
                self.listo.set()
                while True:
                    trabajo, respuesta = self.cola.get()
                    try:
                        respuesta.put(("ok", trabajo(pagina, render)))
                    except Exception as e:      # noqa: BLE001
                        respuesta.put(("mal", e))
        except Exception as e:                  # noqa: BLE001
            self.falla = e
            self.listo.set()

    def _pedir(self, trabajo, espera=60):
        respuesta: queue.Queue = queue.Queue()
        self.cola.put((trabajo, respuesta))
        estado, valor = respuesta.get(timeout=espera)
        if estado == "mal":
            raise valor
        return valor

    def capturar(self, pagina_html: str, w: int, h: int, datos: dict) -> bytes:
        destino = self.carpeta / f"_preview-{os.getpid()}.png"

        def trabajo(pg, render):
            try:
                render._captura(pg, pagina_html, w, h, destino, datos)
                return destino.read_bytes()
            finally:
                # Los temporales viven en la carpeta de la marca —tienen que,
                # para que las rutas relativas de fotos y tipografías
                # resuelvan— y de ahí salen a la imagen si nadie los borra.
                destino.unlink(missing_ok=True)
                for tmp in render._tmp:
                    tmp.unlink(missing_ok=True)
                render._tmp.clear()

        return self._pedir(trabajo)


class Estudio:
    """Un Chromium abierto y la marca cargada, atendiendo previews."""

    def __init__(self, nombre_marca: str):
        self.nombre = nombre_marca
        self.marca, self.carpeta = cargar_marca(nombre_marca)
        self._taller = _Taller(self.marca, self.carpeta)
        self._taller.start()
        self._taller.listo.wait()
        if self._taller.falla:
            raise self._taller.falla
        log.info("estudio de %s listo", self.marca.NOMBRE)

    # ── lectura ──
    def plantillas(self) -> list[dict]:
        from motor import plantillas as mp
        salida = []
        for cid, f in sorted(mp.cargar(self.carpeta, self.marca).items()):
            c = f.contrato
            salida.append({
                "id": cid,
                "nombre": c.get("nombre", cid),
                "descripcion": c.get("descripcion", ""),
                "cuando_usarla": c.get("cuando_usarla", ""),
                "formatos": list(c.get("medidas", {})),
                "campos": len(c.get("campos", [])),
            })
        for cid in getattr(self.marca, "ESCRITAS_EN_PYTHON", ()):
            salida.append({"id": cid, "nombre": cid, "codigo": True,
                           "descripcion": "escrita en Python — no se edita acá",
                           "formatos": [], "campos": 0})
        return salida

    def plantilla(self, cid: str) -> dict:
        d = self.carpeta / "plantillas" / cid
        contrato = json.loads((d / "plantilla.json").read_text(encoding="utf-8"))
        return {
            "id": cid,
            "html": (d / "plantilla.html").read_text(encoding="utf-8"),
            "contrato": contrato,
            "datos": ejemplo(contrato, self.carpeta),
        }

    # ── preview ──
    def previsualizar(self, html: str, contrato: dict, datos: dict,
                      fmt: str) -> bytes:
        from motor import plantillas as mp
        # Compilar es puro y no toca el navegador, así que se hace en el hilo
        # del pedido: un error de plantilla —una llave sin cerrar, un campo que
        # no existe— vuelve al editor sin haber ocupado el taller.
        pagina = mp.compilar(self.marca, self.carpeta, contrato, html, datos, fmt)
        if fmt not in self.marca.FORMATOS:
            raise ValueError(f"la marca no tiene el formato «{fmt}»")
        w, h = self.marca.FORMATOS[fmt]
        return self._taller.capturar(pagina, w, h, datos)

    # ── publicar ──
    def publicar(self, cid: str, html: str, contrato: dict,
                 etiqueta: str, quien: str) -> dict:
        import requests
        from app import config
        from app.supa import Cliente

        datos = next((c for c in config.clientes() if c["marca"] == self.nombre), None)
        if not datos:
            raise RuntimeError(f"«{self.nombre}» no está en CLIENTES")
        cli = Cliente(**datos)
        if not cli.configurado:
            raise RuntimeError(f"«{self.nombre}» está en CLIENTES pero sin clave")

        r = requests.post(
            cli._url("rpc/guardar_plantilla"), headers=cli._cab(), timeout=30,
            json={"p_plantilla": cid, "p_html": html, "p_contrato": contrato,
                  "p_etiqueta": etiqueta or "sin etiqueta",
                  "p_quien": quien or "el estudio", "p_publicar": True})
        if r.status_code not in (200, 201):
            raise RuntimeError(f"la base contestó {r.status_code}: {r.text[:300]}")
        return r.json()


# ── HTTP ──────────────────────────────────────────────────────────────────

class Mostrador(BaseHTTPRequestHandler):
    estudio: Estudio = None
    protocol_version = "HTTP/1.1"

    def log_message(self, formato, *args):
        log.info("%s", formato % args)

    def _responder(self, codigo: int, cuerpo: bytes, tipo: str):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, datos, codigo=200):
        self._responder(codigo, json.dumps(datos, ensure_ascii=False).encode(),
                        "application/json; charset=utf-8")

    # Un error del editor —una llave sin cerrar, un campo que no existe— es la
    # situación NORMAL mientras alguien edita, no una excepción. Vuelve como
    # texto legible para mostrarlo al lado del preview, en vez de un 500 que
    # deja la pantalla en blanco sin decir qué pasó.
    def _error(self, e: Exception):
        mensaje = str(e) or e.__class__.__name__
        # Jinja sabe en qué línea se rompió; sin eso el editor dice
        # «unexpected '/'» sobre doscientas líneas de HTML y hay que buscar a
        # ojo. Con el número, el diseñador va derecho.
        linea = getattr(e, "lineno", None)
        if linea:
            mensaje = f"línea {linea}: {mensaje}"
        log.warning("preview con error: %s", mensaje)
        self._json({"error": mensaje, "tipo": e.__class__.__name__}, 400)

    def do_GET(self):
        try:
            if self.path in ("/", "/index.html"):
                return self._responder(
                    200, (AQUI / "ui.html").read_bytes(),
                    "text/html; charset=utf-8")
            if self.path == "/api/estado":
                return self._json({
                    "marca": self.estudio.nombre,
                    "nombre": self.estudio.marca.NOMBRE,
                    "colores": self.estudio.marca.C,
                    "formatos": list(self.estudio.marca.FORMATOS),
                    "plantillas": self.estudio.plantillas(),
                })
            if self.path.startswith("/api/plantillas/"):
                return self._json(
                    self.estudio.plantilla(self.path.rsplit("/", 1)[-1]))
            self._json({"error": "no existe"}, 404)
        except Exception as e:
            log.error("%s", traceback.format_exc())
            self._error(e)

    def do_POST(self):
        try:
            largo = int(self.headers.get("Content-Length") or 0)
            cuerpo = json.loads(self.rfile.read(largo) or b"{}")

            if self.path == "/api/previsualizar":
                png = self.estudio.previsualizar(
                    cuerpo["html"], cuerpo["contrato"], cuerpo.get("datos") or {},
                    cuerpo.get("formato") or FORMATO_POR_DEFECTO)
                return self._responder(200, png, "image/png")

            if self.path == "/api/publicar":
                return self._json(self.estudio.publicar(
                    cuerpo["id"], cuerpo["html"], cuerpo["contrato"],
                    cuerpo.get("etiqueta", ""), cuerpo.get("quien", "")))

            self._json({"error": "no existe"}, 404)
        except Exception as e:
            log.error("%s", traceback.format_exc())
            self._error(e)


def main(argv):
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    marca = argv[1] if len(argv) > 1 else os.environ.get("MARCA", "")
    if not marca:
        raise SystemExit(__doc__)
    Mostrador.estudio = Estudio(marca)
    puerto = int(os.environ.get("PORT", "8080"))
    log.info("estudio escuchando en http://localhost:%d", puerto)
    ThreadingHTTPServer(("0.0.0.0", puerto), Mostrador).serve_forever()


if __name__ == "__main__":
    main(sys.argv)
