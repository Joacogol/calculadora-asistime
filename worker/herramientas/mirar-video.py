#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Que Gemini MIRE un video largo y diga qué tramos entran en el reel.

    GEMINI_CLAVE=… python3 herramientas/mirar-video.py \\
        --url https://…/proxies/charla.mp4 \\
        --instruccion "un reel corto y con impacto sobre IA en real estate" \\
        --objetivo 30 --guion guion.json

Sin `GEMINI_CLAVE` en el entorno, la busca en Secret Manager
(`gemini-api-key`), como hace el registro de clientes.

## Qué es y qué no es

Es el paso que al editor de reels le faltaba: hoy `montar_reel` corta por
audio —encuentra dónde NADIE HABLA— y elige frases leyendo la transcripción.
Nunca ve la imagen. Esto le da al modelo el video entero y una instrucción, y
le pide UNA sola cosa: la lista de tramos, con inicio y fin, en JSON.

No le pide subtítulos (Whisper los hace mejor y gratis), ni que corte nada
(eso es ffmpeg, en `motor/video.py`), ni prosa. Del 2/9/2026 sabemos que sus
tiempos son precisos (0,17 s de error) y que su prosa no es de fiar: se usan
los números y se descarta el resto.

## Por qué corre dos veces

`--modo ambos` (el default) pregunta en agéntico y en estático y muestra los
dos resultados uno al lado del otro, con sus tokens. El anuncio de Google dice
que el agéntico es para video largo; acá se mide en TU video, con TU
instrucción, y se decide con eso.

## YouTube, y mirar sólo un rango

    python3 herramientas/mirar-video.py \\
        --youtube https://www.youtube.com/watch?v=… --desde 5:00 --hasta 10:00 \\
        --instruccion "un clip de hasta un minuto con lo más interesante sobre IA"

Un video PÚBLICO de YouTube se le pasa por URL, sin bajar nada: Google lo
lee de su lado. Con `--desde/--hasta` se le pide que mire sólo ese rango
—en estático es un campo de la API; en agéntico la API no lo tiene y se lo
dice la instrucción—. Los tiempos que devuelve son del video entero, no del
rango: se validan contra el rango para saber si lo respetó.

## Por qué la copia liviana

Un video de 61 minutos en 4K pesa 11 GB. Inline entran 100 MB. Una copia a
360p y 6 cuadros por segundo pesa ~60 MB y le dice lo mismo a un modelo que
mira un cuadro por segundo: la imagen se achica, el audio queda entero.

Si la copia vino en PARTES (para pasar un tope de almacenamiento), se pasan
todas las `--url` en orden y el script las manda juntas: los tiempos que
devuelve el modelo se corrigen con el desplazamiento de cada parte, así que
lo que sale es SIEMPRE en tiempo del video original.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

# Lo que ya sabe hablar con esta API: se importa del script de medición en vez
# de copiarlo, para que un arreglo allá (el timeout como cuerpo, el 429 que no
# se reintenta) valga acá sin acordarse.
_spec = importlib.util.spec_from_file_location(
    "gemini_video", RAIZ / "herramientas" / "probar-gemini-video.py")
gem = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gem)

#: Menos que esto no es un tramo, es un parpadeo. Más alto que el MIN_TRAMO
#: del guion (0,8 s) a propósito: el motor acepta cortes cortos que una persona
#: pidió; un modelo que propone medio segundo casi seguro se confundió.
MIN_TRAMO = 1.5

#: Cuánto puede pasarse del objetivo antes de avisar. El motor después puede
#: acortar; lo que no puede es inventar material que el modelo no marcó.
TOLERANCIA = 1.25


def clave() -> str:
    c = (os.environ.get("GEMINI_CLAVE") or "").strip()
    if c:
        return c
    try:
        c = subprocess.run(
            ["gcloud", "secrets", "versions", "access", "latest",
             "--secret=gemini-api-key"],
            capture_output=True, text=True, timeout=30).stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        c = ""
    if not c:
        raise SystemExit(
            "falta la clave de Gemini. Exportá GEMINI_CLAVE=… o guardala una "
            "vez en Secret Manager:\n"
            "  printf '%s' 'LA_CLAVE' | gcloud secrets create gemini-api-key --data-file=-")
    return c


