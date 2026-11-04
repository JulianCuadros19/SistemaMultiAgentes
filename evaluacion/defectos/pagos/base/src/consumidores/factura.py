"""Decisiones puras de aplicación y reversión de pagos a facturas."""

from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal

from eventos.aviso_pago_enriquecido import (
    AvisoPagoConfirmadoEnriquecido,
    AvisoPagoReversadoEnriquecido,
    ValidacionEventoInvalido,
)
from eventos.resultados import AjusteFacturaResultado


def manejar_pago_confirmado_factura(
    aviso: AvisoPagoConfirmadoEnriquecido,
) -> AjusteFacturaResultado:
    """Calcula el abono, estado y excedente sin modificar la factura.

    Args:
        aviso: Pago confirmado con el saldo anterior a su aplicación.

    Returns:
        Ajuste con importes en pesos sin decimales.

    Raises:
        ValidacionEventoInvalido: Si el evento o su contexto son inválidos.
    """
    if not isinstance(aviso, AvisoPagoConfirmadoEnriquecido):
        raise ValidacionEventoInvalido("Se requiere un pago confirmado enriquecido.")
    aviso = replace(aviso)
    aplicado = min(aviso.valor, aviso.saldo_actual).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    excedente = max(Decimal(0), aviso.valor - aviso.saldo_actual)
    return AjusteFacturaResultado(
        aviso.numero_factura,
        "pagada" if aviso.valor >= aviso.saldo_actual else "abonada",
        aplicado,
        excedente.quantize(Decimal(1), rounding=ROUND_HALF_UP),
        f"confirmado:{aviso.referencia_pago}:{aviso.numero_factura}",
    )


def manejar_pago_reversado_factura(
    aviso: AvisoPagoReversadoEnriquecido,
) -> AjusteFacturaResultado:
    """Solicita restaurar el estado anterior de factura.

    Args:
        aviso: Reverso con el estado anterior de factura.

    Returns:
        Ajuste de reverso; los importes del resultado son cero.

    Raises:
        ValidacionEventoInvalido: Si el evento o su contexto son inválidos.
    """
    if not isinstance(aviso, AvisoPagoReversadoEnriquecido):
        raise ValidacionEventoInvalido("Se requiere un pago reversado enriquecido.")
    aviso = replace(aviso)
    return AjusteFacturaResultado(
        aviso.numero_factura,
        aviso.estado_anterior,
        Decimal(0),
        Decimal(0),
        f"reversado:{aviso.referencia_pago}:{aviso.numero_factura}",
    )
