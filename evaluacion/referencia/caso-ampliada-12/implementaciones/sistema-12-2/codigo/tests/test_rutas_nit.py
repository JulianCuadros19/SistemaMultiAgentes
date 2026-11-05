import asyncio
import json

import pytest

from rutas.nit import crear_app


async def _solicitar(app, ruta, datos):
    cuerpo = json.dumps(datos).encode("utf-8")
    mensajes = []

    async def recibir():
        return {"type": "http.request", "body": cuerpo, "more_body": False}

    async def enviar(mensaje):
        mensajes.append(mensaje)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": ruta,
        "raw_path": ruta.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 1234),
        "server": ("localhost", 80),
    }
    await app(scope, recibir, enviar)
    estado = next(m["status"] for m in mensajes if m["type"] == "http.response.start")
    contenido = b"".join(m.get("body", b"") for m in mensajes if m["type"] == "http.response.body")
    return estado, json.loads(contenido)


def _post(ruta, datos):
    return asyncio.run(_solicitar(crear_app(), ruta, datos))


def test_rf_01_esc_01_http_calcula_digito():
    assert _post("/v1/nit/calcular-digito", {"numero": "900123456"}) == (
        200,
        {"digito_esperado": 8},
    )


def test_rf_01_esc_02_http_acepta_separadores():
    assert _post("/v1/nit/calcular-digito", {"numero": "900123456-7"}) == (
        200,
        {"digito_esperado": 8},
    )


def test_rf_01_esc_03_http_rechaza_letras():
    assert _post("/v1/nit/calcular-digito", {"numero": "90012A456"}) == (
        400,
        {"detail": "El NIT solo admite dígitos"},
    )


def test_rf_02_esc_01_http_valida_nit():
    assert _post("/v1/nit/validar", {"nit": "900123456-8"}) == (
        200,
        {"valido": True, "digito_esperado": 8},
    )


def test_rf_02_esc_02_http_informa_digito_incorrecto():
    assert _post("/v1/nit/validar", {"nit": "900123456-7"}) == (
        200,
        {"valido": False, "digito_esperado": 8},
    )


def test_rf_02_esc_03_http_rechaza_longitud():
    assert _post("/v1/nit/validar", {"nit": "1234567890123456"}) == (
        400,
        {"detail": "El NIT admite como máximo 15 dígitos"},
    )


@pytest.mark.parametrize(
    ("ruta", "datos"),
    [
        ("/v1/nit/calcular-digito", {}),
        ("/v1/nit/calcular-digito", {"numero": 900123456}),
        ("/v1/nit/validar", {}),
        ("/v1/nit/validar", {"nit": None}),
    ],
)
def test_http_rechaza_contrato_incorrecto(ruta, datos):
    estado, respuesta = _post(ruta, datos)
    assert estado == 422
    assert respuesta["detail"]


def test_http_rechaza_calculo_demasiado_largo():
    assert _post("/v1/nit/calcular-digito", {"numero": "1234567890123456"}) == (
        400,
        {"detail": "El NIT admite como máximo 15 dígitos"},
    )
