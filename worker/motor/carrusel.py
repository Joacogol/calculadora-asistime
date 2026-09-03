# -*- coding: utf-8 -*-
"""Estructura de carruseles y secuencias de stories — sin marca adentro.

Acá está lo que es igual para cualquier marca: la numeración de los archivos,
la proporción única, el índice, las flechas, las zonas seguras de una story y
la caja de respuesta. Cómo se ve cada diapositiva lo pone la marca en su
`DIAPOS`.

El reparto no es arbitrario. Todo lo que está acá es algo que se rompe silencioso
si cada marca lo reimplementa:

- **La proporción única.** Instagram recorta cada imagen a la proporción de la
  primera. Una marca que lo olvide publica carruseles con placas cortadas y no
  se entera hasta que alguien mira el posteo.
- **La numeración.** `01`, `02`, `03` es lo único que garantiza que quien suba
  las imágenes no publique el podio al revés.
- **Las zonas seguras de story.** 190 px arriba y 250 abajo, que es donde
  Instagram pone el nombre de la cuenta y la caja de respuesta. Un titular que
  caiga ahí queda tapado.

Datos que sostienen las reglas de cantidad y ritmo: Metricool, 24,3 millones de
posteos sobre 375.000 cuentas — un carrusel genera nueve veces más guardados que
una foto sola. Socialinsider, 161.180 stories — la primera de una secuencia
pierde el 23,8% de la gente y entre el 57% y el 67% de los que quedan avanza
tocando.
"""
from . import contrato

# Zona segura de story: arriba va el nombre de la cuenta, abajo la caja de
# respuesta de Instagram. Nada importante puede caer en esas bandas.
SQ_TOP, SQ_BOT = 190, 250

MAX_DIAPOS = 10

CSS_MOTOR = """
.cr-idx{position:absolute;left:76px;bottom:64px;z-index:6;
  font-weight:500;font-size:26px;letter-spacing:.30em;opacity:.55}
.cr-fl{position:absolute;right:52px;top:50%;transform:translateY(-50%);z-index:6;
  display:flex;align-items:center;gap:6px}
.cr-fl i{display:block;width:15px;height:15px;border-right:3px solid;
  border-top:3px solid;transform:rotate(45deg)}
.cr-fl i:nth-child(1){opacity:.30}
.cr-fl i:nth-child(2){opacity:.62}
.cr-fl i:nth-child(3){opacity:1}
.sq-idx{position:absolute;left:76px;z-index:7;
  font-weight:500;font-size:25px;letter-spacing:.30em;opacity:.50}
.sq-resp{position:absolute;left:76px;right:76px;bottom:250px;z-index:6}
.sq-caja{border:2px solid;opacity:.78;border-radius:999px;
  padding:26px 40px;display:flex;align-items:center;justify-content:space-between}
.sq-caja span{font-weight:400;font-size:32px;color:#FAFAFA;opacity:.72}
.sq-pin{width:15px;height:15px;border-right:3px solid;border-top:3px solid;
  transform:rotate(45deg)}
"""


def cromo_carrusel(i: int, total: int, ac: str, tinta: str = "#FAFAFA",
                   fuente: str = "sans-serif") -> str:
    """Índice y flecha. La flecha no va en la última: ahí no hay nada más.

    `tinta` la pone la marca. Estaba fija en blanco, que servía mientras la
    única marca del sistema vivía en negro; la segunda tiene diapositivas
    blancas y el índice desaparecía en la mitad del carrusel. Un color de
    interfaz fijo en el motor es una marca escondida adentro del motor.
    """
    idx = (f'<div class="cr-idx" style="color:{tinta};font-family:{fuente}">'
           f'{i+1:02d} / {total:02d}</div>')
    if i >= total - 1:
        return idx
    return idx + f'<div class="cr-fl" style="color:{ac}"><i></i><i></i><i></i></div>'


def cromo_secuencia(i: int, total: int, d: dict, ac: str,
                    tinta: str = "#FAFAFA", fuente: str = "sans-serif",
                    fuente_texto: str = "sans-serif") -> str:
    """Índice de la secuencia, y la caja de respuesta si el cuadro la pide.

    El primer intento fue una barra segmentada arriba, y quedaba justo debajo de
    la barra de progreso que dibuja Instagram: dos barras iguales y ninguna se
    entendía. Un número chico informa lo mismo sin competir con la interfaz.

    Igual hace falta: la barra de Instagram cuenta TODAS las stories de la
    cuenta, no las de esta secuencia. El «01 / 03» es lo único que dice que esto
    es una cosa de tres partes y que vale la pena quedarse.
    """
    out = (f'<div class="sq-idx" style="top:{SQ_TOP - 46}px;color:{tinta};'
           f'font-family:{fuente}">{i+1:02d} / {total:02d}</div>')
    if i == total - 1 and d.get("responder"):
        # La caja va del color del índice, no blanca fija: sobre una marca de
        # fondos claros (Asistime) la caja blanca no se veía. El 3/9/2026 se
        # renderizó una secuencia y la caja estaba, pero invisible.
        out += (f'<div class="sq-resp"><div class="sq-caja" style="border-color:{tinta}">'
                f'<span style="font-family:{fuente_texto};color:{tinta}">{d["responder"]}</span>'
                f'<div class="sq-pin" style="color:{ac}"></div></div></div>')
    return out


