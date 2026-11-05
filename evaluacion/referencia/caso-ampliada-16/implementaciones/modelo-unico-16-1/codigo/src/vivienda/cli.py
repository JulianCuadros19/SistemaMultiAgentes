"""Interfaz de terminal para cuota, tabla, CSV y resumen."""

import argparse
import csv
import sys
from collections.abc import Sequence
from decimal import DecimalException
from pathlib import Path

from vivienda.calculo import (
    EntradaInvalida,
    FilaAmortizacion,
    amortizacion,
    crear_credito,
    cuota_mensual,
    resumen,
)

_COLUMNAS = ("mes", "cuota", "interes", "capital", "saldo")


def _argumentos(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="vivienda",
        description="Calcula créditos de vivienda en pesos, sin seguros ni comisiones.",
    )
    comandos = parser.add_subparsers(dest="comando", required=True)
    for nombre, ayuda in (
        ("cuota", "Mostrar la cuota mensual."),
        ("tabla", "Mostrar toda la amortización y, opcionalmente, guardar un CSV."),
        ("resumen", "Mostrar el total pagado y el total de intereses."),
    ):
        comando = comandos.add_parser(nombre, help=ayuda)
        comando.add_argument("--monto", required=True, help="Pesos enteros: 10000000 a 500000000.")
        comando.add_argument("--plazo", required=True, help="Meses enteros: 12 a 240.")
        comando.add_argument("--tasa", required=True, help="Tasa efectiva anual: 1 a 30, p. ej. 12.50.")
        if nombre == "tabla":
            comando.add_argument("--csv", type=Path, help="Archivo CSV de destino.")
    return parser.parse_args(argv)


def _valores(fila: FilaAmortizacion) -> tuple[int, int, int, int, int]:
    return fila.mes, fila.cuota, fila.interes, fila.capital, fila.saldo


def _guardar_csv(ruta: Path, filas: tuple[FilaAmortizacion, ...]) -> None:
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(_COLUMNAS)
        escritor.writerows(_valores(fila) for fila in filas)


def main(argv: Sequence[str] | None = None) -> int:
    """Ejecuta la terminal y devuelve 0 en éxito o 1 ante errores de datos o archivo.

    Los errores de sintaxis de argumentos son gestionados por argparse, con
    mensaje en stderr y código 2. No se utiliza entrada interactiva.
    """
    argumentos = _argumentos(argv)
    try:
        credito = crear_credito(argumentos.monto, argumentos.plazo, argumentos.tasa)
        if argumentos.comando == "cuota":
            print(f"Cuota mensual: {cuota_mensual(credito)} pesos")
        elif argumentos.comando == "resumen":
            totales = resumen(credito)
            print(f"Total pagado: {totales.total_pagado} pesos")
            print(f"Total de intereses: {totales.total_intereses} pesos")
        else:
            filas = amortizacion(credito)
            if argumentos.csv is not None:
                _guardar_csv(argumentos.csv, filas)
            print("\t".join(_COLUMNAS))
            for fila in filas:
                print("\t".join(str(valor) for valor in _valores(fila)))
    except EntradaInvalida as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"Error al mostrar o guardar el resultado: {error}", file=sys.stderr)
        return 1
    except DecimalException as error:
        print(f"Error en el cálculo decimal: {error}", file=sys.stderr)
        return 1
    return 0
