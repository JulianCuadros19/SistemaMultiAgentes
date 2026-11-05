"""Interfaz de terminal para operaciones independientes de crédito."""

import argparse
import sys
from collections.abc import Sequence

from credito_vivienda.calculos import (
    Credito,
    calcular_cuota,
    calcular_resumen,
    crear_credito,
    generar_tabla,
    guardar_csv,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="credito_vivienda",
        description="Calcula un crédito de vivienda con cuota fija, en pesos.",
    )
    operaciones = parser.add_subparsers(dest="operacion", required=True)
    for nombre in ("cuota", "tabla", "resumen"):
        comando = operaciones.add_parser(nombre)
        comando.add_argument("--monto", required=True, help="Monto en pesos, sin separadores.")
        comando.add_argument("--plazo", required=True, type=int, help="Plazo en meses: 12 a 240.")
        comando.add_argument(
            "--tasa",
            required=True,
            help="Tasa efectiva anual en porcentaje: 1 a 30; decimal con punto.",
        )
        if nombre == "tabla":
            comando.add_argument("--csv", help="Archivo CSV que se crea o sobrescribe.")
    return parser


def _ejecutar(args: argparse.Namespace, credito: Credito) -> None:
    if args.operacion == "cuota":
        print(f"Cuota mensual: {calcular_cuota(credito)} pesos")
    elif args.operacion == "resumen":
        resumen = calcular_resumen(credito)
        print(f"Total pagado: {resumen.total_pagado} pesos")
        print(f"Total de intereses: {resumen.total_intereses} pesos")
    else:
        filas = generar_tabla(credito)
        if args.csv is not None:
            guardar_csv(filas, args.csv)
        print("mes\tcuota\tinteres\tabono_capital\tsaldo")
        for fila in filas:
            print(
                f"{fila.mes}\t{fila.cuota}\t{fila.interes}\t"
                f"{fila.abono_capital}\t{fila.saldo}"
            )


def main(argv: Sequence[str] | None = None) -> int:
    """Ejecuta la CLI; retorna 0 al terminar o 2 ante datos o escritura inválidos."""
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        credito = crear_credito(args.monto, args.plazo, args.tasa)
        _ejecutar(args, credito)
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0
