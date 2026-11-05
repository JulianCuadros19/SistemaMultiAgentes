"""Pruebas del contrato HTTP mediante ASGI, sin red ni httpx."""

import asyncio
import json
from typing import cast

import pytest
from starlette.types import Message, Scope

from predial.api import app

_ERROR_SOLICITUD = (
    "Solicitud inválida: envíe un objeto JSON con los campos y tipos documentados"
)


async def _peticion_asgi(
    ruta: str, cuerpo: bytes, metodo: str,
) -> tuple[int, dict[str, object]]:
    mensajes: list[Message] = []
    enviado = False
    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": metodo,
        "scheme": "http",
        "path": ruta,
        "raw_path": ruta.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [
            (b"host", b"test"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(cuerpo)).encode()),
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
    }

    async def recibir() -> Message:
        nonlocal enviado
        if enviado:
            return {"type": "http.disconnect"}
        enviado = True
        return {"type": "http.request", "body": cuerpo, "more_body": False}

    async def enviar(mensaje: Message) -> None:
        mensajes.append(mensaje)

    await app(scope, recibir, enviar)
    inicio = next(m for m in mensajes if m["type"] == "http.response.start")
    contenido = b"".join(
        m.get("body", b"") for m in mensajes if m["type"] == "http.response.body"
    )
    cabeceras = dict(inicio["headers"])
    assert cabeceras[b"content-type"].startswith(b"application/json")
    return inicio["status"], cast(dict[str, object], json.loads(contenido))


def _peticion(
    ruta: str, datos: object, metodo: str = "POST",
) -> tuple[int, dict[str, object]]:
    return asyncio.run(_peticion_asgi(ruta, json.dumps(datos).encode(), metodo))


@pytest.mark.parametrize(
    ("destino", "estrato", "tarifa"),
    [
        ("residencial", 1, 5),
        ("residencial", 2, 6),
        ("residencial", 3, 8),
        ("residencial", 4, 10),
        ("residencial", 5, 12),
        ("residencial", 6, 14),
        ("comercial", None, 11),
        ("industrial", None, 12),
        ("lote urbanizable no edificado", None, 33),
    ],
)
def test_consulta_y_calculo_por_http(
    destino: str, estrato: int | None, tarifa: int,
) -> None:
    datos: dict[str, object] = {"destino": destino}
    if estrato is not None:
        datos["estrato"] = estrato
    assert _peticion("/tarifa", datos) == (200, {"tarifa": tarifa})
    datos["avaluo"] = 1_000_000
    assert _peticion("/impuesto", datos) == (
        200, {"tarifa": tarifa, "impuesto": 1000 * tarifa},
    )


def test_ejemplo_http() -> None:
    assert _peticion(
        "/impuesto", {"destino": "residencial", "estrato": 3, "avaluo": 120_000_000},
    ) == (200, {"tarifa": 8, "impuesto": 960_000})


@pytest.mark.parametrize("avaluo,impuesto", [(49, 0), (50, 1), (51, 1), (150, 2)])
def test_redondeo_http(avaluo: int, impuesto: int) -> None:
    assert _peticion(
        "/impuesto", {"destino": "residencial", "estrato": 4, "avaluo": avaluo},
    ) == (200, {"tarifa": 10, "impuesto": impuesto})


@pytest.mark.parametrize("ruta", ["/tarifa", "/impuesto"])
@pytest.mark.parametrize("estrato", [0, 7, -1, None])
def test_error_estrato_http(ruta: str, estrato: int | None) -> None:
    datos: dict[str, object] = {"destino": "residencial", "estrato": estrato}
    if ruta == "/impuesto":
        datos["avaluo"] = 1000
    assert _peticion(ruta, datos) == (400, {"error": "Estrato inválido"})


@pytest.mark.parametrize("ruta", ["/tarifa", "/impuesto"])
def test_estrato_residencial_omitido_http(ruta: str) -> None:
    datos: dict[str, object] = {"destino": "residencial"}
    if ruta == "/impuesto":
        datos["avaluo"] = 1000
    assert _peticion(ruta, datos) == (400, {"error": "Estrato inválido"})


