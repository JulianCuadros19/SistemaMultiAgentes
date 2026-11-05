"""Reglas de normalización y cálculo independientes del transporte HTTP."""

_PESOS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)


class NitInvalido(ValueError):
    """Indica que el NIT o el dígito recibido no se puede procesar."""


def normalizar_nit(nit: str) -> str:
    """Elimine puntos y guiones y compruebe entre 1 y 15 dígitos ASCII.

    Args:
        nit: Número del NIT, sin el dígito de verificación.

    Returns:
        Número normalizado, conservando sus ceros iniciales.

    Raises:
        NitInvalido: Si el dato no es texto o no cumple el formato y la longitud.
    """
    if not isinstance(nit, str):
        raise NitInvalido("El NIT debe ser texto")
    numero = nit.replace(".", "").replace("-", "")
    if not numero:
        raise NitInvalido("El NIT debe contener al menos un dígito")
    if not numero.isascii() or not numero.isdigit():
        raise NitInvalido("El NIT solo admite dígitos")
    if len(numero) > len(_PESOS):
        raise NitInvalido("El NIT admite como máximo 15 dígitos")
    return numero


def calcular_digito(nit: str) -> int:
    """Calcule el dígito aplicando los pesos desde la derecha.

    Args:
        nit: Número del NIT como texto, con puntos o guiones opcionales.

    Returns:
        Dígito de verificación entre 0 y 9.

    Raises:
        NitInvalido: Si el número no tiene un formato válido.
    """
    numero = normalizar_nit(nit)
    suma = sum(int(digito) * peso for digito, peso in zip(reversed(numero), _PESOS))
    residuo = suma % 11
    return residuo if residuo in (0, 1) else 11 - residuo


def validar_nit(nit: str, digito: str) -> tuple[bool, int]:
    """Compare el dígito recibido con el esperado, sin consultar registros.

    Args:
        nit: Número del NIT, sin el dígito de verificación.
        digito: Un único dígito ASCII enviado como texto.

    Returns:
        Pareja formada por la coincidencia y el dígito esperado.

    Raises:
        NitInvalido: Si el NIT o el dígito recibido tiene un formato incorrecto.
    """
    esperado = calcular_digito(nit)
    if (
        not isinstance(digito, str)
        or len(digito) != 1
        or not digito.isascii()
        or not digito.isdigit()
    ):
        raise NitInvalido("El dígito de verificación debe ser un único dígito de texto")
    return int(digito) == esperado, esperado
