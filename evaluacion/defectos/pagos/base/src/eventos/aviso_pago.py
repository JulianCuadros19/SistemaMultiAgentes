"""Eventos brutos y validación de avisos de la pasarela."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


class ValidacionEventoInvalido(ValueError):
    """Indica que un campo del evento incumple su restricción."""


def _validar_texto(valor: str) -> None:
    if not isinstance(valor, str) or not valor.strip():
        raise ValidacionEventoInvalido("El texto es obligatorio y no puede estar vacío.")


def _validar_fecha(fecha: date) -> None:
    if type(fecha) is not date:
        raise ValidacionEventoInvalido("Se requiere una fecha calendario válida.")


@dataclass(frozen=True)
class AvisoPagoConfirmado:
    """Aviso bruto de pago confirmado.

    Args:
        referencia_pago: Referencia no vacía del pago.
        numero_factura: Número no vacío de factura.
        valor: Pesos enteros no negativos, representados mediante Decimal.
        fecha: Fecha calendario del pago.

    Raises:
        ValidacionEventoInvalido: Si algún campo es inválido.
    """

    referencia_pago: str
    numero_factura: str
    valor: Decimal
    fecha: date

    def __post_init__(self) -> None:
        """Comprueba las restricciones del aviso.

        Raises:
            ValidacionEventoInvalido: Si algún campo es inválido.
        """
        _validar_texto(self.referencia_pago)
        _validar_texto(self.numero_factura)
        _validar_fecha(self.fecha)
        if not isinstance(self.valor, Decimal) or not self.valor.is_finite():
            raise ValidacionEventoInvalido("El valor debe ser un Decimal finito.")
        if self.valor < 0 or self.valor != self.valor.to_integral_value():
            raise ValidacionEventoInvalido(
                "El valor debe expresarse en pesos enteros no negativos."
            )


@dataclass(frozen=True)
class AvisoPagoReversado:
    """Aviso bruto de reverso.

    Args:
        referencia_pago: Referencia no vacía del pago.
        fecha: Fecha calendario del reverso.
        motivo: Motivo no vacío, exclusivo del reverso.

    Raises:
        ValidacionEventoInvalido: Si algún campo es inválido.
    """

    referencia_pago: str
    fecha: date
    motivo: str

    def __post_init__(self) -> None:
        """Comprueba los campos obligatorios del reverso.

        Raises:
            ValidacionEventoInvalido: Si algún campo es inválido.
        """
        _validar_texto(self.referencia_pago)
        _validar_fecha(self.fecha)
        _validar_texto(self.motivo)
