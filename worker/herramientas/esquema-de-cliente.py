#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""El SQL de un cliente, pero dentro de SU esquema del Supabase compartido.

    python3 herramientas/esquema-de-cliente.py boss-padel-disenos
    python3 herramientas/esquema-de-cliente.py boss-padel-disenos --esquema boss

Escribe en la salida estándar el SQL entero: el esquema, sus tablas, sus
vistas, sus políticas y su bucket. Se aplica una vez por cliente.

── Por qué un esquema y no una columna «cliente» ──────────────────────────

Hasta el 7/9/2026 cada cliente tenía SU PROPIO proyecto de Supabase. La razón
era buena —poder entregarle o venderle su base sin desenredarla de la de otro—
pero se paga un contenedor por cliente, y con cuatro clientes los datos suman
52 MB: se paga por prender la luz, no por lo que hay adentro. Y multiplica el
despliegue: cinco funciones de borde por proyecto, veinte en total, que fue
exactamente cómo tres clientes quedaron con la función vieja sin que nadie se
enterara.

La alternativa habitual —una sola tabla con una columna `cliente` y filtrar en
cada consulta— traslada la separación al código: el día que una consulta se
olvida el filtro, un cliente ve las piezas de otro. Con un esquema por cliente
la separación la hace Postgres, el SQL de cada tabla es el mismo de siempre, y
entregarle a un cliente todo lo suyo sigue siendo un comando (`pg_dump -n`).

Lo que cambia en el código es una cabecera: PostgREST elige el esquema con
`Accept-Profile` (al leer) y `Content-Profile` (al escribir). Ver `app/supa.py`.

── Lo que este script arregla del SQL original ────────────────────────────

1. `public.` pasa a ser el esquema del cliente.
2. `search_path` de las funciones, igual.
3. El bucket deja de llamarse `disenos` para todos: cada cliente tiene el suyo.
4. Las políticas de `storage.objects` llevan el nombre del cliente. Storage es
   UNA tabla compartida por todo el proyecto: dos clientes con una política
   llamada «subir al banco» se pisan, y el segundo alta borra la del primero.
5. **La puerta que sólo existe cuando se comparte proyecto.** Con un proyecto
   por cliente, «cualquiera logueado puede encargar un diseño» era seguro: los
   únicos usuarios eran los de ese cliente. Compartiendo proyecto, todos los
   usuarios de todos los clientes viven en el mismo `auth.users`, así que esa
   misma política deja que el usuario de un cliente encargue piezas —y gaste
   plata— en la base de otro. Por eso cada política de este esquema exige
   además `public.es_de('<marca>')`: que ese usuario esté anotado como suyo.
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent

#: Los archivos que arman un cliente, en orden. `cobro.sql` va último porque
#: sus vistas leen tablas de los anteriores.
ARCHIVOS = ["base-de-un-cliente.sql", "plantillas.sql", "plantilla-pedidos.sql",
            "fotos-editadas.sql", "motor-pedidos.sql", "cobro.sql"]


def esquema_de(marca: str) -> str:
    """`boss-padel-disenos` → `boss_padel`. Un nombre corto y sin guiones."""
    s = re.sub(r"[^a-z0-9]+", "_", marca.lower())
    s = re.sub(r"_?disenos_?$", "", s).strip("_")
    return s or "cliente"


def render(marca: str, esquema: str, bucket: str) -> str:
    partes = [f"""-- Generado por herramientas/esquema-de-cliente.py — no editar a mano.
-- Cliente «{marca}» en el esquema «{esquema}», bucket «{bucket}».
create schema if not exists {esquema};
grant usage on schema {esquema} to anon, authenticated, service_role;
alter default privileges in schema {esquema}
  grant all on tables to anon, authenticated, service_role;
"""]
    for nombre in ARCHIVOS:
        ruta = RAIZ / nombre
        if not ruta.exists():
            raise SystemExit(f"falta {nombre} en {RAIZ}")
        sql = ruta.read_text(encoding="utf-8")

        # 1 y 2. El esquema, en las tablas y en el search_path de las funciones.
        sql = sql.replace("search_path = public", f"search_path = {esquema}")
        sql = sql.replace("public.", f"{esquema}.")

        # 3. El bucket es propio. `auth.users` y `storage.` no se tocan.
        sql = re.sub(r"'disenos'", f"'{bucket}'", sql)

        # 4. Las políticas de storage llevan el nombre del cliente: esa tabla
        #    es una sola para todo el proyecto.
        sql = re.sub(r'(policy if exists |policy )"([^"]+)"( on storage\.objects)',
                     lambda m: f'{m.group(1)}"{m.group(2)} · {esquema}"{m.group(3)}', sql)

        # 5. Nadie encarga nada en la casa de otro.
        sql = re.sub(r"auth\.uid\(\) is not null",
                     f"auth.uid() is not null and public.es_de('{marca}')", sql)
        sql = re.sub(r"auth\.uid\(\) = user_id",
                     f"auth.uid() = user_id and public.es_de('{marca}')", sql)
        partes.append(f"\n-- ═══ {nombre} ═══\n{sql}")
    return "\n".join(partes)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__.strip().splitlines()[0] + "\n\n" +
                         "Uso: python3 herramientas/esquema-de-cliente.py <marca> [--esquema X] [--bucket Y]")
    marca = args[0]
    def opcion(nombre, x):
        if f"--{nombre}" in sys.argv:
            return sys.argv[sys.argv.index(f"--{nombre}") + 1]
        return x
    esquema = opcion("esquema", esquema_de(marca))
    bucket = opcion("bucket", f"disenos-{esquema}".replace("_", "-"))
    print(render(marca, esquema, bucket))


if __name__ == "__main__":
    main()
