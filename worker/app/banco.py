# -*- coding: utf-8 -*-
"""El banco de fotos: la tabla del cliente entra al skill de la marca.

── Por qué existe este módulo ─────────────────────────────────────────────

Hasta acá el banco era un archivo del repositorio: `referencias/fotos.json`
más las imágenes en `assets/`. Eso sirve para las fotos que cargamos nosotros
al dar de alta la marca, y no sirve para nada más: el cliente no puede sumar
una foto sin que alguien despliegue el worker de nuevo.

La tabla `fotos` arregla eso, pero abre un problema nuevo: el agente no habla
con la base. Lee un JSON y usa archivos del disco. Así que alguien tiene que
traducir una cosa en la otra **antes** de que el agente arranque, y ese
alguien es este módulo.

Cada corrida con pedidos pendientes:

  1. lee la tabla `fotos` del cliente
  2. baja al disco las que todavía no estén, a `assets/banco/`
  3. reescribe `referencias/fotos.json` = lo que trae el skill + lo de la tabla

── Dos reglas que no son opcionales ───────────────────────────────────────

**La tabla suma, nunca resta.** Boss Padel tiene hoy ~20 fotos descritas a
mano en su JSON, con el `foco` de cada formato ya resuelto. Si la sincronía
reemplazara el archivo, el día que un cliente estrene la tabla vacía perdería
todo eso de golpe y las piezas saldrían con la cara cortada. Por eso el JSON
que viene en el skill se guarda una vez como `fotos-base.json` y el archivo
que lee el agente se **reconstruye** de ahí en cada corrida: la sincronía es
idempotente y no hay forma de que se coma nada.

**Si la base no contesta, no pasa nada.** Un error leyendo la tabla deja el
banco del skill tal como está y el pedido se diseña igual. El banco es una
mejora, no una dependencia.
"""
import json
import logging
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import config

log = logging.getLogger(__name__)

# Cuántas fotos del cliente entran. El tope existe porque cada foto se baja al
# disco del worker en cada corrida —el contenedor arranca limpio— y eso se
# paga en segundos antes de empezar a diseñar. Con 60 son unos pocos segundos;
# con 600 el pedido esperaría un minuto para nada, porque el agente va a usar
# una sola.
MAX_FOTOS = 60

# El encuadre que se le pone a una foto que todavía no tiene ninguno. No es
# «el correcto»: es un punto de partida razonable —un poco arriba del centro,
# que es donde suele estar la cara— marcado con `foco_confirmado: false` para
# que el agente sepa que tiene que mirar la pieza y corregirlo.
FOCO_PROVISORIO = {
    "post": "50% 35%", "vert": "50% 32%",
    "story": "50% 40%", "reel": "50% 40%",
}

EXT_VALIDAS = {".jpg", ".jpeg", ".png", ".webp"}


def carpeta(marca: str) -> Path:
    return config.RAIZ / ".claude/skills" / marca


def _extension(url: str) -> str:
    ext = Path(unquote(urlparse(url).path)).suffix.lower()
    return ext if ext in EXT_VALIDAS else ".jpg"


def _bajar_faltantes(fotos: list[dict], base: Path) -> dict[str, str]:
    """Trae al disco las fotos del banco. Devuelve {clave: ruta relativa}.

    Una foto que no se pudo bajar **no entra al JSON**. Es a propósito: una
    entrada en el banco cuyo archivo no existe es peor que no tenerla, porque
    el agente la elige, el render falla y el pedido vuelve como error.
    """
    from .supa import bajar, clave_segura

    destino = base / "assets/banco"
    rutas = {}
    nuevas = 0
    for f in fotos:
        clave = (f.get("clave") or "").strip()
        url = (f.get("url") or "").strip()
        if not clave or not url:
            continue
        nombre = clave_segura(clave) + _extension(url)
        archivo = destino / nombre
        if not archivo.exists() or archivo.stat().st_size == 0:
            try:
                bajar(url, archivo)
                nuevas += 1
            except Exception as e:
                log.warning("no pude bajar la foto «%s» del banco: %s", clave, e)
                continue
        rutas[clave] = f"assets/banco/{nombre}"
    if nuevas:
        log.info("banco: %d foto(s) bajadas", nuevas)
    return rutas


