"""Decisión pura de anulación de recibos por reverso de pago."""

from dataclasses import replace

from eventos.aviso_pago_enriquecido import (
    AvisoPagoReversadoEnriquecido,
    ValidacionEventoInvalido,
)
from eventos.resultados import AnulacionReciboResultado


def manejar_pago_reversado_recibo(
    aviso: AvisoPagoReversadoEnriquecido,
) -> AnulacionReciboResultado:
    """Solicita anular el recibo y conservar el motivo del reverso.

    Args:
        aviso: Reverso enriquecido y válido.

    Returns:
        Instrucción de anulación asociada a la referencia del pago.

    Raises:
        ValidacionEventoInvalido: Si el evento o su contexto son inválidos.
    """
    if not isinstance(aviso, AvisoPagoReversadoEnriquecido):
        raise ValidacionEventoInvalido("Se requiere un pago reversado enriquecido.")
    aviso = replace(aviso)
    return AnulacionReciboResultado(
        aviso.referencia_pago,
        aviso.motivo,
        "anulado",
        f"reversado:{aviso.referencia_pago}",
    )
