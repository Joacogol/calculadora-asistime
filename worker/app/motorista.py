# -*- coding: utf-8 -*-
"""Atiende un pedido que necesita tocar el motor. Deja una PROPUESTA.

Hermano del plantillero, y a propósito con la misma forma: un agente con el
repo delante, que cambia, dibuja y mira. Lo que cambia es dónde termina.

## Qué deja, y qué NO deja

Deja un **parche** —el diff, sin aplicar—, la prueba de que no rompió nada, y
las imágenes de lo que sí cambió. No despliega, no hace commit, no toca la
base más allá de su propia fila. El contenedor se recicla y no queda nada.

Aplicarlo y desplegarlo lo decide una persona, mirando.

## Por qué no lo aplica solo

Por proporción, no por timidez. Una plantilla mala rompe una plantilla y se
vuelve atrás publicando la versión anterior: el daño es de una pieza y la
marcha atrás existe. Un cambio de motor malo rompe las catorce plantillas y las
piezas de TODOS los clientes al mismo tiempo, y la marcha atrás es volver a
desplegar.

Esa asimetría es la que decide dónde va la persona. Y no es para siempre: el
día que haya cien propuestas aprobadas sin una sola sorpresa, la regla de abajo
alcanza para aprobar sola las que no mueven nada.

## La regla que lo hace revisable

`verificar-motor.py` dibuja las 48 piezas antes y después. Un cambio que las
deja **idénticas** sólo agregó algo: es aditivo y no puede haber roto nada que
ya andaba. Uno que mueve aunque sea un píxel de una plantilla que nadie pidió
tocar es un problema, aunque el píxel se vea mejor.

Eso no es la opinión de un agente sobre su propio trabajo: es una comparación
mecánica que no se puede convencer. Por eso el prompt se lo pide antes y
después, y por eso la evidencia va a la base junto con el parche.
"""
import asyncio
import json
import logging
import os
import time
from pathlib import Path

import requests
from claude_agent_sdk import ClaudeAgentOptions, query

from . import config
from .disenador import _metricas, _texto

log = logging.getLogger(__name__)

#: Tocar el motor es lo más delicado que hace este sistema. Acá no se ahorra.
MODELO = os.environ.get("MODELO_MOTORISTA", "claude-opus-5")

#: Apagado por defecto, y a propósito. Cada pedido atendido es una corrida del
#: agente de varios minutos que cuesta plata, y a diferencia de una plantilla
#: —que alguien pidió y está esperando— una propuesta de motor puede quedar sin
#: mirar. Se prende cuando hay alguien del otro lado.
ACTIVO = os.environ.get("MOTORISTA", "0") == "1"


