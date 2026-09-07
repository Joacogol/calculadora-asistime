# -*- coding: utf-8 -*-
"""Cuánto hay que oscurecer una foto para que el texto se lea encima.

Nace de un defecto real: un titular rojo sobre una foto de cancha. Medido dio
4,35:1 contra el fondo — pasa el mínimo de texto grande por poco, pero se leía
mal igual porque el fondo era movido, no plano.

Lo que estaba mal de fondo era otra cosa: **el velo era un número fijo**. Un
degradé calibrado para una foto oscura deja el texto ilegible sobre una foto
clara, y sobre una oscura tapa la foto sin necesidad. Con dos marcas y fotos que
sube cualquiera, un número fijo se rompe el día que alguien sube una foto de una
sala de espera blanca.

Acá se mide la foto en la zona donde va a caer el texto y se calcula el velo
mínimo que hace falta. Ni más —que taparía la foto— ni menos.

Los umbrales son los de WCAG, que son los que usa cualquiera para decidir esto:
4,5:1 para texto chico y 3:1 para texto grande. Se apunta un poco por encima
porque el número se calcula sobre la mediana y siempre hay píxeles peores.
"""
import pathlib


def _lum_srgb(r, g, b):
    """Luminancia relativa de un color sRGB, según WCAG."""
    def canal(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)


def contraste(l1: float, l2: float) -> float:
    a, b = max(l1, l2), min(l1, l2)
    return (a + 0.05) / (b + 0.05)


def _hex_a_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def velo_necesario(foto, color_texto="#EB3141", objetivo=4.0,
                   zona=(0.55, 1.0), foco=0.5, maximo=0.92,
                   percentil=75) -> float:
    """Opacidad de negro que hay que poner encima para llegar a `objetivo`.

    `zona` es la franja vertical, en fracción de alto, donde va a caer el texto.
    Devuelve un número entre 0 y `maximo`.

    Si la foto no se puede abrir devuelve un valor conservador: es preferible
    una pieza con la foto un poco apagada a una con el titular ilegible.
    """
    try:
        from PIL import Image
        import numpy as np
    except Exception:
        return 0.80

    try:
        ruta = pathlib.Path(foto)
        if not ruta.exists():
            return 0.80
        im = Image.open(ruta).convert("RGB")
    except Exception:
        return 0.80

    w, h = im.size
    y0, y1 = int(h * zona[0]), int(h * zona[1])
    banda = np.asarray(im.crop((0, y0, w, max(y1, y0 + 1))), dtype=float)
    if banda.size == 0:
        return 0.80

    # NO el promedio: un reflejo brillante no tiene que decidir el velo de toda
    # la pieza. Pero tampoco la mediana pura, que era lo que había: la mediana
    # deja el 50% de la franja MÁS CLARO que el valor con el que se calculó, y
    # el texto que cae ahí se pierde. Medido en la pieza de las dos sedes: al
    # 50% daba 4,6:1 y en el 5% más claro caía a 3,6:1.
    #
    # El percentil 75 es el punto donde el velo cubre las tres cuartas partes
    # de la franja sin que un brillo puntual apague la foto entera.
    med = np.percentile(banda.reshape(-1, 3), percentil, axis=0)
    l_texto = _lum_srgb(*_hex_a_rgb(color_texto))

    # El negro encima multiplica el color en sRGB: c' = c * (1 - a). Se prueba
    # en pasos en vez de despejar porque la conversión a luminancia no es lineal.
    for paso in range(0, int(maximo * 100) + 1, 2):
        a = paso / 100.0
        l_fondo = _lum_srgb(*(med * (1 - a)))
        if contraste(l_texto, l_fondo) >= objetivo:
            return round(a, 2)
    return maximo


