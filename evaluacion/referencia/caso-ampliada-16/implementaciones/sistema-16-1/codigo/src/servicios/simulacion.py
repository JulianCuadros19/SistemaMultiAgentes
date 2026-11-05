"""Cálculo de cuota, amortización y resumen del crédito de vivienda."""

from collections.abc import Iterator
from decimal import ROUND_HALF_UP, Decimal, localcontext

from dominio.credito import AmortizacionFila, DatosInvalidosError, ParametrosCredito, ResumenCredito
from entrada_salida.tabla_csv import EscritorTablaCSV


def _validar(parametros: ParametrosCredito) -> None:
    if not isinstance(parametros, ParametrosCredito):
        raise DatosInvalidosError("Se requieren parámetros de crédito válidos.")
    parametros.validar()


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal(1), rounding=ROUND_HALF_UP)


def _cuota(parametros: ParametrosCredito, tasa: Decimal) -> Decimal:
    with localcontext() as contexto:
        contexto.prec = 40
        divisor = Decimal(1) - (Decimal(1) + tasa) ** (-parametros.plazo_en_meses)
        return _redondear(parametros.monto * tasa / divisor)


def _movimientos(parametros: ParametrosCredito) -> Iterator[AmortizacionFila]:
    tasa = parametros.tasa_mensual()
    cuota_fija = _cuota(parametros, tasa)
    saldo = parametros.monto
    for mes in range(1, parametros.plazo_en_meses + 1):
        with localcontext() as contexto:
            contexto.prec = 40
            interes = _redondear(saldo * tasa)
            cuota = saldo + interes if mes == parametros.plazo_en_meses else cuota_fija
            abono = cuota - interes
            saldo = saldo - abono
            fila = AmortizacionFila(mes, int(cuota), int(interes), int(abono), int(saldo))
        yield fila


def calcular_cuota(parametros: ParametrosCredito) -> int:
    """Calcula la cuota fija mensual redondeada al peso.

    Args:
        parametros: Parámetros del crédito.

    Returns:
        Cuota mensual en pesos enteros.

    Raises:
        DatosInvalidosError: Si los parámetros son inválidos.
    """
    _validar(parametros)
    return int(_cuota(parametros, parametros.tasa_mensual()))


def generar_tabla(
    parametros: ParametrosCredito, escritor: EscritorTablaCSV | None
) -> list[AmortizacionFila]:
    """Genera la amortización y la guarda solo si se proporciona escritor.

    Args:
        parametros: Parámetros del crédito.
        escritor: Destino CSV opcional.

    Returns:
        Filas mensuales con saldo final igual a cero.

    Raises:
        DatosInvalidosError: Si los parámetros son inválidos.
    """
    _validar(parametros)
    filas = list(_movimientos(parametros))
    if escritor is not None:
        escritor.escribir(filas)
    return filas


def calcular_resumen(parametros: ParametrosCredito) -> ResumenCredito:
    """Calcula los totales sin invocar las operaciones de cuota o tabla.

    Args:
        parametros: Parámetros del crédito.

    Returns:
        Total pagado y total de intereses en pesos enteros.

    Raises:
        DatosInvalidosError: Si los parámetros son inválidos.
    """
    _validar(parametros)
    total_pagado = Decimal(0)
    total_intereses = Decimal(0)
    for fila in _movimientos(parametros):
        total_pagado += Decimal(fila.cuota)
        total_intereses += Decimal(fila.interes)
    return ResumenCredito(int(total_pagado), int(total_intereses))
