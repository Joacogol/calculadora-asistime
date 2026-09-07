# -*- coding: utf-8 -*-
"""Motor de piezas — la parte que no sabe de ninguna marca.

Acá vive todo lo que sirve igual para Boss Padel, para una clínica o para lo
que venga: el navegador que convierte HTML en PNG, el que arma reels con
ffmpeg, la síntesis de sonido, los efectos de clima, y la estructura de un
carrusel (numeración, proporción única, índice, flechas, zonas seguras de
story).

Lo que NO vive acá es cómo se ve una marca: colores, tipografías, logo,
plantillas, banco de fotos. Eso es de cada marca y va en su propia carpeta
bajo `.claude/skills/`.

**Por qué está separado.** El sistema se construyó primero para Boss Padel y
después se armó una segunda marca de cero, con su propio generador en Node. El
resultado fue que la segunda no tenía banco de fotos, ni carruseles, ni reels,
ni efectos, ni presentaciones — todo estaba escrito, pero atado a la primera.

Con copias separadas, cada función nueva hay que aplicarla una vez por marca.
Después de la tercera se deja de agregar funciones, no por decisión sino porque
duele. Esta separación es lo que evita eso: una función nueva entra una sola vez
y la tienen todas.

## El contrato

Una marca es un módulo Python que expone:

    C           dict de colores          {"lima": "#E4FF02", ...}
    FORMATOS    dict formato → (w, h)    {"post": (1080, 1080), ...}
    BASE_CSS    str, la hoja de estilo base de la marca
    PLANTILLAS  dict nombre → f(data, fmt) -> html completo
    logo(size, color, align) -> html

Y, si quiere carruseles:

    DIAPOS      dict tipo → f(data, w, h, acento) -> html del cuerpo

`motor.contrato.verificar(marca)` lo chequea y falla con un mensaje claro si
falta algo. Es la diferencia entre «una marca nueva no anda y no se sabe por
qué» y «falta `PLANTILLAS`».
"""
