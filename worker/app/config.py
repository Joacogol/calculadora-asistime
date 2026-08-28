# -*- coding: utf-8 -*-
"""Configuración leída del entorno."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# ── Versión del motor ─────────────────────────────────────────────────────
# Se guarda en `metricas` de cada diseño. Existe por una tarde entera perdida:
# una pieza salió con defectos que ya estaban arreglados, y no había forma de
# saber si el arreglo no servía o si el worker no se había actualizado. Hubo
# que deducirlo midiendo los píxeles de la pieza publicada.
#
# Con esto, una consulta a la base dice qué código produjo cada diseño.
# **Subile el número a cada despliegue que cambie algo visible.**
VERSION = "2026.08.12-1"

# ── Google ────────────────────────────────────────────────────────────────
# En Cloud Run no hace falta ninguna clave: dejalo vacío.
# Sólo se usa para pruebas locales, apuntando a un JSON de cuenta de servicio.
GOOGLE_CREDS = os.environ.get("GOOGLE_CREDS", "")

# Mail de la cuenta de servicio. En Cloud Run es obligatorio: se usa para
# pedir un token con los alcances de Drive y Sheets.
SA_EMAIL = os.environ.get("SA_EMAIL", "")

# ── Los clientes ──────────────────────────────────────────────────────────
# Cada cliente tiene SU propio proyecto de Supabase. El worker es uno solo y
# los recorre a todos: lo que se separa es la data, no el código.
#
# `CLIENTES` es un JSON con la lista. Las claves NO van ahí: cada cliente
# nombra la variable de entorno donde está la suya, y esa variable la llena
# Secret Manager. Así el JSON se puede leer en un log sin regalar nada.
#
#   CLIENTES=[{"marca":"boss-padel-disenos","url":"https://xxx.supabase.co",
#              "key_env":"SUPABASE_KEY_BOSS"},
#             {"marca":"clinica-preventiva-disenos","url":"https://yyy.supabase.co",
#              "key_env":"SUPABASE_KEY_CLINICA"}]
#
# Si `CLIENTES` no está, se usa el modo de un solo cliente con SUPABASE_URL y
# SUPABASE_KEY. Eso mantiene andando el despliegue anterior sin tocar nada.
import json as _json

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
BUCKET = os.environ.get("BUCKET", "disenos")
MARCA_UNICA = os.environ.get("MARCA", "boss-padel-disenos")


def clientes() -> list[dict]:
    """La lista de clientes, con la clave de cada uno ya resuelta."""
    crudo = os.environ.get("CLIENTES", "").strip()
    if not crudo:
        return [{"marca": MARCA_UNICA, "url": SUPABASE_URL,
                 "key": SUPABASE_KEY, "bucket": BUCKET,
                 "nombre": MARCA_UNICA}]
    salida = []
    for c in _json.loads(crudo):
        salida.append({
            "marca": c["marca"],
            "url": (c.get("url") or "").rstrip("/"),
            "key": os.environ.get(c.get("key_env", ""), "") or c.get("key", ""),
            "bucket": c.get("bucket", "disenos"),
            "nombre": c.get("nombre", c["marca"]),
        })
    return salida

# ── Asistime ──────────────────────────────────────────────────────────────
# De dónde sale el manual de marca que edita cada cliente. La clave va aparte,
# en ASISTIME_CLAVE, y la llena Secret Manager: acá sólo la dirección, que no
# es secreta y conviene poder leerla en un log.
ASISTIME_API = os.environ.get("ASISTIME_API", "https://api.asistime.ai").rstrip("/")

# ── Comportamiento ────────────────────────────────────────────────────────
MAX_POR_CICLO = int(os.environ.get("MAX_POR_CICLO", "10"))

# Publicaciones por corrida y por cliente. Bajo a propósito: la corrida es cada
# minuto, así que 3 por minuto son 180 por hora — muy por encima de los 100
# posteos diarios que permite Instagram. Lo que este número acota es cuánto
# puede tardar un cliente antes de que le toque el turno al siguiente.
MAX_PUBLICACIONES = int(os.environ.get("MAX_PUBLICACIONES", "3"))

# El interruptor general. `PUBLICAR=0` deja el worker diseñando y sin tocar
# ninguna cuenta de Instagram: es lo que se pone si algo sale mal y hay que
# frenar todo sin volver atrás el despliegue.
PUBLICAR = os.environ.get("PUBLICAR", "1") != "0"
SALIDA = Path(os.environ.get("SALIDA", "/tmp/piezas"))

# ── Modelo ────────────────────────────────────────────────────────────────
# Hasta el 01/08/2026 esto no estaba puesto y el SDK usaba su default, que es
# Opus: una placa post+story salió US$ 0,99. Del desglose, sólo US$ 0,21 fue
# generar la pieza — el resto fue el skill entero cargándose y recargándose a
# lo largo de 23 turnos.
#
# La pieza simple no necesita Opus: elegir plantilla, sacar datos de un texto
# corto y copiar un `foco` ya resuelto lo hace Sonnet igual de bien por el 40%
# del precio. Lo que sí lo necesita es un reel —decidir qué tramo de qué clip,
# con qué ritmo— y una presentación de ocho slides, donde la estructura es la
# mitad del trabajo.
#
# Si una pieza simple falla con el modelo barato, `disenador.py` la reintenta
# una vez con el caro antes de darla por perdida. Ese reintento es la red: si
# aparece seguido en los logs, el ahorro no está saliendo gratis.
MODELO_SIMPLE = os.environ.get("MODELO_SIMPLE", "claude-sonnet-4-5")
MODELO_COMPLEJO = os.environ.get("MODELO_COMPLEJO", "claude-opus-4-5")

# Formatos que justifican el modelo caro. Ojo con `reel`: ése es la TAPA, una
# imagen fija, y va con el modelo barato como cualquier otra placa. El reel de
# verdad es `video`.
#
# `carrusel` y `secuencia` arrancan acá a propósito, aunque cada diapositiva
# suelta sea una placa simple. Lo difícil de un carrusel no es dibujar cinco
# imágenes: es repartir una idea entre cinco y que la tercera tenga sentido
# después de la segunda. Un arco mal armado desperdicia la pieza entera.
#
# Es una posición de arranque, no una convicción: cuando haya cinco o seis
# carruseles hechos, hay que mirar si Sonnet los resuelve igual y bajarlos.
FORMATOS_COMPLEJOS = {"pdf", "video", "carrusel", "secuencia"}

# ── Datos de cada marca ───────────────────────────────────────────────────
# Se mudaron a `.claude/skills/<marca>/marca.json`. Estaban acá cuando el
# sistema servía a un solo cliente, y pisaban lo que decía el skill: los
# teléfonos del Hípico y de Punta estuvieron mal en producción por eso.
# Un dato de marca dentro del worker es un dato que la marca no controla.
