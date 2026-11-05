"""Adaptador de modelo-unico-16-1: dominio para los cálculos y `cli.main` para la terminal."""

from decimal import Decimal

from vivienda.calculo import amortizacion, crear_credito, cuota_mensual
from vivienda.calculo import resumen as _resumen
from vivienda.cli import main


def cuota(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> int:
    return cuota_mensual(crear_credito(monto, plazo_meses, tasa_efectiva_anual))


def tabla(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal
) -> list[tuple[int, int, int, int]]:
    filas = amortizacion(crear_credito(monto, plazo_meses, tasa_efectiva_anual))
    return [(f.cuota, f.interes, f.capital, f.saldo) for f in filas]


def resumen(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> tuple[int, int]:
    r = _resumen(crear_credito(monto, plazo_meses, tasa_efectiva_anual))
    return r.total_pagado, r.total_intereses


def guardar_tabla_csv(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal, ruta: str
) -> None:
    argumentos = [
        "tabla",
        "--monto",
        str(monto),
        "--plazo",
        str(plazo_meses),
        "--tasa",
        str(tasa_efectiva_anual),
        "--csv",
        ruta,
    ]
    if main(argumentos) != 0:
        raise ValueError("La herramienta no guardó el CSV.")


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
