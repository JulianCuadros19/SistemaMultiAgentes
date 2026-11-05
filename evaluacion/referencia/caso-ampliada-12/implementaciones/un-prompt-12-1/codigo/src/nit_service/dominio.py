"""Reglas del NIT independientes del transporte HTTP."""

from dataclasses import dataclass

_PESOS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)
_DIGITOS = frozenset("0123456789")


class NitError(ValueError):
    """Indica una entrada que no permite calcular o validar un NIT."""


@dataclass(frozen=True)
class ResultadoValidacion:
    """Contiene el número normalizado y el resultado de comparar su dígito."""

    numero: str
    digito: int
    valido: bool
    digito_esperado: int


def normalizar_numero(numero: str) -> str:
    """Quite puntos y guiones y compruebe que quedan de 1 a 15 dígitos ASCII.

    Args:
        numero: Número sin el dígito de verificación.

    Returns:
        Número sin separadores, conservando sus ceros iniciales.

    Raises:
        NitError: Si la entrada no es texto o no cumple las reglas del número.
    """
    if not isinstance(numero, str):
        raise NitError("El número del NIT debe ser una cadena")
    normalizado = numero.replace(".", "").replace("-", "")
    if not normalizado:
        raise NitError("El NIT debe contener al menos 1 dígito")
    if any(caracter not in _DIGITOS for caracter in normalizado):
        raise NitError("El NIT solo admite dígitos")
    if len(normalizado) > len(_PESOS):
        raise NitError("El NIT admite como máximo 15 dígitos")
    return normalizado


def calcular_digito(numero: str) -> int:
    """Calcule el dígito usando los pesos desde la derecha y el residuo módulo 11.

    Args:
        numero: Número de 1 a 15 dígitos, opcionalmente con puntos o guiones.

    Returns:
        Dígito de verificación entre 0 y 9.

    Raises:
        NitError: Si el número no cumple las reglas de entrada.
    """
    normalizado = normalizar_numero(numero)
    suma = sum(int(digito) * peso for digito, peso in zip(reversed(normalizado), _PESOS))
    residuo = suma % 11
    return residuo if residuo in (0, 1) else 11 - residuo


def validar_nit(numero: str, digito: str) -> ResultadoValidacion:
    """Compare un dígito recibido como texto con el calculado para el número.

    Args:
        numero: Número, sin incluir su dígito de verificación.
        digito: Un único carácter ASCII de 0 a 9.

    Returns:
        Resultado que incluye siempre el dígito esperado.

    Raises:
        NitError: Si el número o el dígito tienen un formato incorrecto.
    """
    normalizado = normalizar_numero(numero)
    if not isinstance(digito, str) or len(digito) != 1 or digito not in _DIGITOS:
        raise NitError("El dígito de verificación debe ser un dígito de 0 a 9")
    esperado = calcular_digito(normalizado)
    recibido = int(digito)
    return ResultadoValidacion(normalizado, recibido, recibido == esperado, esperado)


def validar_nit_completo(nit: str) -> ResultadoValidacion:
    """Valide un NIT cuyo último guion separa el número del dígito.

    Args:
        nit: Texto con formato número-dígito; el número admite puntos y guiones.

    Returns:
        Resultado de validar el número y el dígito separados.

    Raises:
        NitError: Si falta el guion final o alguna parte no cumple su formato.
    """
    if not isinstance(nit, str):
        raise NitError("El NIT completo debe ser una cadena")
    numero, separador, digito = nit.rpartition("-")
    if not separador:
        raise NitError("El NIT completo debe separar el dígito con un guion")
    return validar_nit(numero, digito)
