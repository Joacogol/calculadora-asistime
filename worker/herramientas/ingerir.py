# -*- coding: utf-8 -*-
"""Mete fotos elegidas al banco del skill, dejándolas listas para render.

Qué hace con cada una:
  · respeta la orientación del EXIF (si no, las verticales salen acostadas)
  · le saca TODO el metadato — incluida la ubicación GPS, que las cámaras de
    celular graban y que no tiene por qué viajar en una pieza pública
  · la lleva a un tamaño sensato: 1440 px de lado corto alcanza y sobra para
    los 1080 de Instagram, y evita cargar 4000 px que Chromium reescala igual
  · la guarda como JPEG de calidad alta con el nombre limpio

    python3 ingerir.py <carpeta-origen> seleccion.txt

`seleccion.txt` lleva una línea por foto: `nombre-nuevo = archivo-original.jpg`
Las líneas vacías y las que empiezan con # se ignoran.
"""
import re
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

DESTINO = Path(__file__).resolve().parent.parent / \
    ".claude/skills/boss-padel-disenos/assets"

LADO_CORTO = 1440
CALIDAD = 88


def limpiar_nombre(bruto: str) -> str:
    """Sin acentos, sin espacios, sin mayúsculas: los nombres viajan a un JSON,
    a un CSS y a una URL. Cuanto más aburridos, menos se rompen."""
    sin_tildes = unicodedata.normalize("NFKD", bruto).encode("ascii", "ignore").decode()
    guionado = re.sub(r"[^a-zA-Z0-9]+", "-", sin_tildes).strip("-").lower()
    return guionado or "foto"


def redimensionar(im: Image.Image) -> Image.Image:
    corto = min(im.width, im.height)
    if corto <= LADO_CORTO:
        return im
    escala = LADO_CORTO / corto
    return im.resize((round(im.width * escala), round(im.height * escala)),
                     Image.LANCZOS)


def ingerir(origen: Path, nombre: str, destino: Path) -> tuple[int, int]:
    with Image.open(origen) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im = redimensionar(im)
        # Imagen nueva desde los píxeles: así no sobrevive ningún metadato.
        limpia = Image.new("RGB", im.size)
        limpia.paste(im)
        limpia.save(destino, "JPEG", quality=CALIDAD, optimize=True,
                    progressive=True)
        return limpia.size


def leer_seleccion(ruta: Path) -> list[tuple[str, str]]:
    pares = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if "=" not in linea:
            print(f"  ⚠ salteada (sin '='): {linea}")
            continue
        nuevo, viejo = (x.strip() for x in linea.split("=", 1))
        pares.append((limpiar_nombre(nuevo), viejo))
    return pares


def main(origen: Path, seleccion: Path):
    DESTINO.mkdir(parents=True, exist_ok=True)
    indice = {p.name: p for p in origen.rglob("*") if p.is_file()}

    hechas, faltantes = 0, []
    for nombre, archivo in leer_seleccion(seleccion):
        fuente = indice.get(archivo) or (origen / archivo)
        if not fuente.exists():
            faltantes.append(archivo)
            continue
        salida = DESTINO / f"{nombre}.jpg"
        ancho, alto = ingerir(fuente, nombre, salida)
        kb = salida.stat().st_size // 1024
        print(f"  {salida.name:28} {ancho}×{alto}  {kb} KB")
        hechas += 1

    print(f"\n{hechas} fotos en {DESTINO}")
    if faltantes:
        print("No encontré:", ", ".join(faltantes))
    print("Falta la ficha de cada una en referencias/fotos.json "
          "(descripcion, usar_para, quien, foco, calidad).")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]).expanduser(), Path(sys.argv[2]).expanduser())
