"""Pruebas sin red del contrato HTTP mediante la interfaz WSGI real."""

import io
import json
from typing import cast
from wsgiref.types import StartResponse, WSGIEnvironment

import pytest

from nit_service import application


def _consultar(
    ruta: str,
    cuerpo: bytes,
    metodo: str = "POST",
    tipo: str = "application/json",
    longitud: str | None = None,
) -> tuple[str, dict[str, str], dict[str, object]]:
    captura: dict[str, object] = {}

    def iniciar(
        estado: str,
        cabeceras: list[tuple[str, str]],
        exc_info: object = None,
    ) -> None:
        captura["estado"] = estado
        captura["cabeceras"] = dict(cabeceras)

    entorno: WSGIEnvironment = {
        "REQUEST_METHOD": metodo,
        "PATH_INFO": ruta,
        "CONTENT_TYPE": tipo,
        "CONTENT_LENGTH": str(len(cuerpo)) if longitud is None else longitud,
        "wsgi.input": io.BytesIO(cuerpo),
    }
    respuesta = b"".join(application(entorno, cast(StartResponse, iniciar)))
    cabeceras = cast(dict[str, str], captura["cabeceras"])
    assert cabeceras["Content-Type"] == "application/json; charset=utf-8"
    assert int(cabeceras["Content-Length"]) == len(respuesta)
    return str(captura["estado"]), cabeceras, json.loads(respuesta.decode("utf-8"))


def _json(datos: object) -> bytes:
    return json.dumps(datos, ensure_ascii=False).encode("utf-8")


@pytest.mark.parametrize("nit, esperado", [("900123456", 8), ("123456789", 6)])
def test_calcular_por_http(nit: str, esperado: int) -> None:
    estado, _, datos = _consultar("/calcular", _json({"nit": nit}))
    assert estado == "200 OK"
    assert datos == {"digito": esperado}


@pytest.mark.parametrize("digito, valido", [("8", True), ("7", False)])
def test_validar_por_http(digito: str, valido: bool) -> None:
    estado, _, datos = _consultar("/validar", _json({"nit": "900123456", "digito": digito}))
    assert estado == "200 OK"
    assert datos == {"valido": valido, "digito_esperado": 8}


def test_formato_normalizado_por_http() -> None:
    estado, _, datos = _consultar("/calcular", _json({"nit": "000.900-123.456"}))
    assert estado == "200 OK"
    assert datos == {"digito": 8}


@pytest.mark.parametrize("ruta", ["/calcular", "/validar"])
@pytest.mark.parametrize(
    "nit, mensaje",
    [
        ("A", "El NIT solo admite dígitos"),
        ("1" * 16, "El NIT admite como máximo 15 dígitos"),
        ("", "El NIT debe contener al menos un dígito"),
        ("1 2", "El NIT solo admite dígitos"),
        (123, "El NIT debe ser texto"),
        (None, "El NIT debe ser texto"),
    ],
)
def test_errores_del_nit_por_http(ruta: str, nit: object, mensaje: str) -> None:
    solicitud = {"nit": nit}
    if ruta == "/validar":
        solicitud["digito"] = "8"
    estado, _, datos = _consultar(ruta, _json(solicitud))
    assert estado == "400 Bad Request"
    assert datos == {"error": mensaje}


@pytest.mark.parametrize("digito", [8, None, "", "88", "A", " 8"])
def test_digito_mal_formado_por_http(digito: object) -> None:
    estado, _, datos = _consultar("/validar", _json({"nit": "900123456", "digito": digito}))
    assert estado == "400 Bad Request"
    assert datos == {"error": "El dígito de verificación debe ser un único dígito de texto"}


@pytest.mark.parametrize(
    "ruta, solicitud, mensaje",
    [
        ("/calcular", {}, "Campos requeridos y únicos: nit"),
        ("/calcular", {"nit": "1", "otro": 2}, "Campos requeridos y únicos: nit"),
        ("/validar", {"nit": "1"}, "Campos requeridos y únicos: digito, nit"),
        ("/validar", {"digito": "8"}, "Campos requeridos y únicos: digito, nit"),
        (
            "/validar",
            {"nit": "1", "digito": "8", "otro": 2},
            "Campos requeridos y únicos: digito, nit",
        ),
    ],
)
def test_campos_requeridos_y_extras(ruta: str, solicitud: object, mensaje: str) -> None:
    estado, _, datos = _consultar(ruta, _json(solicitud))
    assert estado == "400 Bad Request"
    assert datos == {"error": mensaje}


@pytest.mark.parametrize("cuerpo", [b"", b"{", b"\xff"])
def test_json_invalido(cuerpo: bytes) -> None:
    estado, _, datos = _consultar("/calcular", cuerpo)
    assert estado == "400 Bad Request"
    assert datos == {"error": "El cuerpo debe ser JSON válido en UTF-8"}


@pytest.mark.parametrize("solicitud", [[], None, "123", 123])
def test_cuerpo_no_es_objeto(solicitud: object) -> None:
    estado, _, datos = _consultar("/calcular", _json(solicitud))
    assert estado == "400 Bad Request"
    assert datos == {"error": "El cuerpo debe ser un objeto JSON"}


def test_tipo_de_contenido_incorrecto() -> None:
    estado, _, datos = _consultar("/calcular", _json({"nit": "1"}), tipo="text/plain")
    assert estado == "400 Bad Request"
    assert datos == {"error": "La solicitud debe usar Content-Type application/json"}


def test_tipo_de_contenido_con_charset() -> None:
    estado, _, datos = _consultar(
        "/calcular", _json({"nit": "1"}), tipo="application/json; charset=utf-8"
    )
    assert estado == "200 OK"
    assert datos == {"digito": 8}


@pytest.mark.parametrize("longitud", ["abc", "-1"])
def test_longitud_invalida(longitud: str) -> None:
    estado, _, datos = _consultar("/calcular", b"{}", longitud=longitud)
    assert estado == "400 Bad Request"
    assert datos == {"error": "Content-Length inválido"}


def test_metodo_no_permitido() -> None:
    estado, cabeceras, datos = _consultar("/calcular", b"", metodo="GET")
    assert estado == "405 Method Not Allowed"
    assert cabeceras["Allow"] == "POST"
    assert datos == {"error": "Método no permitido; use POST"}


def test_ruta_desconocida() -> None:
    estado, _, datos = _consultar("/otra", b"{}")
    assert estado == "404 Not Found"
    assert datos == {"error": "Ruta no encontrada"}
