"""Implementación de control del caso 02, para validar las pruebas de referencia (ADR-0019).

No participa en la comparación: sirve para comprobar que las pruebas pasan con una implementación
que sigue la ficha y fallan con cada mutante de `mutantes.json`. Expone directamente la interfaz de
referencia, así que hace también de adaptador.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

DOCE_MESES = "El contrato aún no cumple doce meses desde el último reajuste"


def _meses_cumplidos(desde: date, hasta: date) -> int:
    meses = (hasta.year - desde.year) * 12 + (hasta.month - desde.month)
    return meses - 1 if hasta.day < desde.day else meses


def reajustar(
    canon_actual: int,
    porcentaje_pactado: Decimal,
    ipc_anterior: Decimal,
    fecha_ultimo_reajuste: date,
    fecha_reajuste: date,
) -> tuple[int, Decimal, int]:
    """Nuevo canon, porcentaje aplicado e incremento."""
    if canon_actual <= 0:
        raise ValueError("El canon actual debe ser mayor que cero")
    if not Decimal(0) <= porcentaje_pactado <= Decimal(100):
        raise ValueError("El porcentaje pactado debe estar entre 0 y 100")
    if _meses_cumplidos(fecha_ultimo_reajuste, fecha_reajuste) < 12:
        raise ValueError(DOCE_MESES)
    if ipc_anterior <= 0:
        return canon_actual, Decimal(0), 0
    aplicado = min(porcentaje_pactado, ipc_anterior)
    centenas = Decimal(canon_actual) * (1 + aplicado / 100) / 100
    nuevo = int(centenas.quantize(Decimal(1), rounding=ROUND_HALF_UP)) * 100
    return nuevo, aplicado, nuevo - canon_actual
