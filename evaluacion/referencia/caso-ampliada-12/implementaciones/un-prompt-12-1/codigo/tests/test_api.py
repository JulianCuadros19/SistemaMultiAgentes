import asyncio
import json

import pytest

from nit_service.api import app


def _solicitar(ruta, datos=None, *, metodo="POST", cuerpo=None):
    contenido = json.dumps(datos).encode() if cuerpo is None else cuerpo
    mensajes = []

    async def recibir():
        return {"type": "http.request", "body": contenido, "more_body": False}

    async def enviar(mensaje):
        mensajes.append(mensaje)

    async def ejecutar():
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
            "server": ("localhost", 8000),
        }
        await app(scope, recibir, enviar)

    asyncio.run(ejecutar())
    inicio = next(mensaje for mensaje in mensajes if mensaje["type"] == "http.response.start")
    cuerpo_respuesta = b"".join(
        mensaje.get("body", b"")
        for mensaje in mensajes
        if mensaje["type"] == "http.response.body"
    )
    assert b"application/json" in dict(inicio["headers"])[b"content-type"]
    return inicio["status"], json.loads(cuerpo_respuesta)


def test_http_calcular():
    estado, respuesta = _solicitar("/calcular", {"numero": "123.456-789"})
    assert estado == 200
    assert respuesta == {"numero": "123456789", "digito": 6}


def test_http_validar_campos_separados():
    estado, respuesta = _solicitar("/validar", {"numero": "123.456.789", "digito": "6"})
    assert estado == 200
    assert respuesta == {
        "numero": "123456789",
        "digito": 6,
        "valido": True,
        "digito_esperado": 6,
    }


def test_http_validar_completo_incorrecto():
    estado, respuesta = _solicitar("/validar", {"nit": "123.456.789-5"})
    assert estado == 200
    assert respuesta == {
        "numero": "123456789",
        "digito": 5,
        "valido": False,
        "digito_esperado": 6,
    }


@pytest.mark.parametrize(
    ("nit", "valido"), [("900.123.456-8", False), ("900123456-7", True)]
)
def test_http_ejemplos_900_segun_formula_documentada(nit, valido):
    estado, respuesta = _solicitar("/validar", {"nit": nit})
    assert estado == 200
    assert respuesta["valido"] is valido
    assert respuesta["digito_esperado"] == 7


@pytest.mark.parametrize(
    ("numero", "mensaje"),
    [
        ("123A", "El NIT solo admite dígitos"),
        ("1234567890123456", "El NIT admite como máximo 15 dígitos"),
        ("", "El NIT debe contener al menos 1 dígito"),
    ],
)
@pytest.mark.parametrize("ruta", ["/calcular", "/validar"])
def test_http_errores_del_numero(ruta, numero, mensaje):
    datos = {"numero": numero}
    if ruta == "/validar":
        datos["digito"] = "6"
    estado, respuesta = _solicitar(ruta, datos)
    assert estado == 400
    assert respuesta == {"error": mensaje}


def test_http_error_del_digito():
    estado, respuesta = _solicitar("/validar", {"numero": "123", "digito": "12"})
    assert estado == 400
    assert respuesta == {
        "error": "El dígito de verificación debe ser un dígito de 0 a 9"
    }


def test_http_error_completo_sin_separador():
    estado, respuesta = _solicitar("/validar", {"nit": "1234567896"})
    assert estado == 400
    assert respuesta == {"error": "El NIT completo debe separar el dígito con un guion"}


@pytest.mark.parametrize(
    ("ruta", "datos"),
    [
        ("/calcular", {}),
        ("/calcular", {"numero": 123}),
        ("/calcular", {"numero": None}),
        ("/calcular", {"numero": "123", "extra": "x"}),
        ("/calcular", []),
        ("/validar", {"numero": "123"}),
        ("/validar", {"numero": "123", "digito": 6}),
        ("/validar", {"nit": 123}),
        ("/validar", {"nit": "123-6", "numero": "123", "digito": "6"}),
    ],
)
def test_http_rechaza_estructura_o_tipos_incorrectos(ruta, datos):
    estado, respuesta = _solicitar(ruta, datos)
    assert estado == 422
    assert respuesta == {
        "error": (
            "Solicitud inválida: envíe JSON con los campos documentados, "
            "todos como cadenas y sin campos adicionales"
        )
    }


def test_http_json_malformado():
    estado, respuesta = _solicitar("/calcular", cuerpo=b"{")
    assert estado == 422
    assert "Solicitud inválida" in respuesta["error"]


def test_contrato_openapi():
    estado, contrato = _solicitar("/openapi.json", metodo="GET")
    assert estado == 200
    assert contrato["info"]["version"] == "1.0.0"
    for ruta in ("/calcular", "/validar"):
        operacion = contrato["paths"][ruta]["post"]
        assert operacion["requestBody"]["required"]
        assert {"200", "400", "422"} <= set(operacion["responses"])
    esquema = contrato["components"]["schemas"]["EntradaCalculo"]
    assert esquema["properties"]["numero"]["type"] == "string"
    assert esquema["additionalProperties"] is False
    validacion = contrato["paths"]["/validar"]["post"]
    assert len(validacion["requestBody"]["content"]["application/json"]["schema"]["anyOf"]) == 2
