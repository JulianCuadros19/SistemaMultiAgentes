"""Adaptador de modelo-unico-02-2: la función recibe los datos por nombre."""

from datetime import date
from decimal import Decimal

from reajuste_arriendo import calcular_reajuste


def reajustar(
    canon_actual: int,
    porcentaje_pactado: Decimal,
    ipc_anterior: Decimal,
    fecha_ultimo_reajuste: date,
    fecha_reajuste: date,
) -> tuple[Decimal, Decimal, Decimal]:
    r = calcular_reajuste(
        canon_actual=Decimal(canon_actual),
        porcentaje_pactado=porcentaje_pactado,
        ipc_anterior=ipc_anterior,
        fecha_base=fecha_ultimo_reajuste,
        fecha_reajuste=fecha_reajuste,
    )
    return r.nuevo_canon, r.porcentaje_aplicado, r.incremento
