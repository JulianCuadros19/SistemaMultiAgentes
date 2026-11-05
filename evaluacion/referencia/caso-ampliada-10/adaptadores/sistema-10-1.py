"""Adaptador de sistema-10-1: usa las funciones del servicio, debajo de las rutas."""

from servicios.tarifas import calcular_impuesto as _impuesto
from servicios.tarifas import obtener_tarifa

DESTINOS = {"lote": "lote urbanizable no edificado"}


def consultar_tarifa(destino: str, estrato) -> int:
    return obtener_tarifa(DESTINOS.get(destino, destino), estrato).tarifa


def calcular_impuesto(avaluo: int, destino: str, estrato) -> int:
    return _impuesto(avaluo, DESTINOS.get(destino, destino), estrato).impuesto_calculado
