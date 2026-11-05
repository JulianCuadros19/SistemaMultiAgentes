"""Adaptador de sistema-16-1: la tasa va como fracción y no hay herramienta de terminal.

La especificación de esta versión no declara punto de entrada ni analizador de argumentos
(`USO.md`), así que el código de salida es un comportamiento ausente.
"""

from decimal import Decimal

from dominio.credito import ParametrosCredito
from entrada_salida.tabla_csv import EscritorTablaCSV
from referencia_comun import Ausente
from servicios.simulacion import calcular_cuota, calcular_resumen, generar_tabla


def _parametros(monto: int, plazo_meses: int, tasa: Decimal) -> ParametrosCredito:
    return ParametrosCredito(Decimal(monto), plazo_meses, Decimal(f"{tasa}E-2"))


def cuota(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> int:
    return calcular_cuota(_parametros(monto, plazo_meses, tasa_efectiva_anual))


def tabla(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal
) -> list[tuple[int, int, int, int]]:
    filas = generar_tabla(_parametros(monto, plazo_meses, tasa_efectiva_anual), None)
    return [(f.cuota, f.interes, f.abono_capital, f.saldo) for f in filas]


def resumen(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> tuple[int, int]:
    r = calcular_resumen(_parametros(monto, plazo_meses, tasa_efectiva_anual))
    return r.total_pagado, r.total_intereses


def guardar_tabla_csv(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal, ruta: str
) -> None:
    generar_tabla(_parametros(monto, plazo_meses, tasa_efectiva_anual), EscritorTablaCSV(ruta))


def codigo_de_salida(
    operacion: str, monto: str, plazo_meses: str, tasa_efectiva_anual: str
) -> int:
    raise Ausente("La versión no ofrece una herramienta de terminal.")
