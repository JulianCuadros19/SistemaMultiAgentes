"""Operación de reporte invocable desde Python o desde la terminal."""

import argparse
import sys

from dominio.convencion import Reporte
from servicios.reporte import CarpetaNoExiste, GestorArchivos, generar_reporte


def ejecutar_reporte(ruta: str) -> Reporte:
    """Ejecuta el reporte independiente de la carpeta.

    Args:
        ruta: Carpeta sobre la que se informa.

    Returns:
        Líneas por archivo, conteos por año y tipo y total final.

    Raises:
        CarpetaNoExiste: La carpeta no existe.
    """
    return generar_reporte(ruta, GestorArchivos())


def _principal() -> int:
    argumentos = argparse.ArgumentParser(description="Genera un reporte de escaneos")
    argumentos.add_argument("ruta", help="Carpeta de escaneos")
    opciones = argumentos.parse_args()
    try:
        reporte = ejecutar_reporte(opciones.ruta)
    except CarpetaNoExiste as error:
        print(str(error), file=sys.stderr)
        return 1
    for linea in reporte.lineas_por_archivo:
        print(linea)
    for anio, tipos in sorted(reporte.conteos_por_anio_y_tipo.items()):
        for tipo, cantidad in sorted(tipos.items()):
            print(f"{anio} {tipo}: {cantidad}")
    print(f"Total de archivos: {reporte.total_archivos}")
    return 0


if __name__ == "__main__":
    sys.exit(_principal())
