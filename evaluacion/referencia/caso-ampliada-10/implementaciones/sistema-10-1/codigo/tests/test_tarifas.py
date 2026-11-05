import asyncio
import json

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from esquemas.tarifas import (
    CalculoImpuestoRequest,
    CalculoImpuestoResponse,
    ConsultaTarifaRequest,
    ConsultaTarifaResponse,
)
from rutas.tarifas import construir_router
from servicios.tarifas import (
    AvaluoNoValidoError,
    CalculoImpuestoResultado,
    DestinoNoReconocidoError,
    EstratoInvalidoError,
    TarifaResultado,
    calcular_impuesto,
    obtener_tarifa,
)


def test_rf_01_esc_01_consulta_residencial():
    resultado = obtener_tarifa("residencial", 3)
    assert resultado == TarifaResultado(8, 3)


def test_rf_01_esc_02_consulta_comercial():
    resultado = obtener_tarifa("comercial")
    assert resultado.tarifa == 11
    assert resultado.estrato_aplicado is None


def test_rf_01_esc_03_destino_desconocido():
    with pytest.raises(DestinoNoReconocidoError, match="^Destino económico no reconocido$"):
        obtener_tarifa("desconocido")


def test_rf_01_esc_04_estrato_fuera_de_rango():
    with pytest.raises(EstratoInvalidoError, match="^Estrato inválido$"):
        obtener_tarifa("residencial", 7)


def test_rf_02_esc_01_calculo_residencial():
    resultado = calcular_impuesto(120_000_000, "residencial", 3)
    assert resultado == CalculoImpuestoResultado(960_000, 8, 3)


def test_rf_02_esc_02_calculo_comercial():
    resultado = calcular_impuesto(100_000_000, "comercial")
    assert resultado.impuesto_calculado == 1_100_000
    assert type(resultado.impuesto_calculado) is int
    assert resultado.tarifa == 11
    assert resultado.estrato_aplicado is None


def test_rf_02_esc_03_avaluo_cero():
    with pytest.raises(AvaluoNoValidoError, match="^El avalúo debe ser mayor que cero$"):
        calcular_impuesto(0, "comercial")


def test_rf_02_esc_04_destino_desconocido():
    with pytest.raises(DestinoNoReconocidoError, match="^Destino económico no reconocido$"):
        calcular_impuesto(50_000_000, "desconocido")


@pytest.mark.parametrize("estrato,tarifa", [(1, 5), (2, 6), (3, 8), (4, 10), (5, 12), (6, 14)])
def test_tabla_residencial_y_limites(estrato, tarifa):
    assert obtener_tarifa("residencial", estrato) == TarifaResultado(tarifa, estrato)


@pytest.mark.parametrize("estrato", [None, 0, -1, 7, True, "3", 3.5])
def test_estrato_invalido_en_consulta_y_calculo(estrato):
    with pytest.raises(EstratoInvalidoError):
        obtener_tarifa("residencial", estrato)
    with pytest.raises(EstratoInvalidoError):
        calcular_impuesto(1, "residencial", estrato)


@pytest.mark.parametrize(
    "destino,tarifa", [("comercial", 11), ("industrial", 12), ("lote urbanizable no edificado", 33)]
)
def test_destinos_no_residenciales_ignoran_estrato(destino, tarifa):
    assert obtener_tarifa(destino, 3) == TarifaResultado(tarifa)
    assert calcular_impuesto(1000, destino, 3) == CalculoImpuestoResultado(tarifa, tarifa)


@pytest.mark.parametrize("avaluo", [-1, 0, True, "1000", 1.5])
def test_avaluo_no_entero_positivo(avaluo):
    with pytest.raises(AvaluoNoValidoError):
        calcular_impuesto(avaluo, "comercial")


@pytest.mark.parametrize("destino", ["", "Residencial", " comercial ", None, 1])
def test_destino_debe_ser_nombre_exacto(destino):
    with pytest.raises(DestinoNoReconocidoError):
        obtener_tarifa(destino)


@pytest.mark.parametrize("avaluo,esperado", [(1, 0), (99, 0), (100, 1), (101, 1), (300, 2)])
def test_redondeo_mitades_hacia_arriba(avaluo, esperado):
    assert calcular_impuesto(avaluo, "residencial", 1).impuesto_calculado == esperado


def test_calculo_no_depende_de_precision_decimal_predeterminada():
    avaluo = 10**40
    assert calcular_impuesto(avaluo, "comercial").impuesto_calculado == 11 * 10**37


def test_esquemas_peticion_y_respuesta():
    consulta = ConsultaTarifaRequest("residencial", 3)
    calculo = CalculoImpuestoRequest(120_000_000, "residencial", 3)
    assert consulta.destino == calculo.destino == "residencial"
    assert consulta.estrato == calculo.estrato == 3
    assert calculo.avaluo == 120_000_000
    assert ConsultaTarifaResponse(11).model_dump(exclude_none=True) == {"tarifa": 11}
    assert CalculoImpuestoResponse(960_000, 8, 3).model_dump() == {
        "impuesto_calculado": 960_000,
        "tarifa": 8,
        "estrato_aplicado": 3,
    }


