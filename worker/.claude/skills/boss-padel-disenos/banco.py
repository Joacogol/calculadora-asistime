# -*- coding: utf-8 -*-
"""Lanzador: guarda en el banco lo que descubriste de una foto.

    python3 banco.py foco   <clave> <formato> "X% Y%" [--quien '{...}']
    python3 banco.py anotar <clave> [--quien '{...}'] [--descripcion "..."]
                                    [--etiquetas "cancha,clase"]
    python3 banco.py ver    [clave]

── Para qué ───────────────────────────────────────────────────────────────

Cuando usás una foto que subió el cliente, el encuadre que trae es provisorio
—dice `foco_confirmado: false`— así que generás la pieza, la mirás, y si la
cara quedó cortada o chocando con el titular, la corregís. Ese trabajo hoy se
tira al terminar el pedido: la próxima pieza con esa misma foto vuelve a
arrancar de cero y a cortar la misma cara.

Con esto, lo guardás una vez y queda resuelto para siempre:

    python3 banco.py foco jugadora-saque post "50% 22%"

Lo mismo con `quien`: la persona que sube una foto desde el celular no va a
describir quién aparece, pero vos ya tenés la imagen abierta cuando la usás.
Anotarlo es lo que permite que después alguien pida «que sea con jugadoras» y
esa foto aparezca.

    python3 banco.py anotar jugadora-saque \\
        --quien '{"genero":"femenino","cantidad":"una persona","edad":"adulto",
                  "apariencia":"pelo oscuro atado; remera negra"}'

No hace falta correrlo para las fotos que vienen en el skill: ésas ya tienen
el `foco` resuelto y no están en la tabla.
"""
import json
import pathlib
import sys

AQUI = pathlib.Path(__file__).resolve().parent
# .../worker/.claude/skills/<marca> → .../worker
RAIZ = AQUI.parents[2]
MARCA = AQUI.name
sys.path.insert(0, str(RAIZ))

from app import banco, config          # noqa: E402
from app.supa import Cliente           # noqa: E402

FORMATOS = ("post", "vert", "story", "reel")


def cliente():
    """La base de esta marca. Las claves salen del entorno del worker."""
    for datos in config.clientes():
        if datos["marca"] == MARCA:
            c = Cliente(**datos)
            if not c.configurado:
                break
            return c
    print(f"⚠ no encuentro configurada la base de «{MARCA}». "
          f"El foco no se guarda, pero la pieza se genera igual.")
    return None


def cmd_foco(args):
    """Guarda el encuadre y, de paso, lo que hayas averiguado de la foto.

    Acepta los mismos `--quien` / `--descripcion` / `--etiquetas` que `anotar`
    a propósito: cada comando que corre el agente es un turno, y un turno
    cuesta releer la conversación entera. Guardar el foco y anotar quién
    aparece son dos cosas que se descubren en el MISMO momento —mirando la
    pieza— así que separarlas en dos comandos era pagar dos veces por una.
    """
    if len(args) < 3:
        print("uso: python3 banco.py foco <clave> <formato> \"X% Y%\" "
              "[--quien '{...}'] [--descripcion \"...\"]")
        return 1
    clave, formato, valor = args[0], args[1], args[2]
    extra = args[3:]
    # Las banderas se validan ANTES de tocar nada: si el `--quien` viene con
    # un JSON roto, el agente tiene que enterarse en este turno y no descubrir
    # después que el foco se guardó y la anotación no.
    if extra and _banderas(extra) is None:
        return 1
    if formato not in FORMATOS:
        print(f"⚠ formato «{formato}»: tiene que ser uno de {', '.join(FORMATOS)}")
        return 1
    if "%" not in valor:
        print(f"⚠ «{valor}» no parece un object-position. Va como \"50% 30%\".")
        return 1

    # Primero el JSON: es lo que lee el agente en el resto de ESTE pedido.
    # Si sólo escribiéramos la base, la pieza en curso seguiría con el foco
    # viejo y habría que acordarse de editar el spec a mano.
    banco.aplicar_foco_local(MARCA, clave, formato, valor)

    cli = cliente()
    if cli is None:
        return 0
    if cli.guardar_foco(clave, {formato: valor}):
        print(f"✓ guardado: {clave} · {formato} → {valor}")
    else:
        print(f"⚠ «{clave}» no está en el banco del cliente "
              f"(¿es una foto del skill? ésas ya tienen el foco resuelto)")
    if extra:
        return cmd_anotar([clave] + extra)
    return 0


def _banderas(args):
    """Traduce `--quien '{...}' --descripcion "..."` a un dict. None si algo falla."""
    campos, i = {}, 0
    while i < len(args) - 1:
        bandera, valor = args[i], args[i + 1]
        if bandera == "--quien":
            try:
                campos["quien"] = json.loads(valor)
            except json.JSONDecodeError as e:
                print(f"⚠ --quien tiene que ser JSON válido: {e}")
                return None
        elif bandera == "--descripcion":
            campos["descripcion"] = valor
        elif bandera == "--etiquetas":
            campos["etiquetas"] = [x.strip() for x in valor.split(",") if x.strip()]
        else:
            print(f"⚠ no conozco «{bandera}»")
            return None
        i += 2
    return campos


def cmd_anotar(args):
    if not args:
        print("uso: python3 banco.py anotar <clave> [--quien '{...}'] ...")
        return 1
    clave = args[0]
    campos = _banderas(args[1:])
    if campos is None:
        return 1
    cli = cliente()
    if cli is None:
        return 0
    if cli.anotar_foto(clave, **campos):
        print(f"✓ anotada «{clave}»: {', '.join(campos)}")
    else:
        print(f"⚠ no pude anotar «{clave}» (¿está en el banco del cliente?)")
    return 0


def cmd_ver(args):
    ruta = AQUI / "referencias/fotos.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if args:
        print(json.dumps(datos.get(args[0], {}), ensure_ascii=False, indent=2))
        return 0
    for clave, v in datos.items():
        if not isinstance(v, dict):
            continue
        marca_ = "banco" if v.get("origen") else "skill"
        pendiente = "" if v.get("foco_confirmado", True) else "  ← foco sin confirmar"
        print(f"{clave:28} [{marca_}] {v.get('descripcion','')[:60]}{pendiente}")
    return 0


COMANDOS = {"foco": cmd_foco, "anotar": cmd_anotar, "ver": cmd_ver}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMANDOS:
        print(__doc__)
        raise SystemExit(1)
    raise SystemExit(COMANDOS[sys.argv[1]](sys.argv[2:]))
