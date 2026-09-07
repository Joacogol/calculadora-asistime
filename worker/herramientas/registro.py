#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""El registro de clientes en Secret Manager: crearlo, ver, sumar, quitar.

    python3 herramientas/registro.py crear       # desde clientes.json + los secretos que ya hay
    python3 herramientas/registro.py ver         # las marcas y qué tienen, sin claves
    python3 herramientas/registro.py marcas      # sólo los nombres, para el script de despliegue
    python3 herramientas/registro.py agregar     # pregunta los datos; las claves sin eco
    python3 herramientas/registro.py quitar <marca>

Corre donde haya `gcloud` con sesión —Cloud Shell—, porque el registro es un
secreto y sólo ahí se puede leer y escribir. Todo lo que no toca `gcloud` está
separado en funciones puras, y eso es lo que prueba `probar-registro.py`.

── Por qué un secreto y no una tabla ─────────────────────────────────────

Porque adentro van las `service_role` de cada cliente, y ésas no pueden vivir
en ninguna base de ningún cliente. Secret Manager ya tenía una por cliente;
esto las junta en una y le agrega el nombre y la URL al lado, que es lo que
hacía falta para que sumar un cliente sea escribir una versión nueva y nada
más. Cloud Run monta `latest` en cada arranque, y el worker arranca cada
minuto.

