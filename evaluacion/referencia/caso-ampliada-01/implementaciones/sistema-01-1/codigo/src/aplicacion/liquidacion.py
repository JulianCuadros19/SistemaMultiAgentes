"""Caso de uso para liquidar las comisiones de un negocio cerrado."""

from decimal import Decimal

from dominio.comisiones import (
    Negocio,
    ResultadoComision,
    calcular_para_negocio,
)
from dominio.comisiones import NegocioAbiertoError as NegocioAbiertoError
from dominio.comisiones import ReglaNegocioError as ReglaNegocioError
from dominio.comisiones import ValorNoPermitidoError as ValorNoPermitidoError


def calcular_comision(
    tipo_de_negocio: str,
    numero_de_asesores: int,
    estado_del_negocio: str,
    valor_de_venta_o_canon_mensual: Decimal,
) -> ResultadoComision:
    """Construye el negocio y delega su validación y liquidación al dominio.

    Args:
        tipo_de_negocio: Venta o arriendo.
        numero_de_asesores: Uno o dos asesores.
        estado_del_negocio: Cerrado o abierto.
        valor_de_venta_o_canon_mensual: Importe en pesos, Decimal finito mayor que cero.

    Returns:
        Comisión de la inmobiliaria y comisión individual, sin decimales.

    Raises:
        NegocioAbiertoError: Si el negocio no está cerrado.
        ValorNoPermitidoError: Si el importe no es un Decimal finito y positivo.
        ReglaNegocioError: Si el tipo, estado o número de asesores no está permitido.
    """
    negocio = Negocio(
        tipo_de_negocio,
        numero_de_asesores,
        estado_del_negocio,
        valor_de_venta_o_canon_mensual,
    )
    return calcular_para_negocio(negocio)
