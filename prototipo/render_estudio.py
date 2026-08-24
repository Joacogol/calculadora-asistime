# -*- coding: utf-8 -*-
"""Renderiza piezas usando el motor de plantillas-como-datos."""
import sys, json, pathlib
from playwright.sync_api import sync_playwright
from brand import FORMATOS
import motor

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "out"; OUT.mkdir(exist_ok=True)

def render(jobs):
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": 1080, "height": 1080}, device_scale_factor=1)
        for tpl, data, fmt, name in jobs:
            w, h = FORMATOS[fmt]
            html = motor.componer(tpl, data, fmt)
            tmp = ROOT / "_tmp2.html"; tmp.write_text(html, encoding="utf-8")
            pg.set_viewport_size({"width": w, "height": h})
            pg.goto(f"file://{tmp}")
            pg.wait_for_timeout(320)
            pg.locator(".canvas").screenshot(path=str(OUT / f"{name}.png"))
            print("→", name + ".png")
        b.close()

if __name__ == "__main__":
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    render([(j["plantilla"], j["data"], j.get("formato", "post"), j["nombre"]) for j in spec])
