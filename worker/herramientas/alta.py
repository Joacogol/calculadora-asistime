#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dar de alta un cliente entero con un comando.

    python3 herramientas/alta.py <marca>                 # hace todo lo que falte
    python3 herramientas/alta.py <marca> --simular       # muestra el plan, no toca nada
    python3 herramientas/alta.py <marca> --desde asistime_agente   # retoma desde un paso

Corre donde haya `gcloud` con sesión y `npx` —Cloud Shell— y necesita dos
cosas en el entorno, que no se piden por teclado para que el comando se pueda
dejar corriendo:

    SUPABASE_ACCESS_TOKEN    el token de tu cuenta (supabase.com/dashboard/account/tokens)
    ASISTIME_ADMIN_CLAVE     una clave de Asistime que pueda crear tenants

── Qué hace, y en qué orden ───────────────────────────────────────────────

Los catorce pasos del alta de Stadium, que se hicieron a mano el 25/8/2026,
menos los tres que son de una persona por naturaleza (mirar la identidad,
catalogar las fotos, conectar Instagram). Cada paso guarda lo que produjo en
`.claude/skills/<marca>/alta.json`, así que si algo corta a la mitad, se
vuelve a correr y sigue desde donde quedó. Nada se crea dos veces.

  verificar            la carpeta de la marca carga y cumple el contrato
  supabase_proyecto    el proyecto, y sus claves
  supabase_tablas      las tablas, el bucket y las políticas
  supabase_funciones   las cinco funciones, con verify_jwt apagado
  supabase_secretos    la clave de API de las funciones
  asistime_tenant      el tenant —reusado si ya existe— y su clave de API
  asistime_agente      el agente diseñador con su prompt, publicado
  asistime_documentos  reglas de marca y catálogo, enganchados al agente
  asistime_herramientas  las tools, copiadas de la marca de referencia
  registro             el cliente en el registro del worker (lo ve en un minuto)
  plantillas           sembrar las plantillas y publicar el catálogo
  resumen              lo que queda para una persona

── Por qué las tools se copian de una marca viva ─────────────────────────

Porque son quince archivos de JavaScript que ya andan y que sólo difieren
entre marcas en tres cosas: la dirección de su Supabase, su clave y su
nombre. Tenerlos en el repo sería una segunda copia que se desactualiza; la
copia buena es la que está desplegada. Se leen de la marca de referencia
—Stadium— por la API, se sustituyen esas tres cosas, y se crean en el tenant
nuevo. `probar-alta.py` verifica que la sustitución no deje rastro de la
marca de origen.

── Lo que NO hace ────────────────────────────────────────────────────────

  · La identidad: `marca.json` (bloque «identidad»), `estilo.css`, fuentes y
    logos tienen que estar. Ver `motor/ALTA-DE-MARCA.md`.
  · Las fotos del banco: se catalogan mirándolas.
  · Instagram: es un trámite en la app de Meta, con el cliente presente.
  · El despliegue del worker: la carpeta de la marca tiene que estar en la
    imagen, y eso es un `./desplegar-chat.sh`. Es el único paso que sigue
    necesitando un despliegue, hasta que las marcas se bajen de su base.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import secrets
import subprocess
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

SUPABASE_API = "https://api.supabase.com/v1"
ASISTIME_API = os.environ.get("ASISTIME_API", "https://api.asistime.ai").rstrip("/")
ORGANIZACION = os.environ.get("SUPABASE_ORG", "qnfcntyzpueyesrknfoc")
REGION = os.environ.get("SUPABASE_REGION", "sa-east-1")

#: De quién se copian las tools. Stadium: es la marca que nació entera con la
#: receta y la que tiene el juego completo, incluido `crear_video`.
REFERENCIA = {"tenant": 176, "agente": 544, "ref": "heajbidxysjxxegqemka",
              "nombre": "Stadium",
              "clave": "ea9aa1075970e01b40da429f393981443a831c4a606a0fe7c9cb1a66855238d7"}

FUNCIONES = ("api-disenos", "api-plantillas", "api-publicar", "api-reels", "api-fotos")

