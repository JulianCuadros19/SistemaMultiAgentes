"""Implementación de control del caso 10, para validar las pruebas de referencia (ADR-0019).

No participa en la comparación: sirve para comprobar que las pruebas pasan con una implementación
que sigue la ficha y fallan con cada mutante de `mutantes.json`. Expone directamente la interfaz de
referencia, así que hace también de adaptador.
"""

from decimal import ROUND_HALF_UP, Decimal

RESIDENCIAL = {1: 5, 2: 6, 3: 8, 4: 10, 5: 12, 6: 14}
OTROS = {"comercial": 11, "industrial": 12, "lote": 33}


def consultar_tarifa(destino: str, estrato: int | None) -> int:
    """Tarifa en pesos por cada mil pesos de avalúo."""
    if destino == "residencial":
        if estrato not in RESIDENCIAL:
            raise ValueError("Estrato inválido")
        return RESIDENCIAL[estrato]
    if destino in OTROS:
        return OTROS[destino]
    raise ValueError("Destino económico no reconocido")


def calcular_impuesto(avaluo: int, destino: str, estrato: int | None) -> int:
    """Impuesto en pesos."""
    if avaluo <= 0:
        raise ValueError("El avalúo debe ser mayor que cero")
    tarifa = consultar_tarifa(destino, estrato)
    impuesto = Decimal(avaluo) * tarifa / 1000
    return int(impuesto.quantize(Decimal(1), rounding=ROUND_HALF_UP))
