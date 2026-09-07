# -*- coding: utf-8 -*-
"""Previsualiza el encuadre de cada foto en los cuatro formatos.

El campo `foco` de fotos.json es un object-position de CSS. Escribirlo a ojo
sale mal: en un recorte cuadrado sobre una foto vertical se pierde un tercio
de la altura, y ese tercio suele ser la cabeza del jugador. Esto renderiza el
recorte real para poder verlo antes de fijarlo.

    python3 foco.py post          # una hoja con el recorte cuadrado de cada foto
    python3 foco.py post story    # varios formatos
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent / ".claude/skills/boss-padel-disenos"
FOTOS = RAIZ / "referencias/fotos.json"
ASSETS = RAIZ / "assets"

# Proporciones reales de cada formato del sistema.
RELACION = {"post": 1 / 1, "vert": 1080 / 1350, "story": 1080 / 1920, "reel": 1080 / 1920}

COLUMNAS = 4
CELDA = 360
BANDA = 30
MARGEN = 6
FONDO, LIMA, GRIS = (10, 10, 10), (228, 255, 2), (150, 150, 150)


def _tipo(t):
    r = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(r, t) if Path(r).exists() else ImageFont.load_default()


def recortar(im: Image.Image, relacion: float, foco: str) -> Image.Image:
    """Replica object-fit: cover + object-position, igual que lo hace el navegador."""
    px, py = (float(v.rstrip("%")) / 100 for v in foco.split())
    ancho_obj, alto_obj = 1000, round(1000 / relacion)
    escala = max(ancho_obj / im.width, alto_obj / im.height)
    esc = im.resize((round(im.width * escala), round(im.height * escala)), Image.LANCZOS)
    izq = round((esc.width - ancho_obj) * px)
    arr = round((esc.height - alto_obj) * py)
    return esc.crop((izq, arr, izq + ancho_obj, arr + alto_obj))


def hoja(formato: str, fichas: dict) -> Path:
    relacion = RELACION[formato]
    celda_alto = round(CELDA / relacion)
    nombres = [k for k in fichas if not k.startswith("_")]
    filas = (len(nombres) + COLUMNAS - 1) // COLUMNAS

    ancho = COLUMNAS * CELDA + (COLUMNAS + 1) * MARGEN
    alto = filas * (celda_alto + BANDA) + (filas + 1) * MARGEN
    lienzo = Image.new("RGB", (ancho, alto), FONDO)
    dib = ImageDraw.Draw(lienzo)
    fn, fm = _tipo(15), _tipo(13)

    for i, nombre in enumerate(nombres):
        x = MARGEN + (i % COLUMNAS) * (CELDA + MARGEN)
        y = MARGEN + (i // COLUMNAS) * (celda_alto + BANDA + MARGEN)
        ruta = ASSETS / f"{nombre}.jpg"
        foco = fichas[nombre]["foco"][formato]
        if ruta.exists():
            with Image.open(ruta) as im:
                lienzo.paste(recortar(im.convert("RGB"), relacion, foco).resize(
                    (CELDA, celda_alto), Image.LANCZOS), (x, y))
        else:
            dib.rectangle([x, y, x + CELDA, y + celda_alto], fill=(40, 20, 20))
        by = y + celda_alto
        dib.text((x + 6, by + 4), nombre[:26], fill=LIMA, font=fn)
        dib.text((x + 6, by + 17), foco, fill=GRIS, font=fm)

    salida = Path(f"/tmp/foco-{formato}.jpg")
    lienzo.save(salida, "JPEG", quality=82, optimize=True)
    print(f"{salida}  {lienzo.size[0]}×{lienzo.size[1]}")
    return salida


if __name__ == "__main__":
    fichas = json.loads(FOTOS.read_text(encoding="utf-8"))
    for f in (sys.argv[1:] or ["post"]):
        hoja(f, fichas)
