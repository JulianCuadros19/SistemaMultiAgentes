"""Implementación de control del caso 01, para validar las pruebas de referencia (ADR-0019).

No participa en la comparación: sirve para comprobar que las pruebas pasan con una implementación
que sigue la ficha y fallan con cada mutante de `mutantes.json`. Expone directamente la interfaz de
referencia, así que hace también de adaptador.
"""

from decimal import ROUND_HALF_UP, Decimal

PORCENTAJE_VENTA = Decimal("0.03")
PORCENTAJE_ASESORES = Decimal("0.40")
MINIMO_POR_ASESOR = 300_000


def _pesos(valor: Decimal) -> int:
    return int(valor.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def liquidar(tipo_negocio: str, valor: int, numero_asesores: int, estado: str) -> tuple[int, int]:
    """Comisión de la inmobiliaria y comisión de cada asesor, en pesos."""
    if estado != "cerrado":
        raise ValueError("El negocio aún no está cerrado")
    if valor <= 0:
        raise ValueError("El valor debe ser mayor que cero")
    if numero_asesores not in (1, 2):
        raise ValueError("El número de asesores debe ser 1 o 2")
    if tipo_negocio == "venta":
        comision = Decimal(valor) * PORCENTAJE_VENTA
    elif tipo_negocio == "arriendo":
        comision = Decimal(valor)
    else:
        raise ValueError("Tipo de negocio desconocido")
    por_asesor = comision * PORCENTAJE_ASESORES / numero_asesores
    return _pesos(comision), max(_pesos(por_asesor), MINIMO_POR_ASESOR)
