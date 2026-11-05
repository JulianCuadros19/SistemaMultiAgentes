"""Operación de renombrado invocable desde Python o desde la terminal."""

import argparse
import sys

from dominio.convencion import CambioNombre, ConflictoRenombrado, ErrorRenombrado
from servicios.renombrado import CarpetaNoExiste, GestorArchivos, renombrar_archivos


def ejecutar_renombrar(
    ruta: str, modo_simulacion: bool
) -> tuple[list[CambioNombre], list[ConflictoRenombrado], list[ErrorRenombrado]]:
    """Ejecuta el renombrado independiente de los archivos.

    Args:
        ruta: Carpeta cuyos archivos se normalizan.
        modo_simulacion: True muestra cambios sin aplicarlos.

    Returns:
        Cambios, conflictos y errores.

    Raises:
        CarpetaNoExiste: La carpeta no existe.
        TypeError: El modo de simulación no es booleano.
    """
    return renombrar_archivos(ruta, modo_simulacion, GestorArchivos())


def _principal() -> int:
    argumentos = argparse.ArgumentParser(description="Normaliza nombres de escaneos")
    argumentos.add_argument("ruta", help="Carpeta de escaneos")
    argumentos.add_argument("--simulacion", action="store_true", help="No aplica los cambios")
    opciones = argumentos.parse_args()
    try:
        cambios, conflictos, errores = ejecutar_renombrar(opciones.ruta, opciones.simulacion)
    except CarpetaNoExiste as error:
        print(str(error), file=sys.stderr)
        return 1
    for cambio in cambios:
        print(f"{cambio.anterior} -> {cambio.nuevo}")
    for conflicto in conflictos:
        print(f"{conflicto.archivo}: {conflicto.motivo}")
    for error in errores:
        print(f"{error.archivo}: {error.motivo}")
    return 0


if __name__ == "__main__":
    sys.exit(_principal())
