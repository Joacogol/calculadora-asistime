#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mide si Gemini con video agéntico sirve para algo en este sistema.

    GEMINI_CLAVE=… python3 herramientas/probar-gemini-video.py --marca boss-padel-disenos
    GEMINI_CLAVE=… python3 herramientas/probar-gemini-video.py --url https://…/reel.mp4

No cambia nada del motor. Es una medición: agarra un reel QUE YA SALIÓ, se lo
da a Gemini y compara lo que contesta contra lo que el sistema hizo. Sale de
acá con un sí o un no, no con una impresión.

## Qué se está midiendo, y por qué esas dos preguntas

Google anunció el 1/9/2026 «video agéntico»: el modelo decide qué tramos mirar
y a qué velocidad, en vez de muestrear cuadros a ciegas. **Entiende video, no
lo genera** — Magnific y fal.ai siguen siendo los que generan, y eso no está
en discusión acá.

Las dos preguntas son los dos lugares donde este sistema hoy está ciego:

1. **`momentos`** — dónde están los tramos buenos, con su tiempo. Es lo que
   `montar_reel` necesita y no tiene: hoy corta por silencio, o sea encuentra
   dónde NADIE HABLA, que no es lo mismo que dónde PASA ALGO. Si esto acierta,
   se edita por contenido y no por audio.

2. **`revision`** — qué tiene mal la pieza terminada. `motor/revisar.py` mide
   lo que se puede medir —negro, mudo, medidas, duración— y por regla no dice
   nada de lo que no puede medir. Un título cortado o un logo encima de una
   zona cargada hoy no los ve nadie hasta que la pieza está publicada.

## Se corre dos veces: agéntico y estático

Sin la comparación no se aprende nada. El anuncio promete 66% menos costo y
88% menos tokens; acá se mide en un reel de verdad, con sus tokens y sus
segundos al lado de cada respuesta.