def degrade(alfa: float, tope=0.80) -> str:
    """El degradé de arriba hacia abajo, con el velo calculado en la parte baja.

    Arriba queda un oscurecido suave —para que el logo blanco se lea— y a la
    altura `tope` ya está aplicado el velo completo.

    ── Por qué `tope` es un parámetro y no el 80% fijo que era ────────────

    Con el 80% fijo, este degradé mentía. `velo_necesario` calculaba cuánta
    opacidad hacía falta para que el titular se leyera, y el degradé recién
    entregaba esa opacidad al 80% de la altura — pero el titular no siempre
    está ahí. En una pieza con la tarjeta de sedes abajo, el titular sube al
    56% y ahí el degradé venía aplicando dos tercios de lo pedido.

    Medido sobre una pieza publicada: el rojo de la marca dio **2,19:1** donde
    el cálculo prometía 3,8. No fallaba la cuenta, fallaba dónde se aplicaba.

    Ahora quien dibuja pasa la altura donde EMPIEZA su texto, y a partir de ahí
    el velo está completo.
    """
    a = max(0.0, min(0.95, alfa))
    tope = max(0.30, min(0.95, tope))
    # El respiro claro va antes del texto, no en un porcentaje fijo: si el
    # texto arranca alto, el degradé tiene menos recorrido para oscurecer.
    medio = tope * 0.55
    return (f"linear-gradient(180deg,rgba(0,0,0,{a*0.38:.2f}) 0%,"
            f"rgba(0,0,0,{a*0.10:.2f}) {medio*100:.0f}%,"
            f"rgba(0,0,0,{a:.2f}) {tope*100:.0f}%,"
            f"rgba(0,0,0,{min(a+0.03,0.95):.2f}) 100%)")


# ═══════════════════════════════════════════════════════════════════════════
#  El color de acento encima de una foto
#
#  Agregado el 3/8/2026, después de medir tres stories publicables de Clínica
#  Preventiva donde la palabra destacada iba en el rojo de la marca:
#
#      «EL PROCESO?» sobre el mostrador ......  1,72 : 1
#      «LOS ESTUDIOS» sobre la cara ..........  1,43 : 1
#      «TU CARNÉ» sobre la túnica blanca .....  1,02 : 1
#
#  El mínimo para texto grande es 3,0:1. En la tercera el rojo tenía
#  literalmente la misma luminancia que la túnica: la palabra desaparecía.
#
#  Y no se arregla con más velo. El techo teórico del rojo de esa marca es
#  5,05:1 contra negro PURO: para acercarse habría que tapar la foto casi
#  entera, y entonces no tiene sentido haber puesto una foto.
#
#  La salida no es tipográfica, es de diseño: **cuando el acento no llega como
#  texto, la palabra va adentro de un bloque sólido del color de acento.** El
#  blanco sobre el rojo de marca da 4,16:1 pase lo que pase debajo, porque ya
#  no depende de la foto. Y la firma de la marca —la palabra que importa, en
#  rojo— se conserva: cambia de ser tinta a ser fondo.
#
#  Esto NO es una regla de una marca. Es de todas, porque el problema es de
#  todos los acentos de luminancia media: un lima muy claro falla contra un
#  cielo, un rojo medio falla contra una túnica. Por eso vive en el motor.
# ═══════════════════════════════════════════════════════════════════════════

def luminancia_zona(foto, zona=(0.40, 0.88), percentil=50) -> float | None:
    """La luminancia mediana de la franja donde va a caer el texto."""
    try:
        from PIL import Image
        import numpy as np
    except Exception:
        return None
    try:
        ruta = pathlib.Path(foto)
        if not ruta.exists():
            return None
        im = Image.open(ruta).convert("RGB")
    except Exception:
        return None
    w, h = im.size
    y0, y1 = int(h * zona[0]), int(h * zona[1])
    banda = np.asarray(im.crop((0, y0, w, max(y1, y0 + 1))), dtype=float)
    if banda.size == 0:
        return None
    return _lum_srgb(*np.percentile(banda.reshape(-1, 3), percentil, axis=0))


#: Desde qué proporción de píxeles vacíos una imagen deja de ser una foto de
#: fondo y pasa a ser un objeto recortado. Con un 20% ya no hay foto debajo del
#: texto: hay fondo de marca.
RECORTE_MINIMO = 0.20