def _entrada(f: dict, ruta: str) -> dict:
    """Una fila de la tabla, con la forma que espera el agente."""
    foco = f.get("foco") or {}
    confirmado = bool(foco)
    completo = {**FOCO_PROVISORIO, **foco}
    return {
        "descripcion": (f.get("descripcion") or "").strip()
                       or "Foto que subió el cliente, sin descripción.",
        "usar_para": ", ".join(f.get("etiquetas") or []) or "uso general",
        "quien": f.get("quien") or {},
        "foco": completo,
        "foco_confirmado": confirmado,
        "archivo": ruta,
        "origen": "banco del cliente",
        "medidas": ([f.get("ancho"), f.get("alto")]
                    if f.get("ancho") and f.get("alto") else None),
    }


NOTA_BANCO = (
    "Las entradas con `origen: banco del cliente` las subió el cliente desde "
    "su app y traen `archivo`: usá ESA ruta en el spec, no `assets/<clave>.jpg`. "
    "Si además dicen `foco_confirmado: false`, el encuadre es provisorio: "
    "generá la pieza, MIRÁ el PNG, y si quedó bien o lo tuviste que corregir "
    "guardalo con `python3 banco.py foco <clave> <formato> \"X% Y%\"` — eso hace "
    "que la próxima pieza con esa foto salga bien de una. Si la entrada trae "
    "`quien` vacío, completalo con `python3 banco.py anotar <clave> --quien '{...}'` "
    "después de mirarla."
)


def sincronizar(cli, marca: str) -> int:
    """Deja `referencias/fotos.json` al día. Devuelve cuántas del cliente entraron.

    Se llama una vez por corrida y por cliente, y sólo cuando hay pedidos: si
    no hay nada que diseñar, bajar fotos es tiempo tirado.
    """
    base = carpeta(marca)
    refs = base / "referencias"
    vivo, semilla = refs / "fotos.json", refs / "fotos-base.json"
    if not refs.exists():
        return 0

    # La copia intacta del banco que vino en el skill. Se hace una sola vez, la
    # primera corrida, y es lo que hace que reconstruir sea seguro.
    if not semilla.exists():
        semilla.write_text(
            vivo.read_text(encoding="utf-8") if vivo.exists() else "{}",
            encoding="utf-8")

    try:
        cimiento = json.loads(semilla.read_text(encoding="utf-8"))
    except Exception:
        log.warning("[%s] fotos-base.json ilegible; no toco el banco", marca)
        return 0

    filas = cli.leer_fotos(MAX_FOTOS)
    if not filas:
        # Sin tabla o sin fotos: el banco del skill queda como está. Igual se
        # reescribe desde la semilla, para deshacer la sincronía de una corrida
        # anterior si el cliente desactivó todas sus fotos.
        _escribir(vivo, cimiento)
        return 0

    rutas = _bajar_faltantes(filas, base)
    salida = dict(cimiento)
    sumadas = 0
    for f in filas:
        clave = (f.get("clave") or "").strip()
        if not clave or clave not in rutas:
            continue
        # Una foto del cliente con la misma clave que una del skill gana: es
        # más nueva y la eligió él. Pero se le conserva el `foco` del skill si
        # ella no trajo ninguno, que es el dato caro.
        previo = cimiento.get(clave) if isinstance(cimiento.get(clave), dict) else {}
        entrada = _entrada(f, rutas[clave])
        if not entrada["foco_confirmado"] and previo.get("foco"):
            entrada["foco"] = {**entrada["foco"], **previo["foco"]}
            entrada["foco_confirmado"] = True
        salida[clave] = entrada
        sumadas += 1

    salida["_banco"] = NOTA_BANCO
    _escribir(vivo, salida)
    log.info("[%s] banco sincronizado: %d foto(s) del cliente", marca, sumadas)
    return sumadas


def _escribir(ruta: Path, datos: dict):
    """Escritura atómica: el agente nunca ve un JSON a medio escribir."""
    tmp = ruta.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    tmp.replace(ruta)


# ── Lo que corre el agente ────────────────────────────────────────────────

def aplicar_foco_local(marca: str, clave: str, formato: str, valor: str) -> bool:
    """Refleja en el JSON el foco recién guardado, para la pieza en curso."""
    ruta = carpeta(marca) / "referencias/fotos.json"
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return False
    entrada = datos.get(clave)
    if not isinstance(entrada, dict):
        return False
    entrada.setdefault("foco", {})[formato] = valor
    entrada["foco_confirmado"] = True
    _escribir(ruta, datos)
    return True
