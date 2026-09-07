# -*- coding: utf-8 -*-
"""Cargar el módulo de una marca sin que se pise con las otras.

El problema que resuelve, que costó un reel entero: cada marca vive en
`.claude/skills/<marca>/marca.py`, y hasta el 2/9/2026 todas se cargaban así::

    sys.path.insert(0, str(carpeta))
    marca = importlib.import_module("marca")

Python cachea los módulos POR NOMBRE. Las cuatro marcas se llaman `marca`, así
que la primera que se cargaba en el proceso se quedaba con el nombre y todas
las siguientes recibían **la primera**. En un script suelto no se nota —una
corrida, una marca—, pero el worker es un solo proceso que recorre a los
cuatro clientes seguidos.

Y no es sólo `marca`: Boss y Clínica importan `brand`, `templates`,
`diapositivas` y `presentacion`, los cuatro por nombre pelado. La segunda
marca del recorrido se dibujaba con los colores, el logo y las plantillas de
la primera, sin un solo error en el log.

Cómo se arregla acá:

* cada marca se carga bajo un nombre propio (`marca__boss_padel_disenos`), así
  que no hay dos peleando por la misma entrada del caché;
* durante la carga, las carpetas de las OTRAS marcas salen del `sys.path`, para
  que `import brand` no pueda encontrar el `brand.py` del vecino;
* al terminar, los hermanos de nombre pelado que la carga haya creado se sacan
  del caché. El módulo ya se los llevó adentro (`from brand import C` deja el
  objeto en su propio espacio), así que sacarlos no le quita nada a la marca
  que acaba de cargar y le deja el camino limpio a la próxima.

El resultado se cachea por carpeta: cargar una marca dos veces devuelve el
mismo módulo, que es lo que esperaba el código que llamaba a `import_module`.
"""
import importlib.util
import logging
import re
import sys
from pathlib import Path

log = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parent.parent

_cache: dict[Path, object] = {}


def _nombre(carpeta: Path) -> str:
    """Un nombre de módulo propio y estable para esta marca."""
    return "marca__" + re.sub(r"\W", "_", carpeta.name)


def _vecinas(carpeta: Path) -> set[str]:
    """Las carpetas de las demás marcas, que durante la carga no existen."""
    try:
        return {str(d) for d in carpeta.parent.iterdir()
                if d.is_dir() and d.resolve() != carpeta}
    except OSError:
        return set()


def _hermanos(carpeta: Path) -> list[str]:
    """Los módulos cacheados que salieron de archivos de ESTA carpeta.

    Se los busca por el archivo del que vinieron y no por una lista de nombres
    escrita a mano: si mañana una marca parte su `templates.py` en dos, el
    nuevo aparece acá solo.
    """
    fuera = []
    for nombre, mod in list(sys.modules.items()):
        if nombre.startswith("marca__"):
            continue                       # los nuestros no colisionan
        archivo = getattr(mod, "__file__", None)
        if not archivo:
            continue
        try:
            if Path(archivo).resolve().parent == carpeta:
                fuera.append(nombre)
        except OSError:
            continue
    return fuera


def cargar_marca(carpeta) -> object:
    """El módulo `marca.py` de esta carpeta, aislado de las demás marcas."""
    carpeta = Path(carpeta).resolve()
    if carpeta in _cache:
        return _cache[carpeta]

    nombre = _nombre(carpeta)
    vecinas = _vecinas(carpeta)
    camino_previo = list(sys.path)
    # La carpeta propia primero y la raíz después (`from motor import ...`);
    # las vecinas, afuera, para que ningún hermano se resuelva contra ellas.
    sys.path[:] = ([str(carpeta), str(RAIZ)]
                   + [p for p in sys.path if p not in vecinas])
    # Un hermano que dejó cacheado OTRA marca hay que sacarlo antes de empezar,
    # o `import brand` lo encuentra en el caché y ni mira el `sys.path`.
    for otra in vecinas:
        for viejo in _hermanos(Path(otra)):
            sys.modules.pop(viejo, None)
    try:
        spec = importlib.util.spec_from_file_location(
            nombre, carpeta / "marca.py")
        if spec is None or spec.loader is None:
            raise ImportError(f"no encuentro «marca.py» en {carpeta}")
        modulo = importlib.util.module_from_spec(spec)
        sys.modules[nombre] = modulo
        try:
            spec.loader.exec_module(modulo)
        except Exception:
            sys.modules.pop(nombre, None)
            raise
    finally:
        for propio in _hermanos(carpeta):
            sys.modules.pop(propio, None)
        sys.path[:] = camino_previo

    _cache[carpeta] = modulo
    return modulo


def olvidar(carpeta=None) -> None:
    """Vaciar el caché. Sólo lo usan las pruebas y el estudio al recargar."""
    if carpeta is None:
        _cache.clear()
    else:
        _cache.pop(Path(carpeta).resolve(), None)
