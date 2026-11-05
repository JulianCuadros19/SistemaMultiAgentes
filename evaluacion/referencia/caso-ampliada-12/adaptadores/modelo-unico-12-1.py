"""Adaptador de modelo-unico-12-1: el dígito se recibe aparte y se devuelve como texto."""

from servicio_nit.dominio import calcular_digito as _calcular
from servicio_nit.dominio import validar_nit as _validar


def calcular_digito(numero: str) -> int:
    return int(_calcular(numero))


def validar_nit(nit: str) -> tuple[bool, int]:
    numero, _, digito = nit.rpartition("-")
    resultado = _validar(numero, digito)
    return resultado.valido, int(resultado.digito_esperado)
