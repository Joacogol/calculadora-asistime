# -*- coding: utf-8 -*-
"""Fuente y destino de los pedidos: la base de UN cliente.

Cada cliente tiene su propio proyecto de Supabase. No es una complicación
gratuita: es lo que hace Lovable por defecto —un proyecto, una base— y sobre
todo es lo que permite entregarle o venderle el sistema a un cliente sin tener
que desenredar sus diseños de los de otro.

Lo que NO se separa es el motor: un solo worker recorre todos los clientes y
usa el mismo código para todos. La separación es de datos, no de código.

Por eso este módulo es una clase y no un puñado de funciones sueltas leyendo
variables globales: cada instancia habla con la base de un cliente.

Se usa la service_role key porque el worker corre en un servidor y necesita
saltear las políticas de RLS. Esa clave nunca toca el frontend.
"""
import json
import logging
import mimetypes
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote

import requests

log = logging.getLogger(__name__)

TIEMPO = 30


def clave_segura(nombre: str) -> str:
    """Un nombre de archivo que Supabase Storage acepte.

    Storage rechaza con 400 las claves que traen caracteres fuera de un juego
    reducido. Pasó con `story-nos-vemos-mañana.png`: el agente escribe los
    nombres en castellano y tarde o temprano aparece una ñ, una tilde o un signo
    de pregunta. El diseño se generaba perfecto y se perdía al subirlo.

    Se traduce a ASCII conservando la letra —mañana → manana, día → dia— en vez
    de borrar el carácter, para que el nombre siga siendo legible. El prefijo
    numérico de los carruseles sobrevive, que es lo que ordena la publicación.
    """
    # La extensión se separa antes de limpiar. Sin esto, un nombre raro como
    # «---.png» quedaba en «png»: la limpieza le comía el punto y el archivo
    # perdía el tipo, que es de lo que dependen el visor del chat y el ícono
    # de descarga.
    punto = nombre.rfind(".")
    cuerpo, ext = (nombre[:punto], nombre[punto:]) if punto > 0 else (nombre, "")

    def limpiar(x, permitido=r"[^A-Za-z0-9._-]+"):
        x = unicodedata.normalize("NFKD", x)
        x = x.encode("ascii", "ignore").decode("ascii")
        x = re.sub(permitido, "-", x)
        return re.sub(r"-{2,}", "-", x).strip("-. ")

    cuerpo = limpiar(cuerpo) or "archivo"
    ext = limpiar(ext).lower()
    return f"{cuerpo}.{ext}" if ext else cuerpo


