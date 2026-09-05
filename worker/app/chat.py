# -*- coding: utf-8 -*-
"""Worker: los pedidos entran por la app de cada cliente.

Cada corrida recorre TODOS los clientes configurados. Para cada uno:
  1. lee los diseños pendientes de su tabla `disenos`
  2. toma cada uno con un candado atómico (pendiente → generando)
  3. le pide al agente que diseñe, con la skill de esa marca
  4. sube las piezas al Storage de ESE cliente y lo marca como listo

Cada cliente tiene su propia base porque es lo que permite entregarle o
venderle el sistema sin desenredar sus diseños de los de otro. El motor es uno
solo: una función nueva la reciben todos el mismo día.

Un cliente caído no frena a los demás — si la base de uno no responde, los
otros se siguen atendiendo.
"""
import asyncio
import json
import logging
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import (banco, cobro, config, fotero, manual, motorista, plantillas,
               plantillero, publicador, reelero)
from motor.revisar import en_una_linea, revisar_imagen
from .supa import Cliente
from .disenador import disenar

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("chat")

IMAGENES = {".png", ".jpg", ".jpeg", ".webp"}
DOCUMENTOS = {".pdf"}
VIDEOS = {".mp4", ".mov"}


#: Dónde arrancan las notas cuando quedaron pegadas abajo del copy: el
#: encabezado «QUÉ INTERPRETÉ» —que a veces viene sin tilde— o una línea de
#: guiones, que es lo que el diseñador pone antes de cualquier cosa que no sea
#: el posteo.
_CORTE = re.compile(r"^\s*(qu[eé] interpret|-{3,}\s*$)", re.I)
_SUBRAYADO = re.compile(r"^-{3,}$")


def _separar_notas(copy: str) -> tuple[str, str]:
    """Devuelve (texto del posteo, notas) a partir de un `copy.txt` mezclado.

    Si el archivo trae sólo el copy —que es lo que corresponde desde el
    9/8/2026— devuelve el copy entero y notas vacías, sin tocar nada.
    """
    lineas = (copy or "").split("\n")

    # Un título subrayado con guiones abre una sección. Si hay una que se llama
    # «COPY …», el posteo empieza abajo de ese título; si no hay ninguna, el
    # posteo arranca arriba de todo. Sin esto, un archivo que empieza con
    # «COPY PARA INSTAGRAM» + guiones se cortaba en la primera línea y el copy
    # quedaba vacío.
    inicio = 0
    for i in range(len(lineas) - 1):
        if lineas[i].strip() and _SUBRAYADO.match(lineas[i + 1].strip()):
            if "COPY" in lineas[i].strip().upper():
                inicio = i + 2
            break

    resto = lineas[inicio:]
    for j, l in enumerate(resto):
        if _CORTE.match(l):
            return "\n".join(resto[:j]).strip(), "\n".join(resto[j:]).strip()
    return "\n".join(resto).strip(), ""


