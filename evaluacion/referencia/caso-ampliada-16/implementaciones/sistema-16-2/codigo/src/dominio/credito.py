"""Entidades y cálculos puros del crédito de vivienda."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext


@dataclass(frozen=True)
class AmortizacionFila:
    """Detalle monetario de un mes del crédito.

    Args:
        mes: Número del mes, empezando en uno.
        saldo_inicial: Saldo antes del pago.
        interes: Intereses del mes, redondeados al peso.
        abono_capital: Capital amortizado, redondeado al peso.
        cuota: Pago mensual, con ajuste en el último mes.
        saldo_final: Saldo después del pago.
    """

    mes: int
    saldo_inicial: Decimal
    interes: Decimal
    abono_capital: Decimal
    cuota: Decimal
    saldo_final: Decimal


@dataclass(frozen=True)
class Resumen:
    """Totales del crédito, coherentes con la tabla de amortización.

    Args:
        total_pagado: Suma de todas las cuotas.
        total_intereses: Suma de todos los intereses.
    """

    total_pagado: Decimal
    total_intereses: Decimal


def tasa_mensual(tea: Decimal) -> Decimal:
    """Convierta una tasa anual fraccionaria a tasa efectiva mensual.

    Args:
        tea: Tasa anual fraccionaria; por ejemplo, Decimal('0.12').

    Returns:
        Tasa efectiva mensual sin redondeo al peso.
    """
    with localcontext() as contexto:
        contexto.prec = 40
        return (Decimal(1) + tea) ** (Decimal(1) / Decimal(12)) - Decimal(1)


def cuota_fija(monto: Decimal, plazo: int, tasa_mensual: Decimal) -> Decimal:
    """Calcule la cuota mediante la fórmula de anualidad.

    Args:
        monto: Capital del crédito.
        plazo: Número de pagos mensuales.
        tasa_mensual: Tasa mensual fraccionaria positiva.

    Returns:
        Cuota fija sin redondeo final.
    """
    with localcontext() as contexto:
        contexto.prec = 40
        return monto * tasa_mensual / (
            Decimal(1) - (Decimal(1) + tasa_mensual) ** (-plazo)
        )


def redondear_peso(valor: Decimal) -> Decimal:
    """Redondee un importe a la unidad con mitades hacia arriba.

    Args:
        valor: Importe que se desea redondear.

    Returns:
        Importe redondeado al peso.
    """
    with localcontext() as contexto:
        contexto.prec = max(40, valor.adjusted() + 2)
        return valor.quantize(Decimal(1), rounding=ROUND_HALF_UP)
