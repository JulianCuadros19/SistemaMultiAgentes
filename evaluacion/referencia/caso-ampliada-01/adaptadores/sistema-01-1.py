"""Adaptador de sistema-01-1: la aplicación recibe los datos en otro orden y el valor como `Decimal`."""

from decimal import Decimal

from aplicacion.liquidacion import calcular_comision


def liquidar(
    tipo_negocio: str, valor: int, numero_asesores: int, estado: str
) -> tuple[Decimal, Decimal]:
    r = calcular_comision(tipo_negocio, numero_asesores, estado, Decimal(valor))
    return r.comision_de_la_inmobiliaria, r.comision_de_cada_asesor
