"""Cliente simulado por un modelo de lenguaje, para probar la elicitación con casos sintéticos.

No es un agente del sistema: ocupa el lugar de la persona en la interfaz conversacional y
responde las preguntas del elicitador con los datos de un caso de `evaluacion/casos/`. Su prompt
está en `evaluacion/cliente_simulado.md` y sus llamadas quedan en la traza con el nodo
`cliente_simulado`, aparte del costo del sistema.
"""

import json
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, ValidationError

from multiagente.core.cabecera import ErrorCabecera, separar_cabecera
from multiagente.core.esquemas.comunes import (
    IdArquitectura,
    ModeloEstricto,
    TextoObligatorio,
    Version,
)
from multiagente.llm.invocador import InvocadorNodo, ParametrosNodo
from multiagente.llm.prompts import leer_prompt
from multiagente.llm.traza import RegistradorLlamadas
from multiagente.orquestador.estado import Conversacion

RAIZ_EVALUACION = Path(__file__).resolve().parents[3] / "evaluacion"
"""Carpeta `evaluacion/` del repositorio."""


class CasoElicitacion(ModeloEstricto):
    """Caso sintético: datos de apertura de la sesión y lo que sabe el cliente.

    Attributes:
        arquitecturas_esperadas: Arquitecturas del catálogo a las que apuntan las señales del
            caso, según los criterios de arq-003. Solo sirven para evaluar la selección de N8:
            el cliente simulado no las ve, porque recibe únicamente `conocimiento`.
    """

    model_config = ConfigDict(frozen=True)

    id: TextoObligatorio
    titulo: TextoObligatorio
    cliente: TextoObligatorio
    proyecto: TextoObligatorio
    necesidad: TextoObligatorio
    version: Version
    conocimiento: TextoObligatorio
    arquitecturas_esperadas: tuple[IdArquitectura, ...] = ()


class ErrorCaso(ValueError):
    """Un caso sintético no tiene la forma esperada."""


def cargar_caso(archivo: Path) -> CasoElicitacion:
    """Lee un caso sintético con cabecera YAML; el cuerpo es lo que sabe el cliente.

    Args:
        archivo: Archivo Markdown del caso.

    Returns:
        El caso validado.

    Raises:
        ErrorCaso: Si falta la cabecera o algún campo.
    """
    try:
        cabecera, cuerpo = separar_cabecera(archivo.read_text(encoding="utf-8"))
        return CasoElicitacion.model_validate({**cabecera, "conocimiento": cuerpo})
    except (ErrorCabecera, ValidationError) as error:
        raise ErrorCaso(f"{archivo.name}: {error}") from error


class SalidaCliente(BaseModel):
    """Respuesta del cliente simulado."""

    model_config = ConfigDict(extra="forbid")

    respuesta: str


class ClienteSimulado:
    """Responde las preguntas del elicitador como la persona del caso."""

    def __init__(
        self,
        cliente: OpenAI,
        despliegue: str,
        caso: CasoElicitacion,
        registrador: RegistradorLlamadas,
    ) -> None:
        """Prepara el cliente simulado con esfuerzo de razonamiento medio.

        Con esfuerzo mínimo o bajo confirmaba resúmenes incompletos o equivocados; con esfuerzo
        medio compara el resumen con el caso (ADR-0008). Su latencia no cuenta para el RNF-01.

        Args:
            cliente: Cliente de la API OpenAI v1.
            despliegue: Despliegue del modelo que hace de cliente.
            caso: Caso sintético que conoce el cliente.
            registrador: Destino de la traza de cada llamada.
        """
        self.caso = caso
        self.invocador = InvocadorNodo(
            cliente,
            ParametrosNodo(
                nodo="cliente_simulado",
                despliegue=despliegue,
                esfuerzo="medium",
                max_tokens_salida=6000,
            ),
            leer_prompt(RAIZ_EVALUACION / "cliente_simulado.md"),
            registrador,
        )

    def responder(self, conversacion: Conversacion, pregunta: str) -> str:
        """Responde la pregunta pendiente del elicitador.

        Args:
            conversacion: Conversación hasta la pregunta.
            pregunta: Pregunta del elicitador.

        Returns:
            Respuesta del cliente.
        """
        datos = {
            "caso": self.caso.conocimiento,
            "transcripcion": [
                {"emisor": turno.emisor.value, "texto": turno.texto}
                for turno in conversacion.turnos
            ],
            "pregunta": pregunta,
        }
        mensaje = json.dumps(datos, ensure_ascii=False)
        salida = self.invocador.invocar([{"role": "user", "content": mensaje}], SalidaCliente)
        return salida.respuesta.strip()
