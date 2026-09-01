#!/usr/bin/env python3
"""¿La tabla de precios de la API dice lo mismo que la del motor?

    python3 herramientas/probar-precios.py

El precio de cada modelo vive en `MODELOS`, en `app/reelero.py`: ahí es donde
se calcula lo que se va a cobrar y donde se comparan los topes. Pero la
función de Supabase también lo necesita —tiene que poder decir en el chat
«esto sale 1.400 créditos» ANTES de encargar nada— y una función de Supabase
no puede leer el Python del worker. Así que hay una copia en `PROVEEDORES`,
dentro de `funciones/api-reels/index.ts`.

Dos copias de un número se separan solas. La forma en que se separan es la
peor posible: nadie se entera. El chat sigue diciendo el precio viejo, la
persona dice que sí creyendo que gasta 1.400, y el cobro es otro. Un precio
que miente es peor que no mostrar ninguno, porque sobre el que miente se
toman decisiones.

Esta prueba no arregla la duplicación: la hace ruidosa. Si tocás un precio en
un lado y no en el otro, esto falla y dice cuál es cuál.

Se corre sola en `desplegar-chat.sh`, antes de subir nada.
"""
import ast
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def del_motor() -> dict:
    """`{proveedor: {calidad: (modelo, resolucion, precio_por_segundo)}}`.

    Se lee con `ast` y no importando el módulo: importar `reelero` arrastra el
    paquete entero —y sus variables de entorno— para leer dos diccionarios.
    """
    arbol = ast.parse((RAIZ / "app" / "reelero.py").read_text())
    asignaciones = {
        getattr(n.targets[0], "id", ""): n.value
        for n in arbol.body if isinstance(n, ast.Assign)
    }
    faltan = {"MODELOS", "CALIDADES"} - set(asignaciones)
    if faltan:
        sys.exit(f"✗ no encontré {', '.join(sorted(faltan))} en app/reelero.py")

    # De `MODELOS` se saca SÓLO el bloque `precio` de cada modelo. El resto de
    # la ficha tiene expresiones —`tuple(range(4, 31))`— que `literal_eval` no
    # evalúa, y con razón: no es un literal. Acá no hace falta.
    precios = {}
    for clave, ficha in zip(asignaciones["MODELOS"].keys,
                            asignaciones["MODELOS"].values):
        for k, v in zip(ficha.keys, ficha.values):
            if getattr(k, "value", None) == "precio":
                precios[clave.value] = ast.literal_eval(v)

    calidades = ast.literal_eval(asignaciones["CALIDADES"])
    return {
        prov: {
            cal: (modelo, res, precios[modelo][res])
            for cal, (modelo, res) in porcalidad.items()
        }
        for prov, porcalidad in calidades.items()
    }


def de_la_api() -> dict:
    """Lo mismo, leído del `PROVEEDORES` de la función de Supabase.

    No se parsea el bloque entero: se buscan sólo las fichas de precio, que
    tienen una forma fija y chiquita. Parsear TypeScript con expresiones
    regulares es una mala idea; buscar tres campos con nombre, dentro de un
    archivo que escribimos nosotros, es otra cosa. Y si la forma cambia, no
    encuentra nada y esto grita — no devuelve una tabla incompleta que pasaría
    la comparación por casualidad.
    """
    ts = (RAIZ / "funciones" / "api-reels" / "index.ts").read_text()
    m = re.search(r"const PROVEEDORES = \{(.*?)\n\} as const;", ts, re.S)
    if not m:
        sys.exit("✗ no encontré `const PROVEEDORES = {...} as const;` en index.ts")
    cuerpo = re.sub(r"//[^\n]*", "", m.group(1))

    # Dónde arranca cada proveedor, para saber a cuál pertenece cada precio.
    arranques = [(x.start(), x.group(1))
                 for x in re.finditer(r"^  (\w+): \{", cuerpo, re.M)]
    if not arranques:
        sys.exit("✗ no reconocí ningún proveedor dentro de PROVEEDORES")

    ficha = re.compile(
        r'(\w+): \{ modelo: "([^"]+)", resolucion: "([^"]+)", '
        r'por_segundo: ([\d.]+) \}')
    tabla: dict = {p: {} for _, p in arranques}
    for x in ficha.finditer(cuerpo):
        prov = [p for pos, p in arranques if pos < x.start()][-1]
        tabla[prov][x.group(1)] = (x.group(2), x.group(3), float(x.group(4)))

    vacios = [p for p, c in tabla.items() if not c]
    if vacios:
        sys.exit(f"✗ no le encontré precios a {', '.join(vacios)} en index.ts")
    return tabla


def main() -> int:
    motor, api = del_motor(), de_la_api()
    problemas = []

    for prov in sorted(set(motor) | set(api)):
        if prov not in api:
            problemas.append(f"el motor conoce «{prov}» y la API no lo ofrece")
            continue
        if prov not in motor:
            problemas.append(f"la API ofrece «{prov}» y el motor no lo sabe generar")
            continue
        for cal in sorted(set(motor[prov]) | set(api[prov])):
            a, b = motor[prov].get(cal), api[prov].get(cal)
            if a != b:
                problemas.append(
                    f"{prov}/{cal}: el motor dice {a} y la API dice {b}")

    for p in problemas:
        print("  ✗", p)
    if problemas:
        print("\n✗ las dos tablas de precios se separaron.\n"
              "  La de verdad es MODELOS/CALIDADES en app/reelero.py: es la que\n"
              "  cobra. La de index.ts es la que se le dice a la persona antes\n"
              "  de gastar. Emparejalas.\n")
        return 1

    for prov in sorted(motor):
        for cal, (mod, res, seg) in sorted(motor[prov].items()):
            moneda = "US$" if prov == "fal" else "créditos"
            print(f"  ✓ {prov}/{cal}: {mod} {res} — {seg} {moneda}/segundo")
    print("\n✓ el precio que se dice es el que se cobra\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
