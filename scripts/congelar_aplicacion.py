"""Congela en docker/aplicacion/versiones.txt las versiones del entorno donde pasan las pruebas.

La imagen de la aplicación instala sus dependencias con estas versiones como restricciones
(ADR-0017), así se construye igual en cualquier máquina. Se corre desde la raíz, con el .venv
activo, después de actualizar una dependencia y de que pasen las pruebas sin costo:

    python scripts/congelar_aplicacion.py
"""

import subprocess
import sys
from pathlib import Path

VERSIONES = Path(__file__).resolve().parents[1] / "docker" / "aplicacion" / "versiones.txt"
ENCABEZADO = (
    "# Versiones exactas de la imagen de la aplicación, también las transitivas (ADR-0017).\n"
    "# Son las del entorno donde pasan las pruebas del sistema; la imagen las usa como\n"
    "# restricciones al construirse. Se regeneran con scripts/congelar_aplicacion.py.\n"
)


def main() -> None:
    """Escribe el encabezado y el `pip freeze` del intérprete actual, sin el propio paquete."""
    congeladas = subprocess.run(
        [sys.executable, "-m", "pip", "freeze", "--exclude-editable"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    VERSIONES.write_text(ENCABEZADO + congeladas, encoding="utf-8")
    print(f"{len(congeladas.splitlines())} versiones en {VERSIONES}")


if __name__ == "__main__":
    main()
