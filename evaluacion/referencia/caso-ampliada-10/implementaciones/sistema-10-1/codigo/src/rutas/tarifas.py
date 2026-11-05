"""Rutas HTTP para consultar tarifas y calcular el impuesto predial."""

import fastapi
from pydantic import ValidationError

from esquemas.tarifas import (
    CalculoImpuestoRequest,
    CalculoImpuestoResponse,
    ConsultaTarifaRequest,
    ConsultaTarifaResponse,
)
from servicios.tarifas import (
    AvaluoNoValidoError,
    DestinoNoReconocidoError,
    EstratoInvalidoError,
    calcular_impuesto,
    obtener_tarifa,
)


def _consultar(peticion: ConsultaTarifaRequest) -> ConsultaTarifaResponse:
    try:
        resultado = obtener_tarifa(peticion.destino, peticion.estrato)
    except (DestinoNoReconocidoError, EstratoInvalidoError) as error:
        raise fastapi.HTTPException(status_code=400, detail=str(error)) from error
    return ConsultaTarifaResponse(resultado.tarifa, resultado.estrato_aplicado)


def construir_router() -> fastapi.APIRouter:
    """Construye las rutas de consulta y cálculo del impuesto predial.

    Returns:
        Router con GET y POST /tarifas y POST /impuestos/calcular. Los errores de
        negocio producen HTTP 400; las peticiones mal formadas producen HTTP 422.
    """
    router = fastapi.APIRouter()

    @router.get(
        "/tarifas",
        response_model=ConsultaTarifaResponse,
        response_model_exclude_none=True,
    )
    def _consultar_get(destino: str, estrato: int | None = None) -> ConsultaTarifaResponse:
        try:
            peticion = ConsultaTarifaRequest(destino, estrato)
        except ValidationError as error:
            raise fastapi.HTTPException(
                status_code=422, detail="El estrato solo aplica al destino residencial"
            ) from error
        return _consultar(peticion)

    @router.post(
        "/tarifas",
        response_model=ConsultaTarifaResponse,
        response_model_exclude_none=True,
    )
    def _consultar_post(peticion: ConsultaTarifaRequest) -> ConsultaTarifaResponse:
        return _consultar(peticion)

    @router.post(
        "/impuestos/calcular",
        response_model=CalculoImpuestoResponse,
        response_model_exclude_none=True,
    )
    def _calcular_post(peticion: CalculoImpuestoRequest) -> CalculoImpuestoResponse:
        try:
            resultado = calcular_impuesto(peticion.avaluo, peticion.destino, peticion.estrato)
        except (AvaluoNoValidoError, DestinoNoReconocidoError, EstratoInvalidoError) as error:
            raise fastapi.HTTPException(status_code=400, detail=str(error)) from error
        return CalculoImpuestoResponse(
            resultado.impuesto_calculado, resultado.tarifa, resultado.estrato_aplicado
        )

    return router
