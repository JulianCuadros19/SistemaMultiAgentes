"""Contrato HTTP y reglas de negocio del impuesto predial."""

import json
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

_TARIFAS_RESIDENCIALES = {1: 5, 2: 6, 3: 8, 4: 10, 5: 12, 6: 14}
_TARIFAS_OTROS = {
    "comercial": 11,
    "industrial": 12,
    "lote urbanizable no edificado": 33,
}
_DESTINOS = ["residencial", *_TARIFAS_OTROS]


class ErrorConsulta(ValueError):
    """Indica una consulta inválida; su texto es el mensaje para el consumidor."""


def _validar_campos(datos: dict[str, object], permitidos: set[str]) -> None:
    if datos.keys() - permitidos:
        raise ErrorConsulta("La consulta contiene campos no permitidos")


def _obtener_tarifa(datos: dict[str, object]) -> int:
    if "destino" not in datos:
        raise ErrorConsulta("El destino es obligatorio")
    destino = datos["destino"]
    if not isinstance(destino, str) or destino not in _DESTINOS:
        raise ErrorConsulta("Destino económico no reconocido")
    if destino != "residencial":
        if "estrato" in datos:
            raise ErrorConsulta("El estrato solo aplica para residencial")
        return _TARIFAS_OTROS[destino]
    if "estrato" not in datos:
        raise ErrorConsulta("El estrato es obligatorio para residencial")
    estrato = datos["estrato"]
    if type(estrato) is not int or estrato not in _TARIFAS_RESIDENCIALES:
        raise ErrorConsulta("Estrato inválido")
    return _TARIFAS_RESIDENCIALES[estrato]


def consultar_tarifa(datos: dict[str, object]) -> dict[str, int]:
    """Devuelva la tarifa en pesos por cada mil pesos de avalúo.

    Args:
        datos: Destino y, exclusivamente para residencial, estrato entero de 1 a 6.

    Returns:
        Un diccionario con la clave tarifa_por_mil.

    Raises:
        ErrorConsulta: Si faltan datos, son inválidos o hay campos no permitidos.
    """
    _validar_campos(datos, {"destino", "estrato"})
    return {"tarifa_por_mil": _obtener_tarifa(datos)}


def calcular_impuesto(datos: dict[str, object]) -> dict[str, int]:
    """Calcule el impuesto en pesos enteros con mitades hacia arriba.

    Args:
        datos: Destino, estrato cuando es residencial y avalúo entero positivo.

    Returns:
        Un diccionario con tarifa_por_mil e impuesto_pesos.

    Raises:
        ErrorConsulta: Si faltan datos, son inválidos o hay campos no permitidos.
    """
    _validar_campos(datos, {"destino", "estrato", "avaluo"})
    tarifa = _obtener_tarifa(datos)
    if "avaluo" not in datos:
        raise ErrorConsulta("El avalúo es obligatorio")
    avaluo = datos["avaluo"]
    if type(avaluo) is not int:
        raise ErrorConsulta("El avalúo debe ser un entero en pesos")
    if avaluo <= 0:
        raise ErrorConsulta("El avalúo debe ser mayor que cero")
    impuesto = (avaluo * tarifa + 500) // 1000
    return {"tarifa_por_mil": tarifa, "impuesto_pesos": impuesto}


def _esquema_cuerpo(con_avaluo: bool) -> dict[str, object]:
    propiedades: dict[str, object] = {
        "destino": {"type": "string", "enum": _DESTINOS},
        "estrato": {"type": "integer", "minimum": 1, "maximum": 6},
    }
    obligatorios = ["destino"]
    if con_avaluo:
        propiedades["avaluo"] = {"type": "integer", "minimum": 1}
        obligatorios.append("avaluo")
    esquema = {
        "type": "object",
        "properties": propiedades,
        "required": obligatorios,
        "additionalProperties": False,
        "oneOf": [
            {
                "properties": {"destino": {"const": "residencial"}},
                "required": ["estrato"],
            },
            {
                "properties": {"destino": {"enum": list(_TARIFAS_OTROS)}},
                "not": {"required": ["estrato"]},
            },
        ],
    }
    return {
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": esquema}},
        },
    }


_ERRORES_HTTP = {
    400: {
        "description": "Cuerpo vacío, JSON mal formado o raíz distinta de un objeto.",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                    "required": ["error"],
                },
            },
        },
    },
    415: {"description": "El cuerpo debe usar Content-Type application/json."},
    422: {"description": "Datos de consulta inválidos; respuesta con la clave error."},
}

app = FastAPI(
    title="Consulta del impuesto predial",
    version="1.0.0",
    description=(
        "Dos consultas independientes. Los valores monetarios son pesos enteros; "
        "la tarifa se expresa en pesos por cada mil pesos de avalúo. "
        "Los errores de datos se devuelven como {\"error\": \"mensaje\"}."
    ),
)


@app.exception_handler(ErrorConsulta)
async def manejar_error_consulta(request: Request, exc: ErrorConsulta) -> JSONResponse:
    """Convierta los errores de negocio en respuestas JSON con estado 422."""
    return JSONResponse(status_code=422, content={"error": str(exc)})


async def _leer_datos(request: Request) -> dict[str, object] | JSONResponse:
    tipo = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if tipo != "application/json":
        return JSONResponse(
            status_code=415,
            content={"error": "El contenido debe ser application/json"},
        )
    try:
        datos: object = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return JSONResponse(status_code=400, content={"error": "JSON inválido"})
    if not isinstance(datos, dict):
        return JSONResponse(
            status_code=400,
            content={"error": "El cuerpo debe ser un objeto JSON"},
        )
    return cast(dict[str, object], datos)


@app.post(
    "/tarifa",
    summary="Consultar únicamente la tarifa",
    openapi_extra=_esquema_cuerpo(con_avaluo=False),
    responses=_ERRORES_HTTP,
    response_model=dict[str, int],
)
async def tarifa_http(request: Request) -> dict[str, int] | JSONResponse:
    """Atienda una consulta de tarifa sin calcular el impuesto."""
    datos = await _leer_datos(request)
    if isinstance(datos, JSONResponse):
        return datos
    return consultar_tarifa(datos)


@app.post(
    "/impuesto",
    summary="Calcular el impuesto con avalúo obligatorio",
    openapi_extra=_esquema_cuerpo(con_avaluo=True),
    responses=_ERRORES_HTTP,
    response_model=dict[str, int],
)
async def impuesto_http(request: Request) -> dict[str, int] | JSONResponse:
    """Atienda una consulta de impuesto y devuelva también la tarifa utilizada."""
    datos = await _leer_datos(request)
    if isinstance(datos, JSONResponse):
        return datos
    return calcular_impuesto(datos)
