# -*- coding: utf-8 -*-
"""Que Gemini MIRE el material y diga qué tramos entran en el reel.

## El hueco que tapa

`montar_reel` cortaba a ciegas: encontraba dónde nadie habla y, si pedían un
largo, elegía frases leyendo la transcripción. Nunca veía la imagen ni
entendía el contenido. Cuando alguien manda una charla de una hora y pide «un
reel de un minuto con lo más fuerte sobre IA», hacía falta alguien que la
mirara. Esto es ese alguien.

## Con qué datos se decidió (2/9/2026)

Sobre un podcast en YouTube, rango 5:00–10:00, misma instrucción:

* **agéntico**: 28.721 tokens, 48 s, un tramo válido adentro del rango;
* **estático**: 246.068 tokens (8,5×), 26 s, y se pasó del rango 12 s.

Para material largo, agéntico. Y lo que se le pide son NÚMEROS —tiempos de
inicio y fin— porque es lo que medimos que acierta (0,17 s de error); su
prosa se descarta. No se le piden subtítulos (Whisper los hace mejor y
gratis) ni que corte nada (eso es ffmpeg).

## Cómo se le da el material

Inline entran 100 MB. Un archivo más pesado se convierte en una copia liviana
(360p, 6 cuadros por segundo: ~1 MB por minuto) que dice lo mismo para un
modelo que mira un cuadro por segundo; si aun así pasa el tope, se parte en
pedazos. Los tiempos que devuelve se corrigen con el desplazamiento de cada
pedazo, así que lo que sale de acá está SIEMPRE en el reloj del archivo
original — que es el reloj en que habla el guion.

## Si no puede

Sin clave, sin cuota, sin red o con una respuesta sin JSON, levanta
`NoPudeMirar`. Quien llama decide qué hacer; el worker sigue como hasta hoy
(clips enteros, corte por audio) y lo dice en las notas. Un reel cortado
por audio es peor que uno elegido; muchísimo mejor que ninguno.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

API = "https://generativelanguage.googleapis.com/v1beta/interactions"
#: Los que soportan el modo agéntico según el anuncio del 1/9/2026. El
#: primero es el de mejor calidad; los otros son respaldo si está saturado.
MODELOS = ("gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite")
TIMEOUT = 240
#: Tope inline, con margen: el límite es 100 MB y el base64 agrega un tercio.
MAX_INLINE = 70 * 1024 * 1024
#: Menos que esto no es un tramo, es un parpadeo.
MIN_TRAMO = 1.5
#: Cuánto puede pasarse del objetivo antes de avisar.
TOLERANCIA = 1.25


class NoPudeMirar(RuntimeError):
    """Gemini no pudo o no quiso: quien llama sigue sin él."""


def clave() -> str:
    return (os.environ.get("GEMINI_CLAVE") or "").strip()


def disponible() -> bool:
    return bool(clave())


# ═══ Tiempos y JSON, como los escriba el modelo ═════════════════════════════

def a_segundos(v) -> float:
    """`MM:SS`, `MM:SS.mmm`, `H:MM:SS`, `75`, `75.5` → segundos."""
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


def mmss(seg: float) -> str:
    m, s = divmod(int(round(seg)), 60)
    return f"{m:02d}:{s:02d}"


def extraer_json(texto: str) -> dict:
    """El JSON de la respuesta, aunque venga envuelto en prosa o en ```."""
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip(), flags=re.S)
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b < 0:
        raise ValueError("la respuesta no trae ningún JSON")
    return json.loads(t[a:b + 1])


def texto_de(datos) -> str:
    """El texto de la respuesta, venga en la forma que venga."""
    for camino in (("output_text",), ("text",), ("output", 0, "content", 0, "text"),
                   ("candidates", 0, "content", "parts", 0, "text")):
        v = datos
        try:
            for paso in camino:
                v = v[paso]
            if isinstance(v, str) and v.strip():
                return v
        except (KeyError, IndexError, TypeError):
            continue
    trozos: list[str] = []

    def juntar(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "text" and isinstance(v, str):
                    trozos.append(v)
                else:
                    juntar(v)
        elif isinstance(x, list):
            for v in x:
                juntar(v)
    juntar(datos)
    return "\n".join(trozos)


# ═══ El material: copia liviana y pedazos ═══════════════════════════════════

def _sondear(ruta: Path) -> dict:
    from . import analisis
    return analisis.sondear(ruta)


def copia_liviana(ruta: Path, destino: Path) -> Path:
    """360p a 6 cuadros por segundo, audio mono. ~1 MB por minuto."""
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(ruta),
         "-vf", "scale=-2:360,fps=6", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "34",
         "-c:a", "aac", "-b:a", "32k", "-ac", "1", "-movflags", "+faststart", str(destino)],
        check=True, timeout=3 * 3600, capture_output=True)
    return destino


def partir(ruta: Path, duracion: float, carpeta: Path, tope: int = MAX_INLINE) -> list[tuple[Path, float]]:
    """Pedazos (archivo, desplazamiento) de no más de `tope` bytes, cortando por tiempo."""
    peso = ruta.stat().st_size
    n = max(1, -(-peso // tope))
    if n == 1:
        return [(ruta, 0.0)]
    largo = duracion / n
    salida = []
    for i in range(n):
        dest = carpeta / f"{ruta.stem}_parte{i + 1}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{i * largo:.3f}", "-t", f"{largo:.3f}",
                        "-i", str(ruta), "-c", "copy", "-movflags", "+faststart", str(dest)],
                       check=True, timeout=1800, capture_output=True)
        salida.append((dest, i * largo))
    return salida


def preparar(archivos: list[Path], carpeta: Path) -> list[dict]:
    """Por archivo del guion, los pedazos que se le mandan al modelo.

    Cada pedazo sabe de qué archivo viene y a qué segundo del original
    corresponde su segundo cero. Con eso, lo que el modelo diga de un pedazo
    se traduce al reloj del archivo.
    """
    pedazos = []
    for k, ruta in enumerate(archivos, 1):
        ficha = _sondear(ruta)
        dur = float(ficha.get("duracion") or 0)
        peso = ruta.stat().st_size
        fuente = ruta
        if peso > MAX_INLINE or int(ficha.get("alto") or 0) > 480:
            fuente = copia_liviana(ruta, carpeta / f"{ruta.stem}_liviano.mp4")
        for parte, (pedazo, off) in enumerate(partir(fuente, dur, carpeta), 1):
            pedazos.append({"archivo": ruta.name, "indice": k, "parte": parte,
                            "ruta": pedazo, "desplazamiento": off, "duracion": dur})
    return pedazos


# ═══ La pregunta y la respuesta ═════════════════════════════════════════════

def pregunta(instruccion: str, objetivo: float, pedazos: list[dict]) -> str:
    archivos: dict[int, tuple[str, float, int]] = {}
    for p in pedazos:
        n, d, c = archivos.get(p["indice"], (p["archivo"], p["duracion"], 0))
        archivos[p["indice"]] = (n, d, c + 1)
    lista = "\n".join(
        f"- archivo {i} («{n}», {d / 60:.1f} min" + (f", en {c} partes consecutivas" if c > 1 else "") + ")"
        for i, (n, d, c) in sorted(archivos.items()))
    en_partes = any(c > 1 for _, _, c in archivos.values())
    return (
        "Sos el editor de un reel vertical para Instagram.\n\n"
        f"INSTRUCCIÓN DE QUIEN PIDE EL REEL: «{instruccion.strip()}»\n\n"
        f"El reel tiene que durar como máximo {objetivo:.0f} segundos.\n\n"
        f"El material son estos videos, numerados:\n{lista}\n\n"
        + ("Cuando un archivo viene en partes, cada tramo tiene que decir `parte` y sus tiempos "
           "son DENTRO de esa parte.\n\n" if en_partes else "")
        + "Elegí los tramos EXACTOS que entran, en el orden en que deberían aparecer. Cada tramo "
          "empieza y termina donde el corte no deja una frase a la mitad. Preferí pocos tramos y "
          "buenos a muchos y cortos; ninguno de menos de 2 segundos.\n\n"
          "Contestá SOLAMENTE con este JSON, sin texto antes ni después:\n"
          "{\n"
          '  "tramos": [\n'
          '    {"archivo": 1, "parte": 1, "desde": "MM:SS.mmm", "hasta": "MM:SS.mmm", "por_que": "una línea"}\n'
          "  ],\n"
          '  "gancho": "la frase de 6 a 8 palabras con la que abriría el reel, sacada de lo que se dice"\n'
          "}\n")


def _pedir(k: str, entrada: list[dict], modelo: str) -> dict:
    """Un pedido, reintentando 503/504 con espera doblada y NO el 429."""
    cuerpo = json.dumps({"model": modelo, "input": entrada}).encode()
    espera, ultimo = 15, {}
    for intento in range(1, 5):
        pedido = urllib.request.Request(
            API, data=cuerpo, headers={"Content-Type": "application/json", "x-goog-api-key": k})
        t0 = time.time()
        try:
            with urllib.request.urlopen(pedido, timeout=TIMEOUT) as r:
                return {"datos": json.load(r), "segundos": round(time.time() - t0, 1)}
        except urllib.error.HTTPError as e:
            ultimo = {"error": f"HTTP {e.code}: {e.read()[:400].decode(errors='replace')}", "codigo": e.code}
        except (TimeoutError, urllib.error.URLError, OSError) as e:
            ultimo = {"error": f"sin respuesta: {e}", "codigo": 504}
        if ultimo["codigo"] not in (503, 504) or intento == 4:
            return ultimo
        log.info("Gemini saturado (%s); espero %ds", ultimo["codigo"], espera)
        time.sleep(espera)
        espera *= 2
    return ultimo


def validar(crudos, pedazos: list[dict], objetivo: float) -> tuple[list[dict], list[str]]:
    """Los tramos que sirven, en el reloj de cada archivo original, y los avisos."""
    por_clave = {(p["indice"], p["parte"]): p for p in pedazos}
    buenos, avisos = [], []
    for i, t in enumerate(crudos or []):
        try:
            idx = int(t.get("archivo") or 1)
            parte = int(t.get("parte") or 1)
            d, h = a_segundos(t.get("desde")), a_segundos(t.get("hasta"))
        except (ValueError, TypeError, AttributeError) as e:
            avisos.append(f"tramo {i + 1}: {e}")
            continue
        p = por_clave.get((idx, parte))
        if not p:
            avisos.append(f"tramo {i + 1}: habla del archivo {idx} parte {parte}, que no existe")
            continue
        d, h = d + p["desplazamiento"], h + p["desplazamiento"]
        if h <= d:
            avisos.append(f"tramo {i + 1}: termina antes de empezar")
            continue
        if d < 0 or h > p["duracion"] + 0.5:
            avisos.append(f"tramo {i + 1}: {d:.1f}–{h:.1f} se sale de «{p['archivo']}» ({p['duracion']:.0f} s)")
            continue
        if h - d < MIN_TRAMO:
            avisos.append(f"tramo {i + 1}: dura {h - d:.1f} s")
            continue
        buenos.append({"archivo": p["archivo"], "desde": round(d, 2), "hasta": round(min(h, p["duracion"]), 2),
                       "por_que": str(t.get("por_que") or "").strip()[:200]})
    total = sum(t["hasta"] - t["desde"] for t in buenos)
    if objetivo and total > objetivo * TOLERANCIA:
        avisos.append(f"los tramos suman {total:.0f} s y el objetivo era {objetivo:.0f}: el motor va a acortar")
    return buenos, avisos


def elegir_tramos(archivos: list[Path], instruccion: str, objetivo: float,
                  carpeta=None, modelo: str | None = None) -> dict:
    """Los tramos que Gemini elige para este reel.

    Devuelve `{"tramos": [...], "gancho": str, "avisos": [...], "uso": {...},
    "segundos": float, "modelo": str}` con los tramos ya en el reloj del
    archivo original y listos para el guion. Levanta `NoPudeMirar` si no
    puede: quien llama sigue sin él.
    """
    k = clave()
    if not k:
        raise NoPudeMirar("falta GEMINI_CLAVE")
    archivos = [Path(a) for a in archivos if Path(a).exists()]
    if not archivos:
        raise NoPudeMirar("no hay archivos que mirar")
    carpeta = Path(carpeta) if carpeta else Path(tempfile.mkdtemp(prefix="mirar-"))
    carpeta.mkdir(parents=True, exist_ok=True)
    try:
        pedazos = preparar(archivos, carpeta)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError, OSError) as e:
        raise NoPudeMirar(f"no pude preparar el material: {e}") from e
    entrada: list[dict] = [{"type": "text", "text": pregunta(instruccion, objetivo, pedazos)}]
    for p in pedazos:
        datos = p["ruta"].read_bytes()
        if len(datos) > MAX_INLINE * 1.4:
            raise NoPudeMirar(f"«{p['archivo']}» sigue pesando {len(datos) / 1e6:.0f} MB después de achicarlo")
        entrada.append({"type": "text", "text": f"ARCHIVO {p['indice']}, PARTE {p['parte']}:"})
        entrada.append({"type": "video", "data": base64.b64encode(datos).decode(),
                        "mime_type": "video/mp4", "processing": "agentic"})
    modelos = (modelo,) if modelo else MODELOS
    r: dict = {}
    m = modelos[0]
    for m in modelos:
        r = _pedir(k, entrada, m)
        if not r.get("error"):
            break
        log.warning("Gemini %s: %s", m, r["error"][:200])
        if r.get("codigo") == 429:
            break                                            # cuota: cambiar de modelo no ayuda
    if r.get("error"):
        raise NoPudeMirar(r["error"][:300])
    d = r["datos"]
    try:
        j = extraer_json(texto_de(d))
    except (ValueError, json.JSONDecodeError) as e:
        raise NoPudeMirar(f"la respuesta no trae JSON usable ({e})") from e
    tramos, avisos = validar(j.get("tramos"), pedazos, objetivo)
    if not tramos:
        raise NoPudeMirar("no devolvió ningún tramo válido: " + "; ".join(avisos)[:200])
    uso = d.get("usage") or d.get("usage_metadata") or {}
    log.info("Gemini eligió %d tramos (%.0f s) en %.0f s, %s tokens", len(tramos),
             sum(t["hasta"] - t["desde"] for t in tramos), r["segundos"], uso.get("total_tokens", "?"))
    return {"tramos": tramos, "gancho": str(j.get("gancho") or "").strip(), "avisos": avisos,
            "uso": uso, "segundos": r["segundos"], "modelo": m}
