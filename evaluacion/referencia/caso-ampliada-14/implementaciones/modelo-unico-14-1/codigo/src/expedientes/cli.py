"""Interfaz de terminal de la herramienta de expedientes."""

import argparse
import sys
from collections.abc import Sequence
from typing import cast

from expedientes.core import CarpetaError, Informe, Modo, procesar_carpeta


def _imprimir(informe: Informe, modo: str) -> None:
    for item in informe.resultados:
        cambio = f" -> {item.destino}" if item.destino is not None else ""
        print(f"{item.nombre}{cambio}: {item.estado} — {item.detalle}")
    totales = ", ".join(f"{estado}: {cantidad}" for estado, cantidad in informe.totales.items())
    print(f"Resumen: archivos: {len(informe.resultados)}" + (f"; {totales}" if totales else ""))
    if modo == "reportar":
        print("Por año: " + (", ".join(f"{k}: {v}" for k, v in informe.por_anio.items()) or "0"))
        print("Por tipo: " + (", ".join(f"{k}: {v}" for k, v in informe.por_tipo.items()) or "0"))


def main(argv: Sequence[str] | None = None) -> int:
    """Ejecuta la interfaz y devuelve un código de salida 0, 1 o 2.

    Los argumentos inválidos los rechaza argparse mediante SystemExit(2).
    """
    parser = argparse.ArgumentParser(description="Revisa nombres de expedientes escaneados")
    parser.add_argument("modo", choices=("validar", "renombrar", "reportar"))
    parser.add_argument("carpeta", help="Carpeta de escaneos")
    parser.add_argument("--simular", action="store_true", help="No guardar el renombrado")
    argumentos = parser.parse_args(argv)
    if argumentos.simular and argumentos.modo != "renombrar":
        parser.error("--simular solo se admite con renombrar")
    try:
        informe = procesar_carpeta(
            argumentos.carpeta,
            cast(Modo, argumentos.modo),
            simular=argumentos.simular,
        )
    except CarpetaError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    _imprimir(informe, argumentos.modo)
    return informe.codigo_salida
