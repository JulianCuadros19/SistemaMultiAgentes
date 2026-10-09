"""Elementos compartidos por las pruebas."""

import hashlib
import json
import math
import re
from collections.abc import Callable, Sequence
from types import SimpleNamespace
from typing import Any

import pytest
from openai.types.chat import ChatCompletion
from pydantic import BaseModel


class VectorizadorDePrueba:
    """Vectorizador determinista de bolsa de palabras, para probar sin el modelo real.

    Cada palabra suma en una posición fija del vector según su hash; los textos que comparten
    palabras quedan cerca. No tiene calidad semántica: solo sirve para probar la lógica.
    """

    modelo = "prueba/bolsa-de-palabras"
    dimension = 1024

    def __init__(self) -> None:
        self.llamadas = 0

    def vectorizar(self, textos: Sequence[str]) -> list[list[float]]:
        self.llamadas += 1
        vectores = []
        for texto in textos:
            vector = [0.0] * self.dimension
            for palabra in re.findall(r"\w+", texto.lower()):
                posicion = int(hashlib.md5(palabra.encode()).hexdigest(), 16) % self.dimension
                vector[posicion] += 1.0
            norma = math.sqrt(sum(v * v for v in vector)) or 1.0
            vectores.append([v / norma for v in vector])
        return vectores


@pytest.fixture
def vectorizador_prueba() -> VectorizadorDePrueba:
    return VectorizadorDePrueba()


def completar(
    contenido: str | dict | BaseModel | None,
    *,
    motivo_fin: str = "stop",
    rechazo: str | None = None,
    entrada: int = 500,
    salida: int = 300,
    razonamiento: int = 200,
    modelo: str = "gpt-5-nano-2025-08-07",
) -> ChatCompletion:
    """Construye la respuesta de Chat Completions que devolvería el proveedor."""
    if isinstance(contenido, BaseModel):
        contenido = contenido.model_dump_json()
    elif isinstance(contenido, dict):
        contenido = json.dumps(contenido, ensure_ascii=False)
    return ChatCompletion.model_validate(
        {
            "id": "chatcmpl-prueba",
            "object": "chat.completion",
            "created": 1_790_000_000,
            "model": modelo,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": motivo_fin,
                    "message": {"role": "assistant", "content": contenido, "refusal": rechazo},
                }
            ],
            "usage": {
                "prompt_tokens": entrada,
                "completion_tokens": salida,
                "total_tokens": entrada + salida,
                "completion_tokens_details": {"reasoning_tokens": razonamiento},
            },
        }
    )


class _RespuestaCruda:
    def __init__(self, completion: ChatCompletion) -> None:
        self._completion = completion
        self.headers = {"x-ms-region": "South Central US"}

    def parse(self) -> ChatCompletion:
        return self._completion


Respuesta = ChatCompletion | Callable[[dict[str, Any]], ChatCompletion]


class ClienteModeloFalso:
    """Cliente OpenAI falso: entrega respuestas preparadas y guarda los argumentos de cada llamada.

    Cada respuesta es un `ChatCompletion` o una función que lo construye a partir de los
    argumentos de la llamada. Si se agotan, la llamada falla: así una prueba detecta llamadas de
    más.
    """

    def __init__(self, *respuestas: Respuesta) -> None:
        self.pendientes = list(respuestas)
        self.llamadas: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(with_raw_response=SimpleNamespace(create=self._crear))
        )

    def with_options(self, **opciones: Any) -> "ClienteModeloFalso":
        self.opciones = opciones
        return self

    def _crear(self, **argumentos: Any) -> _RespuestaCruda:
        self.llamadas.append(argumentos)
        if not self.pendientes:
            raise AssertionError("El cliente falso no tiene más respuestas preparadas")
        respuesta = self.pendientes.pop(0)
        if callable(respuesta):
            respuesta = respuesta(argumentos)
        return _RespuestaCruda(respuesta)


@pytest.fixture
def completar_respuesta() -> Callable[..., ChatCompletion]:
    """Fábrica de respuestas de Chat Completions (ver `completar`)."""
    return completar


@pytest.fixture
def cliente_falso() -> Callable[..., ClienteModeloFalso]:
    """Fábrica de clientes OpenAI falsos con respuestas preparadas."""
    return ClienteModeloFalso
