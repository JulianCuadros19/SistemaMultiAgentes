"""Adaptador de sistema-16-2: subcomandos lógicos, con su código de salida en `ErrorCLI`.

Esta versión no declara un punto de entrada de terminal. Sus subcomandos sí definen el código de
salida de un error, y el adaptador lo devuelve; sin error, el código es cero.
"""

from decimal import Decimal

from comandos.cli import ErrorCLI, ejecutar_cuota, ejecutar_resumen, ejecutar_tabla


def cuota(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> Decimal:
    return ejecutar_cuota(tasa_efectiva_anual, Decimal(monto), plazo_meses)


def tabla(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal
) -> list[tuple[Decimal, Decimal, Decimal, Decimal]]:
    filas = ejecutar_tabla(tasa_efectiva_anual, Decimal(monto), plazo_meses, None)
    return [(f.cuota, f.interes, f.abono_capital, f.saldo_final) for f in filas]


def resumen(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> tuple[Decimal, Decimal]:
    r = ejecutar_resumen(tasa_efectiva_anual, Decimal(monto), plazo_meses)
    return r.total_pagado, r.total_intereses


def guardar_tabla_csv(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal, ruta: str
) -> None:
    ejecutar_tabla(tasa_efectiva_anual, Decimal(monto), plazo_meses, ruta)


def codigo_de_salida(
    operacion: str, monto: str, plazo_meses: str, tasa_efectiva_anual: str
) -> int:
    tasa, capital, plazo = Decimal(tasa_efectiva_anual), Decimal(monto), int(plazo_meses)
    try:
        if operacion == "tabla":
            ejecutar_tabla(tasa, capital, plazo, None)
        elif operacion == "resumen":
            ejecutar_resumen(tasa, capital, plazo)
        else:
            ejecutar_cuota(tasa, capital, plazo)
    except ErrorCLI as error:
        return error.codigo_salida
    return 0
