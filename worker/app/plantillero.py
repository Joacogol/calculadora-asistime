# -*- coding: utf-8 -*-
"""Escribe una plantilla nueva a partir de un pedido en castellano.

Hermano de `disenador.py`, y a propósito con la misma forma: un agente con el
skill de la marca delante, el sistema de archivos, y **la posibilidad de mirar
lo que dibujó**.

## Por qué acá y no en un agente de Asistime

Se pensó en serio dejarlo en Asistime: el cerebro versionado, entrenable desde
la plataforma. No sirve por una sola razón, y es la misma que hace bueno al
diseñador de piezas: **el que escribe una plantilla tiene que poder ver el
resultado.** Un agente de Asistime recibe una URL y no puede abrirla — no se
entera de que el titular desbordó, de que el acento no contrasta con la foto,
ni de que el pie quedó pisado. Ninguna de esas tres cosas se ve leyendo el
código.

Acá el agente escribe, corre `previsualizar-borrador.py`, **abre el PNG con
Read**, y corrige. Ese bucle es todo el valor.

## Lo que deja, y lo que NO deja

Deja una versión **sin publicar** en la tabla `plantillas`, más sus previews
subidos. No la pone en uso: eso cambia todas las piezas que se hagan de ahí en
adelante y lo decide una persona, después de mirar.

Y no deja nada en el disco. El borrador vive en `plantillas/_borrador/`, que el
motor no carga —la regla del guión bajo—, y se borra al terminar. El disco del
contenedor se pierde en el despliegue siguiente: lo que vale queda en la base.
"""
import importlib
import json
import os
import logging
import re
import shutil
import time
from pathlib import Path

import requests
from claude_agent_sdk import ClaudeAgentOptions, query

from . import config
from .disenador import _metricas, _texto

log = logging.getLogger(__name__)

#: Una plantilla se escribe una vez y se usa cien: conviene el modelo bueno.
#: Va aparte de MODELO_COMPLEJO a propósito — que alguien baje el modelo de las
#: piezas para ahorrar no tiene por qué bajar el de las plantillas.
#:
#: Se corrió la MISMA plantilla con los dos, cambiando sólo esto. Sonnet costó
#: un tercio y sacó una pieza correcta, pero donde el problema era difícil
#: —el nombre del día que no entra— lo aceptó como límite y lo anotó; Opus lo
#: resolvió calculando el cuerpo tipográfico según el ancho del texto, y dejó
#: dos campos opcionales como los deja el resto de la marca. Esa diferencia se
#: paga una vez y queda en las cien piezas siguientes.
MODELO = os.environ.get("MODELO_PLANTILLERO", "claude-opus-5")

#: Corregir es otro trabajo: la plantilla ya existe, el contrato ya está
#: decidido y el cambio es acotado. Ahí el modelo bueno no compra nada, así que
#: el default es el barato.
MODELO_CORRECCION = os.environ.get("MODELO_CORRECTOR", "claude-sonnet-5")

BORRADOR = "_borrador"

#: Cuántas plantillas del catálogo se le muestran como referencia. Con dos
#: alcanza para que agarre el idioma de la marca. Cada una que abre no se lee
#: una vez: se queda en el contexto y se relee en los cuarenta turnos que
#: siguen, así que la tercera cuesta bastante más de lo que enseña.
REFERENCIAS = 2