def fondo(d: dict, negro: str = "#0A0A0A", oscuro: float = .62) -> str:
    """Foto con degradé, o fondo liso si la diapositiva no lleva foto.

    Que algunas lleven foto y otras no es a propósito: cinco fotos seguidas
    cansan y el banco de una marca nueva rara vez da para tantas. Alternar da
    ritmo y hace la pieza barata en material.
    """
    foto = d.get("foto")
    if not foto:
        return ('<div class="scrim" style="background:'
                f'radial-gradient(120% 80% at 50% 0%,#161616 0%,{negro} 70%)"></div>')
    return (f'<img class="bg" src="{foto}" style="object-position:'
            f'{d.get("foco", "50% 50%")}">'
            f'<div class="scrim" style="background:linear-gradient(180deg,'
            f'rgba(10,10,10,{oscuro*.72:.2f}) 0%,rgba(10,10,10,{oscuro*.45:.2f}) 38%,'
            f'rgba(10,10,10,{oscuro:.2f}) 72%,rgba(10,10,10,.92) 100%)"></div>')


def _pagina(marca, w, h, inner):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{marca.BASE_CSS}{CSS_MOTOR}
body{{width:{w}px}} .canvas{{width:{w}px;height:{h}px}}
</style></head><body><div class="canvas">{inner}</div></body></html>"""


def paginas(marca, data: dict, fmt: str, secuencia: bool = False) -> list[str]:
    """El HTML de cada diapositiva, en orden.

    `fmt` vale para TODAS: es la restricción de Instagram y no se negocia por
    diapositiva. En una secuencia de stories se ignora y siempre es 9:16.
    """
    contrato.verificar(marca, con_carrusel=True)

    slides = data.get("slides") or []
    if not slides:
        raise ValueError("un carrusel necesita al menos una diapositiva")
    if len(slides) > MAX_DIAPOS:
        raise ValueError(
            f"máximo {MAX_DIAPOS} diapositivas — más que eso no lo desliza nadie")

    # El acento por defecto lo declara la marca. Estaba escrito «lima», que es
    # un color que sólo existe en Boss Padel: cualquier otra marca que no
    # pusiera `acento` en el spec explotaba con un KeyError que no decía nada.
    por_defecto = getattr(marca, "ACENTO_POR_DEFECTO", None) or next(iter(marca.C))
    nombre_ac = data.get("acento") or por_defecto
    if nombre_ac not in marca.C:
        raise ValueError(
            f"la marca «{marca.NOMBRE}» no tiene el acento «{nombre_ac}». "
            f"Tiene: {', '.join(marca.C)}")
    ac = marca.C[nombre_ac]
    # El color del índice y de las flechas lo decide la marca: sobre fondo
    # claro el blanco no se ve. Si una diapositiva declara `cromo`, manda ella
    # — es el caso de un carrusel que alterna fondos.
    tinta_def = getattr(marca, "COLOR_CROMO", "#FAFAFA")
    # La tipografía del índice también era de una marca: estaba fija en la
    # condensada de la primera, que la segunda ni siquiera tiene instalada.
    fuente = getattr(marca, "FUENTE_CROMO", "sans-serif")
    # La caja de respuesta lleva la tipografía de CUERPO, no la del índice: el
    # índice va en condensada y la caja es una frase que se lee, no un rótulo.
    fuente_texto = getattr(marca, "FUENTE_TEXTO", "sans-serif")
    total = len(slides)

    # De qué color van el índice y las flechas sobre ESTA diapositiva. Manda
    # el spec si lo dice (`cromo`); si no, la marca puede saberlo por el tipo
    # —una marca de datos lo lee del contrato de la plantilla que dibuja esa
    # diapositiva, ver `plantillas.como_diapositivas`—; y si no, el color de
    # la marca para todas.
    cromo_de = getattr(marca, "CROMO_DIAPO", None)

    def tinta_de(s, tipo):
        if s.get("cromo"):
            return s["cromo"]
        if cromo_de:
            propio = cromo_de(tipo, s)
            if propio:
                return propio
        return tinta_def

    if secuencia:
        w, h = marca.FORMATOS["story"]
        if "cuadro" not in marca.DIAPOS:
            raise ValueError(
                "esta marca no tiene secuencias de stories: le falta DIAPOS['cuadro']")
        # `cuadro` es el DEFECTO, no el único. Hasta el 3/8/2026 la secuencia
        # pasaba todas las diapositivas por `cuadro` e ignoraba el `tipo` en
        # silencio: quien pedía una portada y un cierre recibía cinco cuadros
        # iguales y no se enteraba. Peor todavía, el `cierre` —el único lugar
        # donde alguien que vio toda la secuencia va a escribir por WhatsApp—
        # era imposible de poner.
        def cuerpo(s, w, h, ac):
            tipo = s.get("tipo", "cuadro")
            if tipo not in marca.DIAPOS:
                raise ValueError(
                    f"tipo de diapositiva desconocido: {tipo}. "
                    f"Esta marca tiene: {', '.join(sorted(marca.DIAPOS))}")
            return marca.DIAPOS[tipo](s, w, h, ac)

        return [_pagina(marca, w, h,
                        cuerpo(s, w, h, ac)
                        + cromo_secuencia(i, total, s, ac,
                                          tinta_de(s, s.get("tipo", "cuadro")),
                                          fuente, fuente_texto))
                for i, s in enumerate(slides)]

    w, h = marca.FORMATOS[fmt]
    salida = []
    for i, s in enumerate(slides):
        tipo = s.get("tipo", "texto")
        if tipo not in marca.DIAPOS:
            raise ValueError(
                f"tipo de diapositiva desconocido: {tipo}. "
                f"Esta marca tiene: {', '.join(sorted(marca.DIAPOS))}")
        salida.append(_pagina(marca, w, h,
                              marca.DIAPOS[tipo](s, w, h, ac)
                              + cromo_carrusel(i, total, ac,
                                               tinta_de(s, tipo), fuente)))
    return salida
