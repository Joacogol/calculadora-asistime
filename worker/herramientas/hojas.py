# -*- coding: utf-8 -*-
"""Hojas de contacto para triar el banco de fotos sin quemar contexto.

El problema: mirar una foto en alta le cuesta al modelo unos 25.000 tokens.
Cincuenta fotos son un millón y cuarto — inviable.

La solución: juntarlas de a doce en una grilla numerada. La grilla entera
cuesta lo mismo que una foto chica, así que triar cincuenta fotos pasa a
costar lo que antes costaba mirar cuatro. Con la miniatura alcanza para
decidir lo que importa acá: si hay jugadoras, si es de día, si la composición
deja lugar para un titular. Recién la selección final se mira en alta.

    python3 hojas.py <carpeta-origen> [<carpeta-salida>]
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

COLUMNAS, FILAS = 4, 3
POR_HOJA = COLUMNAS * FILAS

# 4 × 384 = 1536, justo abajo del techo al que la API reescala las imágenes.
# Más grande no se ve mejor: se reescala igual y se paga lo mismo.
CELDA_ANCHO, CELDA_ALTO = 384, 480
BANDA = 34                      # franja negra con el número y el nombre
MARGEN = 6

FONDO = (10, 10, 10)            # el negro de la marca
LIMA = (228, 255, 2)
GRIS = (150, 150, 150)

EXTENSIONES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff"}


def _tipografia(tam: int):
    for ruta in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, tam)
    return ImageFont.load_default()


def _encajar(im: Image.Image, ancho: int, alto: int) -> Image.Image:
    """Recorta al centro para llenar la celda. Sin bandas negras ni deformación."""
    im = im.convert("RGB")
    escala = max(ancho / im.width, alto / im.height)
    nueva = (max(1, round(im.width * escala)), max(1, round(im.height * escala)))
    im = im.resize(nueva, Image.LANCZOS)
    izq = (im.width - ancho) // 2
    arr = (im.height - alto) // 2
    return im.crop((izq, arr, izq + ancho, arr + alto))


def _nombre_corto(nombre: str, limite: int = 26) -> str:
    return nombre if len(nombre) <= limite else nombre[:limite - 1] + "…"


def armar(origen: Path, destino: Path) -> list[Path]:
    fotos = sorted(p for p in origen.rglob("*")
                   if p.is_file() and p.suffix.lower() in EXTENSIONES
                   and not p.name.startswith("."))
    if not fotos:
        print(f"No encontré imágenes en {origen}")
        return []

    destino.mkdir(parents=True, exist_ok=True)
    fuente_num = _tipografia(20)
    fuente_nom = _tipografia(15)

    ancho = COLUMNAS * CELDA_ANCHO + (COLUMNAS + 1) * MARGEN
    alto_celda = CELDA_ALTO + BANDA
    alto = FILAS * alto_celda + (FILAS + 1) * MARGEN

    hojas, indice = [], []
    for nro_hoja, arranque in enumerate(range(0, len(fotos), POR_HOJA), start=1):
        lote = fotos[arranque:arranque + POR_HOJA]
        hoja = Image.new("RGB", (ancho, alto), FONDO)
        dib = ImageDraw.Draw(hoja)

        for pos, ruta in enumerate(lote):
            col, fil = pos % COLUMNAS, pos // COLUMNAS
            x = MARGEN + col * (CELDA_ANCHO + MARGEN)
            y = MARGEN + fil * (alto_celda + MARGEN)

            try:
                with Image.open(ruta) as im:
                    im = ImageOps.exif_transpose(im)
                    hoja.paste(_encajar(im, CELDA_ANCHO, CELDA_ALTO), (x, y))
            except Exception as e:
                dib.rectangle([x, y, x + CELDA_ANCHO, y + CELDA_ALTO], fill=(40, 20, 20))
                dib.text((x + 10, y + 10), f"no se pudo abrir\n{e}", fill=GRIS, font=fuente_nom)

            numero = arranque + pos + 1
            by = y + CELDA_ALTO
            dib.rectangle([x, by, x + CELDA_ANCHO, by + BANDA], fill=FONDO)
            dib.text((x + 8, by + 7), f"{numero:03d}", fill=LIMA, font=fuente_num)
            dib.text((x + 58, by + 10), _nombre_corto(ruta.name), fill=GRIS, font=fuente_nom)

            indice.append(f"{numero:03d}  {ruta.relative_to(origen)}")

        salida = destino / f"hoja-{nro_hoja:02d}.jpg"
        hoja.save(salida, "JPEG", quality=82, optimize=True)
        hojas.append(salida)
        print(f"  {salida.name}  ({len(lote)} fotos)")

    (destino / "indice.txt").write_text("\n".join(indice) + "\n", encoding="utf-8")
    print(f"\n{len(fotos)} fotos · {len(hojas)} hojas · índice en {destino/'indice.txt'}")
    return hojas


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    org = Path(sys.argv[1]).expanduser()
    dst = Path(sys.argv[2]).expanduser() if len(sys.argv) > 2 else org.parent / "hojas"
    armar(org, dst)
