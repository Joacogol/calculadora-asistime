# -*- coding: utf-8 -*-
"""Chromium convirtiendo HTML en PNG y PDF. No sabe de ninguna marca.

Que sea el mismo navegador el que saca las placas, los carruseles y las
presentaciones es lo que garantiza que la tipografía y el interletrado sean
idénticos entre una placa y un PDF.

La marca entra como parámetro: este módulo sólo sabe que existe un objeto con
`FORMATOS`, `PLANTILLAS` y `DIAPOS`.
"""
import json
import logging
import os
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

from . import carrusel as mcarrusel
from . import contrato
from . import efectos
from . import revisar

log = logging.getLogger(__name__)


def _inyectar_efecto(html: str, data: dict, w: int, h: int) -> str:
    """Mete el efecto atmosférico en el HTML que ya armó la plantilla.

    Se hace acá y no adentro de cada plantilla a propósito: son nueve plantillas
    por marca y el efecto es el mismo para todas. El CSS entra antes de cerrar
    el `<style>` y el HTML justo después del `<img class="bg">`.

    El anclaje importa: las plantillas no usan z-index, así que manda el orden
    del documento. Ahí el efecto queda encima de la foto y debajo del texto. Si
    fuera el primer hijo del canvas, la foto lo taparía entero.
    """
    ef = data.get("efecto")
    if not ef:
        return html
    css, extra = efectos.aplicar(
        ef, float(data.get("efecto_fuerza", 1.0)),
        data.get("foto", ""), w, h, data.get("foco", "50% 50%"))

    i = html.rfind("</style>")
    if i > 0:
        html = html[:i] + css + html[i:]

    m = re.search(r'<img class="bg"[^>]*>', html)
    if m:
        corte = m.end()
    else:
        # Plantillas sin foto: no hay nada que tapar.
        j = html.find('class="canvas')
        corte = html.find(">", j) + 1 if j > 0 else 0
    return html[:corte] + extra + html[corte:]


class TextoNoEntra(Exception):
    """Una pieza cuyo texto se sale del lienzo. No se guarda: se levanta.

    Es la única excepción del motor que existe para NO entregar algo que se
    dibujó bien en todo lo demás. Vale la pena: una placa con el título
    cortado se publica igual que una correcta —nadie la mira dos veces— y el
    error se descubre en el feed del cliente.
    """


#: Cuánto aire se le exige al texto contra los costados del lienzo, en píxeles.
#:
#: No es un gusto: la tinta que TOCA el filo se lee como cortada aunque
#: técnicamente entre. El número salió de medir las quince piezas reales de
#: Stadium (cinco plantillas por tres formatos): el texto que más se arrima a
#: un costado queda a 21 px. Con 16 no se toca ninguna pieza que hoy sale bien.
#: Si alguna marca nueva dibuja más al filo que eso, este número baja — pero se
#: baja midiendo, no a ojo.
#:
#: **Sólo a los costados.** Arriba y abajo el límite es el borde pelado, y no
#: por olvido: en esas mismas quince piezas hay texto a 13 px del borde de
#: abajo, y no está mal puesto. La caja de línea incluye ascendentes y
#: descendentes que el interlineado recorta a propósito, así que exigir aire
#: vertical es pelearse con la tipografía. Además el corte que hay que evitar
#: es el de los costados: una palabra que se va por el lado. Un título que se
#: fuera por arriba también se agarra —el borde sigue siendo límite—, sólo que
#: sin franja de cortesía.
MARGEN_SEGURO = 16

