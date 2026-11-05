"""Adaptador de un-prompt-01-1: la función devuelve la comisión de cada asesor en una tupla."""

from comisiones._calculo import calcular_comisiones


def liquidar(tipo_negocio: str, valor: int, numero_asesores: int, estado: str) -> tuple[int, int]:
    r = calcular_comisiones(
        tipo_negocio=tipo_negocio, valor=valor, numero_asesores=numero_asesores, estado=estado
    )
    return r.comision_inmobiliaria, r.comisiones_asesores[0]
