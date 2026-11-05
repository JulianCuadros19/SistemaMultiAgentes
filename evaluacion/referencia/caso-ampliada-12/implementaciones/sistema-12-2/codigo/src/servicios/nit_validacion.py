"""Cálculo y validación de NIT sin dependencias de transporte.

El cálculo usa la convención de pesos y residuos indicada en el documento de uso.
"""


class NITSoloDigitosError(ValueError):
    """Indica que el valor no contiene exclusivamente dígitos permitidos."""

    def __init__(self, mensaje: str) -> None:
        """Inicializa el error.

        Args:
            mensaje: Explicación del dato rechazado.
        """
        super().__init__(mensaje)


class NITMaximoDigitosError(ValueError):
    """Indica que el valor supera el límite de dígitos."""

    def __init__(self, mensaje: str) -> None:
        """Inicializa el error.

        Args:
            mensaje: Explicación del límite superado.
        """
        super().__init__(mensaje)


def _limpiar(valor: str) -> str:
    if not isinstance(valor, str):
        raise NITSoloDigitosError("El NIT solo admite dígitos")
    limpio = valor.replace("-", "").replace(".", "")
    if not limpio or any(caracter not in "0123456789" for caracter in limpio):
        raise NITSoloDigitosError("El NIT solo admite dígitos")
    return limpio


def _comprobar_limite(numero: str) -> None:
    if len(numero) > 15:
        raise NITMaximoDigitosError("El NIT admite como máximo 15 dígitos")


def _calcular(numero: str) -> int:
    pesos = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)
    suma = sum(
        int(digito) * peso
        for digito, peso in zip(reversed(numero), pesos, strict=False)
    )
    residuo = suma % 11
    return residuo if residuo < 2 else 11 - residuo


def calcular_digito(numero: str) -> int:
    """Calcula el dígito esperado, aceptando puntos y guiones.

    Args:
        numero: Número de uno a quince dígitos; puede incluir separadores.

    Returns:
        Dígito esperado entre cero y nueve.

    Raises:
        NITSoloDigitosError: Si no hay dígitos o existen caracteres no permitidos.
        NITMaximoDigitosError: Si el número supera quince dígitos.
    """
    limpio = _limpiar(numero)
    cuerpo = numero
    if "-" in numero:
        prefijo, sufijo = numero.rsplit("-", 1)
        if len(sufijo) == 1 and sufijo in "0123456789" and prefijo:
            cuerpo = prefijo
    if cuerpo != numero:
        limpio = _limpiar(cuerpo)
    _comprobar_limite(limpio)
    return _calcular(limpio)


def validar_nit(nit: str) -> tuple[bool, int]:
    """Compara el último dígito del NIT con el dígito esperado.

    Args:
        nit: NIT completo con número y dígito; admite puntos y guiones.

    Returns:
        Par formado por la validez y el dígito esperado.

    Raises:
        NITSoloDigitosError: Si hay caracteres no permitidos o falta el número.
        NITMaximoDigitosError: Si el NIT limpio supera quince dígitos.
    """
    limpio = _limpiar(nit)
    _comprobar_limite(limpio)
    if len(limpio) < 2:
        raise NITSoloDigitosError("El NIT solo admite dígitos")
    esperado = _calcular(limpio[:-1])
    return int(limpio[-1]) == esperado, esperado
