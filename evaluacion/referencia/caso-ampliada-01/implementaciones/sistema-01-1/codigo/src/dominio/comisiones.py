"""Entidades y reglas para liquidar comisiones de negocios inmobiliarios."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext


@dataclass(frozen=True)
class Negocio:
    """Datos de un negocio cuya liquidación se solicita.

    Args:
        tipo_de_negocio: Tipo de negocio: venta o arriendo.
        numero_de_asesores: Cantidad de asesores: uno o dos.
        estado_del_negocio: Estado del negocio: cerrado o abierto.
        valor_de_venta_o_canon_mensual: Valor de venta o canon mensual en pesos.
    """

    tipo_de_negocio: str
    numero_de_asesores: int
    estado_del_negocio: str
    valor_de_venta_o_canon_mensual: Decimal


@dataclass(frozen=True)
class ResultadoComision:
    """Resultado de la liquidación en pesos colombianos sin decimales.

    Args:
        comision_de_la_inmobiliaria: Comisión de la inmobiliaria redondeada al peso.
        comision_de_cada_asesor: Comisión individual redondeada, con mínimo de 300000.
    """

    comision_de_la_inmobiliaria: Decimal
    comision_de_cada_asesor: Decimal


class NegocioAbiertoError(ValueError):
    """Indica que el negocio todavía no está cerrado.

    Args:
        mensaje: Descripción del rechazo.
    """

    def __init__(self, mensaje: str) -> None:
        """Inicializa la excepción.

        Args:
            mensaje: Descripción del rechazo.
        """
        super().__init__(mensaje)


class ValorNoPermitidoError(ValueError):
    """Indica que el valor monetario no es un Decimal finito y positivo.

    Args:
        mensaje: Descripción del valor no permitido.
    """

    def __init__(self, mensaje: str) -> None:
        """Inicializa la excepción.

        Args:
            mensaje: Descripción del valor no permitido.
        """
        super().__init__(mensaje)


class ReglaNegocioError(ValueError):
    """Indica que los datos incumplen una regla del negocio.

    Args:
        mensaje: Descripción de la regla incumplida.
    """

    def __init__(self, mensaje: str) -> None:
        """Inicializa la excepción.

        Args:
            mensaje: Descripción de la regla incumplida.
        """
        super().__init__(mensaje)


def _validar_negocio(negocio: Negocio) -> None:
    """Valida los datos antes de efectuar operaciones monetarias."""
    if not isinstance(negocio, Negocio):
        raise ReglaNegocioError("Se requiere un Negocio")
    if (
        not isinstance(negocio.tipo_de_negocio, str)
        or negocio.tipo_de_negocio not in ("venta", "arriendo")
    ):
        raise ReglaNegocioError("El tipo de negocio debe ser venta o arriendo")
    if type(negocio.numero_de_asesores) is not int or negocio.numero_de_asesores not in (1, 2):
        raise ReglaNegocioError("El número de asesores debe ser 1 o 2")
    if (
        not isinstance(negocio.estado_del_negocio, str)
        or negocio.estado_del_negocio not in ("cerrado", "abierto")
    ):
        raise ReglaNegocioError("El estado del negocio debe ser cerrado o abierto")
    _validar_valor(negocio.valor_de_venta_o_canon_mensual)
    if negocio.estado_del_negocio == "abierto":
        raise NegocioAbiertoError("El negocio aún no está cerrado")


def _validar_valor(valor: Decimal) -> None:
    """Exige un importe Decimal finito y mayor que cero."""
    if not isinstance(valor, Decimal) or not valor.is_finite() or valor <= 0:
        raise ValorNoPermitidoError("El valor debe ser un Decimal finito mayor que cero")


def calcular_para_negocio(negocio: Negocio) -> ResultadoComision:
    """Calcula las comisiones y aplica el mínimo individual por asesor.

    Args:
        negocio: Negocio con los datos de la liquidación.

    Returns:
        Comisiones redondeadas al peso más cercano.

    Raises:
        NegocioAbiertoError: Si el negocio está abierto.
        ValorNoPermitidoError: Si el importe no es un Decimal finito y positivo.
        ReglaNegocioError: Si el negocio, tipo, estado o cantidad de asesores es inválido.
    """
    _validar_negocio(negocio)
    valor = negocio.valor_de_venta_o_canon_mensual
    with localcontext() as contexto:
        contexto.prec = max(28, len(valor.as_tuple().digits), valor.adjusted() + 1) + 10
        porcentaje = Decimal("0.03") if negocio.tipo_de_negocio == "venta" else Decimal(1)
        comision = valor * porcentaje
        por_asesor = max(
            Decimal(300000),
            comision * Decimal("0.40") / Decimal(negocio.numero_de_asesores),
        )
        return ResultadoComision(
            comision_de_la_inmobiliaria=comision.quantize(Decimal(1), rounding=ROUND_HALF_UP),
            comision_de_cada_asesor=por_asesor.quantize(Decimal(1), rounding=ROUND_HALF_UP),
        )
