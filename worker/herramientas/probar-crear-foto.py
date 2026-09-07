#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Que «crear» no acepte lo que no puede cumplir, antes de cobrarlo.

    python3 herramientas/probar-crear-foto.py

El 4/9/2026 se pidió dos veces un mockup «con la foto adjunta» y con el texto
y los colores oficiales de Asistime. Las dos salieron por `crear`, que es
texto-a-imagen y **no recibe ninguna foto**. El modelo inventó una
conversación de WhatsApp que nunca existió —con un paisaje de stock y una
bandera argentina—, escribió el título con otra tipografía y en otros azules,
y se inventó un lockup «🤩 Asistime». Cien créditos cada intento.

Lo que más importa del caso: **la regla ya estaba escrita** en el prompt del
agente, «no pidas texto, carteles ni logos: el modelo los escribe mal». Una
regla escrita es una sugerencia. Acá es un error, y llega antes del gasto.

La otra mitad de la prueba son los pedidos legítimos: si esto rechaza una foto
normal, el editor deja de servir y alguien lo apaga.
"""
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from app import fotero                                                  # noqa: E402

fallos = []


def revisar(caso, texto, rechaza, dice=""):
    try:
        fotero._revisar_crear(texto)
        paso, motivo = True, ""
    except ValueError as e:
        paso, motivo = False, str(e)
    bien = (not paso) == rechaza and (not rechaza or dice in motivo)
    print(f"  {'✓' if bien else '✗'} {caso}" + ("" if bien else f" — {motivo[:120]}"))
    if not bien:
        fallos.append(caso)


print("\n■ Lo que «crear» no puede y ahora no acepta")
revisar("el mockup con la foto adjunta, tal cual se pidió",
        'Mock-up vertical para story: un teléfono moderno con fondo blanco, '
        'visto de frente. En la pantalla del celular va la foto adjunta (una '
        'captura de WhatsApp). El diseño lleva el texto destacado "Les damos '
        'una pista" usando la tipografía y colores oficiales de Asistime.',
        True, "NO recibe ninguna foto")
revisar("una captura subida", "Poné la captura subida adentro de un marco",
        True, "NO recibe ninguna foto")
revisar("un cartel con texto", "Un cartel de neón que diga BIENVENIDOS",
        True, "no escribe texto")
revisar("la tipografía de la marca",
        "Una placa con la tipografía oficial de la marca", True, "no escribe texto")
revisar("el logo", "Una taza con el logo de la marca en el frente",
        True, "no dibuja logos")

print("\n■ Y lo que sí puede, que tiene que seguir pasando")
revisar("un teléfono sin nada escrito",
        "Mock-up vertical: un teléfono moderno visto de frente sobre fondo "
        "blanco, luz neutra, la pantalla apagada.", False)
revisar("una cancha vacía",
        "Una cancha de pádel al atardecer, vacía, luz cálida, sin gente.", False)
revisar("un plato de comida",
        "Un plato de milanesa con papas sobre una mesa de madera, luz de "
        "ventana, desde arriba.", False)
revisar("una textura",
        "Fondo de cemento gris con textura, iluminación pareja.", False)

print("\n  todo bien" if not fallos else f"\n  {len(fallos)} fallo(s): "
      + ", ".join(fallos))
sys.exit(1 if fallos else 0)
