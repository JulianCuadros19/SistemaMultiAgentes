"""Decisiones puras de actualización de cartera por pago o reverso."""

from dataclasses import replace

from eventos.aviso_pago_enriquecido import (
    AvisoPagoConfirmadoEnriquecido,
    AvisoPagoReversadoEnriquecido,
    ValidacionEventoInvalido,
)
from eventos.resultados import ActualizacionCarteraResultado


def manejar_pago_confirmado_cartera(
    aviso: AvisoPagoConfirmadoEnriquecido,
) -> ActualizacionCarteraResultado:
    """Determina cartera al día si el pago cubre el saldo de la factura.

    Args:
        aviso: Pago confirmado con el saldo anterior a su aplicación.

    Returns:
        Estado de cartera y clave derivada de la referencia.

    Raises:
        ValidacionEventoInvalido: Si el evento o su contexto son inválidos.
    """
    if not isinstance(aviso, AvisoPagoConfirmadoEnriquecido):
        raise ValidacionEventoInvalido("Se requiere un pago confirmado enriquecido.")
    aviso = replace(aviso)
    return ActualizacionCarteraResultado(
        aviso.referencia_pago,
        aviso.id_familia,
        "al día" if aviso.valor >= aviso.saldo_actual else "en mora",
        f"confirmado:{aviso.referencia_pago}",
    )


def manejar_pago_reversado_cartera(
    aviso: AvisoPagoReversadoEnriquecido,
) -> ActualizacionCarteraResultado:
    """Determina cartera a partir del estado restaurado de factura.

    Args:
        aviso: Reverso con el estado anterior de factura.

    Returns:
        Cartera al día si el estado restaurado es pagada; en mora en otro caso.

    Raises:
        ValidacionEventoInvalido: Si el evento o su contexto son inválidos.
    """
    if not isinstance(aviso, AvisoPagoReversadoEnriquecido):
        raise ValidacionEventoInvalido("Se requiere un pago reversado enriquecido.")
    aviso = replace(aviso)
    return ActualizacionCarteraResultado(
        aviso.referencia_pago,
        aviso.id_familia,
        "al día" if aviso.estado_anterior == "pagada" else "en mora",
        f"reversado:{aviso.referencia_pago}",
    )