PROMPT = """Escribí una PLANTILLA nueva para {marca}.

Una plantilla no es una pieza: es el molde con el que después se hacen muchas
piezas parecidas. Se escribe una vez y se usa cien, así que vale la pena que
quede bien.

## El pedido

{pedido}

## El idioma de la marca

{vocabulario}

## Dónde estás

La marca vive en `{skill}`. Ahí adentro:

- `plantillas/` — las plantillas que ya existen. **Leé dos antes de escribir
  nada**: son el idioma de esta marca en uso, y lo que escribas tiene que sonar
  igual. Empezá por {referencias}. Con dos alcanza — cada una que abrís se
  queda en el contexto y se relee en todos los turnos que siguen.
- `assets/` y `fonts/` — las fotos y las tipografías. Se referencian con rutas
  relativas: `assets/loquesea.jpg`.
- `referencias/marca.md` — el manual técnico, si te falta algo puntual.

## Qué tenés que dejar

Dos archivos en `plantillas/{borrador}/`:

**`plantilla.html`** — el diseño. Es el cuerpo que va adentro de `.canvas`; no
escribas `<html>`, `<head>` ni la hoja de estilo: eso lo pone el motor.

Adentro tenés disponible:

| | |
|---|---|
| `{{{{ d.campo }}}}` | los datos de cada pieza, con los defaults ya aplicados |
| `{{{{ m.medida }}}}` | las medidas del formato que se está dibujando |
| `{{{{ c.lima }}}}` `{{{{ c.negro }}}}` … | los colores de la marca |
| `{{{{ ac }}}}` | el color de acento ya resuelto |
| `{{{{ fmt }}}}` | `post`, `vert`, `story` o `reel` |
| `{{{{ logo() }}}}` `{{{{ aros() }}}}` `{{{{ blob() }}}}` | los helpers gráficos |
| `{{{{ plan_titular(foto, ac, c.negro, [0.05, 0.45]) }}}}` | mide la foto y dice si el titular necesita bloque sólido |

Es Jinja: `{{% if d.foto %}}…{{% endif %}}`, `{{% for a, b in d.lista %}}…{{% endfor %}}`.

**`plantilla.json`** — el contrato:

```json
{{
  "id": "un-slug-corto",
  "nombre": "Nombre",
  "descripcion": "qué es, en media línea y en minúscula",
  "cuando_usarla": "cuándo va ésta y no otra. Nombrá la parecida.",
  "medidas": {{
    "post":  {{ "alto": 1080, "…": 0 }},
    "vert":  {{ "alto": 1350, "…": 0 }},
    "story": {{ "alto": 1920, "…": 0 }},
    "reel":  {{ "alto": 1920, "…": 0 }}
  }},
  "campos": [
    {{ "id": "titulo", "tipo": "texto", "etiqueta": "Título",
      "requerido": true, "ejemplo": "algo real, no «Lorem»" }},
    {{ "id": "foto", "tipo": "imagen", "etiqueta": "Foto", "default": "" }}
  ],
  "notas": "el oficio: qué mirar, qué no hacer, por qué es así"
}}
```

Tipos de campo: `texto`, `texto_largo`, `imagen`, `color`, `opcion` (con
`opciones`), `si_no`, `lista` (con `columnas`).

## Las reglas que no se negocian

1. **No inventes un color ni una tipografía.** Componé con `c.*` y con las
   clases que ya usan las otras plantillas (`disp`, `disp-b`, `kicker`,
   `eyebrow`, `body`). Eso es lo que la mantiene on-brand.
2. **Las medidas van por formato, no una sola.** Un cuerpo tipográfico que
   funciona en `post` se ve chico en `story`, que mide 1920 de alto. Mirá cómo
   lo resuelven las otras y hacé lo mismo.
3. **Un campo opcional desaparece entero, con su rótulo.** Si `precio` va
   vacío, no dejes un «$» colgando. `{{% if d.precio %}}…{{% endif %}}`.
4. **`ejemplo` con datos de verdad.** «JUEVES», «097 406 148», «Delfina
   Methol». Con «Lorem ipsum» no se ve si el diseño aguanta.
5. Si el pedido es **corregir una plantilla que ya existe**, usá su mismo `id`:
   queda como una versión nueva de ésa y no como una plantilla aparte.

## El bucle, que es lo que importa

Escribir el HTML es la parte fácil. Lo que hace buena a una plantilla es
mirarla:

```
python3 herramientas/previsualizar-borrador.py {nombre_marca} {borrador} post story
```

**Mientras iterás, dibujá sólo `post` y `story`.** Son los dos que revelan los
problemas: uno es el más apretado y el otro el más alto. `vert` y `reel` se
parecen a esos dos, y cada preview que abrís se queda en el contexto y se
relee en todos los turnos que siguen. Los cuatro, una sola vez, al final.

Deja los PNG **en la misma carpeta. Abrilos con Read.** Y mirá tres cosas:

- ¿el titular entra, o desborda y se corta?
- ¿el texto contrasta con lo que tiene atrás?
- ¿algo queda pisado, o pegado a un borde?

**Escribí el `ejemplo.json` de caso límite ANTES de la primera ronda**, no
después de descubrir que hace falta. Va en la carpeta del borrador y lleva los
datos que rompen: el nombre más largo que se te ocurra, el día con tres
palabras, la sede con nombre compuesto, la lista con ocho ítems. Si la
plantilla aguanta eso, aguanta lo normal — al revés no.

Con el caso límite puesto de entrada, **dos rondas alcanzan**: una para ver qué
se rompe y otra para verificar el arreglo. Si necesitás una tercera, que sea
porque encontraste algo, no porque no habías probado el borde.

## Al terminar

Contá en dos o tres líneas qué decidiste y por qué: qué plantilla tomaste de
referencia, qué campos pusiste requeridos y cuáles no, y qué mirar cuando se
use. Eso es lo que va a leer la persona que decide si la publica.

{manual}"""