def a_segundos(v) -> float:
    """`MM:SS`, `MM:SS.mmm`, `H:MM:SS`, `75`, `75.5` → segundos.

    El modelo escribe tiempos como le sale. Aceptar todas las formas es más
    barato que pedirle una y descubrir que no la respetó cuando el reel ya
    salió cortado en cualquier lado.
    """
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)
    partes = s.split(":")
    if not 2 <= len(partes) <= 3 or not all(re.fullmatch(r"\d+(\.\d+)?", p) for p in partes):
        raise ValueError(f"no entiendo el tiempo {v!r}")
    total = 0.0
    for p in partes:
        total = total * 60 + float(p)
    return total


def extraer_json(texto: str) -> dict:
    """El JSON de la respuesta, aunque venga envuelto en prosa o en ```."""
    t = texto.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b < 0:
        raise ValueError("la respuesta no trae ningún JSON")
    return json.loads(t[a:b + 1])


def validar_tramos(crudos: list, duracion: float, objetivo: float) -> tuple[list[dict], list[str]]:
    """Los tramos que sirven, en segundos, y los avisos de los que no.

    Se descarta lo inválido y se sigue con el resto: un tramo fuera del video
    es un error del modelo, no un motivo para tirar los otros cuatro.
    """
    buenos, avisos = [], []
    for i, t in enumerate(crudos or []):
        try:
            d, h = a_segundos(t.get("desde")), a_segundos(t.get("hasta"))
        except (ValueError, AttributeError) as e:
            avisos.append(f"tramo {i + 1}: {e}")
            continue
        if h <= d:
            avisos.append(f"tramo {i + 1}: termina ({h:.1f}) antes de empezar ({d:.1f})")
            continue
        if d < 0 or (duracion and h > duracion + 0.5):
            avisos.append(f"tramo {i + 1}: {d:.1f}–{h:.1f} se sale del video ({duracion:.1f} s)")
            continue
        if h - d < MIN_TRAMO:
            avisos.append(f"tramo {i + 1}: dura {h - d:.1f} s, menos de {MIN_TRAMO}")
            continue
        buenos.append({"desde": round(d, 2), "hasta": round(h, 2),
                       "por_que": str(t.get("por_que") or "").strip()[:200]})
    total = sum(t["hasta"] - t["desde"] for t in buenos)
    if objetivo and total > objetivo * TOLERANCIA:
        avisos.append(f"suman {total:.0f} s y el objetivo era {objetivo:.0f}: el motor "
                      f"va a tener que acortar")
    if objetivo and buenos and total < objetivo * 0.4:
        avisos.append(f"suman sólo {total:.0f} s de {objetivo:.0f}: quedó corto")
    return buenos, avisos


def con_desplazamiento(tramos: list[dict], partes: list[dict]) -> list[dict]:
    """De tiempo de la PARTE a tiempo del ORIGINAL.

    Cuando el video se mandó en partes, el modelo dice «parte 2, 01:10». Ese
    1:10 es de la parte; en el original es 1:10 más lo que duraron las partes
    anteriores. Se corrige acá, una vez, y nadie más tiene que acordarse.
    """
    if len(partes) <= 1:
        return tramos
    acum, desde_parte = 0.0, {}
    for i, p in enumerate(partes):
        desde_parte[i + 1] = acum
        acum += float(p.get("duracion") or 0)
    salida = []
    for t in tramos:
        n = int(t.get("parte") or 1)
        off = desde_parte.get(n, 0.0)
        salida.append({**t, "desde": round(t["desde"] + off, 2),
                       "hasta": round(t["hasta"] + off, 2)})
    return salida


