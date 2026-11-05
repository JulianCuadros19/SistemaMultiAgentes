import json
from http.client import HTTPConnection
from threading import Thread

import pytest

from nit_service import crear_servidor
from nit_service.http import procesar


@pytest.fixture
def servidor():
    with crear_servidor(puerto=0) as servicio:
        hilo = Thread(target=servicio.serve_forever, daemon=True)
        hilo.start()
        try:
            yield servicio.server_address
        finally:
            servicio.shutdown()
            hilo.join(timeout=5)


def consultar(servidor, ruta, cuerpo, metodo="POST", headers=None):
    conexion = HTTPConnection(*servidor, timeout=5)
    try:
        conexion.request(
            metodo,
            ruta,
            body=cuerpo,
            headers=headers or {"Content-Type": "application/json"},
        )
        respuesta = conexion.getresponse()
        contenido = respuesta.read()
        assert respuesta.getheader("Content-Type") == "application/json; charset=utf-8"
        assert int(respuesta.getheader("Content-Length")) == len(contenido)
        return respuesta.status, json.loads(contenido)
    finally:
        conexion.close()


@pytest.mark.parametrize(
    ("ruta", "nit", "esperado"),
    [
        ("/calcular", "900123456", {"nit": "900123456", "digito": "8"}),
        (
            "/validar",
            "900123456-8",
            {
                "nit": "900123456",
                "digito_recibido": "8",
                "digito_esperado": "8",
                "valido": True,
            },
        ),
        (
            "/validar",
            "900123456-7",
            {
                "nit": "900123456",
                "digito_recibido": "7",
                "digito_esperado": "8",
                "valido": False,
            },
        ),
    ],
)
def test_contrato_por_http(servidor, ruta, nit, esperado):
    assert consultar(servidor, ruta, json.dumps({"nit": nit})) == (200, esperado)


@pytest.mark.parametrize(
    ("nit", "mensaje"),
    [
        ("ABC", "El NIT solo admite dígitos"),
        ("1234567890123456", "El NIT admite como máximo 15 dígitos"),
        (123, "El NIT debe enviarse como texto"),
        ("", "El NIT debe contener al menos un dígito"),
    ],
)
def test_error_de_datos_distinto_de_no_coincidencia(servidor, nit, mensaje):
    assert consultar(servidor, "/calcular", json.dumps({"nit": nit})) == (
        400,
        {"error": mensaje},
    )


@pytest.mark.parametrize("cuerpo", [b"{", b"\xff"])
def test_json_invalido(servidor, cuerpo):
    assert consultar(servidor, "/calcular", cuerpo) == (
        400,
        {"error": "El cuerpo debe ser JSON válido en UTF-8"},
    )


@pytest.mark.parametrize("datos", [{}, [], None, {"nit": "1", "otro": 1}])
def test_forma_del_documento(servidor, datos):
    assert consultar(servidor, "/calcular", json.dumps(datos)) == (
        400,
        {"error": "El cuerpo debe contener únicamente el campo nit"},
    )


def test_ruta_desconocida(servidor):
    assert consultar(servidor, "/otra", "{}") == (404, {"error": "Ruta no encontrada"})


def test_get_no_es_operacion(servidor):
    assert consultar(servidor, "/calcular", None, metodo="GET") == (
        405,
        {"error": "Use POST"},
    )


@pytest.mark.parametrize("longitud", ["-1", "incorrecta"])
def test_content_length_invalido(servidor, longitud):
    assert consultar(servidor, "/calcular", b"", headers={"Content-Length": longitud}) == (
        400,
        {"error": "Se requiere Content-Length válido"},
    )


def test_content_length_ausente(servidor):
    conexion = HTTPConnection(*servidor, timeout=5)
    try:
        conexion.putrequest("POST", "/calcular")
        conexion.endheaders()
        respuesta = conexion.getresponse()
        assert respuesta.status == 400
        assert json.loads(respuesta.read()) == {"error": "Se requiere Content-Length válido"}
    finally:
        conexion.close()


def test_transferencia_fragmentada_no_soportada(servidor):
    assert consultar(
        servidor,
        "/calcular",
        b"",
        headers={"Content-Length": "0", "Transfer-Encoding": "chunked"},
    ) == (400, {"error": "Transfer-Encoding no está soportado"})


def test_procesamiento_no_requiere_servidor():
    assert procesar("/calcular", b'{"nit":"900123456"}') == (
        200,
        {"nit": "900123456", "digito": "8"},
    )