def _vocabulario(carpeta: Path) -> str:
    """El idioma de la marca, en unos cientos de tokens en vez de veintitrés mil.

    Se genera del propio módulo de marca y no se escribe a mano, así que no
    puede quedar viejo: si mañana entra un color nuevo, aparece acá solo. Es lo
    que reemplaza a cargarle el SKILL.md entero — de cuyas 1.049 líneas al que
    escribe una plantilla le sirven unas quince.
    """
    import sys
    sys.path.insert(0, str(carpeta))
    sys.path.insert(0, str(config.RAIZ))
    marca = importlib.import_module("marca")

    colores = " · ".join(f"`c.{k}` {v}" for k, v in marca.C.items())
    formatos = " · ".join(f"`{k}` {w}×{h}" for k, (w, h) in marca.FORMATOS.items())
    # Las clases de texto que ya existen. Salen de la hoja base y no de una
    # lista escrita a mano por lo mismo: una clase nueva aparece sola.
    clases = sorted(set(re.findall(r"^\.([a-z][a-z-]*)\s*\{", marca.BASE_CSS,
                                   flags=re.M)))
    return (f"**Colores.** {colores}\n\n"
            f"**Formatos.** {formatos}\n\n"
            f"**Clases de texto que ya existen** (usá éstas, no inventes "
            f"tipografías): {', '.join('`' + c + '`' for c in clases)}")


PROMPT_CORRECCION = """Corregí la plantilla `{slug}` de {marca}.

## Lo que piden

{pedido}

## Lo que hay hoy

La plantilla está en `plantillas/{borrador}/` — su `plantilla.html` y su
`plantilla.json`, tal como se usan ahora. **Editala. No la reescribas.**

Es una corrección, no una plantilla nueva: mantené el `id`, los campos que ya
tiene y los nombres de todo. Alguien que la usa hoy no tiene por qué enterarse
de que la tocaste, salvo en lo que pidieron.

Sacá un campo sólo si el pedido lo dice con todas las letras. Un campo que
desaparece rompe las piezas que ya lo mandaban.

## El idioma de la marca

{vocabulario}

Adentro del HTML tenés `{{{{ d.campo }}}}`, `{{{{ m.medida }}}}`, `{{{{ c.lima }}}}`,
`{{{{ ac }}}}`, `{{{{ fmt }}}}`, y los helpers `{{{{ logo() }}}}` `{{{{ aros() }}}}`
`{{{{ blob() }}}}` `{{{{ plan_titular(...) }}}}`.

## Cómo verificás

```
python3 herramientas/previsualizar-borrador.py {nombre_marca} {borrador} post story
```

Abrí los PNG con Read. **Acá dibujás para verificar, no para descubrir**: la
plantilla ya funcionaba, así que una ronda alcanza si el cambio salió bien.
Mirá que lo que pidieron esté, y que no se haya roto nada de lo que ya andaba.

Si el cambio toca algo que depende del alto —un cuerpo tipográfico, un
margen— dibujá también `story`, que es donde se nota.

## Al terminar

Contá en dos líneas qué cambiaste y qué mirar. Si algo del pedido no lo
pudiste hacer sin romper otra cosa, decilo: es más útil que hacerlo igual.
"""


