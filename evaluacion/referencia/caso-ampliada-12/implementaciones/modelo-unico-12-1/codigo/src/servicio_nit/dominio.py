"""Reglas de cálculo suministradas, sin excepciones para ejemplos contradictorios."""

from dataclasses import dataclass

_PESOS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)


class ErrorNit(ValueError):
    """Indique que el número o su dígito no cumplen el contrato de entrada."""


def _son_cifras(valor: str) -> bool:
    return bool(valor) and all("0" <= caracter <= "9" for caracter in valor)


def normalizar_nit(nit: str) -> str:
    """Quite puntos y guiones y compruebe un número de una a quince cifras.

    Args:
        nit: Número sin el dígito de verificación, expresado como texto.

    Returns:
        Número sin puntos ni guiones, conservando los ceros iniciales.

    Raises:
        ErrorNit: Si el tipo, contenido o longitud no son admisibles.
    """
    if not isinstance(nit, str):
        raise ErrorNit("El NIT debe ser una cadena de texto")
    numero = nit.replace(".", "").replace("-", "")
    if not numero:
        raise ErrorNit("El NIT no puede estar vacío")
    if not _son_cifras(numero):
        raise ErrorNit("El NIT solo admite dígitos")
    if len(numero) > len(_PESOS):
        raise ErrorNit("El NIT admite como máximo 15 dígitos")
    return numero


def calcular_digito(nit: str) -> str:
    """Calcule el dígito usando los pesos y el módulo once suministrados.

    La fórmula produce 7 para 900123456, no el 8 indicado por el cliente.
    Su aprobación definitiva sigue pendiente; consulte USO.md.

    Args:
        nit: Número sin el dígito de verificación, con puntos o guiones opcionales.

    Returns:
        Una cifra ASCII como cadena de texto.

    Raises:
        ErrorNit: Si el número no cumple las reglas de entrada.
    """
    numero = normalizar_nit(nit)
    suma = sum(int(cifra) * peso for cifra, peso in zip(reversed(numero), _PESOS))
    residuo = suma % 11
    return str(residuo if residuo < 2 else 11 - residuo)


@dataclass(frozen=True)
class Validacion:
    """Resultado: número normalizado, coincidencia y dígito esperado por la fórmula."""

    nit: str
    valido: bool
    digito_esperado: str


def validar_nit(nit: str, digito: str) -> Validacion:
    """Compare un dígito separado con el calculado mediante la fórmula suministrada.

    Args:
        nit: Número sin el dígito de verificación.
        digito: Una cifra ASCII como texto.

    Returns:
        Resultado que incluye el dígito esperado, incluso cuando no coincide.

    Raises:
        ErrorNit: Si el número o el formato del dígito son incorrectos.
    """
    numero = normalizar_nit(nit)
    if not isinstance(digito, str) or len(digito) != 1 or not _son_cifras(digito):
        raise ErrorNit("El dígito de verificación debe ser una sola cifra")
    esperado = calcular_digito(numero)
    return Validacion(nit=numero, valido=digito == esperado, digito_esperado=esperado)
