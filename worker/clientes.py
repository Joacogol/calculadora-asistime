# -*- coding: utf-8 -*-
"""Lee `clientes.json` y le da al script de despliegue lo que necesita.

Existe para que `desplegar-chat.sh` no tenga que armar JSON con comillas dentro
de comillas dentro de un heredoc, que es la clase de cosa que funciona hasta que
un cliente tiene una tilde en el nombre.

    python3 clientes.py marcas      → boss-padel-disenos clinica-preventiva-disenos
    python3 clientes.py secretos    → supabase-key-boss supabase-key-clinica
    python3 clientes.py json        → el valor de la variable CLIENTES
    python3 clientes.py run-secrets → SUPABASE_KEY_BOSS=supabase-key-boss:latest,...

Y lo mismo para las claves de Asistime, que también son una por cliente:

    python3 clientes.py asistime          → una línea «marca variable secreto» por cliente
    python3 clientes.py asistime-secretos → asistime-api-boss asistime-api-clinica
    python3 clientes.py asistime-run-secrets → ASISTIME_CLAVE=asistime-api-boss:latest,…

Los clientes sin URL cargada se ignoran en `json` y en `run-secrets`: así se
puede dejar un cliente a medio dar de alta en el archivo sin que rompa el
despliegue de los que ya andan.

## Por qué la clave de Asistime sale de `marca.json` y no de acá

Porque el nombre de la variable ya vivía ahí —lo lee `app/manual.py` en cada
corrida— y tenerlo en dos archivos es garantizar que algún día digan cosas
distintas. `clientes.json` sigue siendo la lista de clientes; qué documento y
qué clave usa cada marca es un dato de la marca.
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent


def todos():
    datos = json.loads((RAIZ / "clientes.json").read_text(encoding="utf-8"))
    return datos["clientes"]


def listos():
    return [c for c in todos()
            if c.get("url") and not c["url"].startswith("PONER-")]


def asistime():
    """`(marca, variable, secreto)` de cada cliente que declara su clave.

    Sale del `marca.json` de cada skill. Una marca que no la declare queda
    afuera y su manual no se lee — que es preferible a mandarle la clave de
    otro cliente: eso da 403, un error que se lee como «no tenés permiso» y
    manda a buscar el problema donde no está.
    """
    salida = []
    for c in listos():
        ruta = RAIZ / ".claude" / "skills" / c["marca"] / "marca.json"
        try:
            ficha = json.loads(ruta.read_text(encoding="utf-8")).get("asistime") or {}
        except Exception:
            continue
        env, sec = ficha.get("clave_env"), ficha.get("clave_secreto")
        if env and sec:
            salida.append((c["marca"], env, sec))
    return salida


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else "marcas"
    if orden == "marcas":
        print(" ".join(c["marca"] for c in listos()))
    elif orden == "secretos":
        print(" ".join(c["secreto"] for c in listos()))
    elif orden == "json":
        print(json.dumps(
            [{"marca": c["marca"], "nombre": c["nombre"],
              "url": c["url"], "key_env": c["key_env"]} for c in listos()],
            ensure_ascii=False, separators=(",", ":")))
    elif orden == "run-secrets":
        print(",".join(f"{c['key_env']}={c['secreto']}:latest" for c in listos()))
    elif orden == "asistime":
        for marca, env, sec in asistime():
            print(f"{marca} {env} {sec}")
    elif orden == "asistime-secretos":
        print(" ".join(sec for _, _, sec in asistime()))
    elif orden == "asistime-run-secrets":
        print(",".join(f"{env}={sec}:latest" for _, env, sec in asistime()))
    elif orden == "faltantes":
        f = [c["marca"] for c in todos() if c not in listos()]
        print(" ".join(f))
    else:
        print(__doc__)
        sys.exit(1)
