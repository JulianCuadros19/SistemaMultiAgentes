"""Adaptador de modelo-unico-16-3: esta entrega valida los datos, pero no calcula.

Sus funciones de cálculo lanzan `ReglasPendientes` con datos válidos: ese comportamiento está
ausente. Con datos inválidos, el rechazo de la implementación llega tal cual a las pruebas.
"""

from collections.abc import Callable
from decimal import Decimal

from credito_vivienda.cli import main
from credito_vivienda.dominio import (
    ReglasPendientes,
    calcular_cuota,
    calcular_resumen,
    generar_tabla,
    leer_solicitud,
)
from referencia_comun import Ausente


def _calcular(calculo: Callable[..., object], monto: int, plazo: int, tasa: Decimal) -> object:
    solicitud = leer_solicitud(str(monto), str(plazo), str(tasa))
    try:
        return calculo(solicitud)
    except ReglasPendientes as error:
        raise Ausente(str(error)) from error


def cuota(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> int:
    return _calcular(calcular_cuota, monto, plazo_meses, tasa_efectiva_anual)


def tabla(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal
) -> list[tuple[int, int, int, int]]:
    return _calcular(generar_tabla, monto, plazo_meses, tasa_efectiva_anual)


def resumen(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> tuple[int, int]:
    return _calcular(calcular_resumen, monto, plazo_meses, tasa_efectiva_anual)


def guardar_tabla_csv(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal, ruta: str
) -> None:
    _calcular(generar_tabla, monto, plazo_meses, tasa_efectiva_anual)


def codigo_de_salida(
    operacion: str, monto: str, plazo_meses: str, tasa_efectiva_anual: str
) -> int:
    argumentos = [
        operacion,
        "--monto",
        monto,
        "--plazo",
        plazo_meses,
        "--tasa-anual",
        tasa_efectiva_anual,
    ]
    try:
        return main(argumentos)
    except SystemExit as salida:
        return int(salida.code or 0)