def _pendientes(cli, limite: int = 2) -> list[dict]:
    """Los pedidos de plantilla sin atender, del más viejo al más nuevo.

    De a dos por corrida y no más: cada uno es una corrida del agente de varios
    minutos, y el reloj vuelve a disparar dentro de uno.
    """
    r = requests.get(
        cli._url("plantilla_pedidos"), headers=cli._cab(), timeout=30,
        params={"estado": "eq.pendiente", "order": "creado_en.asc",
                "limit": str(limite),
                "select": "id,mensaje,quien,corrige,creado_en"})
    if r.status_code in (400, 404):
        return []           # esta base todavía no tiene la tabla
    r.raise_for_status()
    return r.json()


def _tomar(cli, pedido_id: str) -> bool:
    """Marca el pedido como «generando», pero sólo si sigue pendiente.

    El mismo candado que usa `disenos`: si dos corridas se superponen, la
    segunda no vuelve a armar la misma plantilla. El filtro por estado hace que
    la condición y la escritura pasen en la misma operación.
    """
    r = requests.patch(
        cli._url("plantilla_pedidos"),
        headers=cli._cab({"Prefer": "return=representation"}),
        params={"id": f"eq.{pedido_id}", "estado": "eq.pendiente"},
        data=json.dumps({"estado": "generando"}), timeout=30)
    r.raise_for_status()
    return bool(r.json())


def _marcar(cli, pedido_id: str, estado: str, **campos):
    r = requests.patch(
        cli._url("plantilla_pedidos"),
        headers=cli._cab({"Prefer": "return=minimal"}),
        params={"id": f"eq.{pedido_id}"},
        data=json.dumps({"estado": estado, **campos}), timeout=30)
    r.raise_for_status()
    log.info("[%s] plantilla %s -> %s", cli.marca, pedido_id, estado)


def _guardar(cli, slug: str, html: str, contrato: dict, etiqueta: str,
             quien: str) -> int:
    """Deja la plantilla como versión NO publicada. Devuelve el número."""
    r = requests.post(
        cli._url("rpc/guardar_plantilla"), headers=cli._cab(), timeout=30,
        json={"p_plantilla": slug, "p_html": html, "p_contrato": contrato,
              "p_etiqueta": etiqueta[:120], "p_quien": quien,
              "p_publicar": False})
    r.raise_for_status()
    return r.json()["version"]