#: El SQL, en el orden en que se puede correr: cada uno depende del anterior.
SQL_EN_ORDEN = ("base-de-un-cliente.sql", "plantillas.sql", "motor-pedidos.sql",
                "plantilla-pedidos.sql", "fotos-editadas.sql",
                "migraciones/montaje-de-reels.sql", "migraciones/retoque-de-reels.sql")

PASOS = ("verificar", "supabase_proyecto", "supabase_tablas", "supabase_funciones",
         "supabase_secretos", "asistime_tenant", "asistime_agente",
         "asistime_documentos", "asistime_herramientas", "registro", "plantillas",
         "resumen")


# ═══ Puro: sin red. Es lo que prueba probar-alta.py ═══════════════════════

#: Los formatos que necesitan código y no todas las marcas tienen. `carrusel`
#: y `secuencia` se encadenan con `DIAPOS`; `pdf` se arma con `PRESENTACION`.
#: Son las dos únicas cosas de una marca que todavía no se pueden escribir
#: como datos.
FORMATOS_CON_CODIGO = {"carrusel": "DIAPOS", "secuencia": "DIAPOS",
                       "pdf": "PRESENTACION"}


def formatos_de(modulo) -> set[str]:
    """Los formatos que esta marca NO sabe hacer, de los que necesitan código."""
    return {f for f, atributo in FORMATOS_CON_CODIGO.items()
            if not hasattr(modulo, atributo)}


def podar_formatos(cfg: dict, sobran: set[str]) -> dict:
    """Saca de una tool los formatos que la marca nueva no sabe dibujar.

    Las tools se copian de la marca de referencia, y la de referencia los tiene
    todos. Copiadas tal cual, le ofrecen `carrusel` y `pdf` a una marca cuyo
    motor los rechaza — el agente lee que se puede, lo ofrece, la persona dice
    que sí, y la pieza falla minutos después con un error que él no puede
    explicar.

    Es el mismo error que el catálogo tenía el 2/9/2026, una capa más abajo:
    ahí lo decía la lista de plantillas y acá lo dice el `enum` de la
    herramienta, que es todavía más difícil de ver.

    Se poda en los dos lugares donde el formato manda de verdad: el `enum` del
    parámetro, que es lo que el agente ve, y las listas del código, que son lo
    que la tool acepta. Lo que dice la descripción en prosa NO se toca:
    reescribir una frase a ciegas deja algo peor que lo que había.
    """
    if not sobran:
        return cfg
    podado = json.loads(json.dumps(cfg, ensure_ascii=False))

    props = ((podado.get("parameters") or {}).get("properties") or {})
    items = (props.get("formatos") or {}).get("items") or {}
    if items.get("enum"):
        items["enum"] = [f for f in items["enum"] if f not in sobran]

    # Y en el código, SÓLO adentro de los arreglos de texto: ahí es donde un
    # formato decide si la tool lo acepta. Sacar la palabra suelta de todo el
    # archivo destrozaría los comentarios, que hablan del carrusel en prosa y
    # tienen razón en hacerlo.
    #
    # Se reescribe el arreglo entero y no se borra el elemento con su coma:
    # borrar `"secuencia", ` de `["carrusel", "secuencia"]` deja `["carrusel"]`
    # —el que quedaba sin coma al lado sobrevivía— y ése es justo el caso que
    # esto tiene que resolver.
    codigo = podado.get("code")
    if isinstance(codigo, str):
        def limpiar(m):
            quedan = [x for x in re.findall(r'"([^"\\]*)"', m.group(0))
                      if x not in sobran]
            return "[" + ", ".join(f'"{x}"' for x in quedan) + "]"

        podado["code"] = re.sub(
            r'\[\s*"[^"\\]*"(?:\s*,\s*"[^"\\]*")*\s*\]', limpiar, codigo)
    return podado