Cada versión queda guardada: si un alta sale mal, `gcloud secrets versions
list clientes-registro` muestra las anteriores y se vuelve atrás sin adivinar.
"""
from __future__ import annotations

import getpass
import json
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

SECRETO = "clientes-registro"
SA = "worker-boss-padel@boss-padel-disenos.iam.gserviceaccount.com"


# ── Puro: sin gcloud ───────────────────────────────────────────────────────

def armar(clientes: list[dict]) -> str:
    """El JSON del registro, listo para subir. Valida con el mismo código que
    lo lee el worker, así lo que se sube es lo que va a andar."""
    from app import registro
    texto = json.dumps({"clientes": clientes}, ensure_ascii=False, indent=1)
    registro.leer(texto)                     # levanta RegistroInvalido si está mal
    return texto


def enmascarar(clave: str) -> str:
    """Lo único de una clave que se puede mostrar: cuánto mide y cómo termina."""
    c = (clave or "").strip()
    if not c:
        return "—"
    return f"…{c[-4:]} ({len(c)} caracteres)"


def clave_de(marca: str) -> str:
    """La clave de Asistime de una marca, sacada del registro.

    El worker ya la busca así —`app/manual.py`, primero el registro y después
    la variable de entorno—, pero los scripts que se corren a mano no, y eso
    partió la realidad en dos: el 2/9/2026 el worker atendía cuatro clientes y
    el paso que republica catálogos veía tres, porque miraba `clientes.json` y
    Asistime nunca se agregó ahí. El catálogo de Asistime se quedó viejo sin
    que nada fallara.

    Devuelve "" si no está, o si no hay `gcloud` con sesión: quien llama
    decide si eso es un error.
    """
    try:
        for c in bajar():
            if c["marca"] == marca:
                return (c.get("asistime_clave") or "").strip()
    except Exception:                                        # noqa: BLE001
        pass
    return ""


def tabla(clientes: list[dict]) -> str:
    filas = [f"{'marca':28} {'nombre':20} {'supabase':10} {'asistime':10}"]
    for c in clientes:
        filas.append(f"{c['marca']:28} {c['nombre'][:20]:20} "
                     f"{enmascarar(c.get('service_role', '')):10} "
                     f"{enmascarar(c.get('asistime_clave', '')):10}")
    return "\n".join(filas)


def sumar(clientes: list[dict], nuevo: dict) -> list[dict]:
    """La lista con el cliente nuevo. Si la marca ya estaba, la reemplaza: un
    alta repetida corrige, no duplica."""
    return [c for c in clientes if c["marca"] != nuevo["marca"]] + [nuevo]


def sacar(clientes: list[dict], marca: str) -> list[dict]:
    salida = [c for c in clientes if c["marca"] != marca]
    if len(salida) == len(clientes):
        raise SystemExit(f"«{marca}» no está en el registro")
    return salida


# ── Con gcloud ─────────────────────────────────────────────────────────────

def _gcloud(*args: str, entrada: str | None = None) -> str:
    r = subprocess.run(["gcloud", *args], input=entrada, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"gcloud {' '.join(args[:3])} falló:\n{r.stderr.strip()}")
    return r.stdout


def bajar() -> list[dict]:
    from app import registro
    try:
        crudo = _gcloud("secrets", "versions", "access", "latest", f"--secret={SECRETO}")
    except SystemExit:
        return []
    return [_de_worker(c) for c in (registro.leer(crudo) or [])]


def _de_worker(c: dict) -> dict:
    """Del formato que usa el worker (`key`) al que se guarda (`service_role`)."""
    return {"marca": c["marca"], "nombre": c["nombre"], "url": c["url"],
            "service_role": c["key"], "asistime_clave": c.get("asistime_clave", ""),
            "bucket": c.get("bucket", "disenos")}


def subir(clientes: list[dict]) -> None:
    texto = armar(clientes)
    existe = subprocess.run(["gcloud", "secrets", "describe", SECRETO, "--quiet"],
                            capture_output=True).returncode == 0
    if existe:
        _gcloud("secrets", "versions", "add", SECRETO, "--data-file=-", entrada=texto)
    else:
        _gcloud("secrets", "create", SECRETO, "--data-file=-", "--quiet", entrada=texto)
    _gcloud("secrets", "add-iam-policy-binding", SECRETO,
            f"--member=serviceAccount:{SA}",
            "--role=roles/secretmanager.secretAccessor", "--quiet")
    print(f"✓ {SECRETO}: {len(clientes)} cliente(s). El worker lo ve en la "
          f"próxima corrida (un minuto).")


def crear_desde_clientes_json() -> list[dict]:
    """La primera vez: junta lo que ya está repartido en secretos sueltos."""
    import clientes as cj
    salida = []
    for c in cj.listos():
        service_role = _gcloud("secrets", "versions", "access", "latest",
                               f"--secret={c['secreto']}").strip()
        asistime = ""
        for marca, _env, sec in cj.asistime():
            if marca == c["marca"]:
                asistime = _gcloud("secrets", "versions", "access", "latest",
                                   f"--secret={sec}").strip()
        salida.append({"marca": c["marca"], "nombre": c["nombre"], "url": c["url"],
                       "service_role": service_role, "asistime_clave": asistime,
                       "bucket": "disenos"})
    return salida


def preguntar_nuevo() -> dict:
    print("Un cliente nuevo. Las claves no se ven al escribirlas.")
    marca = input("  marca (carpeta del skill, ej. stadium-disenos): ").strip()
    nombre = input("  nombre para mostrar (ej. Stadium): ").strip()
    url = input("  URL de su Supabase (https://….supabase.co): ").strip()
    service_role = getpass.getpass("  service_role key de su Supabase: ").strip()
    asistime = getpass.getpass("  clave de Asistime de su tenant (Enter si no hay): ").strip()
    return {"marca": marca, "nombre": nombre, "url": url, "service_role": service_role,
            "asistime_clave": asistime, "bucket": "disenos"}


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else "ver"
    if orden == "crear":
        actuales = crear_desde_clientes_json()
        print(tabla(actuales)); subir(actuales)
    elif orden == "ver":
        print(tabla(bajar()))
    elif orden == "marcas":
        print(" ".join(c["marca"] for c in bajar()))
    elif orden == "agregar":
        subir(sumar(bajar(), preguntar_nuevo()))
    elif orden == "quitar":
        subir(sacar(bajar(), sys.argv[2]))
    else:
        print(__doc__); sys.exit(1)
