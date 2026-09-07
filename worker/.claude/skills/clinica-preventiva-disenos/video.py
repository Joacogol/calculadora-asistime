# -*- coding: utf-8 -*-
"""Lanzador: arma un reel de Clínica Preventiva.

    python3 video.py guion.json [carpeta-de-salida]

Acepta las dos formas y se da cuenta sola de cuál es:

  · un GUION DE EDICIÓN —tramos con `desde` y `hasta` del material original—,
    que es lo normal cuando el reel se arma con clips que subió la persona.
    Se valida antes de encodear y los errores salen en castellano.
  · un spec del motor —tramos con `dura`—, que es la forma vieja y sigue
    andando para los reels que se arman con fotos del banco.
"""
import pathlib, sys
AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI)); sys.path.insert(0, str(AQUI.parents[2]))
import marca                            # noqa: E402
from motor import video as motor_video  # noqa: E402
motor_video.configurar(AQUI, *marca.TIPO_REEL, acento=marca.ACENTO_REEL,
                        animo=getattr(marca, "ANIMO_MUSICA", "club"),
                        logo_html=marca.logo(2.4, "#FAFAFA", "center"),
                        css_marca=marca.FONT_CSS + marca.LOGO_CSS)
reel = motor_video.reel
duracion = motor_video.duracion
desde_guion = motor_video.desde_guion


def _es_guion(d: dict) -> bool:
    """Un guion habla de `hasta`; un spec del motor, de `dura`."""
    return any("hasta" in t for t in (d.get("tramos") or []) if isinstance(t, dict))
if __name__ == "__main__":
    import json
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    destino = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else motor_video.SALIDA
    r = reel(spec, destino)
    print(f"→ {r}  ·  {duracion(r):.1f}s  ·  {r.stat().st_size/1024/1024:.1f} MB")
