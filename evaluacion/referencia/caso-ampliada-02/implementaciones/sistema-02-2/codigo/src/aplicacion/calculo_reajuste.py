"""Caso de uso del cálculo anual de reajuste de canon."""

from datetime import date
from decimal import Decimal, localcontext

from dominio.reajuste import (
    DatosObligatoriosFaltantes,
    ResultadoReajuste,
    ValorInvalido,
    calcular_porcentaje_aplicable,
    redondear_a_centena_mas_cercana,
    validar_periodo_doce_meses,
)
from dominio.reajuste import PeriodoInsuficienteDoceMeses as PeriodoInsuficienteDoceMeses


def _validar_decimal(valor: Decimal, dos_decimales: bool = False) -> None:
    if not isinstance(valor, Decimal) or not valor.is_finite():
        raise ValorInvalido()
    if dos_decimales:
        partes = valor.as_tuple()
        exponente = int(partes.exponent)
        if exponente < -2 and any(partes.digits[exponente + 2 :]):
            raise ValorInvalido()


def calcular_reajuste(
    canon_actual: Decimal | None,
    ipc_anterior: Decimal | None,
    porcentaje_pactado: Decimal,
    fecha_inicio_o_ultimo_reajuste: date,
    fecha_reajuste: date,
) -> ResultadoReajuste:
    """Valida y calcula el reajuste anual, redondeando el canon final.

    Args:
        canon_actual: Canon vigente, decimal finito mayor que cero.
        ipc_anterior: IPC anterior, decimal finito con hasta dos decimales.
        porcentaje_pactado: Porcentaje de cero a cien, con hasta dos decimales.
        fecha_inicio_o_ultimo_reajuste: Inicio del periodo anual.
        fecha_reajuste: Fecha de aplicación del reajuste.

    Returns:
        Canon redondeado, porcentaje aplicado e incremento efectivo.

    Raises:
        DatosObligatoriosFaltantes: Si falta el canon o el IPC.
        ValorInvalido: Si los valores numéricos incumplen sus restricciones.
        PeriodoInsuficienteDoceMeses: Si no se acreditan doce meses completos.
    """
    if canon_actual is None or ipc_anterior is None:
        raise DatosObligatoriosFaltantes()
    _validar_decimal(canon_actual)
    _validar_decimal(ipc_anterior, dos_decimales=True)
    _validar_decimal(porcentaje_pactado, dos_decimales=True)
    if canon_actual <= Decimal("0"):
        raise ValorInvalido()
    if not Decimal("0") <= porcentaje_pactado <= Decimal("100"):
        raise ValorInvalido()
    validar_periodo_doce_meses(fecha_inicio_o_ultimo_reajuste, fecha_reajuste)
    porcentaje = calcular_porcentaje_aplicable(ipc_anterior, porcentaje_pactado)
    with localcontext() as contexto:
        partes = canon_actual.as_tuple()
        contexto.prec = max(28, len(partes.digits) + 10, canon_actual.adjusted() + 12)
        incremento = canon_actual * (porcentaje / Decimal("100"))
        canon_final = redondear_a_centena_mas_cercana(canon_actual + incremento)
        incremento_final = canon_final - canon_actual
    return ResultadoReajuste(canon_final, porcentaje, incremento_final)
