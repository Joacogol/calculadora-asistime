"""Identidad de Ducart; el render y los formatos se resuelven en motor/."""
from motor.identidad import cargar as _cargar
from pathlib import Path
_marca = _cargar(__file__)
globals().update({k:v for k,v in vars(_marca).items() if not k.startswith("__")})

def PRESENTACION(data):
    """Compone páginas con las mismas plantillas, sin duplicar su dibujo."""
    slides = data.get("slides", [])
    if not 1 <= len(slides) <= 20:
        raise ValueError("El PDF necesita de 1 a 20 slides [{plantilla,data}].")
    pages=[]
    for slide in slides:
        tpl=slide.get("plantilla","tecnico")
        if tpl not in PLANTILLAS: raise ValueError("Plantilla desconocida: "+tpl)
        pages.append('<section class="canvas" style="width:1080px;height:1350px;break-after:page">'+PLANTILLAS[tpl].cuerpo(slide.get("data",{}),"vert")+'</section>')
    return '<html><head><meta charset="utf-8"><base href="'+AQUI.as_uri()+'/"><style>'+FONT_CSS+BASE_CSS+'@page{size:1080px 1350px;margin:0}section:last-child{break-after:auto}</style></head><body>'+''.join(pages)+'</body></html>',1080,1350
