# -*- coding: utf-8 -*-
"""Efectos atmosféricos para las piezas: lluvia, vidrio mojado, niebla, grano.

Todo se dibuja con CSS y SVG dentro del mismo Chromium que ya renderiza las
placas. No hay imágenes de stock ni PNG de textura: las gotas y las estelas se
generan con `feTurbulence`, que es ruido de Perlin, así que cada pieza tiene un
patrón distinto y ninguno se repite.

La idea es que el pedido pueda decir «que se vea como una ventana con gotas» o
«que llueva» y el sistema lo resuelva, sin que nadie tenga que buscar una
textura ni abrir un editor.

Cada efecto devuelve (css, html). El HTML va adentro del `.canvas` de la
plantilla, después de la foto y antes del texto: el efecto tapa la imagen pero
nunca el titular.
"""

# Cada efecto trae su propia semilla de turbulencia para que dos piezas
# distintas no salgan con el mismo patrón de gotas.
_SEMILLA = {"lluvia": 7, "vidrio": 3, "niebla": 11, "destello": 5}


def _turbulencia(id_: str, frec: str, octavas: int, semilla: int) -> str:
    return (f'<filter id="{id_}" x="-10%" y="-10%" width="120%" height="120%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="{frec}" '
            f'numOctaves="{octavas}" seed="{semilla}" result="ruido"/>')


def vidrio(intensidad: float = 1.0, foto: str = "", ancho: int = 1080,
           alto: int = 1080, foco: str = "50% 50%",
           semilla: int = 7) -> tuple[str, str]:
    """Gotas sobre un vidrio, con la foto desenfocada detrás.

    El primer intento fue recortar la foto nítida con una máscara de ruido, y
    salió mal: las gotas parecían rayones. El error era conceptual — una gota
    de agua no es una mancha, **es una lente**. Muestra el fondo nítido,
    ampliado y en su posición exacta.

    Entonces cada gota es un círculo con la misma foto de fondo, ampliada un
    35% y desplazada para que coincida justo con lo que tapa. Más un brillo
    abajo y una sombra arriba, que es lo que le da volumen. El fondo va
    desenfocado: es lo que se ve a través del vidrio entre gota y gota.
    """
    import random
    g = max(0.35, min(1.7, intensidad))
    r = random.Random(semilla)
    amp = 1.35
    cuantas = int(110 * g)
    gotas = []
    for _ in range(cuantas):
        # muchas chicas, algunas medianas, pocas grandes: es la distribución
        # que tiene el agua sobre un vidrio de verdad
        d = r.choice([r.randint(7, 16)] * 5 + [r.randint(16, 30)] * 3
                     + [r.randint(30, 52)])
        x = r.randint(-10, ancho - d + 10)
        y = r.randint(-10, alto - d + 10)
        bx = -(x + d / 2) * amp + d / 2
        by = -(y + d / 2) * amp + d / 2
        gotas.append(
            f'<i style="left:{x}px;top:{y}px;width:{d}px;height:{d}px;'
            f'background-size:{ancho*amp:.0f}px {alto*amp:.0f}px;'
            f'background-position:{bx:.0f}px {by:.0f}px;'
            f'opacity:{r.uniform(.72, .95):.2f}"></i>')

    return (f"""
.efx-vf{{position:absolute;inset:0;background-image:url({foto});
  background-size:cover;background-position:{foco};
  filter:blur({11*g:.0f}px) brightness(.70) saturate(.85);transform:scale(1.05)}}
.efx-vg{{position:absolute;inset:0}}
.efx-vg i{{position:absolute;display:block;border-radius:50%;
  background-image:url({foto});background-repeat:no-repeat;
  box-shadow:inset 0 -1.5px 2px rgba(255,255,255,.55),
             inset 0 1.5px 3px rgba(0,0,0,.45),
             0 2px 4px rgba(0,0,0,.40);
  filter:brightness(1.06) contrast(1.05)}}
""", f'<div class="efx-vf"></div><div class="efx-vg">{"".join(gotas)}</div>')

def lluvia(intensidad: float = 1.0) -> tuple[str, str]:
    """Estelas de lluvia por encima de lo que haya.

    Tres capas de gradientes, no un PNG: se estiran a cualquier formato sin
    perder nitidez y no pesan nada.

    Dos detalles que costaron. El primero: las líneas necesitan gradiente en
    los DOS ejes. Un `repeating-linear-gradient` vertical con `background-size`
    angosto no tila — el gradiente sólo varía en vertical, así que repetir
    columnas reproduce la misma banda y sale una persiana. La solución es un
    gradiente horizontal para las líneas finas y una máscara vertical para los
    trazos.

    El segundo: con trazos cortos y período parejo se forman hileras alineadas
    que delatan el truco. Los trazos van largos, con poco hueco, y las tres
    capas tienen períodos bien distintos para que no coincidan nunca.
    """
    g = max(0.3, min(1.7, intensidad))
    return (f"""
.efx-lv{{position:absolute;inset:-28%;pointer-events:none;
  mix-blend-mode:screen;opacity:{.55*g:.2f}}}
.efx-lv i{{position:absolute;inset:0;display:block}}
.efx-lv .a{{background-image:repeating-linear-gradient(to right,
   rgba(255,255,255,.60) 0 1.4px, rgba(255,255,255,0) 1.4px 19px);
 -webkit-mask-image:repeating-linear-gradient(to bottom,
   rgba(0,0,0,0) 0 14px, #000 30px 150px, rgba(0,0,0,0) 166px 181px);
 transform:rotate(14deg)}}
.efx-lv .b{{background-image:repeating-linear-gradient(to right,
   rgba(255,255,255,.34) 0 1px, rgba(255,255,255,0) 1px 31px);
 -webkit-mask-image:repeating-linear-gradient(to bottom,
   rgba(0,0,0,0) 0 22px, #000 40px 214px, rgba(0,0,0,0) 232px 253px);
 transform:rotate(16deg) scale(1.18);filter:blur(.6px)}}
.efx-lv .c{{background-image:repeating-linear-gradient(to right,
   rgba(255,255,255,.22) 0 2px, rgba(255,255,255,0) 2px 47px);
 -webkit-mask-image:repeating-linear-gradient(to bottom,
   rgba(0,0,0,0) 0 40px, #000 62px 300px, rgba(0,0,0,0) 322px 347px);
 transform:rotate(12deg) scale(1.35);filter:blur(1.4px)}}
""", '<div class="efx-lv"><i class="a"></i><i class="b"></i><i class="c"></i></div>')

