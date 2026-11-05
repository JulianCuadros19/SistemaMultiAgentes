"""Interfaz de terminal para las tres operaciones independientes."""

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import Never

from credito_vivienda import (
    DatoInvalido,
    ReglasPendientes,
    Solicitud,
    calcular_cuota,
    calcular_resumen,
    generar_tabla,
    leer_solicitud,
)

_OPERACIONES: dict[str, Callable[[Solicitud], Never]] = {
    "cuota": calcular_cuota,
    "tabla": generar_tabla,
    "resumen": calcular_resumen,
}


def _crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="credito_vivienda",
        description=(
            "Crédito de vivienda: validación disponible; cálculo pendiente de "
            "definir las reglas de redondeo."
        ),
    )
    operaciones = parser.add_subparsers(dest="operacion", required=True)
    for nombre, descripcion in (
        ("cuota", "Solicitar la cuota mensual."),
        ("tabla", "Solicitar la tabla de amortización."),
        ("resumen", "Solicitar total pagado e intereses."),
    ):
        comando = operaciones.add_parser(nombre, help=descripcion)
        comando.add_argument("--monto", required=True, help="Pesos sin separadores de miles.")
        comando.add_argument("--plazo", required=True, help="Plazo en meses, entre 12 y 240.")
        comando.add_argument(
            "--tasa-anual", required=True, help="Porcentaje anual: 1 a 30; hasta dos decimales."
        )
        if nombre == "tabla":
            comando.add_argument(
                "--csv",
                metavar="RUTA",
                help="Solicitar CSV en esa ruta; no se escribe mientras el cálculo esté pendiente.",
            )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Ejecuta una operación sin inventar resultados financieros.

    Args:
        argv: Argumentos sin el nombre del programa; None usa los de la terminal.

    Returns:
        2 por dato inválido o 3 por reglas financieras pendientes.

    Raises:
        SystemExit: Para ayuda (0) o errores de sintaxis de argparse (2).
    """
    argumentos = _crear_parser().parse_args(argv)
    try:
        solicitud = leer_solicitud(
            argumentos.monto, argumentos.plazo, argumentos.tasa_anual
        )
        _OPERACIONES[argumentos.operacion](solicitud)
    except DatoInvalido as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    except ReglasPendientes as error:
        print(f"Error: {error}", file=sys.stderr)
        return 3