def sustituir_tool(tool: dict, origen: dict, destino: dict,
                   sobran: set[str] | None = None) -> dict:
    """Una tool de la marca de referencia, reescrita para la nueva.

    Cambia la dirección del Supabase, la clave y el nombre de la marca en el
    código, la descripción y los parámetros. Devuelve sólo lo que `POST
    /tools` acepta: sin ids ni fechas.

    `sobran` son los formatos que la marca nueva no sabe hacer, y se podan:
    ver `podar_formatos`.
    """
    def s(texto: str) -> str:
        t = texto.replace(origen["ref"], destino["ref"])
        t = t.replace(origen["clave"], destino["clave"])
        return t.replace(origen["nombre"], destino["nombre"])

    cfg = json.loads(s(json.dumps(tool["config"], ensure_ascii=False)))
    cfg = podar_formatos(cfg, sobran or set())
    return {"name": tool["name"], "type": tool["type"],
            "description": s(tool.get("description") or ""),
            "isActive": True, "config": cfg, "behaviors": tool.get("behaviors") or {}}


def rastro(texto: str, origen: dict) -> list[str]:
    """Qué quedó de la marca de origen en un texto ya sustituido."""
    return [k for k in ("ref", "clave", "nombre") if origen[k] in texto]


def revisar_ficha(ficha: dict) -> list[str]:
    """Qué tiene mal el `marca.json` de una marca. Vacío si está bien.

    El `marca.json` lo escribe una persona, y el motor lee sus campos mucho
    después: un campo con la forma equivocada no se nota al dar de alta sino
    en el primer pedido de verdad, cuatro minutos tarde y con un mensaje que
    no nombra ni la marca ni el campo.

    Pasó el 2/9/2026 con Asistime: `sedes` escrito como lista `["Todas"]` en
    vez de diccionario. Perfectamente razonable de leer, y el diseño murió con
    «'list' object has no attribute 'get'».

    Se revisa sólo la FORMA de lo que el motor va a leer sin preguntar. Lo que
    falte y sea opcional no se nombra: esto avisa de lo que rompe, no de lo
    que podría estar más completo.
    """
    problemas = []

    sedes = ficha.get("sedes")
    if sedes is not None and not isinstance(sedes, dict):
        problemas.append(
            f"`sedes` es {type(sedes).__name__} y tiene que ser un diccionario "
            f"`nombre → {{contacto, acento}}`. Una marca sin locales igual "
            f'tiene una sede: {{"Todas": {{"contacto": "…", "acento": "…"}}}}')
    elif isinstance(sedes, dict):
        for nombre, datos in sedes.items():
            if not isinstance(datos, dict):
                problemas.append(
                    f"la sede «{nombre}» es {type(datos).__name__} y tiene que "
                    f"ser un diccionario con `contacto` y `acento`")
        por_defecto = ficha.get("sede_por_defecto")
        if por_defecto and por_defecto not in sedes:
            problemas.append(
                f"`sede_por_defecto` dice «{por_defecto}» y esa sede no está "
                f"en `sedes`. Tiene: {', '.join(sedes) or 'ninguna'}")

    for campo in ("fotos", "asistime", "reels", "identidad"):
        v = ficha.get(campo)
        if v is not None and not isinstance(v, dict):
            problemas.append(f"`{campo}` es {type(v).__name__} y tiene que ser "
                             f"un diccionario")

    return problemas


def prompt_para(ficha: dict, contratos: dict) -> str:
    """El prompt del agente diseñador, con lo propio de esta marca adentro."""
    base = (RAIZ / "alta" / "prompt-disenador.md").read_text(encoding="utf-8")
    nombre = ficha["nombre"]
    filas = "\n".join(f"| {c.get('descripcion') or c['id']} | `{c['id']}` |"
                      for c in contratos.values())
    tabla = ("| Lo que manda en la pieza | Plantilla |\n|---|---|\n" + filas) if filas \
        else "Las que diga el catálogo."
    cuidados = (ficha.get("cuidados") or "").strip()
    if cuidados:
        cuidados = "---\n\n## Cuidados propios de esta cuenta\n\n" + cuidados
    reemplazos = {
        "{{NOMBRE}}": nombre,
        "{{QUIEN_ES}}": (ficha.get("quien_es") or "").strip(),
        "{{CUIDADOS}}": cuidados,
        "{{PLANTILLAS}}": tabla,
        "{{COMO_HABLA}}": (ficha.get("como_habla") or
                           "Voseo rioplatense, frases cortas, directo y cálido. Sin "
                           "solemnidad. No uses viñetas para contestar algo que "
                           "entra en dos renglones.").strip(),
    }
    for k, v in reemplazos.items():
        base = base.replace(k, v)
    sobran = re.findall(r"\{\{[A-Z_]+\}\}", base)
    if sobran:
        raise SystemExit(f"el prompt quedó con marcadores sin llenar: {sobran}")
    return base