def transparencia(foto) -> float:
    """Qué proporción de la imagen está vacía. 0.0 si no tiene canal alfa.

    Existe para distinguir dos cosas que el motor trataba igual y no lo son:

      · una FOTO —una cancha, una persona, un plato— que ocupa el rectángulo
        entero y sobre la que el texto necesita un velo para leerse;
      · un OBJETO RECORTADO —Tony, un producto sin fondo, un logo— que no ocupa
        el rectángulo: lo que hay alrededor es el fondo de la marca.

    Tratar al segundo como al primero produce exactamente los dos defectos que
    aparecieron el 4/9/2026 en cuatro piezas seguidas de Asistime:

      1. `object-fit: cover` lo estira a sangre y lo RECORTA. Se pidió «la
         jirafa asomándose desde abajo» y salió una cabeza gigante cortada al
         medio, cuatro veces.
      2. El velo se calcula sobre píxeles vacíos y se pinta encima del fondo de
         la marca. Medido en la pieza real: el fondo claro de Asistime
         (#FBFCFF) salió RGB(220,220,224) — gris. El agente había pedido el
         azul oficial y anotó en sus notas que lo había usado.
    """
    if not foto:
        return 0.0
    ruta = pathlib.Path(foto)
    try:
        from PIL import Image
        with Image.open(ruta) as im:
            if im.mode not in ("RGBA", "LA", "PA") and "transparency" not in im.info:
                return 0.0
            alfa = im.convert("RGBA").getchannel("A")
            # El histograma es mucho más barato que recorrer los píxeles y
            # alcanza: sólo hace falta cuántos están por debajo del umbral.
            h = alfa.histogram()
            vacios = sum(h[:17])
            total = sum(h)
            return vacios / total if total else 0.0
    except Exception:
        return 0.0


def plan_titular(foto, acento: str, oscuro: str = "#111111",
                 zona=(0.40, 0.88), objetivo_blanco=4.0, objetivo_acento=3.0,
                 velo_max=0.86, percentil=75) -> dict:
    """Cómo hay que dibujar un titular de dos colores encima de una foto.

    Devuelve:
      `velo`     opacidad de negro que necesita la parte blanca del titular
      `modo`     `"texto"` si el acento se lee como texto, `"bloque"` si no
      `contraste` el número medido del acento, para poder explicarlo
      `tinta`    de qué color va el texto ADENTRO del bloque

    Sin foto, o si el archivo no se puede abrir, devuelve `bloque`: es la
    opción que se lee siempre, y ante la duda vale más una pieza legible que
    una linda.
    """
    l_acento = _lum_srgb(*_hex_a_rgb(acento))
    # Adentro del bloque, el texto va del color que más contraste con el
    # acento. Un acento claro —un lima, un amarillo— pide tinta oscura; uno
    # medio u oscuro pide blanco.
    tinta = oscuro if l_acento > 0.40 else "#FFFFFF"

    if not foto:
        return {"velo": 0.0, "modo": "texto", "contraste": None,
                "tinta": tinta, "recortada": False, "vacio": 0.0}

    # Un objeto recortado no lleva velo, y no es una preferencia: el velo
    # existe para oscurecer LA FOTO que está debajo del texto blanco, y acá
    # debajo del texto no hay foto sino el fondo de la marca, cuyo contraste ya
    # lo garantiza la paleta. Velarlo no protege nada y sí convierte el blanco
    # de la marca en gris.
    vacio = transparencia(foto)
    if vacio >= RECORTE_MINIMO:
        return {"velo": 0.0, "modo": "texto", "contraste": None,
                "tinta": tinta, "recortada": True, "vacio": round(vacio, 3)}

    velo = velo_necesario(foto, "#FFFFFF", objetivo=objetivo_blanco,
                          zona=zona, maximo=velo_max, percentil=percentil)
    l0 = luminancia_zona(foto, zona, percentil=percentil)
    if l0 is None:
        return {"velo": max(velo, 0.55), "modo": "bloque",
                "contraste": None, "tinta": tinta,
                "recortada": False, "vacio": round(vacio, 3)}

    # El velo es negro encima: en luz lineal multiplica por (1 - a).
    l_fondo = l0 * (1 - velo)
    c = contraste(l_acento, l_fondo)
    return {"velo": velo,
            "modo": "texto" if c >= objetivo_acento else "bloque",
            "contraste": round(c, 2),
            "tinta": tinta,
            "recortada": False, "vacio": round(vacio, 3)}
