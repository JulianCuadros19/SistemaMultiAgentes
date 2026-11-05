"""Servicio HTTP y contrato OpenAPI del impuesto predial."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException

from predial.dominio import ErrorConsulta, calcular_impuesto, consultar_tarifa


class SolicitudTarifa(BaseModel):
    """Entrada de una consulta de tarifa predial."""

    model_config = ConfigDict(strict=True, extra="forbid")

    destino: str = Field(
        description=(
            "Nombre exacto: residencial, comercial, industrial o "
            "lote urbanizable no edificado."
        ),
    )
    estrato: int | None = Field(
        default=None,
        description="Entero de 1 a 6, obligatorio para residencial; ignorado en otros destinos.",
    )


class SolicitudImpuesto(SolicitudTarifa):
    """Entrada del cálculo, con avalúo en pesos enteros."""

    avaluo: int = Field(description="Avalúo positivo en pesos enteros, sin decimales.")


class RespuestaTarifa(BaseModel):
    """Tarifa aplicable, expresada en pesos por cada mil pesos de avalúo."""

    tarifa: int = Field(description="Pesos por cada mil pesos de avalúo.")


class RespuestaImpuesto(RespuestaTarifa):
    """Tarifa aplicada e impuesto redondeado en pesos enteros."""

    impuesto: int = Field(description="Impuesto en pesos enteros; mitades hacia arriba.")


class RespuestaError(BaseModel):
    """Mensaje de error legible para los sistemas consumidores."""

    error: str


app = FastAPI(
    title="Servicio de impuesto predial",
    version="1.0.0",
    description=(
        "Consulta de tarifas por mil y cálculo del impuesto en pesos enteros. "
        "Las entradas inválidas reciben HTTP 400 con un campo error."
    ),
)


@app.exception_handler(ErrorConsulta)
async def error_consulta(_request: Request, exc: ErrorConsulta) -> JSONResponse:
    """Convierta los errores de dominio en respuestas HTTP 400."""
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(RequestValidationError)
async def error_validacion(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    """Rechace JSON mal formado, campos faltantes y tipos incorrectos."""
    return JSONResponse(
        status_code=400,
        content={
            "error": (
                "Solicitud inválida: envíe un objeto JSON con los campos y tipos documentados"
            ),
        },
    )


@app.exception_handler(HTTPException)
async def error_http(_request: Request, exc: HTTPException) -> JSONResponse:
    """Mantenga el formato de error para rutas y métodos no disponibles."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)},
        headers=exc.headers,
    )


@app.post(
    "/tarifa",
    response_model=RespuestaTarifa,
    responses={400: {"model": RespuestaError, "description": "Entrada inválida"}},
)
def consultar_tarifa_http(solicitud: SolicitudTarifa) -> RespuestaTarifa:
    """Consulte la tarifa de un destino y, para residencial, de un estrato."""
    return RespuestaTarifa(
        tarifa=consultar_tarifa(solicitud.destino, solicitud.estrato),
    )


@app.post(
    "/impuesto",
    response_model=RespuestaImpuesto,
    responses={400: {"model": RespuestaError, "description": "Entrada inválida"}},
)
def calcular_impuesto_http(solicitud: SolicitudImpuesto) -> RespuestaImpuesto:
    """Calcule el impuesto usando la misma tabla que la consulta de tarifa."""
    impuesto = calcular_impuesto(solicitud.avaluo, solicitud.destino, solicitud.estrato)
    return RespuestaImpuesto(
        tarifa=consultar_tarifa(solicitud.destino, solicitud.estrato),
        impuesto=impuesto,
    )