def entrada_video(modo: str, *, datos: bytes | None = None, youtube: str | None = None,
                  desde: float | None = None, hasta: float | None = None) -> dict:
    """El objeto `video` del pedido, en la forma que esta API espera.

    Dos formas distintas para `processing`, y no es un capricho nuestro: en
    agéntico es la cadena "agentic"; en estático, si hay rango o fps, es un
    objeto `{"type": "static", "start_offset": …, "end_offset": …}`. Los
    offsets van en SEGUNDOS según la doc del 2/9/2026 —se imprime lo que se
    manda para poder comprobarlo contra lo que devuelve—.

    En agéntico la API no tiene rango: se le pide en la instrucción y se
    valida después. Si no lo respeta, se ve en los tiempos.
    """
    import base64
    v: dict = {"type": "video"}
    if youtube:
        v["uri"] = youtube
    else:
        v["data"] = base64.b64encode(datos or b"").decode()
        v["mime_type"] = "video/mp4"
    con_rango = desde is not None or hasta is not None
    if modo == "static" and con_rango:
        proc: dict = {"type": "static"}
        if desde is not None:
            proc["start_offset"] = int(desde)
        if hasta is not None:
            proc["end_offset"] = int(hasta)
        v["processing"] = proc
    else:
        v["processing"] = modo
    return v


