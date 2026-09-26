"""Pruebas del cliente de modelos sin llamar a la red."""

import pytest
from openai.types.chat import ChatCompletion

from multiagente.core.configuracion import ConfiguracionAzureOpenAI
from multiagente.llm.cliente import consumo_desde_uso


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://recurso.openai.azure.com",
        "https://recurso.openai.azure.com/",
        "https://recurso.openai.azure.com/openai/v1",
        "https://recurso.openai.azure.com/openai/v1/",
        "  https://recurso.openai.azure.com/  ",
    ],
)
def test_url_base_normaliza_el_endpoint(endpoint):
    configuracion = ConfiguracionAzureOpenAI(_env_file=None, endpoint=endpoint, api_key="clave")
    assert configuracion.url_base() == "https://recurso.openai.azure.com/openai/v1/"


def test_clave_no_aparece_en_la_representacion():
    configuracion = ConfiguracionAzureOpenAI(
        _env_file=None, endpoint="https://recurso.openai.azure.com", api_key="clave-secreta"
    )
    assert "clave-secreta" not in repr(configuracion)


def construir_respuesta(uso: dict) -> ChatCompletion:
    return ChatCompletion.model_validate(
        {
            "id": "chatcmpl-prueba",
            "object": "chat.completion",
            "created": 1_790_000_000,
            "model": "gpt-5-nano-2025-08-07",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "Hola"},
                }
            ],
            "usage": uso,
        }
    )


def test_consumo_con_desgloses():
    respuesta = construir_respuesta(
        {
            "prompt_tokens": 120,
            "completion_tokens": 900,
            "total_tokens": 1020,
            "prompt_tokens_details": {"cached_tokens": 64},
            "completion_tokens_details": {"reasoning_tokens": 832},
        }
    )
    consumo = consumo_desde_uso(respuesta.usage)
    assert (consumo.entrada, consumo.entrada_cacheada) == (120, 64)
    assert (consumo.salida, consumo.razonamiento, consumo.salida_visible) == (900, 832, 68)


def test_consumo_sin_desgloses():
    respuesta = construir_respuesta(
        {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    )
    consumo = consumo_desde_uso(respuesta.usage)
    assert (consumo.entrada_cacheada, consumo.razonamiento) == (0, 0)
