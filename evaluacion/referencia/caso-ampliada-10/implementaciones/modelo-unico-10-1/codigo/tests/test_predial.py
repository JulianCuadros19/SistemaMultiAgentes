"""Pruebas de reglas, ejemplos, errores y contrato HTTP sin conexiones de red."""

import asyncio
import json

import pytest
from starlette.types import Message, Scope

from predial import ErrorConsulta, app, calcular_impuesto, consultar_tarifa


async def _intercambio(
    ruta: str,
    cuerpo: bytes,
    metodo: str,
    tipo_contenido: str,
) -> tuple[int, object]:
    mensajes: list[Message] = []
    recibido = False
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
        "headers": [(b"content-type", tipo_contenido.encode())],
        "server": ("localhost", 8000),
        "client": ("localhost", 12345),
    }

    async def recibir() -> Message:
        nonlocal recibido
        if recibido:
            return {"type": "http.disconnect"}
        recibido = True
        return {"type": "http.request", "body": cuerpo, "more_body": False}

    async def enviar(mensaje: Message) -> None:
        mensajes.append(mensaje)

    await app(scope, recibir, enviar)
    inicio = next(m for m in mensajes if m["type"] == "http.response.start")
    cabeceras = dict(inicio["headers"])
    assert cabeceras[b"content-type"].startswith(b"application/json")
    salida = b"".join(m.get("body", b"") for m in mensajes if m["type"] == "http.response.body")
    return inicio["status"], json.loads(salida)


def _http(
    ruta: str,
    datos: object = None,
    *,
    cuerpo: bytes | None = None,
    metodo: str = "POST",
    tipo_contenido: str = "application/json",
) -> tuple[int, object]:
    contenido = json.dumps(datos).encode() if cuerpo is None else cuerpo
    return asyncio.run(_intercambio(ruta, contenido, metodo, tipo_contenido))


@pytest.mark.parametrize("estrato,tarifa", [(1, 5), (2, 6), (3, 8), (4, 10), (5, 12), (6, 14)])
def test_tarifas_residenciales(estrato: int, tarifa: int) -> None:
    assert _http("/tarifa", {"destino": "residencial", "estrato": estrato}) == (
        200,
        {"tarifa_por_mil": tarifa},
    )


@pytest.mark.parametrize(
    "destino,tarifa",
    [("comercial", 11), ("industrial", 12), ("lote urbanizable no edificado", 33)],
)
def test_tarifas_no_residenciales(destino: str, tarifa: int) -> None:
    assert _http("/tarifa", {"destino": destino}) == (200, {"tarifa_por_mil": tarifa})
    assert _http("/impuesto", {"destino": destino, "avaluo": 1000000}) == (
        200,
        {"tarifa_por_mil": tarifa, "impuesto_pesos": tarifa * 1000},
    )


def test_ejemplo_cliente() -> None:
    assert _http(
        "/impuesto", {"destino": "residencial", "estrato": 3, "avaluo": 120000000}
    ) == (200, {"tarifa_por_mil": 8, "impuesto_pesos": 960000})


@pytest.mark.parametrize("avaluo,impuesto", [(99, 0), (100, 1), (101, 1), (300, 2)])
def test_redondeo_al_peso_mitades_hacia_arriba(avaluo: int, impuesto: int) -> None:
    assert _http(
        "/impuesto", {"destino": "residencial", "estrato": 1, "avaluo": avaluo}
    ) == (200, {"tarifa_por_mil": 5, "impuesto_pesos": impuesto})


@pytest.mark.parametrize("ruta", ["/tarifa", "/impuesto"])
@pytest.mark.parametrize("destino", ["desconocido", "Residencial", " comercial ", None, 1, True])
def test_destino_no_reconocido(ruta: str, destino: object) -> None:
    assert _http(ruta, {"destino": destino}) == (
        422,
        {"error": "Destino económico no reconocido"},
    )


@pytest.mark.parametrize("ruta", ["/tarifa", "/impuesto"])
@pytest.mark.parametrize("estrato", [0, 7, -1, 1.0, "1", True, None])
def test_estrato_invalido(ruta: str, estrato: object) -> None:
    assert _http(ruta, {"destino": "residencial", "estrato": estrato}) == (
        422,
        {"error": "Estrato inválido"},
    )


@pytest.mark.parametrize("avaluo", [0, -1, -120000000])
def test_avaluo_no_positivo(avaluo: int) -> None:
    assert _http("/impuesto", {"destino": "comercial", "avaluo": avaluo}) == (
        422,
        {"error": "El avalúo debe ser mayor que cero"},
    )


