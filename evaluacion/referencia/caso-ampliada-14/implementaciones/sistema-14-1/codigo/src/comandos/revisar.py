"""Operación de revisión invocable desde Python o desde la terminal."""

import argparse
import sys

from servicios.revision import CarpetaNoExiste, GestorArchivos, revisar_carpeta


def ejecutar_revisar(ruta: str) -> list[str]:
    """Ejecuta la revisión independiente de una carpeta.

    Args:
        ruta: Carpeta que se revisa.

    Returns:
        Lista de archivos encontrados.

    Raises:
        CarpetaNoExiste: La carpeta no existe.
    """
    return revisar_carpeta(ruta, GestorArchivos())


def _principal() -> int:
    argumentos = argparse.ArgumentParser(description="Revisa una carpeta de escaneos")
    argumentos.add_argument("ruta", help="Carpeta de escaneos")
    opciones = argumentos.parse_args()
    try:
        archivos = ejecutar_revisar(opciones.ruta)
    except CarpetaNoExiste as error:
        print(str(error), file=sys.stderr)
        return 1
    print("Revisión completada")
    for archivo in archivos:
        print(archivo)
    return 0


if __name__ == "__main__":
    sys.exit(_principal())