Y hay un tercer resultado posible que conviene poder ver: que las dos
respuestas sean igual de buenas. Ahí la conclusión no es «no sirve» sino «sirve
y sale más barato en estático», que también es una decisión.
"""
import argparse
import base64
import json
import os
import pathlib
import sys
import time
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

API = "https://generativelanguage.googleapis.com/v1beta/interactions"

#: Los tres que soportan el modo agéntico, del anuncio del 1/9/2026. El
#: `3.8-flash` que aparece en los ejemplos de la doc NO está en esa lista.
MODELO = "gemini-3.7-flash"

#: Inline aguanta 100 MB; un reel de 30 segundos pesa entre 3 y 15. Por encima
#: de eso habría que subirlo por la Files API, y para una medición no vale la
#: pena: se avisa y se corta.
MAX_INLINE = 100 * 1024 * 1024

PREGUNTAS = {
    "momentos": (
        "Este es un reel vertical para Instagram de un club deportivo.\n\n"
        "Marcá los momentos fuertes: aquellos donde pasa algo que valga la pena "
        "dejar en un corte de 15 segundos. Para cada uno dame el tiempo exacto "
        "de inicio y fin en MM:SS.mmm y una línea de por qué.\n\n"
        "Después decime cuáles son los tramos MUERTOS: donde no pasa nada y se "
        "podrían cortar sin que se note.\n\n"
        "Sé concreto con los tiempos. Si no hay momentos fuertes, decilo."),
    "revision": (
        "Este es un reel TERMINADO, listo para publicar en Instagram.\n\n"
        "Revisalo como lo haría alguien que va a apretar publicar, y decime "
        "SÓLO lo que está mal:\n"
        "- ¿algún texto queda cortado, ilegible, o encima de una zona cargada?\n"
        "- ¿el logo se lee y está entero?\n"
        "- ¿hay tramos en negro, congelados o repetidos?\n"
        "- ¿el audio corta, falta, o desentona con la imagen?\n"
        "- ¿algo queda tapado por la interfaz de Instagram "
        "(los primeros 100 px de arriba y los últimos 250 de abajo)?\n\n"
        "Dame cada problema con su tiempo en MM:SS. **Si no encontrás nada "
        "mal, decí exactamente «sin problemas» y nada más** — inventar un "
        "problema que no está es peor que no revisar."),
}


def bajar(url: str) -> bytes:
    if url.startswith(("http://", "https://")):
        with urllib.request.urlopen(url, timeout=120) as r:
            return r.read()
    return pathlib.Path(url).read_bytes()


def ultimo_reel(marca: str) -> str:
    """La URL del último reel terminado de una marca, desde el registro.

    Se saca del registro y no de un argumento para que la medición corra sobre
    una pieza REAL, publicada, y no sobre un video elegido para que salga bien.
    """
    # Por `gcloud`, no por la variable de entorno. `app.registro.leer()` lee
    # `CLIENTES_REGISTRO`, que existe en Cloud Run porque Cloud Run monta el
    # secreto ahí — pero este script corre en Cloud Shell, donde esa variable
    # no está y la única forma de ver el registro es pedírselo a Secret
    # Manager. Leyéndolo mal, el mensaje era «no hay registro de clientes»
    # justo estando parado en la máquina donde sí está.
    import importlib.util
    ruta = RAIZ / "herramientas" / "registro.py"
    spec = importlib.util.spec_from_file_location("registro_cli", ruta)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    try:
        lista = cli.bajar()
    except FileNotFoundError:                                 # no hay gcloud
        lista = []
    if not lista:
        raise SystemExit(
            "no pude leer el registro de clientes con gcloud. Corré esto en "
            "Cloud Shell con sesión iniciada, o pasá --url con el link de un "
            "reel.")
    cliente = next((c for c in lista if c["marca"] == marca), None)
    if not cliente:
        raise SystemExit(
            f"«{marca}» no está en el registro. Tiene: "
            + ", ".join(c["marca"] for c in lista))
    pedido = urllib.request.Request(
        f"{cliente['url']}/rest/v1/reels?estado=eq.listo&url=not.is.null"
        f"&select=id,titulo,url,duracion&order=creado_en.desc&limit=1",
        headers={"apikey": cliente["service_role"],
                 "Authorization": f"Bearer {cliente['service_role']}"})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        filas = json.load(r)
    if not filas:
        raise SystemExit(f"«{marca}» no tiene ningún reel terminado todavía.")
    d = filas[0]
    print(f"  reel: {d.get('titulo') or d['id']} · {d.get('duracion') or '?'} s")
    return d["url"]


def preguntar(clave: str, video: bytes, mime: str, pregunta: str,
              modo: str) -> dict:
    cuerpo = {
        "model": MODELO,
        "input": [
            {"type": "text", "text": pregunta},
            {"type": "video",
             "data": base64.b64encode(video).decode(),
             "mime_type": mime,
             "processing": modo},
        ],
    }
    pedido = urllib.request.Request(
        API, data=json.dumps(cuerpo).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": clave})
    arranque = time.time()
    try:
        with urllib.request.urlopen(pedido, timeout=600) as r:
            datos = json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read()[:400].decode(errors='replace')}",
                "segundos": round(time.time() - arranque, 1)}
    return {"datos": datos, "segundos": round(time.time() - arranque, 1)}


def texto_de(datos: dict) -> str:
    """El texto de la respuesta, sin depender de una sola forma.

    La API está cambiando —los ejemplos de la doc y el anuncio no coinciden ni
    en el nombre del modelo— así que se buscan las formas conocidas y, si
    ninguna sirve, se devuelve el JSON crudo en vez de un texto vacío que
    parecería «no contestó nada».
    """
    for camino in (("output_text",), ("text",),
                   ("output", 0, "content", 0, "text"),
                   ("candidates", 0, "content", "parts", 0, "text")):
        v = datos
        try:
            for paso in camino:
                v = v[paso]
            if isinstance(v, str) and v.strip():
                return v
        except (KeyError, IndexError, TypeError):
            continue
    return json.dumps(datos, ensure_ascii=False)[:2000]


def tokens_de(datos: dict) -> str:
    for k in ("usage", "usage_metadata", "usageMetadata"):
        u = datos.get(k)
        if isinstance(u, dict):
            return " · ".join(f"{a}={b}" for a, b in sorted(u.items())
                              if isinstance(b, int))
    return "sin datos de tokens"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--marca", help="toma el último reel terminado de esa marca")
    g.add_argument("--url", help="un mp4 por URL o una ruta local")
    p.add_argument("--modo", choices=("agentic", "static", "ambos"),
                   default="ambos")
    p.add_argument("--pregunta", choices=(*PREGUNTAS, "todas"), default="todas")
    args = p.parse_args()

    clave = (os.environ.get("GEMINI_CLAVE") or
             os.environ.get("GOOGLE_API_KEY") or "").strip()
    if not clave:
        raise SystemExit(
            "falta GEMINI_CLAVE. Se saca de aistudio.google.com → Get API key.\n"
            "No la pegues en un comando: usá\n"
            '  read -rs -p "clave: " K; export GEMINI_CLAVE="$K"; unset K')

    url = args.url or ultimo_reel(args.marca)
    print(f"  bajando {url[:90]}…")
    video = bajar(url)
    print(f"  {len(video) / 1e6:.1f} MB")
    if len(video) > MAX_INLINE:
        raise SystemExit(
            f"el video pesa {len(video)/1e6:.0f} MB y el envío inline aguanta "
            f"100. Para una medición no vale la pena montar la Files API: "
            f"probá con un reel más corto.")

    modos = ("agentic", "static") if args.modo == "ambos" else (args.modo,)
    cuales = tuple(PREGUNTAS) if args.pregunta == "todas" else (args.pregunta,)

    for nombre in cuales:
        for modo in modos:
            print(f"\n{'═' * 70}\n  {nombre.upper()} · {modo}\n{'═' * 70}")
            r = preguntar(clave, video, "video/mp4", PREGUNTAS[nombre], modo)
            if "error" in r:
                print(f"  ✗ {r['error']}  ({r['segundos']} s)")
                continue
            print(f"  {r['segundos']} s · {tokens_de(r['datos'])}\n")
            print(texto_de(r["datos"]))

    print(f"\n{'─' * 70}")
    print("Lo que hay que mirar al comparar:")
    print("  · ¿los tiempos que da caen donde de verdad pasa algo?")
    print("  · ¿la revisión encuentra algo que `revisar.py` no puede medir?")
    print("  · ¿el agéntico dice algo que el estático no? ¿a qué precio?")
    print("Si las dos respuestas son igual de buenas, la conclusión es")
    print("«sirve, y sale más barato en estático» — que también es una decisión.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
