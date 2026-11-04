"""Construcción de avisos validados, sin publicar ni acceder a persistencia."""

from datetime import date
from decimal import Decimal

from eventos.aviso_pago import (
    AvisoPagoConfirmado,
    AvisoPagoReversado,
    ValidacionEventoInvalido,
)


class AvisoIncompleto(ValueError):
    """Indica que falta un dato obligatorio del aviso."""


def _comprobar_presencia(*valores: object) -> None:
    if any(valor is None or (isinstance(valor, str) and not valor.strip()) for valor in valores):
        raise AvisoIncompleto("El aviso no contiene todos los datos obligatorios.")


def construir_aviso_confirmado(
    referencia_pago: str, numero_factura: str, valor: Decimal, fecha: date
) -> AvisoPagoConfirmado:
    """Construye un evento de pago confirmado listo para publicar.

    Args:
        referencia_pago: Referencia no vacía del pago.
        numero_factura: Número no vacío de factura.
        valor: Pesos enteros no negativos mediante Decimal.
        fecha: Fecha calendario del pago.

    Returns:
        Evento bruto validado.

    Raises:
        AvisoIncompleto: Si falta un dato obligatorio.
        ValidacionEventoInvalido: Si un dato presente es inválido.
    """
    _comprobar_presencia(referencia_pago, numero_factura, valor, fecha)
    try:
        return AvisoPagoConfirmado(referencia_pago, numero_factura, valor, fecha)
    except ValidacionEventoInvalido:
        raise


def construir_aviso_reversado(
    referencia_pago: str, fecha: date, motivo: str
) -> AvisoPagoReversado:
    """Construye un evento de reverso listo para publicar.

    Args:
        referencia_pago: Referencia no vacía del pago.
        fecha: Fecha calendario del reverso.
        motivo: Motivo no vacío del reverso.

    Returns:
        Evento bruto validado.

    Raises:
        AvisoIncompleto: Si falta un dato obligatorio.
        ValidacionEventoInvalido: Si un dato presente es inválido.
    """
    _comprobar_presencia(referencia_pago, fecha, motivo)
    return AvisoPagoReversado(referencia_pago, fecha, motivo)