PROMPT = """Atendé un pedido que necesita tocar el motor de diseño.

## Lo que piden

{resumen}

**Parte del motor:** {parte}

## Antes de tocar nada

Corré esto y esperá a que termine (tarda un minuto):

```
python3 herramientas/verificar-motor.py {marca} --grabar
```

Dibuja las 48 piezas que el motor sabe hacer hoy y guarda la huella de cada
una. Es contra eso que se va a medir lo que hagas.

## La regla

Cuando termines, corré:

```
python3 herramientas/verificar-motor.py {marca} --comparar
```

**Lo que tiene que dar es `48 / 48 idénticas`.** Eso quiere decir que tu cambio
agregó algo sin mover nada de lo que ya andaba, y es la única forma de que
alguien pueda aprobarlo sin revisar las catorce plantillas a mano.

Si algo salió `DISTINTA`, tenés dos opciones y ninguna es seguir de largo:

1. **No era intencional** — arreglalo. Casi siempre es que tocaste algo
   compartido cuando alcanzaba con agregar al lado.
2. **Era inevitable** — porque lo que piden es justamente que algo se vea
   distinto. Entonces decilo con todas las letras: qué se movió, por qué no se
   podía evitar, y por qué el resultado es mejor. Y abrí los PNG de
   `/tmp/verificar-motor/antes/` y `/despues/` para poder contarlo mirando.

Lo que NO se hace es dejar una plantilla movida sin explicación. Del otro lado
hay alguien que va a aprobar esto, y lo único que tiene para decidir es lo que
vos le cuentes.

## Dónde estás

El repo del worker, entero. Lo que se toca para un pedido así suele ser:

- `motor/` — el render, los efectos, la legibilidad. Es COMPARTIDO entre
  marcas: lo que cambies acá le pasa a todos los clientes.
- `.claude/skills/{marca}/marca.json` (bloque `identidad`), `estilo.css` y
  `plantillas/` — lo propio de esta marca. Es DATOS, no código: una marca
  nueva no lleva Python. Los ayudantes de dibujo están en `motor/componentes.py`.
- `motor/plantillas.py` — el contrato de las plantillas-dato. Cambiarlo puede
  obligar a tocar las 12.

**Preferí agregar a modificar.** Un helper nuevo que nadie usa todavía no puede
romper nada; cambiar uno que usan ocho plantillas, sí.

## Qué NO hacés

- **No despliegues, no hagas commit, no toques git.** Lo que dejás es el
  archivo cambiado; el diff lo saca el worker solo.
- **No toques las plantillas de `plantillas/`** salvo que el pedido lo exija.
  Una plantilla se corrige sola por otro camino, más barato y sin desplegar.
- **No borres ni renombres** nada que ya existe. Si algo tiene que dejar de
  usarse, decilo y que lo decida una persona.

## Al terminar

Contá, en este orden:

1. **Qué cambiaste**, archivo por archivo, en una línea cada uno.
2. **Qué dio la verificación.** El número, tal cual.
3. **Qué NO pudiste hacer**, si algo quedó afuera. Es más útil que hacerlo mal.
4. **Qué hay que mirar** cuando esto se despliegue: dónde se va a notar.

Escribilo para alguien que no vio el pedido y tiene que decidir si esto sale.
"""


def _pendientes(cli, limite: int = 1) -> list[dict]:
    """Los pedidos de motor sin atender. De a uno por corrida.

    Uno y no dos, al revés que las plantillas: una propuesta de motor que nadie
    mira es plata quemada, y es más probable que se acumulen sin mirar que las
    plantillas —que alguien pidió y está esperando.
    """
    r = requests.get(
        cli._url("motor_pedidos"), headers=cli._cab(), timeout=30,
        params={"estado": "eq.anotado", "order": "creado_en.asc",
                "limit": str(limite),
                "select": "id,resumen,parte,quien,creado_en"})
    if r.status_code in (400, 404):
        return []           # esta base todavía no tiene la tabla
    r.raise_for_status()
    return r.json()


def _tomar(cli, pedido_id: str) -> bool:
    """Mismo candado que las otras colas: la condición y la escritura juntas."""
    r = requests.patch(
        cli._url("motor_pedidos"),
        headers=cli._cab({"Prefer": "return=representation"}),
        params={"id": f"eq.{pedido_id}", "estado": "eq.anotado"},
        data=json.dumps({"estado": "generando"}), timeout=30)
    r.raise_for_status()
    return bool(r.json())


def _marcar(cli, pedido_id: str, estado: str, **campos):
    requests.patch(
        cli._url("motor_pedidos"), headers=cli._cab(),
        params={"id": f"eq.{pedido_id}"},
        data=json.dumps({"estado": estado, **campos}), timeout=30
    ).raise_for_status()
    log.info("[%s] pedido de motor %s -> %s", cli.marca, pedido_id, estado)


#: Qué archivos se miran para sacar el parche. Código y contratos; ni las
#: fotos, ni las tipografías, ni los PNG que deja la verificación.
MIRAR = (".py", ".json", ".html", ".css", ".md", ".ts", ".sql", ".sh", ".txt")

#: Y qué carpetas no se miran nunca.
IGNORAR = ("__pycache__", ".git", "assets", "fonts", "node_modules", "_borrador")


