"""Servicio HTTP del NIT y contrato OpenAPI."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from nit_service import (
    NitError,
    calcular_digito,
    normalizar_numero,
    validar_nit,
    validar_nit_completo,
)


class _Entrada(BaseModel):
    """Rechaza campos adicionales en las solicitudes."""

    model_config = ConfigDict(extra="forbid")


class EntradaCalculo(_Entrada):
    """Solicitud de cálculo para un número sin su dígito de verificación."""

    numero: StrictStr = Field(description="De 1 a 15 dígitos; admite puntos y guiones")


class EntradaValidacion(_Entrada):
    """Solicitud con número y dígito en campos separados."""

    numero: StrictStr = Field(description="Número sin el dígito de verificación")
    digito: StrictStr = Field(description="Un único carácter ASCII de 0 a 9")


class EntradaNitCompleto(_Entrada):
    """Solicitud con un NIT completo en un único campo."""

    nit: StrictStr = Field(description="NIT completo; el último guion separa el dígito")


class RespuestaCalculo(BaseModel):
    """Número normalizado y dígito calculado."""

    numero: str
    digito: int = Field(ge=0, le=9)


class RespuestaValidacion(BaseModel):
    """Resultado de la validación con el dígito esperado."""

    numero: str
    digito: int = Field(ge=0, le=9)
    valido: bool
    digito_esperado: int = Field(ge=0, le=9)


class RespuestaError(BaseModel):
    """Mensaje de error comprensible para el consumidor."""

    error: str


app = FastAPI(
    title="Servicio de dígito de verificación del NIT",
    version="1.0.0",
    description=(
        "Calcula y compara dígitos mediante los pesos indicados y módulo 11. "
        "No comprueba la existencia ni el registro de una empresa."
    ),
)

_ERRORES = {400: {"model": RespuestaError}, 422: {"model": RespuestaError}}


@app.exception_handler(NitError)
async def manejar_error_nit(_request: Request, exc: NitError) -> JSONResponse:
    """Devuelva HTTP 400 cuando una entrada incumple las reglas del NIT."""
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(RequestValidationError)
async def manejar_error_solicitud(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    """Devuelva HTTP 422 para JSON o estructura de solicitud incorrectos."""
    return JSONResponse(
        status_code=422,
        content={
            "error": (
                "Solicitud inválida: envíe JSON con los campos documentados, "
                "todos como cadenas y sin campos adicionales"
            )
        },
    )


@app.post("/calcular", response_model=RespuestaCalculo, responses=_ERRORES)
def calcular(datos: EntradaCalculo) -> RespuestaCalculo:
    """Calcule el dígito de verificación del número recibido."""
    numero = normalizar_numero(datos.numero)
    return RespuestaCalculo(numero=numero, digito=calcular_digito(numero))


@app.post("/validar", response_model=RespuestaValidacion, responses=_ERRORES)
def validar(datos: EntradaValidacion | EntradaNitCompleto) -> RespuestaValidacion:
    """Valide un NIT completo o sus campos separados."""
    if isinstance(datos, EntradaNitCompleto):
        resultado = validar_nit_completo(datos.nit)
    else:
        resultado = validar_nit(datos.numero, datos.digito)
    return RespuestaValidacion(
        numero=resultado.numero,
        digito=resultado.digito,
        valido=resultado.valido,
        digito_esperado=resultado.digito_esperado,
    )
