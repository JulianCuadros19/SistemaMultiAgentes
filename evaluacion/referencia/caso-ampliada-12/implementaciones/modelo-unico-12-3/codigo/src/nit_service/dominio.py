"""Reglas de cálculo independientes del transporte HTTP."""

from typing import TypedDict

_PESOS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)


class ResultadoValidacion(TypedDict):
    """Resultado de comparar el dígito recibido con el calculado."""

    nit: str
    digito_recibido: str
    digito_esperado: str
    valido: bool


def _normalizar(nit: str) -> str:
    if not isinstance(nit, str):
        raise ValueError("El NIT debe enviarse como texto")
    base = nit.replace(".", "").replace("-", "")
    if not base:
        raise ValueError("El NIT debe contener al menos un dígito")
    if any(caracter not in "0123456789" for caracter in base):
        raise ValueError("El NIT solo admite dígitos")
    if len(base) > 15:
        raise ValueError("El NIT admite como máximo 15 dígitos")
    return base


def _digito(base: str) -> str:
    suma = sum(int(digito) * peso for digito, peso in zip(reversed(base), _PESOS))
    residuo = suma % 11
    return str(residuo if residuo in (0, 1) else 11 - residuo)


def calcular(nit: str) -> str:
    """Calcule el dígito de un NIT base, eliminando puntos y guiones.

    Args:
        nit: NIT base como texto, con entre una y quince cifras.

    Returns:
        Dígito de verificación como texto.

    Raises:
        ValueError: Si el tipo, los caracteres o la longitud no son válidos.
    """
    return _digito(_normalizar(nit))


def validar(nit: str) -> ResultadoValidacion:
    """Compruebe un NIT completo en formato «base-dígito».

    Args:
        nit: NIT completo como texto. El último guion separa el dígito.

    Returns:
        Base normalizada, dígitos recibido y esperado, y coincidencia.

    Raises:
        ValueError: Si el NIT o el dígito recibido están mal escritos.
    """
    if not isinstance(nit, str):
        raise ValueError("El NIT debe enviarse como texto")
    base, separador, recibido = nit.rpartition("-")
    if not separador:
        raise ValueError("Para validar, envíe el NIT en formato NIT-dígito")
    normalizado = _normalizar(base)
    if len(recibido) != 1 or recibido not in "0123456789":
        raise ValueError("El dígito de verificación debe ser una sola cifra")
    esperado = _digito(normalizado)
    return {
        "nit": normalizado,
        "digito_recibido": recibido,
        "digito_esperado": esperado,
        "valido": recibido == esperado,
    }