def clave_nueva() -> str:
    """64 hex, como las que ya usan las tres marcas."""
    return secrets.token_hex(32)


def plan(marca: str, estado: dict) -> list[tuple[str, str]]:
    """Qué paso está hecho y cuál falta, para mostrarlo antes de correr."""
    return [(p, "hecho" if estado.get(p) else "falta") for p in PASOS]


# ═══ Con red ══════════════════════════════════════════════════════════════

class Alta:
    def __init__(self, marca: str, simular: bool):
        self.marca = marca
        self.simular = simular
        self.carpeta = RAIZ / ".claude/skills" / marca
        if not self.carpeta.is_dir():
            raise SystemExit(f"no existe .claude/skills/{marca}")
        self.ficha = json.loads((self.carpeta / "marca.json").read_text(encoding="utf-8"))
        self.archivo_estado = self.carpeta / "alta.json"
        self.estado = json.loads(self.archivo_estado.read_text()) if self.archivo_estado.exists() else {}
        self.nombre = self.ficha.get("nombre") or marca
        self.slug = self.ficha.get("slug") or re.sub(r"[^a-z0-9]+", "-", marca.lower()).strip("-")

    # ── plomería ────────────────────────────────────────────────────────
    def guardar(self, paso: str, datos: dict | None = None):
        self.estado[paso] = datos or {"ok": True}
        if not self.simular:
            self.archivo_estado.write_text(json.dumps(self.estado, indent=1, ensure_ascii=False) + "\n")

    def _token(self, variable: str) -> str:
        v = (os.environ.get(variable) or "").strip()
        if not v and not self.simular:
            raise SystemExit(f"falta {variable} en el entorno")
        return v

    def _supabase(self, metodo, ruta, **kw):
        import requests
        cab = {"Authorization": f"Bearer {self._token('SUPABASE_ACCESS_TOKEN')}",
               "Content-Type": "application/json"}
        r = requests.request(metodo, f"{SUPABASE_API}{ruta}", headers=cab, timeout=120, **kw)
        if r.status_code >= 300:
            raise SystemExit(f"Supabase {metodo} {ruta} → {r.status_code}: {r.text[:400]}")
        return r.json() if r.text else {}

    def _asistime(self, metodo, ruta, **kw):
        import requests
        cab = {"X-API-KEY": self._token("ASISTIME_ADMIN_CLAVE"), "Content-Type": "application/json"}
        r = requests.request(metodo, f"{ASISTIME_API}/api{ruta}", headers=cab, timeout=60, **kw)
        if r.status_code >= 300:
            raise SystemExit(f"Asistime {metodo} {ruta} → {r.status_code}: {r.text[:400]}")
        return r.json() if r.text else {}

    def decir(self, texto):
        print(("   (simulo) " if self.simular else "   ") + texto)

    # ── los pasos ───────────────────────────────────────────────────────
    def verificar(self):
        from motor import contrato, identidad
        m = identidad.cargar(self.carpeta / "marca.py")
        contrato.verificar(m)
        n = len(m.PLANTILLAS)
        if not n:
            raise SystemExit("la marca no tiene ninguna plantilla en plantillas/")
        malos = revisar_ficha(self.ficha)
        if malos:
            raise SystemExit(
                f"el marca.json de «{self.marca}» tiene la forma equivocada:\n  · "
                + "\n  · ".join(malos))
        self.decir(f"«{self.nombre}» carga: {n} plantilla(s), {len(m.C)} colores")
        self.guardar("verificar", {"plantillas": sorted(m.PLANTILLAS)})

    def supabase_proyecto(self):
        self.decir(f"crear el proyecto de Supabase «{self.marca}» en {REGION}")
        if self.simular:
            return
        r = self._supabase("POST", "/projects", json={
            "name": self.marca, "organization_id": ORGANIZACION,
            "region": REGION, "plan": "free", "db_pass": secrets.token_urlsafe(24)})
        ref = r["id"]
        for _ in range(60):                       # hasta 10 minutos
            estado = self._supabase("GET", f"/projects/{ref}").get("status")
            if estado == "ACTIVE_HEALTHY":
                break
            time.sleep(10)
        else:
            raise SystemExit(f"el proyecto {ref} no terminó de crearse")
        claves = {k["name"]: k["api_key"] for k in self._supabase("GET", f"/projects/{ref}/api-keys")}
        self.guardar("supabase_proyecto", {"ref": ref, "url": f"https://{ref}.supabase.co",
                                           "service_role": claves["service_role"],
                                           "anon": claves.get("anon", "")})

    def supabase_tablas(self):
        ref = self.estado.get("supabase_proyecto", {}).get("ref", "<ref>")
        for archivo in SQL_EN_ORDEN:
            self.decir(f"correr {archivo} en {ref}")
            if not self.simular:
                sql = (RAIZ / archivo).read_text(encoding="utf-8")
                self._supabase("POST", f"/projects/{ref}/database/query", json={"query": sql})
        self.guardar("supabase_tablas", {"sql": list(SQL_EN_ORDEN)})

    def supabase_funciones(self):
        ref = self.estado.get("supabase_proyecto", {}).get("ref", "<ref>")
        enlaces = RAIZ / "supabase/functions"
        for f in FUNCIONES:
            self.decir(f"npx supabase functions deploy {f} --project-ref {ref} --no-verify-jwt")
            if self.simular:
                continue
            enlaces.mkdir(parents=True, exist_ok=True)
            destino = enlaces / f
            if not destino.exists():
                destino.symlink_to(RAIZ / "funciones" / f)
            r = subprocess.run(["npx", "supabase", "functions", "deploy", f,
                                "--project-ref", ref, "--no-verify-jwt"],
                               cwd=RAIZ, capture_output=True, text=True)
            if r.returncode:
                raise SystemExit(f"no pude desplegar {f}:\n{r.stderr[-800:]}")
        self.guardar("supabase_funciones", {"funciones": list(FUNCIONES)})

    def supabase_secretos(self):
        ref = self.estado.get("supabase_proyecto", {}).get("ref", "<ref>")
        clave = self.estado.get("supabase_secretos", {}).get("api_clave") or clave_nueva()
        self.decir(f"API_CLAVE (…{clave[-4:]}) como secreto de las funciones de {ref}")
        if not self.simular:
            self._supabase("POST", f"/projects/{ref}/secrets",
                           json=[{"name": "API_CLAVE", "value": clave}])
        self.guardar("supabase_secretos", {"api_clave": clave})

    def _tenant_existente(self) -> int | None:
        """El tenant de esta marca, si ya está en Asistime.

        Se busca —y no se crea de una— porque **lo normal es que ya exista**.
        Boss, Clínica y Stadium eran clientes de Asistime antes de ser clientes
        de diseño, y el tenant de Asistime mismo es el número 1. Crear uno
        nuevo con el mismo nombre partiría al cliente en dos: sus
        conversaciones de un lado y su diseñador del otro.

        Primero se mira lo que diga el `marca.json`; si no dice nada, se busca
        por slug en la lista, que viene paginada.
        """
        puesto = (self.ficha.get("asistime") or {}).get("tenant")
        if puesto:
            return int(puesto)
        pagina = 1
        while True:
            r = self._asistime("GET", f"/admin/tenants?page={pagina}&pageSize=100")
            for t in r.get("data", []):
                if t.get("slug") == self.slug or (t.get("name") or "").strip().lower() == self.nombre.strip().lower():
                    return t["id"]
            meta = r.get("meta") or {}
            if pagina >= (meta.get("totalPages") or 1):
                return None
            pagina += 1

    def asistime_tenant(self):
        if self.simular:
            self.decir(f"buscar el tenant de «{self.nombre}» ({self.slug}); si no está, crearlo")
            self.decir("y en cualquier caso, su aplicación «Estudio de diseño» y una clave para el worker")
            return
        t = self._tenant_existente()
        if t:
            self.decir(f"«{self.nombre}» ya es el tenant {t} en Asistime: lo reuso, no creo otro")
        else:
            t = self._asistime("POST", "/admin/tenants",
                               json={"name": self.nombre, "slug": self.slug})["id"]
            self.decir(f"tenant {t} creado")
        # La aplicación y la clave son SIEMPRE nuevas, aunque el tenant sea
        # viejo: es la credencial con la que el worker lee el manual de esta
        # marca, y tiene que poder revocarse sin tocar nada más del cliente.
        app = self._asistime("POST", f"/tenants/{t}/applications",
                             json={"name": "Estudio de diseño",
                                   "description": "El worker lee el manual de marca y publica el catálogo"})
        k = self._asistime("POST", f"/tenants/{t}/applications/{app['id']}/api-keys",
                           json={"name": "worker"})
        self.decir(f"aplicación {app['id']} y clave …{k['plainKey'][-4:]}")
        self.guardar("asistime_tenant", {"tenant": t, "aplicacion": app["id"],
                                         "clave": k["plainKey"], "reusado": bool(self.ficha.get("asistime", {}).get("tenant"))})

    def asistime_agente(self):
        from motor import identidad
        t = self.estado.get("asistime_tenant", {}).get("tenant", "<tenant>")
        m = identidad.cargar(self.carpeta / "marca.py")
        contratos = {pid: fn.contrato for pid, fn in m.PLANTILLAS.items()}
        prompt = prompt_para(self.ficha, contratos)
        self.decir(f"agente «Diseñador {self.nombre}» en el tenant {t}, prompt de {len(prompt)} caracteres, publicado")
        if self.simular:
            return
        a = self._asistime("POST", f"/tenants/{t}/agents", json={
            "name": f"Diseñador {self.nombre}",
            "description": f"Diseña, edita fotos, genera y monta video y publica para {self.nombre}.",
            "aiModelId": 100, "color": m.C[m.ACENTO_POR_DEFECTO],
            "avatarSeed": f"Diseñador {self.nombre}", "sex": "male"})
        v = self._asistime("POST", f"/tenants/{t}/agents/{a['id']}/prompt-versions",
                           json={"systemPrompt": prompt, "versionLabel": "Alta"})
        self._asistime("POST", f"/tenants/{t}/agents/{a['id']}/prompt-versions/{v['id']}/publish")
        self.guardar("asistime_agente", {"agente": a["id"], "prompt_version": v["id"]})

    def _documento(self, t, nombre, descripcion, contenido):
        d = self._asistime("POST", f"/tenants/{t}/documents",
                           json={"name": nombre, "description": descripcion, "type": "text", "isActive": True})
        v = self._asistime("POST", f"/tenants/{t}/documents/{d['id']}/versions",
                           json={"content": contenido, "versionLabel": "Alta"})
        self._asistime("POST", f"/tenants/{t}/documents/{d['id']}/versions/{v['id']}/publish")
        return d["id"]

    def asistime_documentos(self):
        from motor import identidad
        t = self.estado.get("asistime_tenant", {}).get("tenant", "<tenant>")
        a = self.estado.get("asistime_agente", {}).get("agente", "<agente>")
        m = identidad.cargar(self.carpeta / "marca.py")
        reglas = (self.ficha.get("reglas") or "").strip() or (
            f"# Reglas de marca de {self.nombre}\n\nEste documento lo edita {self.nombre}. "
            "Lo que se escriba acá manda sobre el resto: precios vigentes, qué campaña "
            "corre, cómo se escribe, qué no se dice.\n")
        self.decir(f"dos documentos en el tenant {t}: «Reglas de marca» y «Catálogo de plantillas», enganchados al agente {a}")
        if self.simular:
            return
        doc = self._documento(t, "Reglas de marca", f"El criterio de {self.nombre}; lo edita la marca", reglas)
        cat = self._documento(t, "Catálogo de plantillas", "Lo genera el motor; no se edita a mano", m.CATALOGO())
        self._asistime("PUT", f"/tenants/{t}/agents/{a}/documents", json={"documentIds": [doc, cat]})
        # Lo que el worker y publicar-catalogo.py leen de marca.json. Se FUSIONA
        # con lo que ya hubiera: el bloque puede traer el `tenant` puesto a
        # mano —es como se le dice al alta que reuse uno— y pisarlo entero
        # borraría justamente ese dato.
        self.ficha["asistime"] = {
            **(self.ficha.get("asistime") or {}),
            "tenant": t, "documento": doc, "catalogo": cat,
            "clave_env": f"ASISTIME_CLAVE_{re.sub(r'[^A-Z0-9]', '_', self.marca.upper())}"}
        (self.carpeta / "marca.json").write_text(json.dumps(self.ficha, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.guardar("asistime_documentos", {"documento": doc, "catalogo": cat})

    def asistime_herramientas(self):
        t = self.estado.get("asistime_tenant", {}).get("tenant", "<tenant>")
        a = self.estado.get("asistime_agente", {}).get("agente", "<agente>")
        destino = {"ref": self.estado.get("supabase_proyecto", {}).get("ref", "<ref>"),
                   "clave": self.estado.get("supabase_secretos", {}).get("api_clave", "<clave>"),
                   "nombre": self.nombre}
        self.decir(f"copiar las tools del agente {REFERENCIA['agente']} de {REFERENCIA['nombre']} al tenant {t}, y engancharlas al agente {a}")
        if self.simular:
            return
        from motor import identidad
        sobran = formatos_de(identidad.cargar(self.carpeta / "marca.py"))
        if sobran:
            self.decir(f"  (sin {', '.join(sorted(sobran))}: esta marca no los sabe hacer)")
        # Este GET lee el tenant de la marca de REFERENCIA, no el de la nueva.
        # Una clave de Asistime está atada a UN tenant, así que la clave del
        # cliente nuevo no sirve acá: contesta 403 «Cannot operate in this
        # tenant», que no dice en ningún lado que el problema es de qué tenant
        # es la clave. Pasó el 2/9/2026 con Asistime.
        try:
            origen = self._asistime(
                "GET", f"/tenants/{REFERENCIA['tenant']}/agents/{REFERENCIA['agente']}/tools")
        except SystemExit as e:
            if "403" not in str(e):
                raise
            raise SystemExit(
                f"ASISTIME_ADMIN_CLAVE no puede leer el tenant "
                f"{REFERENCIA['tenant']} ({REFERENCIA['nombre']}), que es de "
                f"donde se copian las herramientas.\n"
                f"Una clave de Asistime vale para UN tenant. Para este paso "
                f"hace falta una que vea los dos: el de {REFERENCIA['nombre']} "
                f"y el de «{self.nombre}».\n"
                f"Si no la tenés, las herramientas se escriben a mano en el "
                f"panel del tenant nuevo — sale mejor, porque una copia "
                f"arrastra frases de la otra marca que quedan falsas.") from e
        ids = []
        for tool in origen:
            nueva = sustituir_tool(tool, REFERENCIA, destino, sobran)
            queda = rastro(json.dumps(nueva, ensure_ascii=False), REFERENCIA)
            if queda:
                raise SystemExit(f"la tool {tool['name']} quedó con {queda} de {REFERENCIA['nombre']}")
            creada = self._asistime("POST", f"/tenants/{t}/tools", json=nueva)
            ids.append(creada["id"])
            self.decir(f"  · {tool['name']} → {creada['id']}")
        self._asistime("PUT", f"/tenants/{t}/agents/{a}/tools", json={"toolIds": ids})
        self.guardar("asistime_herramientas", {"tools": ids})

    def registro(self):
        sp = self.estado.get("supabase_proyecto", {})
        self.decir(f"sumar «{self.marca}» al registro clientes-registro (url {sp.get('url', '<url>')})")
        if self.simular:
            return
        import importlib.util
        spec = importlib.util.spec_from_file_location("registro_cli", pathlib.Path(__file__).with_name("registro.py"))
        reg = importlib.util.module_from_spec(spec); spec.loader.exec_module(reg)
        nuevo = {"marca": self.marca, "nombre": self.nombre, "url": sp["url"],
                 "service_role": sp["service_role"],
                 "asistime_clave": self.estado["asistime_tenant"]["clave"], "bucket": "disenos"}
        reg.subir(reg.sumar(reg.bajar(), nuevo))
        self.guardar("registro")

    def plantillas(self):
        sp = self.estado.get("supabase_proyecto", {})
        self.decir(f"sembrar las plantillas en {sp.get('ref', '<ref>')} y publicar el catálogo")
        if self.simular:
            return
        env = dict(os.environ)
        env["CLIENTES_REGISTRO"] = json.dumps({"clientes": [{
            "marca": self.marca, "nombre": self.nombre, "url": sp["url"],
            "service_role": sp["service_role"],
            "asistime_clave": self.estado["asistime_tenant"]["clave"]}]})
        env[self.ficha["asistime"]["clave_env"]] = self.estado["asistime_tenant"]["clave"]
        for orden in (["python3", "herramientas/sembrar-plantillas.py", self.marca],
                      ["python3", "herramientas/publicar-catalogo.py", self.marca]):
            r = subprocess.run(orden, cwd=RAIZ, env=env, capture_output=True, text=True)
            print(r.stdout.strip())
            if r.returncode:
                raise SystemExit(f"{' '.join(orden[1:])} falló:\n{r.stderr[-600:]}")
        self.guardar("plantillas")

    def resumen(self):
        sp = self.estado.get("supabase_proyecto", {})
        at = self.estado.get("asistime_tenant", {})
        ag = self.estado.get("asistime_agente", {})
        print(f"""
✓ «{self.nombre}» está dado de alta.

   Supabase   {sp.get('url', '—')}
   Asistime   tenant {at.get('tenant', '—')} · agente {ag.get('agente', '—')}
   Registro   el worker lo ve en la próxima corrida

Lo que queda, y es de una persona:

   1. ./desplegar-chat.sh — la carpeta de la marca tiene que estar en la imagen.
   2. Conectar Instagram en la app de Meta y cargar el token en `cuentas_ig`
      (skill asistime-conectar-instagram). Hasta entonces `publicar` contesta
      409 y no rompe nada.
   3. Catalogar el banco de fotos, mirándolas (motor/ALTA-DE-MARCA.md, paso 3).
   4. Un pedido de prueba por el chat, y mirar la pieza.
""")
        self.guardar("resumen")

    # ── correr ──────────────────────────────────────────────────────────
    def correr(self, desde: str | None):
        print(f"\n■ Alta de «{self.nombre}» ({self.marca}){' — SIMULACIÓN' if self.simular else ''}\n")
        for paso, estado in plan(self.marca, self.estado):
            print(f"   {'✓' if estado == 'hecho' else '·'} {paso}")
        print()
        empezar = PASOS.index(desde) if desde else 0
        for i, paso in enumerate(PASOS):
            if i < empezar:
                continue
            if self.estado.get(paso) and paso != "resumen" and not self.simular:
                continue
            print(f"▸ {paso}")
            getattr(self, paso)()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); sys.exit(1)
    desde = None
    if "--desde" in sys.argv:
        desde = sys.argv[sys.argv.index("--desde") + 1]
        if desde not in PASOS:
            raise SystemExit(f"«{desde}» no es un paso. Son: {', '.join(PASOS)}")
    Alta(args[0], simular="--simular" in sys.argv).correr(desde)