#: Mide el texto YA DIBUJADO y lo achica hasta que entre. Corre adentro de
#: Chromium, después de que cargaron las fuentes y antes de la foto.
#:
#: Por qué acá y no en cada plantilla: el 25/8/2026 quedó anotado que tres
#: plantillas de Boss resolvían esto por su cuenta, cada una a su manera y sin
#: enterarse de las otras. El 31/8 una placa de Clínica salió con
#: «PAPANICOLAOU» cortado contra el borde —y esa plantilla YA llamaba a su
#: propio `achicar_titular`, que decide por la CANTIDAD DE LETRAS del título:
#: doce le parecieron pocas, y doce mayúsculas de una sola palabra en un panel
#: de 480 px se pasaban 99. Contar letras nunca iba a ver eso. Una regla que
#: cada plantilla aplica a su manera es una regla que algún día no se aplica;
#: acá pasa TODA pieza de TODA marca y no hay dónde olvidarse.
#:
#: Se mide con un `Range` sobre el contenido y no con el rectángulo del
#: elemento, y esa diferencia es justamente el caso que falló: una palabra
#: larga sin dónde cortar se desborda de su caja, pero la CAJA sigue midiendo
#: lo que decía el CSS. El rectángulo diría que está todo bien.
#:
#: El límite es el LIENZO y no la caja del elemento. Se probó con la caja —el
#: interior del contenedor, ya sin padding— y hay que descartarla: medido
#: contra las quince piezas reales de Stadium, TODAS se pasan de su caja por
#: arriba y por abajo entre 1 y 37 px, porque la caja de línea incluye
#: ascendentes y descendentes que un interlineado de 0.84 recorta a propósito.
#: Con ese límite el motor achicaba «$ 3.990» de 118 px a 64 y arruinaba
#: piezas que estaban bien. Contra el lienzo, esas mismas quince piezas dan
#: cero: el guardián no toca nada de lo que hoy funciona.
QUE_ENTRE = """
(margen) => {
  const canvas = document.querySelector('.canvas');
  if (!canvas) return [];
  const c = canvas.getBoundingClientRect();
  const lim = {l: c.left + margen, r: c.right - margen,
               t: c.top, b: c.bottom};

  // Sólo los elementos que dibujan texto PROPIO. Un contenedor hereda el
  // texto de sus hijos y contarlo sería achicar dos veces lo mismo.
  //
  // `<style>` está en la lista porque el logo de Stadium es un SVG con su CSS
  // adentro: sin esto, el motor medía «.st0 { fill: #...» como si fuera un
  // titular y podía rechazar una pieza impecable por un texto invisible.
  const MUDOS = ['STYLE', 'SCRIPT', 'TITLE', 'DEFS', 'METADATA'];
  const conTexto = [...canvas.querySelectorAll('*')].filter(
    el => !MUDOS.includes(el.tagName.toUpperCase()) &&
      getComputedStyle(el).visibility !== 'hidden' &&
      [...el.childNodes].some(
        n => n.nodeType === Node.TEXT_NODE && n.textContent.trim()));

  const tinta = (el) => {
    const r = document.createRange();
    r.selectNodeContents(el);
    return r.getBoundingClientRect();
  };
  const afuera = (el) => {
    const t = tinta(el);
    // Sin caja no hay tinta: `display:none` o un nodo vacío.
    if (!t.width && !t.height) return 0;
    return Math.max(0, lim.l - t.left, t.right - lim.r,
                       lim.t - t.top, t.bottom - lim.b);
  };

  const ajustados = [];
  for (const el of conTexto) {
    if (afuera(el) <= 1) continue;
    const original = parseFloat(getComputedStyle(el).fontSize) || 0;
    if (!original) continue;

    // Se achica de a poco y se vuelve a medir. De a 4% para que el cambio no
    // se note al lado de una pieza hecha antes; el piso es 55% porque más
    // abajo el titular deja de ser un titular y el problema es otro.
    let fs = original;
    let vueltas = 0;
    while (afuera(el) > 1 && vueltas < 60 && fs > original * 0.55) {
      fs *= 0.96;
      el.style.fontSize = fs + 'px';
      vueltas++;
    }
    ajustados.push({
      texto: el.textContent.trim().slice(0, 70),
      de: Math.round(original),
      a: Math.round(fs),
      sigue_afuera: Math.round(afuera(el)),
    });
  }
  return ajustados;
}
"""