@pytest.mark.parametrize("ruta", ["/tarifa", "/impuesto"])
@pytest.mark.parametrize("destino", ["desconocido", "Comercial", "comercial ", ""])
def test_error_destino_http(ruta: str, destino: str) -> None:
    datos: dict[str, object] = {"destino": destino}
    if ruta == "/impuesto":
        datos["avaluo"] = 1000
    assert _peticion(ruta, datos) == (400, {"error": "Destino económico no reconocido"})


@pytest.mark.parametrize("avaluo", [0, -1])
def test_error_avaluo_http(avaluo: int) -> None:
    assert _peticion("/impuesto", {"destino": "comercial", "avaluo": avaluo}) == (
        400, {"error": "El avalúo debe ser mayor que cero"},
    )


@pytest.mark.parametrize(
    "destino", ["comercial", "industrial", "lote urbanizable no edificado"],
)
@pytest.mark.parametrize("estrato", [None, 0, 7])
def test_estrato_no_residencial_ignorado_http(destino: str, estrato: int | None) -> None:
    assert _peticion("/tarifa", {"destino": destino, "estrato": estrato}) == _peticion(
        "/tarifa", {"destino": destino},
    )
    assert _peticion(
        "/impuesto", {"destino": destino, "estrato": estrato, "avaluo": 1000},
    ) == _peticion("/impuesto", {"destino": destino, "avaluo": 1000})


@pytest.mark.parametrize(
    ("ruta", "datos"),
    [
        ("/tarifa", {}),
        ("/tarifa", {"destino": None}),
        ("/tarifa", {"destino": 1}),
        ("/tarifa", {"destino": "residencial", "estrato": "3"}),
        ("/tarifa", {"destino": "residencial", "estrato": 3.0}),
        ("/tarifa", {"destino": "residencial", "estrato": True}),
        ("/tarifa", {"destino": "comercial", "estrato": "3"}),
        ("/tarifa", {"destino": "comercial", "extra": 1}),
        ("/tarifa", []),
        ("/tarifa", None),
        ("/impuesto", {"destino": "comercial"}),
        ("/impuesto", {"destino": "comercial", "avaluo": None}),
        ("/impuesto", {"destino": "comercial", "avaluo": "1000"}),
        ("/impuesto", {"destino": "comercial", "avaluo": 1000.0}),
        ("/impuesto", {"destino": "comercial", "avaluo": 1000.5}),
        ("/impuesto", {"destino": "comercial", "avaluo": True}),
        ("/impuesto", {"destino": "comercial", "avaluo": 1000, "extra": 1}),
    ],
)
def test_estructura_y_tipos_invalidos_http(ruta: str, datos: object) -> None:
    assert _peticion(ruta, datos) == (400, {"error": _ERROR_SOLICITUD})


def test_json_mal_formado() -> None:
    assert asyncio.run(_peticion_asgi("/tarifa", b"{", "POST")) == (
        400, {"error": _ERROR_SOLICITUD},
    )


def test_ruta_inexistente() -> None:
    estado, respuesta = _peticion("/inexistente", {})
    assert estado == 404
    assert isinstance(respuesta["error"], str)


def test_metodo_no_permitido() -> None:
    estado, respuesta = _peticion("/tarifa", {}, metodo="GET")
    assert estado == 405
    assert isinstance(respuesta["error"], str)


def test_contrato_openapi_disponible() -> None:
    estado, contrato = _peticion("/openapi.json", {}, metodo="GET")
    assert estado == 200
    rutas = cast(dict[str, dict[str, object]], contrato["paths"])
    for ruta in ("/tarifa", "/impuesto"):
        operacion = cast(dict[str, object], rutas[ruta]["post"])
        respuestas = cast(dict[str, object], operacion["responses"])
        assert "200" in respuestas
        assert "400" in respuestas
        assert "requestBody" in operacion
