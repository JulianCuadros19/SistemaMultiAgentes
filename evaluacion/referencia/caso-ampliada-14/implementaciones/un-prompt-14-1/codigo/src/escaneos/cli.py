"""Interfaz de terminal de la herramienta de escaneos."""

import argparse
import sys
from collections.abc import Iterator, Sequence
from typing import cast

from escaneos.core import Informe, Operacion, procesar


def _parser() -> argparse.ArgumentParser:
    """Construir los tres comandos independientes."""
    parser = argparse.ArgumentParser(
        prog="escaneos",
        description="Validar, renombrar o contar nombres de archivos de escaneos.",
    )
    comandos = parser.add_subparsers(dest="operacion", required=True)
    for nombre, ayuda in (
        ("validar", "Listar nombres inválidos y sus motivos"),
        ("renombrar", "Corregir nombres sin sobrescribir destinos"),
        ("reporte", "Contar nombres válidos por año y tipo"),
    ):
        comando = comandos.add_parser(nombre, help=ayuda)
        comando.add_argument("carpeta", help="Carpeta obligatoria de escaneos")
        if nombre == "renombrar":
            comando.add_argument(
                "--simular", action="store_true", help="Mostrar cambios sin modificar archivos"
            )
    return parser


def _lineas(informe: Informe) -> Iterator[str]:
    """Generar una línea por archivo y el resumen final."""
    for archivo in informe.archivos:
        destino = f" -> {archivo.destino!r}" if archivo.destino is not None else ""
        motivo = archivo.motivo.replace("\r", "\\r").replace("\n", "\\n")
        yield f"[{archivo.estado}] {archivo.nombre!r}{destino}: {motivo}"
    totales = ", ".join(f"{estado}={total}" for estado, total in informe.totales.items())
    sufijo = f", {totales}" if totales else ""
    yield f"Resumen: Total={informe.total}{sufijo}"
    if informe.operacion == "reporte":
        anios = ", ".join(f"{anio}={total}" for anio, total in informe.por_anio.items())
        tipos = ", ".join(f"{tipo}={total}" for tipo, total in informe.por_tipo.items())
        yield f"Por año: {anios or '(sin archivos válidos)'}"
        yield f"Por tipo: {tipos or '(sin archivos válidos)'}"


def main(argv: Sequence[str] | None = None) -> int:
    """Ejecutar la CLI y devolver su código de salida.

    Los errores de argumentos terminan mediante SystemExit de argparse.
    Los resultados van a stdout y los errores de acceso a la carpeta a stderr.
    """
    argumentos = _parser().parse_args(argv)
    try:
        informe = procesar(
            argumentos.carpeta,
            cast(Operacion, argumentos.operacion),
            simular=getattr(argumentos, "simular", False),
        )
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    for linea in _lineas(informe):
        print(linea)
    return informe.codigo_salida