#: La firma de la marca no la pisa nadie. Se mide con geometría y adentro del
#: navegador, que sabe exactamente dónde quedó cada caja después de aplicar el
#: retoque — cosa que ninguna comparación de píxeles puede saber.
#:
#: El 4/9/2026 el agente subió el titular con un retoque y le quedó encima del
#: isotipo: 712 píxeles de tinta adentro de la caja del logo. La pieza salió
#: así. Lo que falla acá no lo causa el dibujo, así que las medidas del dibujo
#: no lo veían; y no es «tapar» en el sentido de los píxeles, porque el texto
#: se MOVIÓ. Es una superposición, y una superposición se mide con rectángulos.
MARCAS_LIBRES = """
() => {
  const marcas = [...document.querySelectorAll('.marca-iso, .marca-logo')];
  if (!marcas.length) return [];
  // Sólo lo que DIBUJA algo propio: un contenedor se superpone con todo lo
  // que tiene adentro y avisaría siempre.
  const MUDOS = ['STYLE','SCRIPT','TITLE','DEFS','METADATA'];
  const pinta = [...document.querySelectorAll('.canvas *')].filter(
    el => !MUDOS.includes(el.tagName.toUpperCase()) &&
      getComputedStyle(el).visibility !== 'hidden' &&
      [...el.childNodes].some(
        n => n.nodeType === Node.TEXT_NODE && n.textContent.trim()));

  const avisos = [];
  for (const m of marcas) {
    const a = m.getBoundingClientRect();
    if (!a.width || !a.height) continue;
    for (const el of pinta) {
      if (m.contains(el) || el.contains(m)) continue;
      const r = document.createRange();
      r.selectNodeContents(el);
      const b = r.getBoundingClientRect();
      const ancho = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const alto  = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (ancho > 2 && alto > 2) {
        const texto = el.textContent.trim().slice(0, 40);
        avisos.push(`«${texto}» le queda encima al logo de la marca `
          + `(se pisan ${Math.round(ancho)}x${Math.round(alto)} px). `
          + `El logo firma la pieza: no se le pone nada arriba`);
        break;
      }
    }
  }
  return avisos;
}
"""


#: Cómo alinea la pieza. Es un hecho y no un defecto —una pieza centrada está
#: bien, una alineada a la izquierda también— pero MEZCLAR las dos es lo
#: primero que delata una pieza armada por partes. El 4/9/2026: isotipo en
#: x=106, pie en x=97, titular centrado en x=249. Tres bloques, dos criterios.
#:
#: Se mide adentro del navegador por lo mismo que la superposición del logo:
#: después del retoque, el único que sabe dónde quedó cada caja es Chromium.
COMO_ALINEA = """
() => {
  const canvas = document.querySelector('.canvas');
  if (!canvas) return null;
  const c = canvas.getBoundingClientRect();
  const MUDOS = ['STYLE','SCRIPT','TITLE','DEFS','METADATA'];
  const bloques = [...canvas.querySelectorAll('*')].filter(
    el => !MUDOS.includes(el.tagName.toUpperCase()) &&
      getComputedStyle(el).visibility !== 'hidden' &&
      [...el.childNodes].some(
        n => n.nodeType === Node.TEXT_NODE && n.textContent.trim()));
  [...canvas.querySelectorAll('.marca-iso, .marca-logo')].forEach(
    m => bloques.push(m));

  let centrados = 0, laterales = 0;
  for (const el of bloques) {
    let r;
    if (el.classList.contains('marca-iso') || el.classList.contains('marca-logo')) {
      r = el.getBoundingClientRect();
    } else {
      const rango = document.createRange();
      rango.selectNodeContents(el);
      r = rango.getBoundingClientRect();
    }
    if (!r.width || r.width > c.width * 0.96) continue;
    const izq = r.left - c.left, der = c.right - r.right;
    // Centrado = le sobra lo mismo de los dos lados.
    if (Math.abs(izq - der) < c.width * 0.03) centrados++;
    else laterales++;
  }
  if (centrados && laterales) {
    return `la pieza mezcla ${centrados} bloque(s) centrado(s) con `
      + `${laterales} pegado(s) a un costado — elegí una sola alineación`;
  }
  return null;
}
"""


