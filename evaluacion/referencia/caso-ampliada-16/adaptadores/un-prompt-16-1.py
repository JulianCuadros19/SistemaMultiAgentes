"""Adaptador de un-prompt-16-1: los cálculos del dominio y la herramienta de terminal `cli.main`."""

from decimal import Decimal

from credito_vivienda.calculos import (
    calcular_cuota,
    calcular_resumen,
    crear_credito,
    generar_tabla,
    guardar_csv,
)
from credito_vivienda.cli import main


def cuota(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> int:
    return calcular_cuota(crear_credito(monto, plazo_meses, tasa_efectiva_anual))


def tabla(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal
) -> list[tuple[int, int, int, int]]:
    filas = generar_tabla(crear_credito(monto, plazo_meses, tasa_efectiva_anual))
    return [(f.cuota, f.interes, f.abono_capital, f.saldo) for f in filas]


def resumen(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> tuple[int, int]:
    r = calcular_resumen(crear_credito(monto, plazo_meses, tasa_efectiva_anual))
    return r.total_pagado, r.total_intereses


def guardar_tabla_csv(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal, ruta: str
) -> None:
    guardar_csv(generar_tabla(crear_credito(monto, plazo_meses, tasa_efectiva_anual)), ruta)


def codigo_de_salida(
    operacion: str, monto: str, plazo_meses: str, tasa_efectiva_anual: str
) -> int:
    argumentos = [
        operacion,
        "--monto",
        monto,
        "--plazo",
        plazo_meses,
        "--tasa",
        tasa_efectiva_anual,
    ]
    try:
        return main(argumentos)
    except SystemExit as salida:
        return int(salida.code or 0)