def test_esquemas_rechazan_estrato_no_aplicable():
    with pytest.raises(ValidationError, match="El estrato solo aplica al destino residencial"):
        ConsultaTarifaRequest("comercial", 3)
    with pytest.raises(ValidationError, match="El estrato solo aplica al destino residencial"):
        CalculoImpuestoRequest(1000, "industrial", 3)


@pytest.mark.parametrize("avaluo", [True, "1000", 1.5])
def test_esquema_rechaza_avaluo_no_entero(avaluo):
    with pytest.raises(ValidationError):
        CalculoImpuestoRequest(avaluo, "comercial")


@pytest.mark.parametrize("estrato", [True, "3", 3.5])
def test_esquema_rechaza_estrato_no_entero(estrato):
    with pytest.raises(ValidationError):
        ConsultaTarifaRequest("residencial", estrato)


def test_esquema_campos_obligatorios():
    with pytest.raises(ValidationError):
        CalculoImpuestoRequest.model_validate({"destino": "comercial"})
    with pytest.raises(ValidationError):
        ConsultaTarifaRequest.model_validate({})


async def _solicitar(method, path, datos=None, query=b""):
    app = FastAPI()
    app.include_router(construir_router())
    cuerpo = b"" if datos is None else json.dumps(datos).encode()
    mensajes = []
    entregado = False

    async def recibir():
        nonlocal entregado
        if not entregado:
            entregado = True
            return {"type": "http.request", "body": cuerpo, "more_body": False}
        return {"type": "http.disconnect"}

    async def enviar(mensaje):
        mensajes.append(mensaje)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query,
        "root_path": "",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 1),
        "server": ("prueba", 80),
    }
    await app(scope, recibir, enviar)
    estado = next(
        mensaje["status"] for mensaje in mensajes if mensaje["type"] == "http.response.start"
    )
    respuesta = b"".join(
        mensaje.get("body", b"")
        for mensaje in mensajes
        if mensaje["type"] == "http.response.body"
    )
    return estado, json.loads(respuesta)


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_rutas_consulta_residencial(method):
    estado, respuesta = asyncio.run(
        _solicitar(
            method,
            "/tarifas",
            {"destino": "residencial", "estrato": 3} if method == "POST" else None,
            b"destino=residencial&estrato=3" if method == "GET" else b"",
        )
    )
    assert estado == 200
    assert respuesta == {"tarifa": 8, "estrato_aplicado": 3}


def test_ruta_comercial_omite_estrato():
    estado, respuesta = asyncio.run(_solicitar("GET", "/tarifas", query=b"destino=comercial"))
    assert estado == 200
    assert respuesta == {"tarifa": 11}


@pytest.mark.parametrize(
    "path,datos,esperado",
    [
        ("/tarifas", {"destino": "desconocido"}, "Destino económico no reconocido"),
        ("/tarifas", {"destino": "residencial", "estrato": 7}, "Estrato inválido"),
        (
            "/impuestos/calcular",
            {"avaluo": 0, "destino": "comercial"},
            "El avalúo debe ser mayor que cero",
        ),
        (
            "/impuestos/calcular",
            {"avaluo": 50_000_000, "destino": "desconocido"},
            "Destino económico no reconocido",
        ),
    ],
)
def test_rutas_errores_de_negocio(path, datos, esperado):
    estado, respuesta = asyncio.run(_solicitar("POST", path, datos))
    assert estado == 400
    assert respuesta == {"detail": esperado}


@pytest.mark.parametrize(
    "datos,esperado",
    [
        (
            {"avaluo": 120_000_000, "destino": "residencial", "estrato": 3},
            {"impuesto_calculado": 960_000, "tarifa": 8, "estrato_aplicado": 3},
        ),
        (
            {"avaluo": 100_000_000, "destino": "comercial"},
            {"impuesto_calculado": 1_100_000, "tarifa": 11},
        ),
    ],
)
def test_ruta_calculo(datos, esperado):
    estado, respuesta = asyncio.run(_solicitar("POST", "/impuestos/calcular", datos))
    assert estado == 200
    assert respuesta == esperado


@pytest.mark.parametrize(
    "path,datos",
    [
        ("/tarifas", {}),
        ("/tarifas", {"destino": "comercial", "estrato": 3}),
        ("/impuestos/calcular", {"destino": "comercial"}),
        ("/impuestos/calcular", {"destino": "comercial", "avaluo": 1.5}),
    ],
)
def test_rutas_peticion_invalida(path, datos):
    estado, respuesta = asyncio.run(_solicitar("POST", path, datos))
    assert estado == 422
    assert "detail" in respuesta