class Render:
    """Un Chromium abierto, renderizando piezas de UNA marca.

    `raiz` es la carpeta de la marca: el HTML intermedio tiene que escribirse
    ahí porque las plantillas referencian `assets/` y `fonts/` con rutas
    relativas. Si lo escribiéramos en /tmp, Chromium no encontraría ni las fotos
    ni las tipografías.

    Los temporales llevan el PID en el nombre y se borran en un `finally`: dos
    archivos de depuración quedaron olvidados dentro de una skill y viajaron a la
    imagen de Docker sumando 8.000 tokens de basura que el agente podía leer.
    """

    def __init__(self, marca, raiz: pathlib.Path):
        contrato.verificar(marca)
        self.marca = marca
        self.raiz = pathlib.Path(raiz)
        self._tmp: list[pathlib.Path] = []
        #: Lo que hubo que achicar para que entrara. Se cuenta en las notas de
        #: la pieza: un texto que se achicó salió bien, pero que haya hecho
        #: falta es una señal de que el pedido venía largo para esa plantilla.
        self.ajustes: list[dict] = []
        #: Lo que el motor MIDIÓ y está mal, en castellano. Se imprime al
        #: final del render, que es donde lo lee el agente sin que nadie se lo
        #: pida: la salida del comando que ya corrió. Un aviso en un archivo
        #: aparte es un aviso que no se lee.
        self.avisos: list[str] = []
        #: Cómo quedó compuesta cada pieza a medida. No son defectos: son
        #: hechos para que quien la armó la juzgue. Ver `revisar.composicion`.
        self.composicion: list[str] = []

    def _temporal(self, sufijo: str) -> pathlib.Path:
        p = self.raiz / f"_tmp-{os.getpid()}{sufijo}"
        self._tmp.append(p)
        return p

    def _captura(self, pg, html, w, h, destino, data=None):
        tmp = self._temporal(f"-{destino.stem}.html")
        tmp.write_text(_inyectar_efecto(html, data or {}, w, h), encoding="utf-8")
        pg.set_viewport_size({"width": w, "height": h})
        pg.goto(f"file://{tmp}")
        pg.wait_for_timeout(320)

        # El texto se MIDE ya dibujado, justo antes de la foto. Ver `QUE_ENTRE`.
        for aviso in pg.evaluate(MARCAS_LIBRES):
            self.avisos.append(f"{destino.stem}: {aviso}")
        mezcla = pg.evaluate(COMO_ALINEA)
        if mezcla:
            self.composicion.append(f"{destino.stem}: {mezcla}")

        ajustes = pg.evaluate(QUE_ENTRE, MARGEN_SEGURO)
        rotos = [a for a in ajustes if a["sigue_afuera"] > 1]
        if rotos:
            cuales = "; ".join(
                f"«{a['texto']}» se sale {a['sigue_afuera']} px" for a in rotos)
            raise TextoNoEntra(
                f"en {destino.stem} el texto no entra en la pieza aunque se "
                f"achicó al mínimo: {cuales}. Hay que acortarlo o corregir la "
                f"plantilla — una pieza con el texto cortado no se publica.")
        if ajustes:
            self.ajustes.extend({**a, "pieza": destino.stem} for a in ajustes)

        pg.locator(".canvas").screenshot(path=str(destino))
        return destino

    def placa(self, pg, tpl, data, fmt, nombre, salida):
        w, h = self.marca.FORMATOS[fmt]
        html = self.marca.PLANTILLAS[tpl](data, fmt)
        hecha = self._captura(pg, html, w, h, salida / f"{nombre}.png", data)
        d = data or {}
        # Con foto no se mide, y no es pereza: la medida busca la tinta de la
        # plantilla mirando dónde la imagen cambia de golpe, y una foto cambia
        # de golpe en todas partes. Sobre una foto, cualquier dibujo daría
        # «tapa el 40%» y el aviso sería falso siempre — que es la única
        # manera segura de que nadie lo lea nunca más.
        if (d.get("dibujo") or d.get("retoque")) and not d.get("foto") \
                and not d.get("efecto"):
            self._medir_a_medida(pg, tpl, data, fmt, w, h, hecha)
        return hecha

    def _medir_a_medida(self, pg, tpl, data, fmt, w, h, hecha):
        """La misma pieza SIN retoque y SIN dibujo, para saber qué se rompió.

        Renderizar dos veces suena caro y no lo es —es una captura más, y sólo
        en las piezas a medida, que son pocas—; a cambio la medida es exacta.
        Comparar contra la plantilla pelada no requiere adivinar dónde está el
        logo ni qué plantilla se usó: lo que cambió es lo que se pidió a medida.

        El retoque **sí** se deja puesto en la comparación, y se probó al revés:
        sacándolo también, mover el titular con un retoque —algo perfectamente
        legítimo— se leía como «el dibujo tapó el 100% del título», porque en
        una imagen estaba arriba y en la otra en el medio. Mover no es tapar.
        Lo que el retoque le pueda hacer al logo o al pie se mide aparte y por
        geometría, en `_marcas_pisadas`.
        """
        limpio = self._temporal(f"-{hecha.stem}-sin-dibujo.png")
        # La captura de comparación es interna y no se entrega: sus avisos son
        # los de la pieza y ya se dieron, con el nombre de verdad. Si no se
        # descartan, cada aviso sale dos veces y el segundo con un nombre de
        # archivo temporal, que no le dice nada a nadie.
        antes = len(self.avisos)
        try:
            pelado = {**data, "dibujo": None}
            html = self.marca.PLANTILLAS[tpl](pelado, fmt)
            self._captura(pg, html, w, h, limpio, pelado)
            del self.avisos[antes:]
            zonas = (getattr(self.marca, "ZONAS_SEGURAS", None) or {}).get(fmt)
            self.avisos += [f"{hecha.stem}: {p}"
                            for p in revisar.revisar_dibujo(hecha, limpio, zonas)]
            self.composicion += [f"{hecha.stem}: {l}"
                                 for l in revisar.composicion(hecha, limpio)]
        except Exception as e:                               # noqa: BLE001
            # Medir no puede romper una pieza que ya salió: si esto falla, la
            # pieza está hecha igual y lo único que se pierde es el aviso.
            log.warning("no pude medir %s: %s", hecha.stem, e)

    def carrusel(self, pg, data, fmt, nombre, salida, secuencia=False):
        """Todas las diapositivas de un carrusel o secuencia.

        Dos cosas se resuelven acá y no en el spec, porque son las dos que se
        rompen solas si dependen de que alguien se acuerde:

        **Un solo formato para todas.** Instagram recorta cada diapositiva a la
        proporción de la primera, así que `fmt` se aplica al carrusel entero.

        **La numeración.** Los archivos salen `nombre-01.png`, `-02.png`. Van a
        aparecer en ese orden en el explorador de quien los suba, que es lo único
        que garantiza que el podio no se publique al revés.
        """
        w, h = (self.marca.FORMATOS["story"] if secuencia
                else self.marca.FORMATOS[fmt])
        paginas = mcarrusel.paginas(self.marca, data, fmt, secuencia)
        rutas = []
        for i, html in enumerate(paginas):
            d = (data.get("slides") or [])[i]
            rutas.append(self._captura(pg, html, w, h,
                                       salida / f"{nombre}-{i+1:02d}.png", d))
        return rutas

    def presentacion(self, pg, data, nombre, salida):
        if not hasattr(self.marca, "PRESENTACION"):
            raise ValueError("esta marca no tiene presentaciones PDF: "
                             "le falta `PRESENTACION`")
        html, ancho, alto = self.marca.PRESENTACION(data)
        tmp = self._temporal(f"-{nombre}-deck.html")
        tmp.write_text(html, encoding="utf-8")
        pg.set_viewport_size({"width": ancho, "height": alto})
        pg.goto(f"file://{tmp}")
        # Las fuentes tienen que estar cargadas antes de imprimir: si no, la
        # primera página sale con la tipografía de respaldo.
        pg.wait_for_function("document.fonts.ready.then(() => true)")
        pg.wait_for_timeout(450)
        destino = salida / f"{nombre}.pdf"
        pg.pdf(path=str(destino), width=f"{ancho}px", height=f"{alto}px",
               print_background=True,
               margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        return destino

    def correr(self, spec, salida):
        salida = pathlib.Path(salida)
        salida.mkdir(parents=True, exist_ok=True)
        hechas = []
        try:
            with sync_playwright() as p:
                b = p.chromium.launch()
                pg = b.new_page(viewport={"width": 1080, "height": 1080},
                                device_scale_factor=1)
                for j in spec:
                    tpl = j["plantilla"]
                    if tpl == "presentacion":
                        hechas.append(self.presentacion(
                            pg, j["data"], j["nombre"], salida))
                    elif tpl in ("carrusel", "secuencia"):
                        hechas += self.carrusel(
                            pg, j["data"], j.get("formato", "vert"),
                            j["nombre"], salida, secuencia=(tpl == "secuencia"))
                    else:
                        hechas.append(self.placa(
                            pg, tpl, j["data"], j.get("formato", "post"),
                            j["nombre"], salida))
                b.close()
        finally:
            for t in self._tmp:
                t.unlink(missing_ok=True)
        return hechas


def desde_linea_de_comandos(marca, raiz, argv):
    """El lanzador que cada marca expone como `render.py spec.json [salida]`.

    Quien lee esta salida es el diseñador, así que un texto que no entra sale
    como una frase y no como un traceback: el que tiene que acortar el título
    es él, y una pila de llamadas de Python no le dice qué acortar.
    """
    spec = json.loads(pathlib.Path(argv[1]).read_text(encoding="utf-8"))
    destino = argv[2] if len(argv) > 2 else pathlib.Path(raiz) / "out"
    r = Render(marca, raiz)
    try:
        hechas = r.correr(spec, destino)
    except TextoNoEntra as e:
        print(f"\nNO SE DIBUJÓ: {e}\n", file=sys.stderr)
        raise SystemExit(2)
    for p in hechas:
        print("→", p)
    # Un texto que se achicó salió bien, pero conviene decirlo: significa que
    # el pedido venía largo para esa plantilla y la próxima puede no entrar.
    for a in r.ajustes:
        print(f"   (se achicó «{a['texto'][:44]}» de {a['de']} a {a['a']} px "
              f"en {a['pieza']} para que entrara)")
    # Primero los hechos de la composición, que no piden nada y se leen de
    # corrido; después los avisos, que sí piden. Al revés, los avisos quedan
    # sepultados entre números.
    if r.composicion:
        print("\n   cómo quedó compuesta:")
        for c in r.composicion:
            print(f"   · {c}")
    # Los avisos van al final y con una marca visible: son lo único de esta
    # salida que pide una acción. Ver `Render.avisos`.
    for a in r.avisos:
        print(f"\n⚠  {a}")
    if r.avisos:
        print("\n   Corregí y volvé a renderizar antes de seguir.")
