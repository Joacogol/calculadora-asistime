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


def ok(caso, condicion, visto=""):
    """Una comprobación suelta, para lo que no es un prompt de `crear`."""
    print(f"  {'✓' if condicion else '✗'} {caso}"
          + ("" if condicion else f" — vi {visto!r}"))
    if not condicion:
        fallos.append(caso)


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

# ── La foto de entrada se copia a nuestro bucket ─────────────────────────
#
# Magnific baja la foto por su cuenta: le pasamos una URL y va a buscarla. Con
# una URL ajena, lo que vuelve es el error de ELLOS bajándola —«Value cannot be
# null (Parameter \'pointer\')»— que no dice nada de lo que pasó. El 8/9/2026 una
# foto de producto de larrique.com.uy, que se abre perfecto en un navegador,
# hacía fallar el recorte así, y el mismo sitio le contestaba 403 al
# «Python-urllib» con el que `urlopen` se presenta solo.
#
# Copiándola primero, Magnific siempre baja de un bucket público nuestro. Lo
# que se fija acá es que se copie la ajena y NO la que ya es nuestra: copiar la
# propia sería pagar dos veces el mismo archivo por nada.
print("\n■ La foto de entrada se copia y se convierte antes de ir a Magnific")

NUESTRA = ("https://qxjvtxumkljsroukpkny.supabase.co/storage/v1/object/public/"
           "disenos-larrique/editadas/abc.jpg")
subidas = []


def _subir_falso(local, nombre):
    subidas.append(nombre)
    return f"https://ejemplo.test/storage/v1/object/public/bucket/{nombre}"


def _falso(formato, modo="RGB"):
    """Un `bajar` que deja una imagen DE VERDAD en ese formato.

    Tiene que ser real y no unos bytes con la cabecera correcta: lo que se está
    probando es justamente la conversión, y para convertir hay que poder abrir.
    """
    def _bajar(url, destino):
        from PIL import Image
        Image.new(modo, (40, 30), (200, 30, 30) if modo == "RGB" else
                  (200, 30, 30, 128)).save(destino, formato)
        return destino
    return _bajar


real_bajar = fotero.bajar
try:
    # Una foto de WhatsApp llega como webp, y quitar fondo NO lee webp: contesta
    # «The URL does not point to an image», que suena a URL rota y en realidad
    # es un formato que no entiende. Tiene que salir convertida.
    fotero.bajar = _falso("WEBP")
    salida = fotero.copiar_entrante({"id": "f1", "foto": "https://ajena.test/p.webp"},
                                    _subir_falso)
    ok("un webp de chat se convierte a jpg", subidas == ["entrantes/f1.jpg"], subidas)
    ok("y lo que se manda es NUESTRA copia",
       salida.startswith("https://ejemplo.test/"), salida)

    subidas.clear()
    fotero.bajar = _falso("WEBP", "RGBA")
    fotero.copiar_entrante({"id": "f2", "foto": "https://ajena.test/t.webp"},
                           _subir_falso)
    ok("uno con transparencia va a png, no a jpg",
       subidas == ["entrantes/f2.png"], subidas)

    subidas.clear()
    fotero.bajar = _falso("JPEG")
    fotero.copiar_entrante({"id": "f3", "foto": "https://ajena.test/p.jpg"},
                           _subir_falso)
    ok("un jpg que ya venía bien sigue siendo jpg",
       subidas == ["entrantes/f3.jpg"], subidas)

    subidas.clear()
    igual = fotero.copiar_entrante({"id": "f4", "foto": NUESTRA}, _subir_falso)
    ok("una que ya es nuestra no se copia", subidas == [], subidas)
    ok("y se manda tal cual", igual == NUESTRA, igual)

    subidas.clear()
    vacio = fotero.copiar_entrante({"id": "f5", "foto": ""}, _subir_falso)
    ok("sin foto no revienta (es el caso de `crear`)",
       vacio == "" and subidas == [], (vacio, subidas))
finally:
    fotero.bajar = real_bajar

# Y el User-Agent, que es la otra mitad del mismo problema: el que bajaba era
# el worker y lo rechazaban por el nombre con que se presenta.
ok("el worker se presenta como un navegador",
   "Mozilla/" in fotero.NAVEGADOR and "urllib" not in fotero.NAVEGADOR,
   fotero.NAVEGADOR[:40])

print("\n  todo bien" if not fallos else f"\n  {len(fallos)} fallo(s): "
      + ", ".join(fallos))
sys.exit(1 if fallos else 0)
