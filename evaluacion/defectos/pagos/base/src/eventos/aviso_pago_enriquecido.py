"""Eventos enriquecidos con el contexto de factura y familia."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


class ValidacionEventoInvalido(ValueError):
    """Indica que el contexto o los datos del evento son inválidos."""


def _validar_pesos(valor: Decimal) -> None:
    if not isinstance(valor, Decimal) or not valor.is_finite():
        raise ValidacionEventoInvalido("Se requieren pesos representados por un Decimal finito.")
    if valor < 0 or valor != valor.to_integral_value():
        raise ValidacionEventoInvalido("Se requieren pesos enteros no negativos.")


class _EventoValidado:
    def __post_init__(self) -> None:
        for nombre, valor in vars(self).items():
            if nombre in {"valor", "saldo_actual"}:
                _validar_pesos(valor)
            elif nombre == "fecha":
                if type(valor) is not date:
                    raise ValidacionEventoInvalido("Se requiere una fecha calendario válida.")
            elif not isinstance(valor, str) or not valor.strip():
                raise ValidacionEventoInvalido(f"El campo {nombre} debe ser texto no vacío.")
            elif nombre in {"estado_actual", "estado_anterior"}:
                if valor not in {"pagada", "abonada", "pendiente"}:
                    raise ValidacionEventoInvalido("El estado de factura no está permitido.")


@dataclass(frozen=True)
class AvisoPagoConfirmadoEnriquecido(_EventoValidado):
    """Pago confirmado con el contexto anterior a su aplicación.

    Args:
        referencia_pago: Referencia del pago.
        numero_factura: Número de factura.
        valor: Pesos enteros no negativos.
        fecha: Fecha calendario del pago.
        saldo_actual: Saldo anterior al pago, en pesos enteros no negativos.
        estado_actual: Estado anterior al pago: pagada, abonada o pendiente.
        id_familia: Identificador no vacío de familia.
    """

    referencia_pago: str
    numero_factura: str
    valor: Decimal
    fecha: date
    saldo_actual: Decimal
    estado_actual: str
    id_familia: str


@dataclass(frozen=True)
class AvisoPagoReversadoEnriquecido(_EventoValidado):
    """Reverso con la factura resuelta por su referencia.

    Args:
        referencia_pago: Referencia del pago.
        fecha: Fecha calendario del reverso.
        motivo: Motivo no vacío del reverso.
        numero_factura: Número de factura asociado al pago.
        estado_anterior: Estado de factura que debe restaurarse.
        id_familia: Identificador no vacío de familia.
    """

    referencia_pago: str
    fecha: date
    motivo: str
    numero_factura: str
    estado_anterior: str
    id_familia: str
