"""Configuración de estilo del código generado (`config/estilo_generado/`).

Es configuración versionada, no conocimiento (decisiones 2 y 3 de `CLAUDE.md`): N10 la recibe
tal cual como dato y N12 la aplica con Ruff. La huella identifica qué versión de la configuración
rigió cada versión del código (RF-36).

Ruff solo lee el código: el análisis no ejecuta nada de lo generado y por eso corre en el
anfitrión, a diferencia de la importación y las pruebas, que van al entorno aislado (RNF-03).
"""

import hashlib
import json
import subprocess
import sys
import tempfile
from collections.abc import Mapping
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


class HallazgoEstilo(BaseModel):
    """Infracción de la configuración de estilo que reporta Ruff."""

    model_config = ConfigDict(frozen=True)

    codigo: str
    archivo: str
    linea: int
    mensaje: str


def hallazgos_de_estilo(
    archivos: Mapping[str, str], ruta_estilo: Path = RUTA_ESTILO_GENERADO
) -> list[HallazgoEstilo]:
    """Analiza los archivos Python con Ruff y la configuración de estilo del código generado.

    Los archivos se escriben en una carpeta temporal que se borra al terminar.

    Args:
        archivos: Contenido de cada archivo por su ruta relativa; solo se analizan los `.py`.
        ruta_estilo: Configuración de Ruff que se aplica.

    Returns:
        Los hallazgos ordenados por archivo y línea; vacía si el código cumple el estilo.

    Raises:
        RuntimeError: Si Ruff no pudo analizar el código.
    """
    with tempfile.TemporaryDirectory(prefix="estilo-generado-") as carpeta:
        raiz = Path(carpeta)
        for ruta, contenido in archivos.items():
            if ruta.endswith(".py"):
                destino = raiz / ruta
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_text(contenido, encoding="utf-8")
        proceso = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--config",
                str(ruta_estilo),
                "--output-format=json",
                "--no-cache",
                "--exit-zero",
                ".",
            ],
            cwd=raiz,
            capture_output=True,
            text=True,
            check=False,
        )
        if proceso.returncode != 0:
            raise RuntimeError(f"Ruff no pudo analizar el código: {proceso.stderr.strip()}")
        hallazgos = [
            HallazgoEstilo(
                codigo=item["code"] or "sintaxis",
                archivo=Path(item["filename"]).relative_to(raiz.resolve()).as_posix(),
                linea=item["location"]["row"],
                mensaje=item["message"],
            )
            for item in json.loads(proceso.stdout or "[]")
        ]
    return sorted(hallazgos, key=lambda h: (h.archivo, h.linea, h.codigo))
