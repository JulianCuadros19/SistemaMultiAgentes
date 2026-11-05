"""Adaptador de un-prompt-12-1: usa las funciones del dominio, debajo de las rutas."""

from nit_service.dominio import calcular_digito as _calcular
from nit_service.dominio import validar_nit_completo


def calcular_digito(numero: str) -> int:
    return _calcular(numero)


def validar_nit(nit: str) -> tuple[bool, int]:
    resultado = validar_nit_completo(nit)
    return resultado.valido, resultado.digito_esperado
