"""Parametrización de la arquitectura elegida: especificación de diseño (N8, segunda llamada).

El modelo declara módulos, interfaces, dependencias y modelo de datos. El código asigna los
campos deterministas (identificador, versión, arquitectura base y requerimientos cubiertos) y
valida contra el esquema del Anexo B, que incluye la ausencia de ciclos (validación 1). Las
validaciones de cobertura y de catálogo son de N9.
"""

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict, ValidationError

from multiagente.agentes.arquitecto.contexto import mensaje_contexto
from multiagente.agentes.contexto import json_texto
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno, TipoInterfaz
from multiagente.llm.invocador import ErrorValidacionSalida
from multiagente.orquestador.estado import Arquitectura, Contexto, Requerimientos

ID_ESPECIFICACION = "ED-01"
"""Una especificación por módulo y por sesión; las revisiones suben la versión."""


class InterfazModelo(BaseModel):
    """Interfaz pública, tal como la devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    tipo: TipoInterfaz
    firma: str
    descripcion: str
    excepciones: list[str]


class ModuloModelo(BaseModel):
    """Módulo, tal como lo devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    ruta: str
    responsabilidad: str
    capa: str
    interfaces_publicas: list[InterfazModelo]
    dependencias_permitidas: list[str]
    requerimientos: list[str]


class CampoModelo(BaseModel):
    """Campo de una entidad, tal como lo devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    tipo: str
    obligatorio: bool
    restriccion: str | None


class EntidadModelo(BaseModel):
    """Entidad del modelo de datos, tal como la devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    campos: list[CampoModelo]


class DependenciaModelo(BaseModel):
    """Dependencia externa, tal como la devuelve el modelo."""

    model_config = ConfigDict(extra="forbid")

    paquete: str
    proposito: str


class SalidaEspecificacion(BaseModel):
    """Salida de la parametrización: el contenido de la especificación del Anexo B."""

    model_config = ConfigDict(extra="forbid")

    modulos: list[ModuloModelo]
    modelo_datos: list[EntidadModelo]
    dependencias_externas: list[DependenciaModelo]
    reglas_de_dependencia: list[str]


def mensajes_parametrizacion(
    requerimientos: Requerimientos,
    contexto: Contexto,
    previa: Arquitectura,
    elegida: str,
    registro: str,
) -> list[ChatCompletionMessageParam]:
    """Arma los mensajes de datos de la parametrización.

    En una corrección incluye la especificación anterior, los errores de validación de N9 y las
    observaciones del revisor.

    Args:
        requerimientos: Requerimientos aprobados en N6.
        contexto: Contexto acumulado; solo se presenta el del arquitecto.
        previa: Diseño anterior de la sesión.
        elegida: Arquitectura elegida en la selección.
        registro: Registro de decisión de la selección.

    Returns:
        Dos mensajes de datos que acompañan al prompt de parametrización.
    """
    datos: dict[str, object] = {
        "arquitectura_elegida": elegida,
        "registro_decision": registro,
        "requerimientos": [r.model_dump(mode="json") for r in requerimientos.requerimientos],
        "observaciones_revisor": list(previa.observaciones_revisor),
    }
    if previa.especificacion is not None and (
        previa.errores_validacion or previa.observaciones_revisor
    ):
        datos["correccion"] = {
            "especificacion_previa": previa.especificacion.model_dump(mode="json"),
            "errores_validacion": list(previa.errores_validacion),
        }
    return [mensaje_contexto(contexto), {"role": "user", "content": json_texto(datos)}]


def _errores(error: ValidationError) -> list[str]:
    return [
        f"{'.'.join(str(parte) for parte in detalle['loc']) or 'especificacion'}: "
        f"{str(detalle['msg']).removeprefix('Value error, ')}"
        for detalle in error.errors()
    ]


def especificacion_desde_salida(
    salida: SalidaEspecificacion,
    requerimientos: Requerimientos,
    elegida: str,
    version: str,
) -> EspecificacionDiseno:
    """Completa los campos deterministas y valida contra el esquema del Anexo B.

    Args:
        salida: Salida del modelo.
        requerimientos: Requerimientos aprobados; son los que la especificación cubre.
        elegida: Arquitectura elegida en la selección.
        version: Versión de la especificación.

    Returns:
        La especificación validada.

    Raises:
        ErrorValidacionSalida: Si incumple el esquema o tiene dependencias circulares.
    """
    datos = salida.model_dump(mode="json")
    for modulo in datos["modulos"]:
        modulo["requerimientos"] = [rf.strip() for rf in modulo["requerimientos"]]
    for entidad in datos["modelo_datos"]:
        for campo in entidad["campos"]:
            campo["restriccion"] = (campo["restriccion"] or "").strip() or None
    try:
        return EspecificacionDiseno.model_validate(
            {
                **datos,
                "id_especificacion": ID_ESPECIFICACION,
                "version": version,
                "arquitectura_base": elegida,
                "requerimientos_cubiertos": [
                    r.id_requerimiento for r in requerimientos.requerimientos
                ],
            }
        )
    except ValidationError as error:
        raise ErrorValidacionSalida(_errores(error)) from error
