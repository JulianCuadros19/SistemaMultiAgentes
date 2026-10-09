"""Casos sintéticos de diseño y de desarrollo para probar a los agentes por separado.

- Un caso de diseño trae requerimientos aprobados con las arquitecturas que admiten. Sirve para
  probar al arquitecto sin elicitación: `ElicitadorFijo` entrega la síntesis del caso y la sesión
  llega a N7 con requerimientos aprobados. Las candidatas son las que dan los criterios de
  selección (arq-003) para la naturaleza del caso; la prueba verifica que la elegida esté entre
  ellas.
- Un caso de desarrollo agrega el diseño que aprobó el arquitecto humano en una corrida real del
  paso 8. Sirve para probar al desarrollador sin diseñar: `ArquitectoFijo` entrega el diseño y la
  sesión llega a N10 con una especificación aprobada, siempre la misma.

No contienen datos de Realtix.
"""

import json
from pathlib import Path
from typing import Self

from pydantic import ConfigDict, Field, ValidationError, model_validator

from multiagente.core.esquemas.comunes import IdArquitectura, ModeloEstricto, TextoObligatorio
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.orquestador.servicios import Diseno, Sintesis


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


class CasoDesarrollo(CasoDiseno):
    """Caso sintético de desarrollo: un caso de diseño con su diseño aprobado."""

    registro_decision: TextoObligatorio
    especificacion: EspecificacionDiseno

    @model_validator(mode="after")
    def _cubre_los_requerimientos_del_caso(self) -> Self:
        propios = [r.id_requerimiento for r in self.sintesis.requerimientos]
        if sorted(self.especificacion.requerimientos_cubiertos) != sorted(propios):
            raise ValueError(
                f"La especificación debe cubrir exactamente los requerimientos del caso: {propios}"
            )
        return self

    @property
    def diseno(self) -> Diseno:
        """Diseño aprobado del caso, como lo entrega N8."""
        return Diseno(registro_decision=self.registro_decision, especificacion=self.especificacion)


class ErrorCasoDiseno(ValueError):
    """Un caso de diseño o de desarrollo no tiene la forma esperada."""


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


def cargar_caso_desarrollo(archivo: Path) -> CasoDesarrollo:
    """Lee un caso de desarrollo en JSON.

    Args:
        archivo: Archivo del caso.

    Returns:
        El caso validado, con su síntesis y su especificación.

    Raises:
        ErrorCasoDiseno: Si el archivo no es JSON o no cumple el esquema.
    """
    try:
        return CasoDesarrollo.model_validate(json.loads(archivo.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError) as error:
        raise ErrorCasoDiseno(f"{archivo.name}: {error}") from error


def exportar_caso_desarrollo(caso: CasoDiseno, diseno: Diseno, archivo: Path) -> CasoDesarrollo:
    """Guarda un caso de diseño con el diseño aprobado como caso de desarrollo.

    El identificador cambia el prefijo `caso-diseno` por `caso-desarrollo`.

    Args:
        caso: Caso de diseño del que salieron los requerimientos.
        diseno: Registro y especificación aprobados en N9.
        archivo: Archivo JSON de destino; se sobrescribe si existe.

    Returns:
        El caso de desarrollo guardado.
    """
    datos = caso.model_dump(mode="json") | diseno.model_dump(mode="json")
    datos["id"] = caso.id.replace("caso-diseno", "caso-desarrollo", 1)
    desarrollo = CasoDesarrollo.model_validate(datos)
    archivo.write_text(
        json.dumps(desarrollo.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return desarrollo
