"""Pruebas HTTP a través de ASGI, sin sockets, red ni dependencias de pruebas HTTP."""

import asyncio
import json

import pytest

from servicio_nit import app, crear_app


async def _intercambiar(
    ruta: str, cuerpo: bytes, metodo: str = "POST"
) -> tuple[int, dict[str, object]]:
    mensajes: list[dict[str, object]] = []
    entregado = False
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": metodo,
        "scheme": "http",
        "path": ruta,
        "raw_path": ruta.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
    }

    async def recibir() -> dict[str, object]:
        nonlocal entregado
        if entregado:
            return {"type": "http.disconnect"}
        entregado = True
        return {"type": "http.request", "body": cuerpo, "more_body": False}

    async def enviar(mensaje: dict[str, object]) -> None:
        mensajes.append(mensaje)

    await app(scope, recibir, enviar)
    inicio = next(m for m in mensajes if m["type"] == "http.response.start")
    estado = inicio["status"]
    assert isinstance(estado, int)
    partes: list[bytes] = []
    for mensaje in mensajes:
        if mensaje["type"] == "http.response.body":
            parte = mensaje.get("body", b"")
            assert isinstance(parte, bytes)
            partes.append(parte)
    respuesta = json.loads(b"".join(partes))
    assert isinstance(respuesta, dict)
    return estado, respuesta


def _consultar(ruta: str, datos: object) -> tuple[int, dict[str, object]]:
    return asyncio.run(_intercambiar(ruta, json.dumps(datos).encode()))


def test_calcular_por_http() -> None:
    estado, respuesta = _consultar("/calcular", {"nit": "123.456.789-"})
    assert estado == 200
    assert respuesta == {"nit": "123456789", "digito": "6"}


@pytest.mark.parametrize(
    ("numero", "digito", "valido", "esperado"),
    [
        ("123456789", "6", True, "6"),
        ("123456789", "5", False, "6"),
        ("900123456", "7", True, "7"),
        ("900123456", "8", False, "7"),
        ("000.123.456.789-", "6", True, "6"),
    ],
)
def test_validar_por_http(
    numero: str, digito: str, valido: bool, esperado: str
) -> None:
    estado, respuesta = _consultar("/validar", {"nit": numero, "digito": digito})
    assert estado == 200
    assert respuesta == {
        "nit": numero.replace(".", "").replace("-", ""),
        "valido": valido,
        "digito_esperado": esperado,
    }


@pytest.mark.parametrize("ruta", ["/calcular", "/validar"])
@pytest.mark.parametrize(
    ("numero", "mensaje"),
    [
        ("123A", "El NIT solo admite dígitos"),
        ("1" * 16, "El NIT admite como máximo 15 dígitos"),
        ("", "El NIT no puede estar vacío"),
        (" 123", "El NIT solo admite dígitos"),
    ],
)
def test_errores_del_numero_por_http(ruta: str, numero: str, mensaje: str) -> None:
    datos = {"nit": numero}
    if ruta == "/validar":
        datos["digito"] = "6"
    estado, respuesta = _consultar(ruta, datos)
    assert estado == 400
    assert respuesta == {"error": mensaje}


@pytest.mark.parametrize("digito", ["", "A", "12"])
def test_errores_del_digito_por_http(digito: str) -> None:
    estado, respuesta = _consultar("/validar", {"nit": "123456789", "digito": digito})
    assert estado == 400
    assert respuesta == {"error": "El dígito de verificación debe ser una sola cifra"}


@pytest.mark.parametrize(
    ("ruta", "datos"),
    [
        ("/calcular", {}),
        ("/calcular", {"nit": 123456789}),
        ("/calcular", {"nit": None}),
        ("/calcular", {"nit": "123456789", "otro": "dato"}),
        ("/calcular", ["123456789"]),
        ("/validar", {"nit": "123456789"}),
        ("/validar", {"digito": "6"}),
        ("/validar", {"nit": "123456789", "digito": 6}),
        ("/validar", {"nit": "123456789", "digito": None}),
    ],
)
def test_estructura_invalida(ruta: str, datos: object) -> None:
    estado, respuesta = _consultar(ruta, datos)
    assert estado == 400
    assert respuesta == {"error": "Solicitud JSON inválida o incompleta"}


@pytest.mark.parametrize("cuerpo", [b"", b"{", b"null"])
def test_json_invalido_o_ausente(cuerpo: bytes) -> None:
    estado, respuesta = asyncio.run(_intercambiar("/calcular", cuerpo))
    assert estado == 400
    assert respuesta == {"error": "Solicitud JSON inválida o incompleta"}


def test_ruta_inexistente() -> None:
    estado, respuesta = _consultar("/inexistente", {})
    assert estado == 404
    assert respuesta == {"detail": "Not Found"}


def test_metodo_no_permitido() -> None:
    estado, respuesta = asyncio.run(_intercambiar("/calcular", b"", "GET"))
    assert estado == 405
    assert respuesta == {"detail": "Method Not Allowed"}


def test_contrato_openapi() -> None:
    esquema = crear_app().openapi()
    assert "/calcular" in esquema["paths"]
    assert "/validar" in esquema["paths"]
    for ruta in ("/calcular", "/validar"):
        operacion = esquema["paths"][ruta]["post"]
        assert "application/json" in operacion["requestBody"]["content"]
        assert "400" in operacion["responses"]
    assert "discrepancia" in esquema["info"]["description"]