def _bajar_publicada(cli, slug: str) -> tuple[str, dict] | None:
    """La versión EN USO de una plantilla, para editarla en vez de rehacerla.

    Busca en dos lados y en este orden, que es el mismo que usa el motor para
    decidir qué dibuja:

    1. la base, donde está la versión publicada;
    2. el disco, donde está la que trajo el despliegue.

    El segundo paso no es un plan B: es el caso normal de una plantilla que
    nadie tocó todavía. La base sólo tiene las que alguien publicó desde que
    existe la tabla; las otras once de Boss viven en el despliegue y son
    igual de reales. Sin este paso, pedir «a la de torneos hacele el título
    más grande» terminaría escribiendo una plantilla nueva parecida a torneo
    —que es exactamente lo que corregir vino a evitar— sólo porque todavía no
    la sembró nadie.
    """
    try:
        r = requests.get(
            cli._url("plantillas"), headers=cli._cab(), timeout=30,
            params={"plantilla": f"eq.{slug}", "publicada": "is.true",
                    "select": "html,contrato", "limit": "1"})
        if r.status_code == 200 and r.json():
            f = r.json()[0]
            return f["html"], f["contrato"]
    except requests.RequestException as e:
        # Que la base no conteste no tiene por qué impedir corregir: el disco
        # tiene una versión buena. Se anota y se sigue.
        log.warning("[%s] no pude consultar «%s» en la base (%s); voy al disco",
                    cli.marca, slug, e)

    d = _skill(cli.marca) / "plantillas" / slug
    j, h = d / "plantilla.json", d / "plantilla.html"
    if j.exists() and h.exists():
        log.info("[%s] «%s» no está en la base: la tomo del despliegue",
                 cli.marca, slug)
        return (h.read_text(encoding="utf-8"),
                json.loads(j.read_text(encoding="utf-8")))
    return None


def _skill(marca: str) -> Path:
    return config.RAIZ / ".claude" / "skills" / marca


def _referencias(carpeta: Path) -> list[str]:
    """Las plantillas más chicas del catálogo, que son las más fáciles de leer."""
    con_tamano = []
    for d in sorted((carpeta / "plantillas").iterdir()):
        html = d / "plantilla.html"
        if d.is_dir() and not d.name.startswith("_") and html.exists():
            con_tamano.append((html.stat().st_size, d.name))
    return [n for _, n in sorted(con_tamano)[:REFERENCIAS]]


_SLUG = re.compile(r"^[a-z][a-z0-9_-]{1,30}$")


