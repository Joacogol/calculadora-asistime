#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hacerle a Gemini UNA pregunta sobre un rango de un video, y guardar la respuesta.

    python3 herramientas/preguntar-video.py \\
        --youtube https://www.youtube.com/watch?v=… --desde 5:02 --hasta 5:11 \\
        --pregunta "…" [--modo agentic|static] [--salida respuesta.json]

Es la herramienta de MEDIR: la pregunta la escribe quien mide, y la respuesta
se guarda tal cual para compararla contra una verdad que se conoce por otro
lado. No decide nada del motor. Comparte con `mirar-video.py` la forma del
pedido y el manejo de 503/429, para que un arreglo allá valga acá.
"""
import argparse
import importlib.util
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("mirar", RAIZ / "herramientas" / "mirar-video.py")
mirar = importlib.util.module_from_spec(_s); _s.loader.exec_module(mirar)
gem = mirar.gem


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--youtube", required=True)
    p.add_argument("--desde"); p.add_argument("--hasta")
    p.add_argument("--pregunta", required=True)
    p.add_argument("--modo", choices=("agentic", "static"), default="agentic")
    p.add_argument("--modelo", default=gem.MODELO)
    p.add_argument("--salida")
    a = p.parse_args()
    desde = mirar.a_segundos(a.desde) if a.desde else None
    hasta = mirar.a_segundos(a.hasta) if a.hasta else None
    rango = ""
    if desde is not None or hasta is not None:
        rango = (f"\n\nMirá SOLAMENTE entre {mirar.mmss(desde or 0)} y "
                 f"{mirar.mmss(hasta) if hasta is not None else 'el final'} del video. "
                 f"Los tiempos que des son del video entero, en MM:SS.")
    texto = a.pregunta + rango + "\n\nContestá SOLAMENTE con JSON, sin texto antes ni después."
    k = mirar.clave()
    ent = mirar.entrada_video(a.modo, youtube=a.youtube, desde=desde, hasta=hasta)
    if isinstance(ent.get("processing"), dict):
        ent["processing"] = a.modo          # el objeto con offsets la API lo rechaza (2/9/2026)
    print(f"· {a.modo} · {a.youtube} · {mirar.mmss(desde or 0)}–{mirar.mmss(hasta) if hasta else 'fin'}", flush=True)
    r = mirar._preguntar_entradas(k, [{"type": "text", "text": texto}, ent], a.modelo)
    if r.get("error"):
        print("✗", r["error"][:500])
        for l in gem.detallar(r["error"]):
            print(" ", l)
        return 1
    d = r["datos"]
    uso = d.get("usage") or d.get("usage_metadata") or {}
    crudo = gem.texto_de(d)
    print(f"  {r['segundos']:.0f} s · tokens totales: {uso.get('total_tokens', '?')}")
    try:
        j = mirar.extraer_json(crudo)
        print(json.dumps(j, ensure_ascii=False, indent=2))
    except Exception:                                        # noqa: BLE001
        j = {"_crudo": crudo}
        print("  (no vino JSON limpio) →", crudo[:1200])
    if a.salida:
        pathlib.Path(a.salida).write_text(json.dumps({"pregunta": texto, "modo": a.modo, "modelo": a.modelo,
                                                      "segundos": r["segundos"], "uso": uso, "respuesta": j},
                                                     ensure_ascii=False, indent=2), "utf-8")
        print(f"· guardado en {a.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
