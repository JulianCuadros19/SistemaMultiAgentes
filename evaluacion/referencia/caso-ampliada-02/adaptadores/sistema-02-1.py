"""Adaptador de sistema-02-1: la aplicación recibe el canon como `Decimal`."""

from datetime import date
from decimal import Decimal

from aplicacion.reajuste import realizar_reajuste


def reajustar(
    canon_actual: int,
    porcentaje_pactado: Decimal,
    ipc_anterior: Decimal,
    fecha_ultimo_reajuste: date,
    fecha_reajuste: date,
) -> tuple[Decimal, Decimal, Decimal]:
    r = realizar_reajuste(
        Decimal(canon_actual),
        porcentaje_pactado,
        ipc_anterior,
        fecha_ultimo_reajuste,
        fecha_reajuste,
    )
    return r.nuevo_canon, r.porcentaje_aplicado, r.valor_del_incremento