def duracion_de(ruta_o_url: str) -> float:
    """Segundos, con ffprobe. Cero si no hay ffprobe: se valida menos, no se frena."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", ruta_o_url],
            capture_output=True, text=True, timeout=120).stdout.strip()
        return float(out)
    except Exception:                                        # noqa: BLE001
        return 0.0


def mmss(seg: float) -> str:
    m, s_ = divmod(int(round(seg)), 60)
    return f"{m:02d}:{s_:02d}"


def pregunta(instruccion: str, objetivo: float, partes: int, duracion: float,
             desde: float | None = None, hasta: float | None = None) -> str:
    dur = f" El video dura {duracion / 60:.0f} minutos." if duracion else ""
    if desde is not None or hasta is not None:
        a = mmss(desde or 0)
        b = mmss(hasta) if hasta is not None else "el final"
        dur += (f" MIRÁ SOLAMENTE entre {a} y {b} del video: todo tramo que elijas "
                f"tiene que estar dentro de ese rango, con los tiempos del video "
                f"entero (no relativos al rango).")
    en_partes = (f" El video viene en {partes} partes consecutivas: en cada tramo "
                 f"indicá `parte` (1 a {partes}) y los tiempos DENTRO de esa parte."
                 if partes > 1 else "")
    return (
        "Sos el editor de un reel vertical para Instagram.\n\n"
        f"INSTRUCCIÓN DE QUIEN PIDE EL REEL: «{instruccion}»\n\n"
        f"El reel tiene que durar como máximo {objetivo:.0f} segundos.{dur}{en_partes}\n\n"
        "Elegí los tramos EXACTOS del video que entran en el reel, en el orden "
        "en que deberían aparecer. Cada tramo tiene que empezar y terminar en un "
        "lugar donde el corte no deje una frase a la mitad. Preferí pocos "
        "tramos y buenos a muchos y cortos. Ningún tramo de menos de 2 segundos.\n\n"
        "Contestá SOLAMENTE con este JSON, sin texto antes ni después:\n"
        "{\n"
        '  "tramos": [\n'
        '    {"desde": "MM:SS.mmm", "hasta": "MM:SS.mmm", "por_que": "una línea"}\n'
        "  ],\n"
        '  "gancho": "la frase de 6 a 8 palabras con la que abriría el reel, sacada de lo que se dice"\n'
        "}\n"
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", action="append", default=[],
                   help="URL de la copia liviana. Repetible si viene en partes, en orden.")
    p.add_argument("--youtube", help="URL de un video PÚBLICO de YouTube (Google lo lee de su lado)")
    p.add_argument("--desde", help="mirar sólo desde este tiempo (MM:SS o segundos)")
    p.add_argument("--hasta", help="mirar sólo hasta este tiempo (MM:SS o segundos)")
    p.add_argument("--instruccion", required=True)
    p.add_argument("--objetivo", type=float, default=30, help="segundos de reel (default 30)")
    p.add_argument("--modo", choices=("ambos", "agentic", "static"), default="ambos")
    p.add_argument("--modelo", default=gem.MODELO)
    p.add_argument("--guion", help="dónde escribir el guion listo para montar_reel")
    args = p.parse_args()

    if bool(args.youtube) == bool(args.url):
        raise SystemExit("pasá --youtube o --url (una de las dos, no las dos)")
    desde = a_segundos(args.desde) if args.desde else None
    hasta = a_segundos(args.hasta) if args.hasta else None
    if desde is not None and hasta is not None and hasta <= desde:
        raise SystemExit("--hasta tiene que ser mayor que --desde")

    k = clave()
    partes = []
    if args.youtube:
        print(f"· YouTube {args.youtube}" + (f" · rango {mmss(desde or 0)}–{mmss(hasta) if hasta else 'fin'}" if (desde or hasta) else ""), flush=True)
    for u in args.url:
        print(f"· bajando {u}", flush=True)
        datos = gem.bajar(u)
        if len(datos) > gem.MAX_INLINE:
            raise SystemExit(f"{u} pesa {len(datos) / 1e6:.0f} MB: el tope inline es 100 MB. "
                             f"Partila o achicala más.")
        partes.append({"url": u, "bytes": datos, "duracion": duracion_de(u)})
    total_dur = sum(p_["duracion"] for p_ in partes)
    print(f"  {len(partes)} parte(s), {sum(len(p_['bytes']) for p_ in partes) / 1e6:.0f} MB, "
          f"{total_dur / 60:.1f} min", flush=True)

    texto_pregunta = pregunta(args.instruccion, args.objetivo, max(len(partes), 1), total_dur, desde, hasta)
    modos = ("agentic", "static") if args.modo == "ambos" else (args.modo,)
    resultados = {}
    for modo in modos:
        print(f"\n■ {modo.upper()} ({args.modelo})", flush=True)
        # Con varias partes se mandan todas en el mismo pedido: el modelo las
        # ve seguidas y numera la parte en cada tramo.
        if args.youtube:
            ent = entrada_video(modo, youtube=args.youtube, desde=desde, hasta=hasta)
            print(f"  processing = {json.dumps(ent['processing'])}", flush=True)
            r = _preguntar_entradas(k, [{"type": "text", "text": texto_pregunta}, ent], args.modelo)
            # El 2/9/2026 la API rechazó el objeto con offsets («Invalid input
            # at input[1].processing»): la doc era ambigua y la forma que
            # armamos no es la suya. En vez de perder la corrida, se vuelve a
            # pedir en la forma simple y el rango va en la instrucción, como
            # en agéntico. La validación de después dice si lo respetó.
            if r.get("codigo") == 400 and "processing" in (r.get("error") or "") \
                    and isinstance(ent.get("processing"), dict):
                print("  la API no aceptó el rango como campo; lo pido en la instrucción", flush=True)
                ent["processing"] = modo
                r = _preguntar_entradas(k, [{"type": "text", "text": texto_pregunta}, ent], args.modelo)
        elif len(partes) == 1:
            r = gem.con_paciencia(k, partes[0]["bytes"], "video/mp4", texto_pregunta, modo, args.modelo)
        else:
            r = _preguntar_varias(k, partes, texto_pregunta, modo, args.modelo)
        if r.get("error"):
            print("  ✗", r["error"][:400])
            for linea in gem.detallar(r["error"]):
                print("   ", linea)
            resultados[modo] = {"error": r["error"]}
            continue
        d = r["datos"]
        uso = d.get("usage") or d.get("usage_metadata") or {}
        texto = gem.texto_de(d)
        try:
            j = extraer_json(texto)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"  ✗ no devolvió JSON usable ({e}). Contestó:\n{texto[:800]}")
            resultados[modo] = {"error": "sin JSON", "texto": texto}
            continue
        tramos, avisos = validar_tramos(j.get("tramos"), total_dur if len(partes) == 1 else 0, args.objetivo)
        if desde is not None or hasta is not None:
            fuera = [t for t in tramos if (desde is not None and t["desde"] < desde - 1)
                     or (hasta is not None and t["hasta"] > hasta + 1)]
            if fuera:
                avisos.append(f"{len(fuera)} tramo(s) fuera del rango pedido "
                              f"{mmss(desde or 0)}–{mmss(hasta) if hasta else 'fin'}: "
                              + ", ".join(f"{mmss(t['desde'])}–{mmss(t['hasta'])}" for t in fuera))
                tramos = [t for t in tramos if t not in fuera]
        if len(partes) > 1:
            tramos = con_desplazamiento(tramos, partes)
            tramos, mas = validar_tramos(tramos, total_dur, args.objetivo)
            avisos += mas
        suma = sum(t["hasta"] - t["desde"] for t in tramos)
        print(f"  {r['segundos']:.0f} s · tokens {json.dumps(uso) if uso else '?'}")
        print(f"  gancho: «{j.get('gancho', '')}»")
        for t in tramos:
            print(f"  {t['desde']:7.1f} → {t['hasta']:7.1f}  ({t['hasta'] - t['desde']:4.1f} s)  {t['por_que']}")
        print(f"  = {len(tramos)} tramos, {suma:.0f} s")
        for a in avisos:
            print("  ⚠", a)
        resultados[modo] = {"tramos": tramos, "gancho": j.get("gancho", ""),
                            "segundos": r["segundos"], "uso": uso, "avisos": avisos}

    if args.guion:
        # El primer modo que haya salido bien escribe el guion. Es el contrato
        # de `motor/guion.py`: los tiempos son del material original y los
        # subtítulos los saca el motor escuchando.
        elegido = next((m for m in modos if resultados.get(m, {}).get("tramos")), None)
        if elegido:
            g = {
                "_origen": f"gemini {elegido} {args.modelo}",
                "_instruccion": args.instruccion,
                "tramos": [{"archivo": args.youtube or "ORIGINAL.mp4", "desde": t["desde"], "hasta": t["hasta"]}
                           for t in resultados[elegido]["tramos"]],
                "subtitulos": "auto",
                "hook": resultados[elegido]["gancho"] or "auto",
            }
            pathlib.Path(args.guion).write_text(json.dumps(g, ensure_ascii=False, indent=2), "utf-8")
            print(f"\n· guion ({elegido}) escrito en {args.guion} — `archivo` apunta al "
                  f"video ORIGINAL, no a la copia liviana")
        else:
            print("\n· ningún modo devolvió tramos: no escribo guion")
    return 0


def _preguntar_varias(k, partes, texto, modo, modelo):
    """Un pedido con todas las partes, numeradas, en orden."""
    entrada = [{"type": "text", "text": texto}]
    for i, p_ in enumerate(partes, 1):
        entrada.append({"type": "text", "text": f"PARTE {i}:"})
        entrada.append(entrada_video(modo, datos=p_["bytes"]))
    return _preguntar_entradas(k, entrada, modelo)


def _preguntar_entradas(k, entrada, modelo):
    """Un pedido con la lista de entradas ya armada. Reintenta 503/504, no 429."""
    import time
    cuerpo = {"model": modelo, "input": entrada}
    espera = 15
    for intento in range(1, 5):
        pedido = urllib.request.Request(
            gem.API, data=json.dumps(cuerpo).encode(),
            headers={"Content-Type": "application/json", "x-goog-api-key": k})
        t0 = time.time()
        try:
            with urllib.request.urlopen(pedido, timeout=gem.TIMEOUT) as r:
                return {"datos": json.load(r), "segundos": round(time.time() - t0, 1)}
        except urllib.error.HTTPError as e:
            r_ = {"error": f"HTTP {e.code}: {e.read()[:400].decode(errors='replace')}", "codigo": e.code}
        except TimeoutError:
            r_ = {"error": f"no contestó en {gem.TIMEOUT} s", "codigo": 504}
        if r_["codigo"] not in (503, 504) or intento == 4:
            return r_
        print(f"  Google saturado ({r_['codigo']}). Espero {espera} s y vuelvo…", flush=True)
        time.sleep(espera); espera *= 2
    return r_


if __name__ == "__main__":
    sys.exit(main())