def _leer_borrador(carpeta: Path) -> tuple[str, dict]:
    """Lo que dejó el agente, validado antes de tocar la base."""
    d = carpeta / "plantillas" / BORRADOR
    faltan = [f for f in ("plantilla.html", "plantilla.json")
              if not (d / f).exists()]
    if faltan:
        raise ValueError(
            f"el borrador quedó incompleto: falta {', '.join(faltan)}")

    html = (d / "plantilla.html").read_text(encoding="utf-8")
    try:
        contrato = json.loads((d / "plantilla.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"el contrato no es JSON válido: {e}") from e

    slug = str(contrato.get("id", "")).strip()
    if not _SLUG.match(slug):
        raise ValueError(
            f"el `id` del contrato tiene que ser un slug corto en minúscula "
            f"(letras, números, guiones). Llegó: {slug!r}")
    if not contrato.get("medidas"):
        raise ValueError("el contrato no declara ningún formato en `medidas`")
    if not contrato.get("campos"):
        raise ValueError("el contrato no declara ningún campo")
    return html, contrato


def _dibujar(marca_nombre: str, carpeta: Path, html: str, contrato: dict
             ) -> list[Path]:
    """Renderiza TODOS los formatos que el contrato declara.

    Es la verificación que importa, y por eso se hace acá en vez de confiar en
    que el agente la haya hecho: una plantilla que no dibuja no es una
    plantilla, y guardarla sería dejar una bomba para la pieza siguiente.
    """
    import sys
    sys.path.insert(0, str(carpeta))
    sys.path.insert(0, str(config.RAIZ))
    marca = importlib.import_module("marca")

    from motor import plantillas as mp
    from motor.render import Render
    from playwright.sync_api import sync_playwright

    d = carpeta / "plantillas" / BORRADOR
    datos = _ejemplo(contrato, carpeta)
    salidas, render = [], Render(marca, carpeta)
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page(viewport={"width": 1080, "height": 1080},
                          device_scale_factor=1)
        try:
            for fmt in contrato["medidas"]:
                if fmt not in marca.FORMATOS:
                    raise ValueError(
                        f"el contrato declara el formato «{fmt}», que la marca "
                        f"no tiene. Tiene: {', '.join(marca.FORMATOS)}")
                cuerpo = mp.compilar(marca, carpeta, contrato, html, datos, fmt)
                w, h = marca.FORMATOS[fmt]
                destino = d / f"preview-{fmt}.png"
                render._captura(pg, cuerpo, w, h, destino, datos)
                salidas.append(destino)
        finally:
            nav.close()
            for tmp in render._tmp:
                tmp.unlink(missing_ok=True)
    return salidas


def _ejemplo(contrato: dict, carpeta: Path) -> dict:
    muestra = {"texto": "Texto de ejemplo", "si_no": True,
               "texto_largo": "Un párrafo de ejemplo, largo como para ver "
                              "cómo cae el texto cuando el contenido no es corto."}
    fotos = sorted((carpeta / "assets").glob("*.jpg"))
    d = {}
    for campo in contrato.get("campos", []):
        cid, tipo = campo["id"], campo.get("tipo", "texto")
        if "ejemplo" in campo:
            d[cid] = campo["ejemplo"]
        elif tipo == "imagen":
            d[cid] = f"assets/{fotos[0].name}" if fotos else ""
        elif tipo == "opcion":
            d[cid] = campo.get("default", (campo.get("opciones") or [""])[0])
        elif tipo == "lista":
            cols = campo.get("columnas") or [{"id": "texto"}]
            d[cid] = [[c.get("etiqueta", c["id"]) for c in cols] for _ in range(3)]
        elif "default" in campo:
            d[cid] = campo["default"]
        elif campo.get("requerido"):
            d[cid] = muestra.get(tipo, "Texto de ejemplo")
        else:
            d[cid] = ""
    return d


async def _correr(prompt: str, marca: str,
                  modelo: str = MODELO) -> tuple[str, dict]:
    """Una pasada del agente. Devuelve (último texto, métricas)."""
    # SIN `skills=[marca]`, y es la diferencia más grande de costo que tiene
    # este módulo. El SKILL.md de Boss pesa 23.324 tokens y de eso al que
    # escribe una plantilla le sirven 590: el resto son reels, carruseles,
    # video, el banco de fotos y las reglas de publicación. Cargarlo entero
    # cuesta releerlo en CADA turno — cuarenta y tres veces en la primera
    # corrida medida.
    #
    # Lo que necesita se lo da el prompt, y lo que le falte lo abre con Read.
    opciones = ClaudeAgentOptions(
        cwd=str(config.RAIZ),
        model=modelo,
        setting_sources=["project"],
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        permission_mode="dontAsk",
        max_turns=60,
    )
    ultimo, resultado = "", None
    try:
        async for msg in query(prompt=prompt, options=opciones):
            if type(msg).__name__ == "ResultMessage":
                resultado = msg
                continue
            texto = _texto(msg)
            if texto:
                ultimo = texto
                log.info("plantillero: %s", texto[:300])
    except Exception as e:
        # Igual que en el diseñador: el agente puede cortar habiendo dejado los
        # archivos hechos. Preferimos revisar qué dejó antes de descartar todo.
        log.warning("el plantillero cortó con error (%s); reviso qué dejó", e)
    return ultimo, (_metricas(resultado, modelo) or {})


async def atender(cli, pedido: dict) -> bool:
    """Arma la plantilla que pidieron y deja el borrador. True si salió."""
    pid, arranque = pedido["id"], time.time()
    if not _tomar(cli, pid):
        log.info("[%s] el pedido %s ya lo tomó otra corrida", cli.marca, pid)
        return False

    carpeta = _skill(cli.marca)
    borrador = carpeta / "plantillas" / BORRADOR
    shutil.rmtree(borrador, ignore_errors=True)
    borrador.mkdir(parents=True, exist_ok=True)

    try:
        from . import manual
        texto_manual, _ = manual.leer(cli.marca)
        nombre = getattr(config, "NOMBRE_MARCA", cli.nombre)

        # Corregir y escribir de cero son dos trabajos distintos y cuestan
        # distinto. Rehacer una plantilla para mover un número de tamaño son
        # cuarenta y tres turnos y US$3,50 medidos; editarla son cuatro. La
        # diferencia no es el prompt: es que el que corrige no lee
        # referencias, no inventa el contrato, y dibuja para verificar en vez
        # de para descubrir.
        anterior = _bajar_publicada(cli, pedido["corrige"]) if pedido.get("corrige") else None
        modelo = MODELO
        if anterior:
            modelo = MODELO_CORRECCION
            (borrador / "plantilla.html").write_text(anterior[0], encoding="utf-8")
            (borrador / "plantilla.json").write_text(
                json.dumps(anterior[1], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
            prompt = PROMPT_CORRECCION.format(
                slug=pedido["corrige"], marca=nombre, nombre_marca=cli.marca,
                pedido=pedido["mensaje"], borrador=BORRADOR,
                vocabulario=_vocabulario(carpeta))
            log.info("[%s] corrijo «%s» en vez de armar una nueva",
                     cli.marca, pedido["corrige"])
        else:
            if pedido.get("corrige"):
                # Pidieron corregir algo que no está publicado. Se arma de
                # nuevo y se dice, en vez de fallar: el pedido es válido.
                log.warning("[%s] «%s» no está publicada: la armo de cero",
                            cli.marca, pedido["corrige"])
            prompt = PROMPT.format(
                marca=nombre, nombre_marca=cli.marca,
                pedido=pedido["mensaje"], skill=carpeta, borrador=BORRADOR,
                referencias=", ".join(f"`{r}`" for r in _referencias(carpeta)),
                vocabulario=_vocabulario(carpeta),
                manual=("\n## El criterio de la marca\n\nManda sobre todo lo de "
                        f"arriba.\n\n{texto_manual}" if texto_manual else ""))

        ultimo, met = await _correr(prompt, cli.marca, modelo)
        html, contrato = _leer_borrador(carpeta)
        previews = _dibujar(cli.marca, carpeta, html, contrato)

        slug = contrato["id"]
        version = _guardar(cli, slug, html, contrato,
                           etiqueta=f"pedida: {pedido['mensaje'][:90]}",
                           quien=pedido.get("quien") or "el chat")

        urls = [cli.subir(p, f"plantillas/{slug}-v{version}/{p.name}")
                for p in previews]

        met["segundos_totales"] = round(time.time() - arranque)
        _marcar(cli, pid, "listo", plantilla=slug, version=version,
                preview=urls, notas=(ultimo or "")[:4000], metricas=met)
        log.info("[%s] plantilla «%s» v%s lista en %ds · %d previews",
                 cli.marca, slug, version, met["segundos_totales"], len(urls))
        return True

    except Exception as e:
        log.exception("[%s] no pude armar la plantilla del pedido %s",
                      cli.marca, pid)
        # El mensaje va en castellano y entero: lo lee el chat y se lo cuenta a
        # la persona. «Error 500» no le sirve a nadie.
        _marcar(cli, pid, "error", mensaje_agente=str(e)[:900])
        return False
    finally:
        # El borrador no sobrevive a la corrida. Lo que vale quedó en la base.
        shutil.rmtree(borrador, ignore_errors=True)


async def atender_todos(cli) -> int:
    """Los pedidos de plantilla de esta corrida. Devuelve cuántos se armaron.

    Es `async` porque el ciclo del worker ya lo es: abrir un bucle de eventos
    propio adentro de uno que ya está corriendo revienta con «this event loop
    is already running», y es el tipo de error que aparece recién el día que
    entra el primer pedido de verdad.
    """
    pendientes = _pendientes(cli)
    if not pendientes:
        return 0
    hechos = 0
    for p in pendientes:
        try:
            hechos += bool(await atender(cli, p))
        except Exception:
            log.exception("[%s] el pedido de plantilla %s se cayó entero",
                          cli.marca, p["id"])
    return hechos
