"""Cliente de modelos de lenguaje por la API OpenAI v1 con Chat Completions."""

import time
from typing import Literal

from openai import OpenAI
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict

from multiagente.core.configuracion import ConfiguracionAzureOpenAI
from multiagente.llm.costos import ConsumoTokens

EsfuerzoRazonamiento = Literal["minimal", "low", "medium", "high"]

TIEMPO_ESPERA_SEGUNDOS = 60.0
REINTENTOS = 2


class RespuestaModelo(BaseModel):
    """Resultado de una llamada con los datos que exige la traza de costo."""

    model_config = ConfigDict(frozen=True)

    contenido: str
    motivo_fin: str
    modelo: str
    consumo: ConsumoTokens
    latencia_ms: int
    region: str | None


def crear_cliente(configuracion: ConfiguracionAzureOpenAI) -> OpenAI:
    """Crea el cliente OpenAI apuntando a la API v1 del recurso de Azure.

    Args:
        configuracion: Endpoint y clave del recurso.

    Returns:
        Cliente con tiempo de espera y reintentos acotados.
    """
    return OpenAI(
        base_url=configuracion.url_base(),
        api_key=configuracion.api_key.get_secret_value(),
        timeout=TIEMPO_ESPERA_SEGUNDOS,
        max_retries=REINTENTOS,
    )


def consumo_desde_uso(uso: CompletionUsage) -> ConsumoTokens:
    """Convierte el bloque `usage` de la API en el consumo que registra el sistema.

    Args:
        uso: Bloque `usage` de la respuesta.

    Returns:
        Consumo con la entrada cacheada y el razonamiento desglosados.
    """
    detalle_entrada = uso.prompt_tokens_details
    detalle_salida = uso.completion_tokens_details
    return ConsumoTokens(
        entrada=uso.prompt_tokens,
        entrada_cacheada=(detalle_entrada.cached_tokens or 0) if detalle_entrada else 0,
        salida=uso.completion_tokens,
        razonamiento=(detalle_salida.reasoning_tokens or 0) if detalle_salida else 0,
    )


def invocar(
    cliente: OpenAI,
    *,
    despliegue: str,
    mensajes: list[ChatCompletionMessageParam],
    esfuerzo: EsfuerzoRazonamiento,
    max_tokens_salida: int,
) -> RespuestaModelo:
    """Hace una llamada y mide su consumo y su latencia.

    El esfuerzo de razonamiento y el límite de salida son obligatorios: en los modelos de
    razonamiento, el límite incluye los tokens de razonamiento ocultos, y si se agota antes
    de producir texto la respuesta llega vacía con motivo de fin `length`.

    Args:
        cliente: Cliente creado con `crear_cliente`.
        despliegue: Nombre del despliegue del modelo, tomado de la configuración.
        mensajes: Mensajes de la conversación en formato Chat Completions.
        esfuerzo: Esfuerzo de razonamiento del modelo.
        max_tokens_salida: Límite de tokens de salida, razonamiento incluido.

    Returns:
        Contenido, motivo de fin, modelo, consumo, latencia y región de procesamiento.

    Raises:
        ValueError: Si la respuesta no trae el bloque de uso de tokens.
    """
    inicio = time.perf_counter()
    crudo = cliente.chat.completions.with_raw_response.create(
        model=despliegue,
        messages=mensajes,
        reasoning_effort=esfuerzo,
        max_completion_tokens=max_tokens_salida,
    )
    latencia_ms = round((time.perf_counter() - inicio) * 1000)
    respuesta = crudo.parse()
    if respuesta.usage is None:
        raise ValueError("La respuesta no incluye el uso de tokens")
    eleccion = respuesta.choices[0]
    return RespuestaModelo(
        contenido=eleccion.message.content or "",
        motivo_fin=eleccion.finish_reason,
        modelo=respuesta.model,
        consumo=consumo_desde_uso(respuesta.usage),
        latencia_ms=latencia_ms,
        region=crudo.headers.get("x-ms-region"),
    )
