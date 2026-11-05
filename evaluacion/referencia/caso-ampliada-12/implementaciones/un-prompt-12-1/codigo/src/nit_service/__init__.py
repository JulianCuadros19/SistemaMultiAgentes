"""Cálculo y validación del dígito de verificación de un NIT."""

from nit_service.dominio import (
    NitError,
    ResultadoValidacion,
    calcular_digito,
    normalizar_numero,
    validar_nit,
    validar_nit_completo,
)

__all__ = [
    "NitError",
    "ResultadoValidacion",
    "calcular_digito",
    "normalizar_numero",
    "validar_nit",
    "validar_nit_completo",
]
