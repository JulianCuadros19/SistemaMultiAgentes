"""Cliente de modelos de lenguaje por la API OpenAI v1 con Chat Completions."""

import time
from dataclasses import dataclass
from typing import Generic, TypeVar

from openai import Omit, OpenAI, omit, pydantic_function_tool
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.completion_create_params import ResponseFormat
from pydantic import BaseModel, ConfigDict, ValidationError

from multiagente.core.configuracion import ConfiguracionAzureOpenAI, EsfuerzoRazonamiento
from multiagente.llm.costos import ConsumoTokens

TIEMPO_ESPERA_SEGUNDOS = 60.0
REINTENTOS = 2

M = TypeVar("M", bound=BaseModel)


class RespuestaModelo(BaseModel):
    """Resultado de una llamada con los datos que exige la traza de costo."""

    model_config = ConfigDict(frozen=True)

    contenido: str
    motivo_fin: str
    modelo: str
    consumo: ConsumoTokens
    latencia_ms: int
    region: str | None
    rechazo: str | None = None


class ErrorRespuestaModelo(RuntimeError):
    """El modelo respondió, pero sin una salida utilizable.

    La llamada se cobra igual, por eso el error conserva la respuesta medida: quien invoca debe
    registrarla en la traza de costo antes de decidir qué hacer.

    Attributes:
        respuesta: Respuesta medida de la llamada fallida.
    """

    def __init__(self, mensaje: str, respuesta: RespuestaModelo) -> None:
        """Crea el error con su mensaje y la respuesta medida.

        Args:
            mensaje: Descripción del fallo.
            respuesta: Respuesta medida de la llamada.
        """
        super().__init__(mensaje)
        self.respuesta = respuesta


class ErrorLimiteSalida(ErrorRespuestaModelo):
    """El límite de tokens de salida se agotó antes de completar la respuesta."""


class ErrorFiltroContenido(ErrorRespuestaModelo):
    """El filtro de contenido del proveedor bloqueó la respuesta."""


class ErrorRechazoModelo(ErrorRespuestaModelo):
    """El modelo se negó a producir la salida estructurada."""


class ErrorSalidaInvalida(ErrorRespuestaModelo):
    """El contenido no cumple el esquema de salida esperado."""


@dataclass(frozen=True)
class SalidaEstructurada(Generic[M]):
    """Salida validada de una llamada estructurada y la respuesta medida que la produjo."""

    valor: M
    respuesta: RespuestaModelo


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


def formato_json(esquema: type[BaseModel]) -> ResponseFormat:
    """Construye el formato de respuesta estricto a partir de un modelo Pydantic.

    El modo estricto exige que todos los campos sean obligatorios y no admite restricciones como
    la longitud mínima; por eso los modelos de salida de los nodos usan tipos planos y la
    validación de dominio ocurre después, con los esquemas del sistema.

    Args:
        esquema: Modelo Pydantic de la salida.

    Returns:
        Parámetro `response_format` de tipo `json_schema` con `strict` activado.
    """
    parametros = pydantic_function_tool(esquema)["function"]["parameters"]
    return {
        "type": "json_schema",
        "json_schema": {"name": esquema.__name__, "schema": parametros, "strict": True},
    }


def _llamar(
    cliente: OpenAI,
    *,
    despliegue: str,
    mensajes: list[ChatCompletionMessageParam],
    esfuerzo: EsfuerzoRazonamiento,
    max_tokens_salida: int,
    formato: ResponseFormat | Omit = omit,
) -> RespuestaModelo:
    """Hace una llamada y mide su consumo, su latencia y su región de procesamiento."""
    inicio = time.perf_counter()
    crudo = cliente.chat.completions.with_raw_response.create(
        model=despliegue,
        messages=mensajes,
        reasoning_effort=esfuerzo,
        max_completion_tokens=max_tokens_salida,
        response_format=formato,
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
        rechazo=eleccion.message.refusal,
    )


def invocar(
    cliente: OpenAI,
    *,
    despliegue: str,
    mensajes: list[ChatCompletionMessageParam],
    esfuerzo: EsfuerzoRazonamiento,
    max_tokens_salida: int,
) -> RespuestaModelo:
    """Hace una llamada de texto libre y mide su consumo y su latencia.

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
    return _llamar(
        cliente,
        despliegue=despliegue,
        mensajes=mensajes,
        esfuerzo=esfuerzo,
        max_tokens_salida=max_tokens_salida,
    )


def invocar_estructurado(
    cliente: OpenAI,
    *,
    despliegue: str,
    mensajes: list[ChatCompletionMessageParam],
    esfuerzo: EsfuerzoRazonamiento,
    max_tokens_salida: int,
    esquema: type[M],
) -> SalidaEstructurada[M]:
    """Hace una llamada con salida estructurada y valida el contenido contra el esquema.

    Args:
        cliente: Cliente creado con `crear_cliente`.
        despliegue: Nombre del despliegue del modelo, tomado de la configuración.
        mensajes: Mensajes de la conversación en formato Chat Completions.
        esfuerzo: Esfuerzo de razonamiento del modelo.
        max_tokens_salida: Límite de tokens de salida, razonamiento incluido.
        esquema: Modelo Pydantic de la salida, con tipos planos (ver `formato_json`).

    Returns:
        La salida validada y la respuesta medida.

    Raises:
        ErrorLimiteSalida: Si el límite de salida se agotó.
        ErrorFiltroContenido: Si el filtro de contenido bloqueó la respuesta.
        ErrorRechazoModelo: Si el modelo se negó a responder.
        ErrorSalidaInvalida: Si el contenido no cumple el esquema.
    """
    respuesta = _llamar(
        cliente,
        despliegue=despliegue,
        mensajes=mensajes,
        esfuerzo=esfuerzo,
        max_tokens_salida=max_tokens_salida,
        formato=formato_json(esquema),
    )
    consumo = respuesta.consumo
    if respuesta.motivo_fin == "length":
        raise ErrorLimiteSalida(
            f"Se agotó el límite de {max_tokens_salida} tokens de salida "
            f"({consumo.razonamiento} de razonamiento) sin completar la respuesta",
            respuesta,
        )
    if respuesta.motivo_fin == "content_filter":
        raise ErrorFiltroContenido("El filtro de contenido bloqueó la respuesta", respuesta)
    if respuesta.rechazo:
        raise ErrorRechazoModelo(f"El modelo se negó a responder: {respuesta.rechazo}", respuesta)
    try:
        valor = esquema.model_validate_json(respuesta.contenido)
    except ValidationError as error:
        raise ErrorSalidaInvalida(
            f"La salida no cumple el esquema {esquema.__name__}: {error}", respuesta
        ) from error
    return SalidaEstructurada(valor=valor, respuesta=respuesta)
