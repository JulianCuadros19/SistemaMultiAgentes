"""Decisión pura de emisión del recibo de un pago confirmado."""

from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal

from eventos.aviso_pago_enriquecido import (
    AvisoPagoConfirmadoEnriquecido,
    ValidacionEventoInvalido,
)
from eventos.resultados import EmisionReciboResultado


def manejar_pago_confirmado_emitir_recibo(
    aviso: AvisoPagoConfirmadoEnriquecido,
) -> EmisionReciboResultado:
    """Solicita emitir un recibo sin asignar su consecutivo.

    Args:
        aviso: Pago confirmado enriquecido y válido.

    Returns:
        Instrucción con factura, referencia, importe total y fecha del pago.

    Raises:
        ValidacionEventoInvalido: Si el evento o su contexto son inválidos.
    """
    if not isinstance(aviso, AvisoPagoConfirmadoEnriquecido):
        raise ValidacionEventoInvalido("Se requiere un pago confirmado enriquecido.")
    aviso = replace(aviso)
    return EmisionReciboResultado(
        aviso.numero_factura,
        aviso.referencia_pago,
        aviso.valor.quantize(Decimal(1), rounding=ROUND_HALF_UP),
        aviso.fecha,
        f"confirmado:{aviso.referencia_pago}",
    )
