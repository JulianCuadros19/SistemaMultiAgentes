"""Adaptador de sistema-12-2: usa las funciones del servicio, debajo de las rutas."""

from servicios.nit_validacion import calcular_digito as _calcular
from servicios.nit_validacion import validar_nit as _validar


def calcular_digito(numero: str) -> int:
    return _calcular(numero)


def validar_nit(nit: str) -> tuple[bool, int]:
    return _validar(nit)
