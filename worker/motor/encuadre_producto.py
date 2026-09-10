"""Encaje de un producto sin deformarlo dentro de una zona con borde oblicuo.

La plantilla define la zona; el motor mide el alfa del archivo. En fotos
opacas se protege el rectángulo completo: no se adivina qué píxeles son fondo.
"""
from PIL import Image, ImageOps


def encuadrar(foto, ancho, alto, superior, inferior, derecha, corte_arriba,
              corte_abajo, margen=24, ocupacion=0.86):
    with Image.open(foto) as archivo:
        im = ImageOps.exif_transpose(archivo).convert('RGBA')
    w, h = im.size
    alfa = im.getchannel('A')
    caja = alfa.getbbox()
    if not caja:
        raise ValueError('La foto de producto es totalmente transparente.')
    x0, y0, x1, y1 = caja
    bw, bh = x1-x0, y1-y0
    if not 0 <= superior < inferior <= alto or not 0 < derecha <= ancho:
        raise ValueError('Zona de producto inválida.')
    # El extremo izquierdo de cada fila permite aprovechar el aire alrededor
    # de una manguera o un pico sin acercar el cuerpo a la diagonal.
    filas=[]
    for row in range(y0,y1):
        b=alfa.crop((0,row,w,row+1)).getbbox()
        if b:
            filas.append((row-y0,b[0]-x0))
    pendiente=(corte_abajo-corte_arriba)/alto
    def lugar(s):
        y=(superior+inferior-s*bh)/2
        minimo=max(corte_arriba+pendiente*(y+s*r)+margen-s*x
                   for r,x in filas)
        maximo=derecha-s*bw
        return y,minimo,maximo
    lo=0.0
    hi=min((inferior-superior)*ocupacion/bh, (derecha-margen)/bw)
    for _ in range(50):
        mid=(lo+hi)/2
        _,a,b=lugar(mid)
        if a<=b:lo=mid
        else:hi=mid
    if lo<=0.001:
        raise ValueError('No hay espacio seguro para la foto del producto.')
    y,a,b=lugar(lo)
    x=(a+b)/2
    return {'left':x-lo*x0,'top':y-lo*y0,'width':lo*w,'height':lo*h,
            'visible':[x,y,x+lo*bw,y+lo*bh], 'escala':lo,
            'transparente':alfa.getextrema()[0]<255}