def _duracion(ruta: Path) -> float:
    """Segundos de un video. Si ffprobe falla, 0: el chat lo muestra igual."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(ruta)],
            capture_output=True, text=True, timeout=20)
        return round(float(r.stdout.strip()), 1)
    except Exception:
        return 0.0


async def procesar(cli: Cliente, pedido: dict):
    pid = pedido["id"]
    if not cli.tomar(pid):
        log.info("[%s] diseño %s ya lo tomó otra corrida", cli.marca, pid)
        return

    salida = config.SALIDA / str(pid)
    if salida.exists():
        shutil.rmtree(salida)

    try:
        ok, titulo, metricas = await disenar(pedido, salida, cli)
        if not ok:
            # Si el agente dejó escrito por qué no generó nada, ese texto vale
            # mucho más que un mensaje genérico: puede ser «me faltan los
            # horarios concretos» y entonces la persona sabe exactamente qué
            # agregar. Hasta el 8/8/2026 esa explicación se tiraba y todos los
            # fallos se veían iguales.
            # Puede haberla dejado en cualquiera de los dos: cuando no genera
            # nada, la explicación es lo único que escribe.
            partes = []
            for nombre in ("copy.txt", "notas.txt"):
                f = salida / nombre
                if f.exists():
                    t = f.read_text(encoding="utf-8", errors="replace").strip()
                    if t:
                        partes.append(t)
            nota = "\n\n".join(partes)
            cli.marcar(pid, "error", metricas=metricas,
                       mensaje_agente=(nota[:1500] if nota else
                                       "No se pudo generar la pieza. "
                                       "Probá reformulando el pedido."))
            return

        # Tres canales, porque el chat hace tres cosas distintas con ellos:
        #   urls        las imágenes, que muestra con un <img>
        #   documentos  los PDF, que no se previsualizan: tarjeta de descarga
        #   videos      los reels, que reproduce con un <video>
        # El resto (spec.json, HTML intermedio, PNG de rótulos) es material de
        # trabajo y no se sube.
        archivos, docs, videos, copy, notas = [], [], [], "", ""
        revisadas: list[str] = []
        for a in sorted(salida.iterdir()):
            if not a.is_file():
                continue
            if a.name == "copy.txt":
                copy = a.read_text(encoding="utf-8", errors="replace")
                continue
            if a.name == "notas.txt":
                notas = a.read_text(encoding="utf-8", errors="replace")
                continue
            ext = a.suffix.lower()
            if ext in IMAGENES:
                # Se la mira antes de subirla. La medida no se compara contra
                # nada: un diseño sale en 1080×1350, 1080×1920 o 1080×1080
                # según lo que se pidió, y acá no hay una medida esperada. Lo
                # que sí se puede medir es que no sea un rectángulo vacío —una
                # plantilla que no cargó, una foto que no llegó—, porque ese
                # archivo existe, pesa poco y nadie lo mira hasta que está
                # publicado.
                revisadas.extend(f"{a.name}: {x}" for x in revisar_imagen(a))
                archivos.append(cli.subir(a, f"{pid}/{a.name}"))
            elif ext in DOCUMENTOS:
                docs.append({"nombre": a.name,
                             "url": cli.subir(a, f"{pid}/{a.name}"),
                             "peso": a.stat().st_size})
            elif ext in VIDEOS:
                videos.append({"nombre": a.name,
                               "url": cli.subir(a, f"{pid}/{a.name}"),
                               "peso": a.stat().st_size,
                               "duracion": _duracion(a)})

        # Última red antes de guardar. El diseñador tiene que escribir el copy
        # y las notas en archivos separados, pero si alguna vez vuelve a
        # mezclarlos, lo que se publica no puede arrastrar las notas: el 9/8/2026
        # salieron públicas en el Instagram del club.
        copy, colados = _separar_notas(copy)
        if colados and not notas:
            notas = colados
        elif colados:
            notas = f"{notas.rstrip()}\n\n{colados}"

        # Lo que se vio en las placas viaja con las notas, que es lo que el
        # agente le lee a la persona. No frena la entrega: la pieza sale
        # igual y el aviso va con ella.
        if revisadas:
            visto = en_una_linea(revisadas)
            notas = f"{notas.rstrip()}\n\n{visto}" if notas else visto

        # ── El spec se GUARDA ────────────────────────────────────────
        #
        # Sin esto, corregir una pieza es imposible. El 5/9/2026 salió una story
        # que estaba bien y se pidió un solo cambio —«que la jirafa arranque
        # desde abajo sin espacio»—: volvió OTRA pieza, con otro fondo, otra
        # tipografía y otro centrado. No fue desobediencia: el spec vivía en un
        # directorio temporal y moría con el contenedor, así que no había nada
        # que corregir y el pedido se rehizo entero desde el mensaje.
        #
        # Es exactamente el problema que ya estaba resuelto para los reels
        # —`ver_reel` + `retocar_reel` sobre el guion guardado— y que para los
        # diseños no existía. El spec pesa unos pocos KB y es lo único que hace
        # falta para que una corrección sea una corrección.
        spec = None
        archivo_spec = salida / "spec.json"
        if archivo_spec.exists():
            try:
                spec = json.loads(archivo_spec.read_text(encoding="utf-8"))
            except Exception:
                log.warning("[%s] diseño %s: spec.json ilegible, no lo guardo",
                            cli.marca, pid)

        cli.marcar(pid, "listo", titulo=titulo, urls=archivos,
                   documentos=docs, videos=videos, copy=copy, notas=notas,
                   metricas=metricas, **({"spec": spec} if spec else {}))
        log.info("[%s] diseño %s listo — %d imágenes, %d documentos, %d videos",
                 cli.marca, pid, len(archivos), len(docs), len(videos))

        # El cobro va DESPUÉS de entregar. Si registrarlo falla, el cliente ya
        # tiene su pieza: preferimos perder el cobro de un diseño antes que
        # perder el diseño. Queda en el log para corregirlo a mano.
        cobro.registrar(cli, pid, (metricas or {}).get("costo_usd", 0.0),
                        detalle=" · ".join(pedido.get("formatos") or []))

    except Exception as e:
        log.exception("[%s] falló el diseño %s", cli.marca, pid)
        cli.marcar(pid, "error", mensaje_agente=str(e)[:500])
    finally:
        shutil.rmtree(salida, ignore_errors=True)


async def atender(cli: Cliente) -> int:
    pendientes = cli.leer_pedidos(config.MAX_POR_CICLO)
    if not pendientes:
        return 0
    log.info("[%s] %d diseños pendientes", cli.marca, len(pendientes))

    # El saldo se mira ANTES de bajar adjuntos y de arrancar el agente: es lo
    # único que evita gastar plata que el cliente no tiene. Y se mira una vez
    # por corrida, no una por pieza — si el saldo alcanza para empezar, las
    # piezas de esta tanda salen y el corte llega en la siguiente.
    ok, aviso = cobro.puede_generar(cli)
    if not ok:
        log.warning("[%s] sin saldo: %d pedidos quedan pendientes",
                    cli.marca, len(pendientes))
        for p in pendientes:
            # `pendiente` no: quedaría reintentándose cada minuto para siempre.
            # Se marca como error CON el motivo, y el chat lo muestra.
            cli.marcar(p["id"], "error", mensaje_agente=aviso)
        return 0

    # El banco del cliente entra al skill ANTES de diseñar, y sólo si hay algo
    # que diseñar: baja archivos al disco y no tiene sentido pagarlo en las
    # corridas vacías, que son la mayoría. Si falla, se sigue: el banco que
    # viene en el skill alcanza para trabajar.
    try:
        banco.sincronizar(cli, cli.marca)
    except Exception:
        log.exception("[%s] no pude sincronizar el banco de fotos", cli.marca)

    # Las plantillas publicadas entran al skill acá, por lo mismo: sólo si hay
    # algo que diseñar. Si falla, se sigue con las que vinieron en el
    # despliegue — que es exactamente lo que había antes de que esto existiera.
    try:
        plantillas.sincronizar(cli, cli.marca)
    except Exception:
        log.exception("[%s] no pude sincronizar las plantillas", cli.marca)

    for pedido in pendientes:
        await procesar(cli, pedido)
    return len(pendientes)


async def ciclo():
    inicio = datetime.now(timezone.utc)
    # El manual se lee una vez por corrida y por marca. Se olvida acá y no al
    # final para que una corrida que se muere a mitad de camino no deje el
    # texto viejo cacheado para la siguiente.
    manual.limpiar()
    plantillas.limpiar()
    hechos = subidos = plantillas_nuevas = propuestas = reels = fotos = 0
    for datos in config.clientes():
        # Sólo lo que `Cliente` entiende. El registro trae además la clave de
        # Asistime, que la lee `manual.py` por su cuenta.
        cli = Cliente(marca=datos["marca"], url=datos["url"], key=datos["key"],
                      bucket=datos.get("bucket", "disenos"),
                      nombre=datos.get("nombre", ""))
        if not cli.configurado:
            log.warning("[%s] sin URL o sin clave: lo salteo", cli.marca)
            continue
        # Un cliente puede estar en el registro antes de que su marca esté en
        # la imagen —el registro se actualiza en un minuto, la imagen en un
        # despliegue—. Se saltea con aviso y no rompe la corrida de los demás:
        # ese es todo el sentido de que el registro sea aparte.
        if not (config.RAIZ / ".claude/skills" / cli.marca / "marca.py").exists():
            log.warning("[%s] está en el registro pero su carpeta de marca no "
                        "está en esta imagen: lo salteo hasta el próximo "
                        "despliegue", cli.marca)
            continue
        try:
            hechos += await atender(cli)
        except Exception:
            # Un cliente caído no puede frenar a los demás.
            log.exception("[%s] no pude atenderlo en esta corrida", cli.marca)

        # Publicar va DESPUÉS de diseñar y en su propio try. Son dos trabajos
        # distintos que comparten la corrida: que Instagram esté caído no
        # puede impedir que se generen los diseños del día, y una pieza que
        # falló al generarse no tiene por qué frenar la publicación de otra
        # que ya estaba programada desde ayer.
        # Los pedidos de plantilla van en su propio try y DESPUÉS de las
        # piezas. Son dos trabajos que comparten la corrida: armar una
        # plantilla lleva minutos, y no puede retrasar las piezas del día —
        # que es lo que el club está esperando ahora.
        try:
            plantillas_nuevas += await plantillero.atender_todos(cli)
        except Exception:
            log.exception("[%s] falló la cola de plantillas", cli.marca)

        # Los reels van en su propio try y NO son un diseño más, aunque se
        # pidan por el mismo chat. Un diseño se hace entero adentro de una
        # corrida; un reel tarda unos cuatro minutos y este proceso vive uno,
        # así que la fila cruza cuatro o cinco corridas y en cada una avanza un
        # paso. Por eso acá no se espera nada: se mueve lo que se pueda mover y
        # el ciclo termina.
        #
        # `to_thread` no es adorno: el rótulo se dibuja con la API sync de
        # Playwright, que se niega a correr adentro de un loop de asyncio, y
        # este ciclo es async. Sin esto revienta recién con el primer reel de
        # verdad — cuando el video ya está generado y pagado.
        try:
            reels += await asyncio.to_thread(reelero.atender, cli)
        except Exception:
            log.exception("[%s] falló la cola de reels", cli.marca)

        # Las ediciones de foto van antes que los reels a propósito: cuestan
        # centavos, tardan segundos y hay alguien esperándolas en un chat.
        # Los reels cuestan créditos de verdad y tardan minutos: que una
        # corrida se vaya en un reel no puede dejar sin atender un «sacale el
        # fondo a esta foto» que se resuelve en cinco segundos.
        try:
            fotos += await asyncio.to_thread(fotero.atender, cli)
        except Exception:
            log.exception("[%s] falló la cola de fotos", cli.marca)

        # Los pedidos de motor van al final y apagados por defecto
        # (MOTORISTA=1 los prende). Lo que dejan es una PROPUESTA para que
        # alguien mire: no despliegan nada. Van últimos porque son lo menos
        # urgente de la corrida — nadie está esperando en un chat.
        try:
            propuestas += await motorista.atender_todos(cli)
        except Exception:
            log.exception("[%s] falló la cola de motor", cli.marca)

        if config.PUBLICAR:
            try:
                subidos += publicador.atender(cli)
            except Exception:
                log.exception("[%s] falló la cola de publicación", cli.marca)

    if not (hechos or subidos or plantillas_nuevas or propuestas or reels
            or fotos):
        log.info("sin diseños pendientes, plantillas, reels, fotos ni "
                 "publicaciones en cola")
        return
    dur = (datetime.now(timezone.utc) - inicio).total_seconds()
    log.info("ciclo terminado en %.0fs · %d diseños · %d plantillas · "
             "%d publicaciones · %d propuestas de motor · %d pasos de reel · "
             "%d fotos", dur, hechos, plantillas_nuevas, subidos, propuestas,
             reels, fotos)


async def main():
    config.SALIDA.mkdir(parents=True, exist_ok=True)
    lista = config.clientes()
    listos = [c for c in lista if c["url"] and c["key"]]
    if not listos:
        log.error("ningún cliente configurado: revisá CLIENTES_REGISTRO, "
                  "CLIENTES, o SUPABASE_URL y SUPABASE_KEY")
        sys.exit(1)

    for c in lista:
        if c not in listos:
            log.warning("cliente %s incompleto: le falta URL o clave", c["marca"])
    log.info("worker arriba · %d cliente(s): %s",
             len(listos), ", ".join(c["marca"] for c in listos))
    await ciclo()


if __name__ == "__main__":
    asyncio.run(main())
