"""Aplicación REST para calcular dígitos y validar NIT."""

from typing import Annotated

from fastapi import FastAPI, HTTPException
from pydantic import BeforeValidator

from esquemas.nit import (
    CalculoDigitoRequest,
    CalculoDigitoResponse,
    ValidarNitRequest,
    ValidarNitResponse,
)
from servicios.nit_validacion import (
    NITMaximoDigitosError,
    NITSoloDigitosError,
    calcular_digito,
    validar_nit,
)


def _comprobar_numero(valor: object) -> object:
    if isinstance(valor, dict) and "numero" not in valor:
        raise ValueError("El campo numero es obligatorio")
    return valor


def _comprobar_nit(valor: object) -> object:
    if isinstance(valor, dict) and "nit" not in valor:
        raise ValueError("El campo nit es obligatorio")
    return valor


def _calcular(
    peticion: Annotated[CalculoDigitoRequest, BeforeValidator(_comprobar_numero)],
) -> CalculoDigitoResponse:
    try:
        digito = calcular_digito(peticion.numero)
    except (NITSoloDigitosError, NITMaximoDigitosError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return CalculoDigitoResponse(digito)


def _validar(
    peticion: Annotated[ValidarNitRequest, BeforeValidator(_comprobar_nit)],
) -> ValidarNitResponse:
    try:
        valido, esperado = validar_nit(peticion.nit)
    except (NITSoloDigitosError, NITMaximoDigitosError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ValidarNitResponse(valido, esperado)


def crear_app() -> object:
    """Crea una aplicación independiente con las dos rutas REST.

    Returns:
        Aplicación FastAPI que implementa el protocolo ASGI.
    """
    app = FastAPI(title="Servicio de validación de NIT", version="0.1")
    app.add_api_route(
        "/v1/nit/calcular-digito",
        _calcular,
        methods=["POST"],
        response_model=CalculoDigitoResponse,
        summary="Calcular el dígito esperado",
    )
    app.add_api_route(
        "/v1/nit/validar",
        _validar,
        methods=["POST"],
        response_model=ValidarNitResponse,
        summary="Validar un NIT completo",
    )
    return app
