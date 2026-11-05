"""Entidades y validación de parámetros del crédito de vivienda."""

from dataclasses import dataclass
from decimal import Decimal, localcontext


class DatosInvalidosError(ValueError):
    """Indica que un parámetro del crédito es inválido.

    Args:
        mensaje: Descripción del dato rechazado.
    """

    def __init__(self, mensaje: str) -> None:
        """Inicializa la excepción con un mensaje en español."""
        super().__init__(mensaje)


@dataclass
class ParametrosCredito:
    """Parámetros validados de una simulación.

    Args:
        monto: Capital en pesos enteros, representado mediante Decimal.
        plazo_en_meses: Número de meses entre 12 y 240.
        tasa_efectiva_anual: Tasa expresada como fracción, entre 0.01 y 0.30.

    Raises:
        DatosInvalidosError: Si algún parámetro incumple las restricciones.
    """

    monto: Decimal
    plazo_en_meses: int
    tasa_efectiva_anual: Decimal

    def __post_init__(self) -> None:
        """Valida los parámetros al construir la instancia.

        Raises:
            DatosInvalidosError: Si algún parámetro es inválido.
        """
        self.validar()

    def validar(self) -> None:
        """Comprueba tipos, valores finitos, rangos y precisión.

        Raises:
            DatosInvalidosError: Si algún parámetro es inválido.
        """
        if not isinstance(self.monto, Decimal) or not self.monto.is_finite():
            raise DatosInvalidosError("El monto debe ser un Decimal finito en pesos enteros.")
        if not Decimal(10000000) <= self.monto <= Decimal(500000000):
            raise DatosInvalidosError("El monto debe estar entre 10.000.000 y 500.000.000.")
        if self.monto != self.monto.to_integral_value():
            raise DatosInvalidosError("El monto debe contener pesos enteros.")
        if type(self.plazo_en_meses) is not int or not 12 <= self.plazo_en_meses <= 240:
            raise DatosInvalidosError("El plazo en meses debe ser un entero entre 12 y 240.")
        tasa = self.tasa_efectiva_anual
        if not isinstance(tasa, Decimal) or not tasa.is_finite():
            raise DatosInvalidosError("La tasa debe ser un Decimal finito.")
        if not Decimal("0.01") <= tasa <= Decimal("0.30"):
            raise DatosInvalidosError("La tasa debe estar entre 0.01 y 0.30.")
        if tasa != tasa.quantize(Decimal("0.01")):
            raise DatosInvalidosError("La tasa debe tener hasta dos decimales.")

    def tasa_mensual(self) -> Decimal:
        """Calcula la tasa mensual equivalente usando Decimal.

        Returns:
            Tasa mensual equivalente a la tasa efectiva anual.
        """
        with localcontext() as contexto:
            contexto.prec = 40
            return (Decimal(1) + self.tasa_efectiva_anual) ** (Decimal(1) / Decimal(12)) - 1


@dataclass
class AmortizacionFila:
    """Fila de amortización con importes redondeados al peso.

    Args:
        mes: Número de mes, comenzando en uno.
        cuota: Pago mensual en pesos enteros.
        interes: Interés del mes en pesos enteros.
        abono_capital: Capital amortizado en pesos enteros.
        saldo: Capital pendiente en pesos enteros.
    """

    mes: int
    cuota: int
    interes: int
    abono_capital: int
    saldo: int


@dataclass
class ResumenCredito:
    """Totales del crédito redondeados al peso.

    Args:
        total_pagado: Suma de los pagos en pesos enteros.
        total_intereses: Suma de los intereses en pesos enteros.
    """

    total_pagado: int
    total_intereses: int
