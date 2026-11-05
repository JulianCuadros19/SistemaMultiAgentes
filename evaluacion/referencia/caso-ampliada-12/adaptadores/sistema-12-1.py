"""Adaptador de sistema-12-1: usa las funciones del servicio, debajo de las rutas."""

from servicios.nit import calcular_digito as _calcular
from servicios.nit import validar_nit as _validar


def calcular_digito(numero: str) -> int:
    return _calcular(numero)


def validar_nit(nit: str) -> tuple[bool, int]:
    valido, esperado, _ = _validar(nit)
    return valido, esperado
