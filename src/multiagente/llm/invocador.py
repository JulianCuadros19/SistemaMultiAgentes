"""Invocación de un nodo con modelo: prompt versionado, parámetros configurados y traza."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypeVar

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from multiagente.core.configuracion import EsfuerzoRazonamiento
from multiagente.llm.cliente import ErrorRespuestaModelo, RespuestaModelo, invocar_estructurado
from multiagente.llm.costos import Tarifa, buscar_tarifa, calcular_costo, cargar_tarifas
from multiagente.llm.prompts import Prompt
from multiagente.llm.traza import RegistradorLlamadas, RegistroLlamada

M = TypeVar("M", bound=BaseModel)


@dataclass(frozen=True)
class ParametrosNodo:
    """Despliegue y razonamiento de un nodo, tomados de la configuración (RNF-06)."""

    nodo: str
    despliegue: str
    esfuerzo: EsfuerzoRazonamiento
    max_tokens_salida: int


class InvocadorNodo:
    """Invoca el modelo de un nodo con su prompt de sistema y registra cada llamada."""

    def __init__(
        self,
        cliente: OpenAI,
        parametros: ParametrosNodo,
        prompt: Prompt,
        registrador: RegistradorLlamadas,
        tarifas: dict[str, Tarifa] | None = None,
    ) -> None:
        """Prepara el invocador del nodo.

        Args:
            cliente: Cliente de la API OpenAI v1.
            parametros: Despliegue, esfuerzo y límite de salida del nodo.
            prompt: Prompt de sistema versionado del nodo.
            registrador: Destino de la traza de cada llamada.
            tarifas: Tarifas por modelo; si se omiten, se leen de `config/tarifas_modelos.toml`.
        """
        self.cliente = cliente
        self.parametros = parametros
        self.prompt = prompt
        self.registrador = registrador
        self.tarifas = tarifas if tarifas is not None else cargar_tarifas()

    def invocar(self, mensajes: list[ChatCompletionMessageParam], esquema: type[M]) -> M:
        """Antepone el prompt de sistema, invoca con salida estructurada y registra la llamada.

        La llamada se registra también cuando falla, porque se cobra igual.

        Args:
            mensajes: Mensajes de datos que acompañan al prompt.
            esquema: Modelo Pydantic de la salida.

        Returns:
            La salida validada contra el esquema.

        Raises:
            ErrorRespuestaModelo: Si la respuesta no es utilizable; ya quedó registrada.
        """
        parametros = self.parametros
        completos: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self.prompt.texto},
            *mensajes,
        ]
        try:
            salida = invocar_estructurado(
                self.cliente,
                despliegue=parametros.despliegue,
                mensajes=completos,
                esfuerzo=parametros.esfuerzo,
                max_tokens_salida=parametros.max_tokens_salida,
                esquema=esquema,
            )
        except ErrorRespuestaModelo as error:
            self._registrar(error.respuesta, type(error).__name__)
            raise
        self._registrar(salida.respuesta)
        return salida.valor

    def _registrar(self, respuesta: RespuestaModelo, error: str | None = None) -> None:
        parametros = self.parametros
        costo = calcular_costo(respuesta.consumo, buscar_tarifa(self.tarifas, respuesta.modelo))
        self.registrador.registrar(
            RegistroLlamada(
                fecha=datetime.now(UTC),
                nodo=parametros.nodo,
                prompt=self.prompt.identificador,
                huella_prompt=self.prompt.huella,
                despliegue=parametros.despliegue,
                modelo=respuesta.modelo,
                region_procesamiento=respuesta.region,
                esfuerzo=parametros.esfuerzo,
                max_tokens_salida=parametros.max_tokens_salida,
                motivo_fin=respuesta.motivo_fin,
                consumo=respuesta.consumo,
                costo_usd=costo,
                latencia_ms=respuesta.latencia_ms,
                error=error,
            )
        )