def _archivos() -> dict[str, str]:
    """El código del worker, tal como está ahora. {ruta relativa: contenido}.

    NO usa git, y es a propósito: el contenedor desplegado no es un repo —el
    Dockerfile copia el código, no el `.git`—, así que `git diff` ahí devuelve
    vacío siempre. Un parche que sale vacío en producción y anda en la máquina
    del que lo escribió es la peor clase de bug: parece que funciona.
    """
    raiz = Path(config.RAIZ)
    salida = {}
    for f in raiz.rglob("*"):
        if not f.is_file() or f.suffix not in MIRAR:
            continue
        if any(parte in IGNORAR for parte in f.parts):
            continue
        try:
            salida[str(f.relative_to(raiz))] = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
    return salida


def _parche(antes: dict[str, str], despues: dict[str, str]
            ) -> tuple[str, list[str]]:
    """El diff entre dos fotos del código, y qué archivos cambiaron.

    Se saca comparando y no pidiéndoselo al agente por una razón: el agente
    cuenta lo que cree que hizo, y esto cuenta lo que hizo. Cuando no coinciden,
    lo que importa es lo segundo.
    """
    import difflib
    trozos, tocados = [], []
    for ruta in sorted(set(antes) | set(despues)):
        a = antes.get(ruta, "").splitlines(keepends=True)
        b = despues.get(ruta, "").splitlines(keepends=True)
        if a == b:
            continue
        tocados.append(ruta)
        trozos.extend(difflib.unified_diff(
            a, b, f"a/{ruta}", f"b/{ruta}",
            "" if ruta in antes else "(nuevo)",
            "" if ruta in despues else "(borrado)"))
    return "".join(trozos), tocados


def _restaurar(antes: dict[str, str]) -> None:
    """Deja el código como estaba antes de la corrida.

    El contenedor se recicla igual, pero una corrida que arranca de lo que dejó
    la anterior mide contra la base equivocada — y eso no se ve, se hereda.
    """
    raiz = Path(config.RAIZ)
    for ruta, texto in antes.items():
        f = raiz / ruta
        try:
            if not f.exists() or f.read_text(encoding="utf-8") != texto:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(texto, encoding="utf-8")
        except OSError as e:
            log.warning("no pude restaurar %s: %s", ruta, e)
    # Y lo que el agente creó de cero se va: no formaba parte del worker.
    for f in raiz.rglob("*"):
        if (f.is_file() and f.suffix in MIRAR
                and not any(p in IGNORAR for p in f.parts)
                and str(f.relative_to(raiz)) not in antes):
            f.unlink(missing_ok=True)


def _evidencia(marca: str) -> dict:
    """Qué dio la verificación, leído del disco y no del relato del agente."""
    huella = Path("/tmp/huella-motor.json")
    antes = Path("/tmp/verificar-motor/antes")
    despues = Path("/tmp/verificar-motor/despues")
    if not (huella.exists() and despues.is_dir()):
        return {"corrio": False,
                "por_que": "el agente no corrió la verificación"}

    previa = json.loads(huella.read_text(encoding="utf-8"))
    import hashlib
    ahora = {p.name: hashlib.md5(p.read_bytes()).hexdigest()
             for p in sorted(despues.glob("*.png"))}
    movidas = sorted(n for n in set(previa) & set(ahora) if previa[n] != ahora[n])
    faltan = sorted(set(previa) - set(ahora))
    return {
        "corrio": True,
        "total": len(previa),
        "identicas": len(previa) - len(movidas) - len(faltan),
        "movidas": movidas,
        "faltan": faltan,
        "aditivo": not (movidas or faltan),
        "carpetas": {"antes": str(antes), "despues": str(despues)},
    }


