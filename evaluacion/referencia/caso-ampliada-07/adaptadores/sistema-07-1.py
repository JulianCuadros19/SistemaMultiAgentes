"""Adaptador de sistema-07-1: corre el orquestador, lee su CSV y traduce los nombres de las columnas."""

import csv

from orquestacion.pipeline import Orquestador


def conciliar(
    banco_a: str, banco_b: str, banco_c: str, facturas: str, carpeta_salida: str
) -> tuple[list[dict[str, str]], dict[str, int]]:
    destino = f"{carpeta_salida}/resultados.csv"
    resumen = Orquestador().ejecutar(banco_a, banco_b, banco_c, facturas, destino)
    with open(destino, encoding="utf-8", newline="") as archivo:
        filas = [
            {
                "referencia": fila["referencia"],
                "valor_facturado": fila["valor facturado"],
                "valor_pagado": fila["valor pagado"],
                "banco": fila["banco"],
                "estado": fila["estado"],
                "diferencia": fila["diferencia"],
            }
            for fila in csv.DictReader(archivo)
        ]
    totales = {
        "conciliado": resumen.conciliado,
        "diferencia": resumen.diferencia,
        "pago sin factura": resumen.pago_sin_factura,
        "pendiente": resumen.pendiente,
    }
    return filas, totales
