"""Adaptador de modelo-unico-16-2: la terminal es interactiva, con una sola operación.

La herramienta pide monto, plazo, tasa y si guarda el CSV. El adaptador le entrega esas respuestas
por la entrada estándar, dentro del mismo proceso, y responde «n» a guardar.
"""

import io
import sys
from decimal import Decimal

from vivienda.calculo import calcular, guardar_csv
from vivienda.cli import main


def _resultado(monto: int, plazo_meses: int, tasa: Decimal) -> object:
    return calcular(str(monto), str(plazo_meses), str(tasa))


def cuota(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> int:
    return _resultado(monto, plazo_meses, tasa_efectiva_anual).cuota_mensual


def tabla(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal
) -> list[tuple[int, int, int, int]]:
    filas = _resultado(monto, plazo_meses, tasa_efectiva_anual).tabla
    return [(f.cuota, f.interes, f.abono_capital, f.saldo) for f in filas]


def resumen(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> tuple[int, int]:
    r = _resultado(monto, plazo_meses, tasa_efectiva_anual)
    return r.total_pagado, r.total_intereses


def guardar_tabla_csv(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal, ruta: str
) -> None:
    guardar_csv(_resultado(monto, plazo_meses, tasa_efectiva_anual), ruta)


def codigo_de_salida(
    operacion: str, monto: str, plazo_meses: str, tasa_efectiva_anual: str
) -> int:
    entrada = sys.stdin
    sys.stdin = io.StringIO(f"{monto}\n{plazo_meses}\n{tasa_efectiva_anual}\nn\n")
    try:
        return main()
    except SystemExit as salida:
        return int(salida.code or 0)
    finally:
        sys.stdin = entrada
