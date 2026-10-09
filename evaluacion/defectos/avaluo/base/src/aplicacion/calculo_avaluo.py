"""Caso de uso para calcular avalúos en pesos colombianos enteros."""

from decimal import ROUND_HALF_UP, Decimal, localcontext

from dominio.avaluo import (
    AreaConstruidaInvalida,
    AreaTerrenoInvalida,
    NumeroPredialInvalido,
    Predio,
    ResultadoAvaluo,
    ValoresUnitariosNoEncontrados,
    VigenciaInvalida,
)
from infraestructura.valores_unitarios_repositorio import (
    obtener_valores_unitarios,
    validar_vigencia,
)

__all__ = [
    "AreaConstruidaInvalida",
    "AreaTerrenoInvalida",
    "NumeroPredialInvalido",
    "ValoresUnitariosNoEncontrados",
    "VigenciaInvalida",
    "calcular_avaluo",
]


def _precision(valores: tuple[Decimal, ...]) -> int:
    return max(28, sum(len(v.as_tuple().digits) + abs(v.as_tuple().exponent) for v in valores) + 4)


def calcular_avaluo(
    numero_predial: str,
    vigencia: int,
    area_terreno: Decimal,
    area_construida: Decimal,
) -> ResultadoAvaluo:
    """Calcula los componentes del avalúo y suma sus importes redondeados.

    Args:
        numero_predial: Identificador de exactamente 30 dígitos.
        vigencia: Año de cuatro dígitos, hasta el año actual más uno.
        area_terreno: Área finita positiva en metros cuadrados.
        area_construida: Área finita no negativa en metros cuadrados.

    Returns:
        Componentes y total en pesos sin decimales, redondeados con ROUND_HALF_UP.

    Raises:
        NumeroPredialInvalido: Si el identificador es inválido.
        VigenciaInvalida: Si el año es inválido.
        AreaTerrenoInvalida: Si el área de terreno es inválida.
        AreaConstruidaInvalida: Si el área construida es inválida.
        ValoresUnitariosNoEncontrados: Si faltan los valores unitarios.
    """
    predio = Predio(numero_predial, area_terreno, area_construida)
    validar_vigencia(vigencia)
    valores = obtener_valores_unitarios(predio.numero_predial, vigencia)
    with localcontext() as contexto:
        contexto.prec = _precision(
            (area_terreno, area_construida, valores.valor_terreno_m2, valores.valor_construccion_m2)
        )
        terreno = (predio.area_terreno * valores.valor_terreno_m2).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        construccion = (predio.area_construida * valores.valor_construccion_m2).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        return ResultadoAvaluo(terreno, construccion, terreno + construccion)
