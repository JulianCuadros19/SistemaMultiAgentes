"""Prompts versionados de los agentes (RF-36).

Cada prompt es un archivo `prompts/<agente>/<nombre>.md` con cabecera YAML. Ningún prompt se
define dentro del código de un nodo: el código solo arma los datos que acompañan al prompt.
"""

import hashlib
from pathlib import Path

from pydantic import ConfigDict, ValidationError

from multiagente.core.cabecera import ErrorCabecera, separar_cabecera
from multiagente.core.esquemas.comunes import ModeloEstricto, TextoObligatorio, Version

RAIZ_PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
"""Carpeta `prompts/` del repositorio."""


class MetadatosPrompt(ModeloEstricto):
    """Cabecera YAML de un prompt."""

    id: TextoObligatorio
    agente: TextoObligatorio
    nodo: TextoObligatorio
    version: Version
    descripcion: TextoObligatorio


class Prompt(ModeloEstricto):
    """Prompt de sistema de un nodo, con su versión y la huella de su contenido."""

    model_config = ConfigDict(frozen=True)

    metadatos: MetadatosPrompt
    texto: TextoObligatorio
    huella: TextoObligatorio

    @property
    def identificador(self) -> str:
        """Identificador y versión, p. ej. `elicitador.dialogo@1.0`, para la traza."""
        return f"{self.metadatos.id}@{self.metadatos.version}"


class ErrorPrompt(ValueError):
    """Un prompt no existe o no tiene la forma esperada."""


def leer_prompt(archivo: Path) -> Prompt:
    """Lee un prompt versionado desde un archivo y valida su cabecera.

    Args:
        archivo: Archivo Markdown con cabecera YAML.

    Returns:
        El prompt con sus metadatos, su texto y la huella SHA-256 del archivo completo.

    Raises:
        ErrorPrompt: Si el archivo no existe o si su cabecera es inválida.
    """
    if not archivo.is_file():
        raise ErrorPrompt(f"{archivo.name}: no existe")
    texto = archivo.read_text(encoding="utf-8")
    try:
        cabecera, cuerpo = separar_cabecera(texto)
        return Prompt(
            metadatos=MetadatosPrompt.model_validate(cabecera),
            texto=cuerpo,
            huella=hashlib.sha256(texto.encode("utf-8")).hexdigest(),
        )
    except ErrorCabecera as error:
        raise ErrorPrompt(f"{archivo.name}: {error}") from error
    except ValidationError as error:
        raise ErrorPrompt(f"{archivo.name}: prompt inválido: {error}") from error


def cargar_prompt(agente: str, nombre: str, raiz: Path = RAIZ_PROMPTS) -> Prompt:
    """Lee el prompt versionado de un agente.

    Args:
        agente: Carpeta del agente dentro de `prompts/`.
        nombre: Nombre del archivo sin la extensión `.md`.
        raiz: Carpeta raíz de los prompts.

    Returns:
        El prompt con sus metadatos, su texto y la huella SHA-256 del archivo completo.

    Raises:
        ErrorPrompt: Si el archivo no existe, si su cabecera es inválida o si declara otro
            agente.
    """
    prompt = leer_prompt(raiz / agente / f"{nombre}.md")
    if prompt.metadatos.agente != agente:
        raise ErrorPrompt(
            f"{nombre}.md: declara el agente {prompt.metadatos.agente} pero está en {agente}"
        )
    return prompt