class Cliente:
    """La base de un cliente, con su marca."""

    def __init__(self, marca: str, url: str, key: str,
                 bucket: str = "disenos", nombre: str = ""):
        self.marca = marca
        self.url = (url or "").rstrip("/")
        self.key = key or ""
        self.bucket = bucket or "disenos"
        self.nombre = nombre or marca

    def __repr__(self):
        return f"<Cliente {self.marca} {self.url}>"

    @property
    def configurado(self) -> bool:
        return bool(self.url and self.key)

    def _url(self, camino: str) -> str:
        return f"{self.url}/rest/v1/{camino}"

    def _cab(self, extra=None):
        c = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        if extra:
            c.update(extra)
        return c

    # ───────────────────────────────────────────────────────────── PEDIDOS

    # Las columnas del pedido, en dos grupos. `fotos_elegidas` la agrega
    # `fotos.sql`, que es posterior a los primeros clientes: si se pidiera sin
    # más, un cliente que todavía no corrió esa migración dejaría de recibir
    # TODOS sus diseños por una columna que ni usa. Se pide, y si la base dice
    # que no existe, se anota y se sigue sin ella.
    COLUMNAS = "id,mensaje,formatos,sede,quien,creado_en,adjuntos"
    COLUMNAS_NUEVAS = "fotos_elegidas,logo_socio,corrige"

    def leer_pedidos(self, limite: int):
        """Los diseños pendientes, del más viejo al más nuevo."""
        cols = self.COLUMNAS
        if getattr(self, "_banco_ok", True):
            cols += "," + self.COLUMNAS_NUEVAS
        pedir = lambda c: requests.get(  # noqa: E731
            self._url("disenos"),
            headers=self._cab(),
            params={
                "estado": "eq.pendiente",
                "order": "creado_en.asc",
                "limit": str(limite),
                "select": c,
            },
            timeout=TIEMPO,
        )
        r = pedir(cols)
        if r.status_code == 400 and self.COLUMNAS_NUEVAS in cols:
            log.warning("[%s] a la base le faltan columnas nuevas (%s): "
                        "corré base-de-un-cliente.sql. Sigo sin ellas.",
                        self.marca, self.COLUMNAS_NUEVAS)
            self._banco_ok = False
            r = pedir(self.COLUMNAS)
        r.raise_for_status()

        pedidos = []
        for f in r.json():
            pedidos.append({
                "id": f["id"],
                "fila": f["id"],
                # La marca sale del cliente, no de la fila. Con una base por
                # cliente no hay forma de que un pedido pida la marca de otro:
                # está determinado por en qué base entró.
                "marca": self.marca,
                "texto": (f.get("mensaje") or "").strip(),
                "sede": (f.get("sede") or "").strip(),
                "formatos": f.get("formatos") or ["post"],
                "cuando": f.get("creado_en", ""),
                "quien": (f.get("quien") or "Chat").strip(),
                "adjuntos": f.get("adjuntos") or [],
                # Claves del banco, no archivos: ver el comentario en fotos.sql.
                "fotos_elegidas": f.get("fotos_elegidas") or [],
                # El logo de la empresa con la que se firma un convenio. Tiene
                # campo propio y no viaja en `adjuntos` a propósito: con una
                # foto y un logo adjuntos, el agente tenía que adivinar cuál
                # era cuál, y adivinar termina con el logo de la empresa usado
                # como foto de fondo.
                "logo_socio": (f.get("logo_socio") or "").strip(),
                # El diseño que este pedido viene a CORREGIR. Con esto puesto,
                # el worker le pasa al agente el spec exacto de esa pieza y le
                # pide que cambie sólo lo que se pide. Sin esto, un pedido de
                # cambio rehace la pieza entera y vuelve otra distinta.
                "corrige": (f.get("corrige") or "") or None,
            })
        return [p for p in pedidos if p["texto"]]

    def marcar(self, pedido_id: str, estado: str, **campos):
        """Cambia el estado de un diseño. El chat lo ve al instante."""
        r = requests.patch(
            self._url("disenos"),
            headers=self._cab({"Prefer": "return=minimal"}),
            params={"id": f"eq.{pedido_id}"},
            data=json.dumps({"estado": estado, **campos}),
            timeout=TIEMPO,
        )
        r.raise_for_status()
        log.info("[%s] diseño %s -> %s", self.marca, pedido_id, estado)

    def tomar(self, pedido_id: str) -> bool:
        """Marca el diseño como «generando», pero sólo si sigue pendiente.

        Es el candado: si dos corridas se superponen, la segunda no vuelve a
        generar la misma pieza. El filtro por estado hace que la condición y la
        escritura ocurran en la misma operación.
        """
        r = requests.patch(
            self._url("disenos"),
            headers=self._cab({"Prefer": "return=representation"}),
            params={"id": f"eq.{pedido_id}", "estado": "eq.pendiente"},
            data=json.dumps({"estado": "generando"}),
            timeout=TIEMPO,
        )
        r.raise_for_status()
        return bool(r.json())

    # ────────────────────────────────────────────────────────────── FOTOS

    def leer_diseno(self, diseno_id: str) -> dict | None:
        """Un diseño ya hecho, con su `spec`. Para poder CORREGIRLO.

        Devuelve None y no falla si no está o si la tabla es vieja: una
        corrección sin spec sigue siendo un pedido válido —se avisa y se rehace
        a mano— y no vale la pena tirar el trabajo por eso.
        """
        try:
            r = requests.get(
                self._url("disenos"),
                headers=self._cab(),
                params={"id": f"eq.{diseno_id}",
                        "select": "id,mensaje,spec,urls,titulo",
                        "limit": 1},
                timeout=TIEMPO)
            r.raise_for_status()
            filas = r.json()
            return filas[0] if filas else None
        except Exception as e:
            log.warning("[%s] no pude leer el diseño %s: %s",
                        self.marca, diseno_id, e)
            return None

    def leer_fotos(self, limite: int = 60) -> list[dict]:
        """El banco de fotos que cargó el cliente desde su app.

        Devuelve `[]` —y no falla— en los dos casos en que un cliente no tiene
        banco: nunca corrió `fotos.sql`, o lo corrió y todavía no subió nada.
        Ninguno de los dos es un error del worker, y en los dos el agente tiene
        que poder seguir trabajando con el banco que viene en el skill.

        Se piden las más nuevas primero y con tope: cada foto que entra acá se
        baja al disco del worker antes de diseñar, así que la lista larga se
        paga en segundos de cada corrida, no en bytes de una tabla.
        """
        try:
            r = requests.get(
                self._url("fotos"),
                headers=self._cab(),
                params={
                    "activa": "is.true",
                    "order": "creado_en.desc",
                    "limit": str(limite),
                    "select": "clave,url,descripcion,etiquetas,quien,foco,"
                              "ancho,alto",
                },
                timeout=TIEMPO,
            )
            if r.status_code == 404:
                return []
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            log.warning("[%s] no pude leer el banco de fotos; sigo con el "
                        "del skill", self.marca)
            return []

    def guardar_foco(self, clave: str, foco: dict) -> bool:
        """Guarda el encuadre que el agente resolvió mirando la pieza.

        Es la parte del banco que lo hace mejorar solo. El agente ya hace este
        trabajo hoy —genera, mira el PNG, corrige el `foco` y vuelve a
        generar— y hasta ahora se tiraba a la basura al terminar el pedido: la
        próxima pieza con esa misma foto arrancaba de cero y volvía a cortar la
        misma cara.

        Se **fusiona** con lo que ya había en vez de reemplazarlo, porque cada
        pedido resuelve el encuadre de los formatos que le tocaron. Un pedido
        de story no puede borrar el `post` que dejó resuelto otro de la semana
        pasada.
        """
        try:
            r = requests.get(
                self._url("fotos"),
                headers=self._cab(),
                params={"clave": f"eq.{clave}", "limit": "1",
                        "select": "id,foco"},
                timeout=TIEMPO,
            )
            r.raise_for_status()
            filas = r.json()
            if not filas:
                log.warning("[%s] no hay foto «%s» en el banco", self.marca, clave)
                return False
            fusion = {**(filas[0].get("foco") or {}), **(foco or {})}
            r = requests.patch(
                self._url("fotos"),
                headers=self._cab({"Prefer": "return=minimal"}),
                params={"id": f"eq.{filas[0]['id']}"},
                data=json.dumps({"foco": fusion}),
                timeout=TIEMPO,
            )
            r.raise_for_status()
            log.info("[%s] foco de «%s» -> %s", self.marca, clave, fusion)
            return True
        except requests.RequestException:
            log.exception("[%s] no pude guardar el foco de «%s»",
                          self.marca, clave)
            return False

    def anotar_foto(self, clave: str, **campos) -> bool:
        """Completa lo que la persona no escribió: `quien`, `descripcion`…

        Quien sube una foto desde el celular no va a describir quién aparece.
        El agente sí puede: ya tiene la imagen abierta cuando la usa. Sin esto,
        una foto subida por el cliente nunca se puede filtrar por «que sea con
        jugadoras» y el banco cargado por el cliente vale menos que el que
        viene en el skill.
        """
        campos = {k: v for k, v in campos.items() if v not in (None, "", {}, [])}
        if not campos:
            return False
        try:
            r = requests.patch(
                self._url("fotos"),
                headers=self._cab({"Prefer": "return=representation"}),
                params={"clave": f"eq.{clave}", "select": "clave"},
                data=json.dumps(campos),
                timeout=TIEMPO,
            )
            r.raise_for_status()
            return bool(r.json())
        except requests.RequestException:
            log.exception("[%s] no pude anotar la foto «%s»", self.marca, clave)
            return False

    # ──────────────────────────────────────────────────────── PUBLICACIONES

    def leer_cuenta_ig(self) -> dict | None:
        """La cuenta de Instagram conectada, con su token.

        Devuelve None si el cliente todavía no conectó ninguna, que es el caso
        normal: publicar es opcional y no todos los clientes lo van a usar.
        Tampoco falla si la tabla no existe —un cliente que no corrió
        `publicar.sql`—: eso es «no hay cuenta», no un error del worker.
        """
        try:
            r = requests.get(
                self._url("cuentas_ig"),
                headers=self._cab(),
                params={"activa": "is.true", "limit": "1",
                        "order": "creado_en.desc",
                        "select": "id,usuario,ig_user_id,token,expira_en,"
                                  "renovado_en"},
                timeout=TIEMPO,
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            filas = r.json()
            return filas[0] if filas else None
        except requests.RequestException:
            log.exception("[%s] no pude leer la cuenta de Instagram", self.marca)
            return None

    def guardar_cuenta_ig(self, cuenta_id: str, **campos):
        r = requests.patch(
            self._url("cuentas_ig"),
            headers=self._cab({"Prefer": "return=minimal"}),
            params={"id": f"eq.{cuenta_id}"},
            data=json.dumps(campos),
            timeout=TIEMPO,
        )
        r.raise_for_status()

    def leer_publicaciones(self, limite: int, rancio: str = ""):
        """Lo que toca publicar ahora.

        Son dos casos distintos y por eso el filtro es un `or`:

          · `programado` con la hora cumplida — lo normal.
          · `subiendo` **y sin tocar hace rato** — una fila que quedó a mitad
            de camino porque la corrida anterior se murió, o un video que
            todavía estaba procesando cuando se acabó el tiempo.

        Lo de «sin tocar hace rato» no es cosmético. Las corridas arrancan cada
        minuto y una puede tardar más de un minuto, así que dos se pisan. Si
        levantáramos cualquier fila en `subiendo`, la segunda corrida publicaría
        el mismo contenedor que la primera está por publicar: **dos posteos
        iguales en la cuenta del cliente**. El disparador de `actualizado_en`
        hace que una fila en curso tenga marca fresca, y eso la protege.
        """
        r = requests.get(
            self._url("publicaciones"),
            headers=self._cab(),
            params={
                "or": (f"(and(estado.eq.programado,publicar_en.lte.now()),"
                       f"and(estado.eq.subiendo,actualizado_en.lt.{rancio}))"),
                "order": "publicar_en.asc",
                "limit": str(limite),
                "select": "id,diseno_id,tipo,urls,caption,estado,contenedor,"
                          "intentos,esperas,publicar_en",
            },
            timeout=TIEMPO,
        )
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json()

    def tomar_publicacion(self, pub_id: str, estado_previo: str,
                          rancio: str = "") -> bool:
        """El mismo candado que en los diseños, por un motivo más caro.

        Dos corridas superpuestas sobre un diseño harían trabajo de más. Sobre
        una publicación harían DOS POSTEOS en la cuenta del cliente, que no se
        pueden deshacer desde acá.

        Para `programado` alcanza con el cambio de estado. Para `subiendo` no
        —el estado no cambia, así que el filtro no filtra nada— y hace falta
        además la condición de que nadie la haya tocado en los últimos minutos.
        """
        filtros = {"id": f"eq.{pub_id}", "estado": f"eq.{estado_previo}"}
        if estado_previo == "subiendo":
            filtros["actualizado_en"] = f"lt.{rancio}"
        r = requests.patch(
            self._url("publicaciones"),
            headers=self._cab({"Prefer": "return=representation"}),
            params=filtros,
            data=json.dumps({"estado": "subiendo"}),
            timeout=TIEMPO,
        )
        r.raise_for_status()
        return bool(r.json())

    def marcar_publicacion(self, pub_id: str, estado: str, **campos):
        r = requests.patch(
            self._url("publicaciones"),
            headers=self._cab({"Prefer": "return=minimal"}),
            params={"id": f"eq.{pub_id}"},
            data=json.dumps({"estado": estado, **campos}),
            timeout=TIEMPO,
        )
        r.raise_for_status()
        log.info("[%s] publicación %s -> %s", self.marca, pub_id, estado)

    # ───────────────────────────────────────────────────────────── STORAGE

    def subir(self, ruta: Path, destino: str) -> str:
        """Sube un archivo a Storage y devuelve su URL pública.

        El binario va tal cual por HTTP, leído del disco. No se codifica ni
        pasa por el contexto de ningún modelo: esa es la razón de ser de este
        worker.

        El nombre se limpia acá y no en quien llama: es el único lugar por donde
        pasan todos los archivos de todas las marcas, así que es el único donde
        el arreglo no se puede olvidar.
        """
        partes = [clave_segura(x) for x in destino.split("/") if x]
        destino = "/".join(partes)
        mime = mimetypes.guess_type(ruta.name)[0] or "application/octet-stream"
        with ruta.open("rb") as f:
            r = requests.post(
                f"{self.url}/storage/v1/object/{self.bucket}/{quote(destino)}",
                headers={
                    "apikey": self.key,
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": mime,
                    "x-upsert": "true",
                },
                data=f,
                timeout=180,
            )
        if r.status_code >= 400:
            # El cuerpo de la respuesta dice el motivo real; sin esto el log
            # sólo muestra «400 Bad Request» y no se sabe qué rechazó.
            raise RuntimeError(
                f"Storage rechazó «{destino}» ({r.status_code}): "
                f"{r.text[:200]}")
        log.info("[%s] subido %s (%d KB)", self.marca, destino,
                 ruta.stat().st_size // 1024)
        return (f"{self.url}/storage/v1/object/public/"
                f"{self.bucket}/{quote(destino)}")


def bajar(url: str, destino: Path) -> Path:
    """Trae un archivo que subió la persona al disco del worker.

    Es una función suelta y no un método a propósito: va **sin ninguna clave**.
    El bucket es de lectura pública y estas URLs salieron de la base. Mandar la
    service_role key a una URL que vino de datos sería regalarla el día que esa
    URL apunte a otro lado.
    """
    r = requests.get(url, timeout=TIEMPO, stream=True)
    r.raise_for_status()
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("wb") as f:
        for trozo in r.iter_content(chunk_size=65536):
            f.write(trozo)
    log.info("bajado %s (%d KB)", destino.name, destino.stat().st_size // 1024)
    return destino
