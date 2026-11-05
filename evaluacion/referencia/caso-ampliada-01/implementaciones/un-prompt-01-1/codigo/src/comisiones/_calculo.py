"""Implemente las reglas de liquidación sin redondeos intermedios."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Literal


@dataclass(frozen=True)
class ResultadoComisiones:
    """Contenga los importes finales en pesos colombianos enteros.

    Attributes:
        comision_inmobiliaria: Comisión de la inmobiliaria.
        comisiones_asesores: Comisión de cada asesor, en orden de participación.
            Contiene uno o dos importes, según el número de asesores.
    """

    comision_inmobiliaria: int
    comisiones_asesores: tuple[int, ...]


def _convertir_valor(valor: int | float | str | Decimal) -> Fraction:
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str, Decimal)):
        raise ValueError("El valor debe ser numérico, finito y mayor que cero")

    try:
        if isinstance(valor, Decimal):
            decimal = valor
        elif isinstance(valor, float):
            decimal = Decimal(str(valor))
        else:
            decimal = Decimal(valor)
    except InvalidOperation as exc:
        raise ValueError("El valor debe ser numérico, finito y mayor que cero") from exc

    if not decimal.is_finite() or decimal <= 0:
        raise ValueError("El valor debe ser numérico, finito y mayor que cero")
    return Fraction(decimal)


def _validar_datos(tipo_negocio: str, numero_asesores: int, estado: str) -> None:
    if tipo_negocio not in ("venta", "arriendo"):
        raise ValueError("El tipo de negocio debe ser venta o arriendo")
    if estado not in ("cerrado", "abierto"):
        raise ValueError("El estado debe ser cerrado o abierto")
    if estado == "abierto":
        raise ValueError("El negocio aún no está cerrado")
    if (
        isinstance(numero_asesores, bool)
        or not isinstance(numero_asesores, int)
        or numero_asesores not in (1, 2)
    ):
        raise ValueError("El número de asesores debe ser 1 o 2")


def _redondear_pesos(importe: Fraction) -> int:
    # Todos los importes son positivos: en un empate, se redondea hacia arriba.
    return (2 * importe.numerator + importe.denominator) // (2 * importe.denominator)


def calcular_comisiones(
    *,
    tipo_negocio: Literal["venta", "arriendo"],
    valor: int | float | str | Decimal,
    numero_asesores: int,
    estado: Literal["cerrado", "abierto"],
) -> ResultadoComisiones:
    """Liquide un negocio cerrado aplicando reparto, mínimo y redondeo.

    Args:
        tipo_negocio: "venta" o "arriendo".
        valor: Precio de venta o primer canon mensual, positivo y finito.
            Admite int, Decimal, float o texto decimal sin separadores de miles.
        numero_asesores: Número entero de participantes, 1 o 2.
        estado: "cerrado" o "abierto". Los negocios abiertos se rechazan.

    Returns:
        Comisión inmobiliaria y una comisión por asesor, en pesos enteros.
        El mínimo de 300.000 pesos se aplica individualmente. Los cálculos
        son exactos y solo se redondean los importes finales; medio peso
        se redondea hacia arriba.

    Raises:
        ValueError: Si algún dato es inválido o el negocio está abierto.
        TypeError: Si falta un argumento obligatorio.
    """
    _validar_datos(tipo_negocio, numero_asesores, estado)
    importe = _convertir_valor(valor)
    tasa_inmobiliaria = Fraction(3, 100) if tipo_negocio == "venta" else Fraction(1)
    comision_inmobiliaria = importe * tasa_inmobiliaria
    comision_individual = comision_inmobiliaria * Fraction(2, 5) / numero_asesores
    comision_individual = max(comision_individual, Fraction(300_000))

    return ResultadoComisiones(
        comision_inmobiliaria=_redondear_pesos(comision_inmobiliaria),
        comisiones_asesores=(_redondear_pesos(comision_individual),) * numero_asesores,
    )
