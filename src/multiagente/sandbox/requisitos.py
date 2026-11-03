"""Versiones de las librerías instaladas en la imagen del entorno aislado.

En `docker/sandbox/` están versionados:
- `requisitos.txt`, con una versión fija por librería del catálogo tecnológico;
- `versiones.txt`, con la versión de cada paquete instalado, también los transitivos;
- `cierres.json`, con las dependencias, directas y transitivas, de cada librería.

El paquete exportado de un módulo los usa para su `requirements.txt`: son las versiones con que
el tester lo probó (RF-35, ADR-0014).
"""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

CARPETA_IMAGEN = Path(__file__).resolve().parents[3] / "docker" / "sandbox"
"""Carpeta de la imagen del entorno aislado, con sus archivos de versiones."""

RUTA_REQUISITOS = CARPETA_IMAGEN / "requisitos.txt"

_NOMBRE = re.compile(r"[A-Za-z0-9_.-]+")


def nombre_canonico(nombre: str) -> str:
    """Nombre de una distribución, sin extras y normalizado según PEP 503.

    Args:
        nombre: Nombre tal como se declara, por ejemplo `psycopg[binary]` o `typing_extensions`.

    Returns:
        El nombre en minúsculas y con guiones: `psycopg`, `typing-extensions`.
    """
    return re.sub(r"[-_.]+", "-", nombre.split("[", 1)[0].strip()).lower()


def _lineas(ruta: Path) -> list[str]:
    """Líneas con contenido de un archivo de requisitos, sin comentarios."""
    lineas = (linea.split("#", 1)[0].strip() for linea in ruta.read_text("utf-8").splitlines())
    return [linea for linea in lineas if linea]


def requisitos_del_entorno(ruta: Path = RUTA_REQUISITOS) -> dict[str, str]:
    """Lee los requisitos fijados del entorno aislado.

    Args:
        ruta: Archivo de requisitos de la imagen.

    Returns:
        La línea de requisito de cada librería, por su nombre canónico; por ejemplo,
        `psycopg` → `psycopg[binary]==3.3.6`.
    """
    requisitos: dict[str, str] = {}
    for linea in _lineas(ruta):
        if nombre := _NOMBRE.match(linea):
            requisitos[nombre_canonico(nombre.group(0))] = linea
    return requisitos


@dataclass(frozen=True)
class VersionesProbadas:
    """Versiones con que el tester prueba los módulos en el entorno aislado.

    Attributes:
        requisitos: Línea de requisito de cada librería del catálogo, por su nombre canónico.
        versiones: Línea `nombre==versión` de cada paquete instalado, por su nombre canónico.
        cierres: Nombres canónicos de las dependencias, directas y transitivas, de cada
            librería del catálogo.
    """

    requisitos: Mapping[str, str] = field(default_factory=dict)
    versiones: Mapping[str, str] = field(default_factory=dict)
    cierres: Mapping[str, tuple[str, ...]] = field(default_factory=dict)


def versiones_probadas(carpeta: Path = CARPETA_IMAGEN) -> VersionesProbadas:
    """Lee las versiones con que el entorno aislado prueba los módulos.

    Args:
        carpeta: Carpeta de la imagen, con `requisitos.txt`, `versiones.txt` y `cierres.json`.

    Returns:
        Los requisitos del catálogo, la versión de cada paquete instalado y el cierre de
        dependencias de cada librería.
    """
    versiones = {
        nombre_canonico(linea.split("==", 1)[0]): linea
        for linea in _lineas(carpeta / "versiones.txt")
    }
    cierres = json.loads((carpeta / "cierres.json").read_text(encoding="utf-8"))
    return VersionesProbadas(
        requisitos=requisitos_del_entorno(carpeta / "requisitos.txt"),
        versiones=versiones,
        cierres={nombre: tuple(dependencias) for nombre, dependencias in cierres.items()},
    )