def _subir_movidas(cli, pid: str, evidencia: dict) -> dict:
    """Sube el antes y el después de lo que se movió, para poder mirarlo.

    Sólo lo que cambió. Subir las 48 idénticas sería ruido: lo que hay que
    decidir es si el cambio que se ve está bien, no si las otras siguen igual
    —eso ya lo dice el número.
    """
    if not evidencia.get("corrio") or evidencia.get("aditivo"):
        return evidencia
    urls = {"antes": [], "despues": []}
    for cual in ("antes", "despues"):
        base = Path(evidencia["carpetas"][cual])
        for nombre in evidencia["movidas"][:12]:
            png = base / nombre
            if not png.exists():
                continue
            try:
                urls[cual].append(
                    cli.subir(png, f"motor/{pid}/{cual}-{nombre}"))
            except Exception as e:
                log.warning("[%s] no pude subir %s/%s: %s",
                            cli.marca, cual, nombre, e)
    evidencia["imagenes"] = urls
    return evidencia


async def _correr(prompt: str) -> tuple[str, dict]:
    """Una pasada del agente. Devuelve (último texto, métricas).

    Sin `Skill` y sin la marca cargada: lo que toca acá es código del motor, no
    el idioma de una marca. Lo que necesite lo abre con Read.
    """
    opciones = ClaudeAgentOptions(
        cwd=str(config.RAIZ),
        model=MODELO,
        setting_sources=["project"],
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        permission_mode="dontAsk",
        max_turns=80,
        # Igual que en `disenador._correr`: un `Read` de un PNG grande
        # pasa el tope de 1 MB por mensaje del SDK y corta la corrida.
        max_buffer_size=32 * 1024 * 1024,
    )
    ultimo, resultado = "", None
    async for m in query(prompt=prompt, options=opciones):
        t = _texto(m)
        if t:
            ultimo = t
            log.info("motorista: %s", t[:300])
        if type(m).__name__ == "ResultMessage":
            resultado = m
    return ultimo, (_metricas(resultado, MODELO) or {})


async def atender(cli, pedido: dict) -> bool:
    """Atiende un pedido de motor y deja la propuesta. No aplica nada."""
    pid = pedido["id"]
    if not _tomar(cli, pid):
        return False        # otra corrida lo agarró primero
    arranque = time.time()
    log.info("[%s] atiendo un pedido de motor: %s", cli.marca,
             pedido["resumen"][:120])

    antes = _archivos()
    try:
        prompt = PROMPT.format(
            resumen=pedido["resumen"],
            parte=pedido.get("parte") or "no lo dijeron",
            marca=cli.marca)
        ultimo, met = await _correr(prompt)

        parche, tocados = _parche(antes, _archivos())
        evidencia = _subir_movidas(cli, pid, _evidencia(cli.marca))
        met["segundos_totales"] = round(time.time() - arranque)
        met["archivos_tocados"] = tocados

        if not parche.strip():
            # No dejó nada. Eso puede ser correcto —«esto no se resuelve en el
            # motor»— y hay que poder distinguirlo de una corrida fallida.
            _marcar(cli, pid, "propuesto", notas=(ultimo or "")[:8000],
                    evidencia=evidencia, metricas=met)
            log.info("[%s] el motorista no cambió nada; su explicación queda "
                     "en el pedido", cli.marca)
            return True

        _marcar(cli, pid, "propuesto", parche=parche[:200000],
                evidencia=evidencia, notas=(ultimo or "")[:8000], metricas=met)
        log.info("[%s] propuesta lista en %ds · %d archivo(s) · %s",
                 cli.marca, met["segundos_totales"], len(tocados),
                 "aditiva" if evidencia.get("aditivo") else
                 f"mueve {len(evidencia.get('movidas', []))}")
        return True

    except Exception as e:
        log.exception("[%s] no pude atender el pedido de motor %s",
                      cli.marca, pid)
        _marcar(cli, pid, "error", notas=str(e)[:900])
        return False
    finally:
        _restaurar(antes)


async def atender_todos(cli) -> int:
    """Los pedidos de motor de esta corrida. Devuelve cuántos se atendieron."""
    if not ACTIVO:
        return 0
    hechos = 0
    for pedido in _pendientes(cli):
        if await atender(cli, pedido):
            hechos += 1
    return hechos
