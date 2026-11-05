"""Adaptador de un-prompt-10-1: usa las funciones del dominio, debajo de las rutas."""

from predial.dominio import calcular_impuesto as _impuesto
from predial.dominio import consultar_tarifa as _tarifa

DESTINOS = {"lote": "lote urbanizable no edificado"}


def consultar_tarifa(destino: str, estrato) -> int:
    return _tarifa(DESTINOS.get(destino, destino), estrato)


def calcular_impuesto(avaluo: int, destino: str, estrato) -> int:
    return _impuesto(avaluo, DESTINOS.get(destino, destino), estrato)
