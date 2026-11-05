"""Adaptador de sistema-02-2: la función recibe primero el IPC y luego lo pactado."""

from datetime import date
from decimal import Decimal

from aplicacion.calculo_reajuste import calcular_reajuste


def reajustar(
    canon_actual: int,
    porcentaje_pactado: Decimal,
    ipc_anterior: Decimal,
    fecha_ultimo_reajuste: date,
    fecha_reajuste: date,
) -> tuple[Decimal, Decimal, Decimal]:
    r = calcular_reajuste(
        Decimal(canon_actual),
        ipc_anterior,
        porcentaje_pactado,
        fecha_ultimo_reajuste,
        fecha_reajuste,
    )
    return r.canon_reajustado, r.porcentaje_aplicado, r.valor_incremento
