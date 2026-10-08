"""Tipos y modelos compartidos por los esquemas de los Anexos A y B."""

from collections import Counter
from collections.abc import Iterable
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

TextoObligatorio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
"""Texto que no puede quedar vacío ni compuesto solo por espacios."""

IdRequerimiento = Annotated[str, StringConstraints(pattern=r"^RF-\d{2,}$")]
IdHistoria = Annotated[str, StringConstraints(pattern=r"^HU-\d{2,}$")]
IdEscenario = Annotated[str, StringConstraints(pattern=r"^ESC-\d{2,}$")]
IdEspecificacion = Annotated[str, StringConstraints(pattern=r"^ED-\d{2,}$")]
IdArquitectura = Annotated[str, StringConstraints(pattern=r"^ARQ-\d{2}$")]
Version = Annotated[str, StringConstraints(pattern=r"^\d+\.\d+$")]


class Prioridad(StrEnum):
    """Prioridad acordada con el cliente para una historia o un requerimiento."""

    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class Impacto(StrEnum):
    """Impacto de la solicitud en la ficha del requerimiento (Anexo A)."""

    ALTO = "alto"
    MEDIO = "medio"
    BAJO = "bajo"


class ModeloEstricto(BaseModel):
    """Base de los esquemas: rechaza campos no declarados y recorta espacios."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Enunciado(ModeloEstricto):
    """Historia de usuario en sus tres partes: como, quiero y para."""

    como: TextoObligatorio
    quiero: TextoObligatorio
    para: TextoObligatorio


def repetidos(valores: Iterable[str]) -> list[str]:
    """Devuelve los valores que aparecen más de una vez, en orden alfabético.

    Args:
        valores: Valores a revisar.

    Returns:
        Lista de valores repetidos, vacía si todos son únicos.
    """
    return sorted(valor for valor, veces in Counter(valores).items() if veces > 1)
