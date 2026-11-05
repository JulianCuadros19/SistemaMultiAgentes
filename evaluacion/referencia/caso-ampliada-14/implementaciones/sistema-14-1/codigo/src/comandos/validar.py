"""Operación de validación invocable desde Python o desde la terminal."""

import argparse
import sys

from dominio.convencion import ResultadoValidacion
from servicios.validacion import CarpetaNoExiste, GestorArchivos, validar_nombres


def ejecutar_validar(ruta: str) -> tuple[list[ResultadoValidacion], dict[str, int]]:
    """Ejecuta la validación independiente de los nombres.

    Args:
        ruta: Carpeta cuyos nombres se validan.

    Returns:
        Incumplimientos y totales por motivo.

    Raises:
        CarpetaNoExiste: La carpeta no existe.
    """
    return validar_nombres(ruta, GestorArchivos())


def _principal() -> int:
    argumentos = argparse.ArgumentParser(description="Valida nombres de escaneos")
    argumentos.add_argument("ruta", help="Carpeta de escaneos")
    opciones = argumentos.parse_args()
    try:
        resultados, totales = ejecutar_validar(opciones.ruta)
    except CarpetaNoExiste as error:
        print(str(error), file=sys.stderr)
        return 1
    for resultado in resultados:
        print(f"{resultado.archivo}: {resultado.motivo}")
    for motivo, total in totales.items():
        print(f"{motivo}: {total}")
    print(f"Total de incumplimientos: {len(resultados)}")
    return 0


if __name__ == "__main__":
    sys.exit(_principal())