@pytest.mark.parametrize("avaluo", [1.0, 1.5, "1000", "1.000", "1,000", True, None])
def test_avaluo_no_entero(avaluo: object) -> None:
    assert _http("/impuesto", {"destino": "comercial", "avaluo": avaluo}) == (
        422,
        {"error": "El avalúo debe ser un entero en pesos"},
    )


@pytest.mark.parametrize("ruta", ["/tarifa", "/impuesto"])
def test_destino_obligatorio(ruta: str) -> None:
    assert _http(ruta, {}) == (422, {"error": "El destino es obligatorio"})


@pytest.mark.parametrize("ruta", ["/tarifa", "/impuesto"])
def test_estrato_residencial_obligatorio(ruta: str) -> None:
    assert _http(ruta, {"destino": "residencial"}) == (
        422,
        {"error": "El estrato es obligatorio para residencial"},
    )


@pytest.mark.parametrize("ruta", ["/tarifa", "/impuesto"])
@pytest.mark.parametrize("destino", ["comercial", "industrial", "lote urbanizable no edificado"])
@pytest.mark.parametrize("estrato", [1, None])
def test_estrato_prohibido_para_otros_destinos(ruta: str, destino: str, estrato: object) -> None:
    assert _http(ruta, {"destino": destino, "estrato": estrato}) == (
        422,
        {"error": "El estrato solo aplica para residencial"},
    )


def test_impuesto_exige_avaluo_y_no_devuelve_solo_tarifa() -> None:
    assert _http("/impuesto", {"destino": "comercial"}) == (
        422,
        {"error": "El avalúo es obligatorio"},
    )


@pytest.mark.parametrize(
    "ruta,datos",
    [
        ("/tarifa", {"destino": "comercial", "avaluo": 1000}),
        ("/impuesto", {"destino": "comercial", "avaluo": 1000, "descuento": 10}),
    ],
)
def test_campos_no_permitidos(ruta: str, datos: dict[str, object]) -> None:
    assert _http(ruta, datos) == (
        422,
        {"error": "La consulta contiene campos no permitidos"},
    )


@pytest.mark.parametrize("cuerpo", [b"", b"{", b"{\"destino\":", b"\xff"])
def test_json_invalido(cuerpo: bytes) -> None:
    assert _http("/tarifa", cuerpo=cuerpo) == (400, {"error": "JSON inválido"})


@pytest.mark.parametrize("datos", [None, [], "comercial", 123, True])
def test_cuerpo_debe_ser_objeto(datos: object) -> None:
    assert _http("/tarifa", datos) == (400, {"error": "El cuerpo debe ser un objeto JSON"})


def test_tipo_de_contenido() -> None:
    assert _http("/tarifa", {"destino": "comercial"}, tipo_contenido="text/plain") == (
        415,
        {"error": "El contenido debe ser application/json"},
    )
    assert _http("/tarifa", {"destino": "comercial"}, tipo_contenido="") == (
        415,
        {"error": "El contenido debe ser application/json"},
    )
    assert _http(
        "/tarifa", {"destino": "comercial"}, tipo_contenido="application/json; charset=utf-8"
    ) == (200, {"tarifa_por_mil": 11})


def test_metodo_y_ruta_desconocidos() -> None:
    assert _http("/tarifa", metodo="GET") == (405, {"detail": "Method Not Allowed"})
    assert _http("/no-existe") == (404, {"detail": "Not Found"})


def test_sin_maximo_de_negocio_y_sin_perdida_de_precision() -> None:
    avaluo = 10**100 + 499
    assert _http("/impuesto", {"destino": "industrial", "avaluo": avaluo}) == (
        200,
        {"tarifa_por_mil": 12, "impuesto_pesos": (avaluo * 12 + 500) // 1000},
    )


def test_funciones_python_y_error_de_dominio() -> None:
    assert consultar_tarifa({"destino": "comercial"}) == {"tarifa_por_mil": 11}
    assert calcular_impuesto({"destino": "industrial", "avaluo": 1000}) == {
        "tarifa_por_mil": 12,
        "impuesto_pesos": 12,
    }
    with pytest.raises(ErrorConsulta, match="^El destino es obligatorio$"):
        consultar_tarifa({})


def test_contrato_openapi_disponible_sin_red() -> None:
    estado, contrato = _http("/openapi.json", metodo="GET")
    assert estado == 200
    assert isinstance(contrato, dict)
    for ruta in ("/tarifa", "/impuesto"):
        operacion = contrato["paths"][ruta]["post"]
        esquema = operacion["requestBody"]["content"]["application/json"]["schema"]
        assert esquema["additionalProperties"] is False
        assert "destino" in esquema["required"]
        assert len(esquema["oneOf"]) == 2
        assert ("avaluo" in esquema["required"]) == (ruta == "/impuesto")
        for estado_error in ("400", "415", "422"):
            assert estado_error in operacion["responses"]
