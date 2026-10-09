"""Configuración de estilo del código generado (`config/estilo_generado/`).

Es configuración versionada, no conocimiento (decisiones 2 y 3 de `CLAUDE.md`): N10 la recibe
tal cual como dato y N12 la aplica con Ruff. La huella identifica qué versión de la configuración
rigió cada versión del código (RF-36).
"""

import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict

RUTA_ESTILO_GENERADO = (
    Path(__file__).resolve().parents[3] / "config" / "estilo_generado" / "ruff.toml"
)
"""Configuración de Ruff del código que genera el agente desarrollador."""


class EstiloGenerado(BaseModel):
    """Contenido de la configuración de estilo y su huella SHA-256."""

    model_config = ConfigDict(frozen=True)

    archivo: str
    texto: str
    huella: str


def cargar_estilo(ruta: Path = RUTA_ESTILO_GENERADO) -> EstiloGenerado:
    """Lee la configuración de estilo del código generado.

    Args:
        ruta: Archivo de configuración de Ruff.

    Returns:
        El nombre del archivo, su contenido y su huella.
    """
    datos = ruta.read_bytes()
    return EstiloGenerado(
        archivo=ruta.name,
        texto=datos.decode("utf-8"),
        huella=hashlib.sha256(datos).hexdigest(),
    )
