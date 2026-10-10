"""Versiones de las librerías instaladas en la imagen del entorno aislado.

`docker/sandbox/requisitos.txt` fija una versión por librería del catálogo tecnológico. El
paquete exportado de un módulo las usa para su `requirements.txt`: son las versiones con que el
tester lo probó (RF-35).
"""

import re
from pathlib import Path

RUTA_REQUISITOS = Path(__file__).resolve().parents[3] / "docker" / "sandbox" / "requisitos.txt"

_NOMBRE = re.compile(r"[A-Za-z0-9_.-]+")


def requisitos_del_entorno(ruta: Path = RUTA_REQUISITOS) -> dict[str, str]:
    """Lee los requisitos fijados del entorno aislado.

    Args:
        ruta: Archivo de requisitos de la imagen.

    Returns:
        La línea de requisito de cada librería, por su nombre en minúsculas y sin extras; por
        ejemplo, `psycopg` → `psycopg[binary]==3.3.6`.
    """
    requisitos: dict[str, str] = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.split("#", 1)[0].strip()
        if linea and (nombre := _NOMBRE.match(linea)):
            requisitos[nombre.group(0).lower().replace("_", "-")] = linea
    return requisitos
