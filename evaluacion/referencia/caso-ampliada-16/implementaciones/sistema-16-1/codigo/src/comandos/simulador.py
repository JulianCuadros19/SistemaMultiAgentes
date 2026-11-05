"""Adaptadores lógicos de los subcomandos del simulador."""

from servicios.simulacion import (
    AmortizacionFila,
    EscritorTablaCSV,
    ParametrosCredito,
    ResumenCredito,
    calcular_cuota,
    calcular_resumen,
    generar_tabla,
)
from servicios.simulacion import DatosInvalidosError as DatosInvalidosError


def main_cuota(parametros: ParametrosCredito) -> int:
    """Invoca el cálculo de cuota mensual.

    Args:
        parametros: Parámetros del crédito.

    Returns:
        Cuota mensual en pesos enteros.

    Raises:
        DatosInvalidosError: Si los parámetros son inválidos.
    """
    return calcular_cuota(parametros)


def main_tabla(
    parametros: ParametrosCredito, escritor: EscritorTablaCSV | None
) -> list[AmortizacionFila]:
    """Invoca la generación de tabla con guardado opcional.

    Args:
        parametros: Parámetros del crédito.
        escritor: Destino CSV opcional.

    Returns:
        Tabla de amortización completa.

    Raises:
        DatosInvalidosError: Si los parámetros son inválidos.
    """
    return generar_tabla(parametros, escritor)


def main_resumen(parametros: ParametrosCredito) -> ResumenCredito:
    """Invoca el cálculo independiente del resumen.

    Args:
        parametros: Parámetros del crédito.

    Returns:
        Totales pagados y de intereses.

    Raises:
        DatosInvalidosError: Si los parámetros son inválidos.
    """
    return calcular_resumen(parametros)
