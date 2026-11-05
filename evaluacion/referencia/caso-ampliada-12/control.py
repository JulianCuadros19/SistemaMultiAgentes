"""Implementación de control del caso 12, para validar las pruebas de referencia (ADR-0019).

No participa en la comparación: sirve para comprobar que las pruebas pasan con una implementación
que sigue la ficha y fallan con cada mutante de `mutantes.json`. Expone directamente la interfaz de
referencia, así que hace también de adaptador.
"""

PESOS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)
SOLO_DIGITOS = "El NIT solo admite dígitos"
MAXIMO = "El NIT admite como máximo 15 dígitos"


def _limpiar(numero: str) -> str:
    limpio = numero.strip().replace(".", "").replace("-", "")
    if not limpio or not all(caracter in "0123456789" for caracter in limpio):
        raise ValueError(SOLO_DIGITOS)
    if len(limpio) > len(PESOS):
        raise ValueError(MAXIMO)
    return limpio


def calcular_digito(numero: str) -> int:
    """Dígito de verificación del número."""
    limpio = _limpiar(numero)
    suma = sum(int(digito) * peso for digito, peso in zip(reversed(limpio), PESOS, strict=False))
    residuo = suma % 11
    return residuo if residuo in (0, 1) else 11 - residuo


def validar_nit(nit: str) -> tuple[bool, int]:
    """Si el NIT completo es válido, y el dígito esperado."""
    numero, _, digito = nit.strip().rpartition("-")
    esperado = calcular_digito(numero)
    if len(digito) != 1 or digito not in "0123456789":
        raise ValueError("El dígito de verificación debe ser un dígito de 0 a 9")
    return int(digito) == esperado, esperado
