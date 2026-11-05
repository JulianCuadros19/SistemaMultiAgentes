"""Cálculo y validación de NIT sin dependencias del protocolo HTTP."""


class MaxLengthExceededError(ValueError):
    """Indica que la entrada limpia supera los quince dígitos."""

    def __init__(self) -> None:
        """Construye el error de longitud con el mensaje del dominio."""
        super().__init__("El NIT admite como máximo 15 dígitos")


class InvalidCharactersError(ValueError):
    """Indica que la entrada no contiene exclusivamente dígitos y separadores."""

    def __init__(self) -> None:
        """Construye el error de contenido con el mensaje del dominio."""
        super().__init__("El NIT solo admite dígitos")


def _limpiar(texto: str) -> str:
    """Elimina separadores y comprueba el contenido antes de utilizarlo."""
    if not isinstance(texto, str):
        raise InvalidCharactersError()
    limpio = texto.replace(".", "").replace("-", "")
    if not limpio or any(caracter not in "0123456789" for caracter in limpio):
        raise InvalidCharactersError()
    if len(limpio) > 15:
        raise MaxLengthExceededError()
    return limpio


def _calcular(numero: str) -> int:
    """Aplica los pesos al texto ya validado, admitiendo una base vacía."""
    pesos = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)
    suma = sum(int(digito) * peso for digito, peso in zip(reversed(numero), pesos, strict=False))
    residuo = suma % 11
    return residuo if residuo in (0, 1) else 11 - residuo


def calcular_digito(numero: str) -> int:
    """Calcula el dígito de verificación tras eliminar puntos y guiones.

    Args:
        numero: Texto con entre uno y quince dígitos, además de separadores opcionales.

    Returns:
        Dígito de verificación entre cero y nueve.

    Raises:
        MaxLengthExceededError: Si hay más de quince dígitos.
        InvalidCharactersError: Si no hay dígitos o aparece otro carácter.
    """
    return _calcular(_limpiar(numero))


def validar_nit(nit: str) -> tuple[bool, int, int]:
    """Compara el último dígito del NIT con el calculado para los anteriores.

    Args:
        nit: Texto con entre uno y quince dígitos, incluyendo el de verificación.

    Returns:
        Tupla de validez, dígito esperado y dígito calculado. Los dos últimos
        corresponden al resultado del algoritmo para la base del NIT.

    Raises:
        InvalidCharactersError: Si no hay dígitos o aparece otro carácter.
        MaxLengthExceededError: Si el NIT limpio supera los quince dígitos.
    """
    limpio = _limpiar(nit)
    recibido = int(limpio[-1])
    calculado = _calcular(limpio[:-1])
    return recibido == calculado, calculado, calculado
