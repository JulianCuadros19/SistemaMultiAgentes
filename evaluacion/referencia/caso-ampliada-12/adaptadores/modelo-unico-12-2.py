"""Adaptador de modelo-unico-12-2: el dígito se recibe aparte."""

from nit_service.dominio import calcular_digito as _calcular
from nit_service.dominio import validar_nit as _validar


def calcular_digito(numero: str) -> int:
    return _calcular(numero)


def validar_nit(nit: str) -> tuple[bool, int]:
    numero, _, digito = nit.rpartition("-")
    return _validar(numero, digito)
