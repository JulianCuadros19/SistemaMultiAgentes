"""Contrato HTTP JSON del servicio provisional de verificación de NIT."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from servicio_nit.dominio import ErrorNit, calcular_digito, normalizar_nit, validar_nit


class NumeroSolicitud(BaseModel):
    """Solicitud de cálculo con el número separado del dígito de verificación."""

    model_config = ConfigDict(extra="forbid", strict=True)
    nit: str = Field(description="Número como texto; admite puntos y guiones, no incluye el DV.")


class ValidacionSolicitud(NumeroSolicitud):
    """Solicitud de validación con una cifra de verificación en un campo separado."""

    digito: str = Field(description="Dígito de verificación como texto de una cifra ASCII.")


class CalculoRespuesta(BaseModel):
    """Número normalizado y dígito calculado según la fórmula provisional."""

    nit: str
    digito: str


class ValidacionRespuesta(BaseModel):
    """Coincidencia y dígito esperado según la fórmula provisional."""

    nit: str
    valido: bool
    digito_esperado: str


class ErrorRespuesta(BaseModel):
    """Mensaje de error de una solicitud rechazada."""

    error: str


def crear_app() -> FastAPI:
    """Construya una aplicación independiente con dos operaciones y documentación OpenAPI."""
    aplicacion = FastAPI(
        title="Servicio de dígito de verificación de NIT",
        version="0.1.0",
        description=(
            "Implementación provisional de la fórmula suministrada. "
            "La fórmula produce 7 para 900123456, pero el cliente indica 8; "
            "esta discrepancia sigue pendiente de aprobación. "
            "No comprueba existencia, registro ni validez legal del NIT."
        ),
    )

    @aplicacion.exception_handler(ErrorNit)
    async def manejar_error_nit(request: Request, error: ErrorNit) -> JSONResponse:
        """Devuelva los mensajes de dominio con estado HTTP 400."""
        return JSONResponse(status_code=400, content={"error": str(error)})

    @aplicacion.exception_handler(RequestValidationError)
    async def manejar_solicitud_invalida(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        """Unifique errores de JSON, campos ausentes, tipos y campos adicionales."""
        return JSONResponse(
            status_code=400,
            content={"error": "Solicitud JSON inválida o incompleta"},
        )

    @aplicacion.post(
        "/calcular",
        response_model=CalculoRespuesta,
        responses={400: {"model": ErrorRespuesta, "description": "Solicitud inválida"}},
    )
    def calcular(solicitud: NumeroSolicitud) -> CalculoRespuesta:
        """Calcule el dígito de un número sin consultar registros externos."""
        numero = normalizar_nit(solicitud.nit)
        return CalculoRespuesta(nit=numero, digito=calcular_digito(numero))

    @aplicacion.post(
        "/validar",
        response_model=ValidacionRespuesta,
        responses={400: {"model": ErrorRespuesta, "description": "Solicitud inválida"}},
    )
    def validar(solicitud: ValidacionSolicitud) -> ValidacionRespuesta:
        """Valide la coincidencia del dígito y devuelva siempre el esperado."""
        resultado = validar_nit(solicitud.nit, solicitud.digito)
        return ValidacionRespuesta(
            nit=resultado.nit,
            valido=resultado.valido,
            digito_esperado=resultado.digito_esperado,
        )

    return aplicacion


app = crear_app()
