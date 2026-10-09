"""Casos sintéticos de diseño: requerimientos aprobados con las arquitecturas que admiten.

Sirven para probar al arquitecto sin elicitación: `ElicitadorFijo` entrega la síntesis del caso
y la sesión llega a N7 con requerimientos aprobados. Las candidatas son las que dan los criterios
de selección (arq-003) para la naturaleza del caso; la prueba verifica que la elegida esté entre
ellas. No contienen datos de Realtix.
"""

import json
from pathlib import Path

from pydantic import ConfigDict, Field, ValidationError

from multiagente.core.esquemas.comunes import IdArquitectura, ModeloEstricto, TextoObligatorio
from multiagente.orquestador.servicios import Sintesis


class CasoDiseno(ModeloEstricto):
    """Caso sintético de diseño."""

    model_config = ConfigDict(frozen=True)

    id: TextoObligatorio
    titulo: TextoObligatorio
    cliente: TextoObligatorio
    proyecto: TextoObligatorio
    necesidad: TextoObligatorio
    candidatas: list[IdArquitectura] = Field(min_length=1)
    criterio: TextoObligatorio
    sintesis: Sintesis


class ErrorCasoDiseno(ValueError):
    """Un caso de diseño no tiene la forma esperada."""


def cargar_caso_diseno(archivo: Path) -> CasoDiseno:
    """Lee un caso de diseño en JSON.

    Args:
        archivo: Archivo del caso.

    Returns:
        El caso validado, con su síntesis conforme al Anexo A.

    Raises:
        ErrorCasoDiseno: Si el archivo no es JSON o no cumple el esquema.
    """
    try:
        return CasoDiseno.model_validate(json.loads(archivo.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError) as error:
        raise ErrorCasoDiseno(f"{archivo.name}: {error}") from error
