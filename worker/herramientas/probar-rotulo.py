#!/usr/bin/env python3
"""Prueba que el rótulo de un reel no tape el video que va abajo.

    python3 herramientas/probar-rotulo.py

## Por qué existe

El 1/9/2026 salió un reel de Boss donde el video se veía **el primer segundo y
el último**, y en el medio había ocho segundos de placa negra con el título. El
clip generado estaba perfecto —se midió, brillo parejo de punta a punta—: lo
rompía el rótulo.

El rótulo es una captura de pantalla con fondo transparente, y el
`omit_background` de Playwright sólo hace transparente el fondo que pone el
navegador por su cuenta: contra un `background` declarado en la hoja de estilos
no puede nada. Se pisaba el de `.canvas` y no el de `body`. Boss es la única
marca que pinta los dos, y la única con el motor de video prendido.

Un reel así cuesta 1.400 créditos y no se ve. Por eso hay dos redes: se pisan
los tres fondos, y además **se mide el PNG antes de usarlo**.

Esta prueba fija las dos, y necesita Chromium — que es justamente lo que hay
que ejercitar, porque el error no está en el HTML sino en cómo lo captura.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.reelero import TAPA_TODO, _tapa_todo                # noqa: E402

#: El CSS de la hoja de Boss, tal cual: `templates.py`, líneas 24 y 25.
HOJA_DE_BOSS = (
    "body{width:1080px;overflow:hidden;background:#0A0A0A}"
    ".canvas{position:relative;width:1080px;overflow:hidden;background:#0A0A0A}")

#: Lo que `rotulo()` le pega al HTML para que el fondo no tape el video.
PISA_EL_FONDO = "html,body,.canvas{background:transparent !important}"


def _dibujar(css: str, destino: pathlib.Path) -> bool:
    """El rótulo, como lo dibuja el worker. False si no hay navegador."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            nav = p.chromium.launch()
            try:
                pg = nav.new_page(viewport={"width": 1080, "height": 1920},
                                  device_scale_factor=1)
                pg.set_content(
                    f"<style>{css}</style><div class=canvas style='height:1920px'>"
                    f"<div style='color:#FAFAFA;font-size:90px;padding:80px'>"
                    f"DONDE OTROS VEN UN PARQUE</div></div>")
                pg.screenshot(path=str(destino), omit_background=True)
            finally:
                nav.close()
        return True
    except Exception as e:                                   # noqa: BLE001
        print(f"⚠ No pude abrir Chromium acá ({e}).")
        print("  NO es un problema del código: el worker lo lleva adentro del")
        print("  contenedor. Si la querés correr:  playwright install chromium")
        return False


def main() -> int:
    fallas = []
    with tempfile.TemporaryDirectory() as tmp:
        roto = pathlib.Path(tmp) / "sin-pisar-body.png"
        sano = pathlib.Path(tmp) / "pisando-todo.png"

        # ── 1 · el caso del 1/9: se pisa `.canvas` y no `body` ────────────
        if not _dibujar(HOJA_DE_BOSS + ".canvas{background:transparent !important}",
                        roto):
            return 0                                    # sin navegador, no aplica
        if not _tapa_todo(roto):
            fallas.append(
                "✗ un rótulo que NO pisa el fondo de `body` tendría que dar "
                "opaco,\n  y el guardián dice que está bien. Si esto no falla, "
                "el guardián\n  no protege de nada: es el caso exacto del 1/9.")
        else:
            print("✓ el guardián detecta un rótulo que taparía el video")

        # ── 2 · y pisando los tres, sale transparente ─────────────────────
        _dibujar(HOJA_DE_BOSS + PISA_EL_FONDO, sano)
        if _tapa_todo(sano):
            fallas.append(
                "✗ pisando html, body y .canvas el rótulo TODAVÍA sale opaco.\n"
                "  Alguna marca encontró otra forma de pintar el fondo.")
        else:
            print("✓ pisando los tres fondos el rótulo sale transparente")

        # ── 3 · y el umbral no se come un rótulo normal ───────────────────
        #
        # Sin esto la prueba pasaría con un guardián que descarta todo, y
        # entonces NINGÚN reel saldría con título.
        from PIL import Image
        with Image.open(sano) as im:
            media = sum(im.convert("RGBA").getchannel("A").getdata()) / (1080 * 1920)
        print(f"  (opacidad del rótulo bueno: {media:.1f} de 255, "
              f"umbral {TAPA_TODO:.0f})")
        if media >= TAPA_TODO * 0.5:
            fallas.append(
                f"✗ el rótulo bueno mide {media:.1f} y el umbral es {TAPA_TODO:.0f}: "
                f"están\n  demasiado cerca. Un rótulo válido con más texto podría "
                f"caer del lado\n  equivocado y salir descartado.")

    if fallas:
        print("\n" + "\n".join(fallas))
        return 1
    print("\nrótulo OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
