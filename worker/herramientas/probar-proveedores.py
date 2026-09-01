#!/usr/bin/env python3
"""Prueba que los dos proveedores de video no se mezclen ni se pisen.

    python3 herramientas/probar-proveedores.py

## Por qué existe

Desde el 1/9/2026 hay dos proveedores para generar un video: Magnific, que
cobra en **créditos**, y fal.ai, que cobra en **dólares**. No hay tipo de
cambio entre los dos, y **no debe haberlo inventado nadie**: el día que alguien
ponga una equivalencia a ojo para poder compararlos en un solo número, el tope
de gasto va a proteger a uno y mentir sobre el otro sin que se note.

Esta prueba fija esa frontera. No toca ninguna API: sólo mira las tablas y la
función que decide el plan, que es donde se decide la plata.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import reelero as R                                 # noqa: E402


def main() -> int:
    fallas = []

    # ── 1 · cada modelo declara proveedor y moneda ────────────────────────
    for nombre, m in R.MODELOS.items():
        if not m.get("proveedor") or not m.get("moneda"):
            fallas.append(f"✗ el modelo «{nombre}» no dice de qué proveedor es "
                          f"ni en qué moneda cobra.")
    if not fallas:
        print(f"✓ los {len(R.MODELOS)} modelos declaran proveedor y moneda")

    # ── 2 · un plan NUNCA sale de un proveedor distinto al pedido ─────────
    #
    # Es lo que impide que un pedido a fal se resuelva con un modelo de
    # Magnific porque «entraba mejor en el tope»: son topes distintos, en
    # monedas distintas, y elegir entre ellos no significa nada.
    for prov in R.CALIDADES:
        for calidad in ("borrador", "normal", "maxima"):
            plan, _ = R._plan(calidad, 5, 10_000.0, prov)
            if not plan:
                fallas.append(f"✗ {prov}/{calidad}: no hay ningún plan ni con "
                              f"un tope enorme.")
                continue
            if plan["proveedor"] != prov:
                fallas.append(
                    f"✗ se pidió {prov} en calidad {calidad} y el plan salió "
                    f"con {plan['proveedor']} ({plan['modelo']}).")
    if not any(f.startswith("✗ se pidió") for f in fallas):
        print("✓ un plan nunca cambia de proveedor por su cuenta")

    # ── 3 · el tope frena, y frena en la moneda correcta ─────────────────
    #
    # Un dólar de tope contra un modelo que cobra dólares: entra. El MISMO
    # número contra Magnific, que cobra créditos, no paga ni el más barato.
    # Si esto no distinguiera, un tope pensado en dólares dejaría pasar miles
    # de créditos.
    caro, _ = R._plan("normal", 5, 1.0, "magnific")
    if caro is not None:
        fallas.append(
            f"✗ con un tope de 1 (créditos) Magnific devolvió un plan de "
            f"{caro['creditos']}: el tope no está frenando nada.")
    else:
        print("✓ un tope de 1 crédito no paga ningún reel de Magnific")

    barato, _ = R._plan("normal", 5, 1.0, "fal")
    if barato is None:
        fallas.append("✗ con un tope de US$1 fal no devolvió ningún plan, y "
                      "cinco segundos a 768p salen US$0,40.")
    elif barato["moneda"] != "usd":
        fallas.append(f"✗ el plan de fal dice cobrar en «{barato['moneda']}».")
    else:
        print(f"✓ US$1 de tope paga un reel de fal "
              f"({barato['duracion']}s = {R.plata(barato['creditos'], 'usd')})")

    # ── 4 · el precio de fal es el de LISTA, no el promocional ───────────
    #
    # fal lanzó H3 Max con 75% de descuento hasta el 7/9/2026. Si la tabla
    # guardara el precio promocional, a partir del 8 cada video costaría cuatro
    # veces lo que el tope cree — y el tope es lo único que hay entre un bucle
    # y la tarjeta.
    if R.MODELOS["h3-max"]["precio"]["768p"] < 0.08:
        fallas.append(
            "✗ el precio de h3-max a 768p está por debajo de US$0,08 el "
            "segundo: eso es la promo de lanzamiento, no el precio.")
    else:
        print("✓ h3-max está cargado al precio de lista, no al promocional")

    # ── 5 · y las duraciones son las medidas, no las supuestas ───────────
    if R.MODELOS["h3-max"]["duraciones"] != (5,):
        print("  (h3-max declara más de 5s: espero que se haya medido contra "
              "la API y no supuesto)")

    if fallas:
        print("\n" + "\n".join(fallas))
        return 1
    print("\nproveedores OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
