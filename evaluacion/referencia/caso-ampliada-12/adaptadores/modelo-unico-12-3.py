"""Adaptador de modelo-unico-12-3: los dígitos se devuelven como texto."""

from nit_service.dominio import calcular, validar


def calcular_digito(numero: str) -> int:
    return int(calcular(numero))


def validar_nit(nit: str) -> tuple[bool, int]:
    resultado = validar(nit)
    return resultado["valido"], int(resultado["digito_esperado"])
