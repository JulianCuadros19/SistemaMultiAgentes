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


def cargar_prompt(agente: str, nombre: str, raiz: Path = RAIZ_PROMPTS) -> Prompt:
    """Lee un prompt versionado y valida su cabecera.

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
    archivo = raiz / agente / f"{nombre}.md"
    ruta = f"{agente}/{nombre}.md"
    if not archivo.is_file():
        raise ErrorPrompt(f"{ruta}: no existe")
    texto = archivo.read_text(encoding="utf-8")
    try:
        cabecera, cuerpo = separar_cabecera(texto)
        metadatos = MetadatosPrompt.model_validate(cabecera)
        prompt = Prompt(
            metadatos=metadatos,
            texto=cuerpo,
            huella=hashlib.sha256(texto.encode("utf-8")).hexdigest(),
        )
    except ErrorCabecera as error:
        raise ErrorPrompt(f"{ruta}: {error}") from error
    except ValidationError as error:
        raise ErrorPrompt(f"{ruta}: prompt inválido: {error}") from error
    if metadatos.agente != agente:
        raise ErrorPrompt(f"{ruta}: declara el agente {metadatos.agente} pero está en {agente}")
    return prompt