def niebla(intensidad: float = 1.0) -> tuple[str, str]:
    """Bruma baja. Sirve para dar profundidad a una cancha vacía."""
    g = max(0.3, min(1.6, intensidad))
    return (f"""
.efx-niebla{{position:absolute;inset:0;pointer-events:none;
  opacity:{.55*g:.2f};mix-blend-mode:screen}}
""", f"""
<div class="efx-niebla">
  <svg width="100%" height="100%" preserveAspectRatio="none" viewBox="0 0 1080 1080">
    <defs>
      {_turbulencia("efx-f-niebla", "0.004 0.009", 4, _SEMILLA["niebla"])}
        <feColorMatrix in="ruido" type="matrix"
          values="0 0 0 0 .82  0 0 0 0 .87  0 0 0 0 .95  0 0 0 .55 0"/>
      </filter>
      <linearGradient id="efx-g-niebla" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="white" stop-opacity="0"/>
        <stop offset="55%" stop-color="white" stop-opacity=".5"/>
        <stop offset="100%" stop-color="white" stop-opacity="1"/>
      </linearGradient>
      <mask id="efx-m-niebla">
        <rect width="1080" height="1080" fill="url(#efx-g-niebla)"/>
      </mask>
    </defs>
    <rect width="1080" height="1080" filter="url(#efx-f-niebla)" mask="url(#efx-m-niebla)"/>
  </svg>
</div>
""")


def grano(intensidad: float = 1.0) -> tuple[str, str]:
    """Grano de película. Muy sutil a propósito: le saca lo digital a una foto
    nocturna sin que nadie note que está."""
    g = max(0.2, min(1.5, intensidad))
    return (f"""
.efx-grano{{position:absolute;inset:0;pointer-events:none;
  opacity:{.16*g:.2f};mix-blend-mode:overlay}}
""", f"""
<div class="efx-grano">
  <svg width="100%" height="100%" preserveAspectRatio="none" viewBox="0 0 1080 1080">
    <filter id="efx-f-grano"><feTurbulence type="fractalNoise"
      baseFrequency="0.9" numOctaves="3" seed="2"/></filter>
    <rect width="1080" height="1080" filter="url(#efx-f-grano)"/>
  </svg>
</div>
""")


def destello(intensidad: float = 1.0) -> tuple[str, str]:
    """Haz de luz en diagonal, como el reflejo de un foco de cancha."""
    g = max(0.3, min(1.6, intensidad))
    return (f"""
.efx-destello{{position:absolute;inset:-20%;pointer-events:none;
  mix-blend-mode:screen;opacity:{.42*g:.2f};
  background:linear-gradient(115deg,
    rgba(255,255,255,0) 34%, rgba(255,255,255,.55) 47%,
    rgba(228,255,2,.22) 52%, rgba(255,255,255,0) 63%);
  filter:blur(26px)}}
""", '<div class="efx-destello"></div>')


EFECTOS = {"vidrio": vidrio, "lluvia": lluvia, "niebla": niebla,
           "grano": grano, "destello": destello}

# Lo que puede decir un pedido y a qué efecto corresponde. Sirve para que el
# agente no tenga que adivinar el nombre técnico.
SINONIMOS = {
    "vidrio": ["ventana con gotas", "vidrio mojado", "gotas", "llovido",
               "detrás de un vidrio", "empañado"],
    "lluvia": ["que llueva", "lluvia", "diluvio", "día de lluvia", "chaparrón"],
    "niebla": ["niebla", "bruma", "neblina", "humo", "misterioso"],
    "grano": ["grano", "analógico", "textura de película", "vintage"],
    "destello": ["destello", "reflejo", "rayo de luz", "flash", "brillo"],
}


def aplicar(nombres, intensidad: float = 1.0, foto: str = "",
            ancho: int = 1080, alto: int = 1080,
            foco: str = "50% 50%") -> tuple[str, str]:
    """Combina varios efectos. Devuelve (css, html) listos para inyectar.

    El orden importa y está fijo: el vidrio va primero porque reemplaza la
    foto de fondo, y el grano último porque tiene que caer sobre todo lo
    demás.
    """
    if isinstance(nombres, str):
        nombres = [nombres]
    orden = ["vidrio", "niebla", "lluvia", "destello", "grano"]
    elegidos = [n for n in orden if n in nombres]
    css, html = [], []
    for n in elegidos:
        f = EFECTOS[n]
        c, h = f(intensidad, foto, ancho, alto, foco) if n == "vidrio" else f(intensidad)
        css.append(c)
        html.append(h)
    return "\n".join(css), "\n".join(html)
