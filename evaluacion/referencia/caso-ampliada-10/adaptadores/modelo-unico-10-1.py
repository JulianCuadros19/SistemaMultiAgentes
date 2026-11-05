"""Adaptador de modelo-unico-10-1: las funciones reciben un diccionario, sin estrato si no aplica."""

from predial.servicio import calcular_impuesto as _impuesto
from predial.servicio import consultar_tarifa as _tarifa

DESTINOS = {"lote": "lote urbanizable no edificado"}


def _datos(destino, estrato) -> dict[str, object]:
    datos: dict[str, object] = {"destino": DESTINOS.get(destino, destino)}
    if estrato is not None:
        datos["estrato"] = estrato
    return datos


def consultar_tarifa(destino: str, estrato) -> int:
    return _tarifa(_datos(destino, estrato))["tarifa_por_mil"]


def calcular_impuesto(avaluo: int, destino: str, estrato) -> int:
    return _impuesto({**_datos(destino, estrato), "avaluo": avaluo})["impuesto_pesos"]
