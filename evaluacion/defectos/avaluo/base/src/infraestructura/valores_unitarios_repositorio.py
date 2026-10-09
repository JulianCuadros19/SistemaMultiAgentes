"""Consulta de valores unitarios en un almacenamiento local en memoria."""

from datetime import date

from dominio.avaluo import (
    NumeroPredialInvalido,
    ValoresUnitarios,
    ValoresUnitariosNoEncontrados,
    VigenciaInvalida,
    numero_predial_valido,
)

_VALORES_UNITARIOS: dict[tuple[str, int], ValoresUnitarios] = {}


def validar_vigencia(vigencia: int) -> None:
    """Valida que la vigencia sea un año de cuatro dígitos, hasta el año actual más uno.

    Args:
        vigencia: Año de la vigencia.

    Raises:
        VigenciaInvalida: Si el año no cumple la restricción.
    """
    if type(vigencia) is not int or not 1000 <= vigencia <= min(9999, date.today().year + 1):
        raise VigenciaInvalida(
            "La vigencia debe tener cuatro dígitos y no superar el año actual + 1."
        )


def obtener_valores_unitarios(numero_predial: str, vigencia: int) -> ValoresUnitarios:
    """Obtiene los valores aplicables al predio en la vigencia solicitada.

    Args:
        numero_predial: Identificador de exactamente 30 dígitos.
        vigencia: Año de cuatro dígitos, hasta el año actual más uno.

    Returns:
        Valores unitarios registrados para la clave solicitada.

    Raises:
        NumeroPredialInvalido: Si el identificador es inválido.
        VigenciaInvalida: Si el año es inválido.
        ValoresUnitariosNoEncontrados: Si la clave no está registrada.
    """
    if not numero_predial_valido(numero_predial):
        raise NumeroPredialInvalido("El número predial debe contener exactamente 30 dígitos.")
    validar_vigencia(vigencia)
    valores = _VALORES_UNITARIOS.get((numero_predial, vigencia))
    if valores is None:
        raise ValoresUnitariosNoEncontrados(
            "No hay valores unitarios para el predio y la vigencia."
        )
    return valores
