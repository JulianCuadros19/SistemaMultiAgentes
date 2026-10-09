"""Invocación de un nodo con modelo: prompt versionado, parámetros configurados y traza."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypeVar

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from multiagente.core.configuracion import EsfuerzoRazonamiento
from multiagente.llm.cliente import (
    ErrorRespuestaModelo,
    ErrorSalidaInvalida,
    RespuestaModelo,
    invocar_estructurado,
)
from multiagente.llm.costos import Tarifa, buscar_tarifa, calcular_costo, cargar_tarifas
from multiagente.llm.prompts import Prompt
from multiagente.llm.traza import RegistradorLlamadas, RegistroLlamada

M = TypeVar("M", bound=BaseModel)
R = TypeVar("R")

REINTENTOS_CORRECCION = 1
"""Reintentos de una salida que incumple el esquema o las reglas del nodo (ADR-0008)."""

CLAVE_PROBLEMAS = "problemas_intento_anterior"
"""Clave del mensaje de datos que lleva al modelo los problemas de su intento anterior."""


class ErrorValidacionSalida(ValueError):
    """La salida cumple el esquema estricto, pero incumple una regla del nodo.

    Attributes:
        problemas: Descripción de cada incumplimiento, que se entrega al modelo al reintentar.
    """

    def __init__(self, problemas: list[str]) -> None:
        """Crea el error con la lista de problemas.

        Args:
            problemas: Incumplimientos encontrados; no puede ir vacía.
        """
        super().__init__("; ".join(problemas))
        self.problemas = problemas


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

    def invocar_validado(
        self,
        mensajes: list[ChatCompletionMessageParam],
        esquema: type[M],
        validar: Callable[[M], R],
    ) -> R:
        """Invoca, valida la salida y, si no es válida, reintenta una vez con los problemas.

        El reintento repite los mismos mensajes más uno de datos con la clave
        `problemas_intento_anterior`, que el prompt del nodo indica cómo atender. Si el segundo
        intento también falla, el error se propaga: el nodo falla y la sesión se reanuda desde
        su último punto de control.

        Args:
            mensajes: Mensajes de datos que acompañan al prompt.
            esquema: Modelo Pydantic de la salida.
            validar: Convierte la salida en el resultado del nodo o lanza
                `ErrorValidacionSalida`.

        Returns:
            El resultado que entrega `validar`.

        Raises:
            ErrorSalidaInvalida: Si la salida no cumple el esquema en ningún intento.
            ErrorValidacionSalida: Si la salida incumple las reglas en ningún intento.
            ErrorRespuestaModelo: Si la respuesta no es utilizable por otro motivo.
        """
        actuales = list(mensajes)
        for intento in range(REINTENTOS_CORRECCION + 1):
            try:
                return validar(self.invocar(actuales, esquema))
            except (ErrorSalidaInvalida, ErrorValidacionSalida) as error:
                if intento == REINTENTOS_CORRECCION:
                    raise
                problemas = (
                    error.problemas if isinstance(error, ErrorValidacionSalida) else [str(error)]
                )
                contenido = json.dumps({CLAVE_PROBLEMAS: problemas}, ensure_ascii=False)
                actuales = [*mensajes, {"role": "user", "content": contenido}]
        raise AssertionError("inalcanzable")

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
