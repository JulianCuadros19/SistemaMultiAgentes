"""Esquemas Pydantic de las peticiones y respuestas de tarifas prediales."""

from collections.abc import Callable
from typing import ParamSpec, Self

from pydantic import BaseModel, Field, model_validator

_P = ParamSpec("_P")


def _constructor_validado(constructor: Callable[_P, None]) -> Callable[_P, None]:
    """Indica que el constructor delega toda la validación a BaseModel."""
    setattr(constructor, "__pydantic_base_init__", True)
    return constructor


class ConsultaTarifaRequest(BaseModel):
    """Petición de consulta de tarifa.

    Args:
        destino: Nombre del destino económico.
        estrato: Entero opcional, exclusivamente para destino residencial.

    Raises:
        ValueError: Si el estrato se proporciona para otro destino.
        pydantic.ValidationError: Si los campos tienen tipos incorrectos.
    """

    destino: str = Field(strict=True)
    estrato: int | None = Field(default=None, strict=True)

    @_constructor_validado
    def __init__(self, destino: str, estrato: int | None = None) -> None:
        """Valida y construye la petición.

        Args:
            destino: Nombre del destino económico.
            estrato: Estrato residencial opcional.

        Raises:
            pydantic.ValidationError: Si los datos no cumplen el esquema.
        """
        super().__init__(destino=destino, estrato=estrato)

    @model_validator(mode="after")
    def _validar_aplicacion_estrato(self) -> Self:
        if self.estrato is not None and self.destino != "residencial":
            raise ValueError("El estrato solo aplica al destino residencial")
        return self


class ConsultaTarifaResponse(BaseModel):
    """Respuesta de consulta de tarifa.

    Args:
        tarifa: Tarifa entera por mil.
        estrato_aplicado: Estrato residencial aplicado, o ninguno.
    """

    tarifa: int = Field(strict=True)
    estrato_aplicado: int | None = Field(default=None, strict=True, ge=1, le=6)

    def __init__(self, tarifa: int, estrato_aplicado: int | None = None) -> None:
        """Construye la respuesta validando sus tipos.

        Args:
            tarifa: Tarifa entera por mil.
            estrato_aplicado: Estrato residencial aplicado, o ninguno.

        Raises:
            pydantic.ValidationError: Si los datos no cumplen el esquema.
        """
        super().__init__(tarifa=tarifa, estrato_aplicado=estrato_aplicado)


class CalculoImpuestoRequest(BaseModel):
    """Petición de cálculo del impuesto.

    Args:
        avaluo: Avalúo en pesos enteros.
        destino: Nombre del destino económico.
        estrato: Entero opcional, exclusivamente para destino residencial.

    Raises:
        ValueError: Si el estrato se proporciona para otro destino.
        pydantic.ValidationError: Si los campos tienen tipos incorrectos.
    """

    avaluo: int = Field(strict=True)
    destino: str = Field(strict=True)
    estrato: int | None = Field(default=None, strict=True)

    @_constructor_validado
    def __init__(self, avaluo: int, destino: str, estrato: int | None = None) -> None:
        """Valida y construye la petición.

        Args:
            avaluo: Avalúo en pesos enteros.
            destino: Nombre del destino económico.
            estrato: Estrato residencial opcional.

        Raises:
            pydantic.ValidationError: Si los datos no cumplen el esquema.
        """
        super().__init__(avaluo=avaluo, destino=destino, estrato=estrato)

    @model_validator(mode="after")
    def _validar_aplicacion_estrato(self) -> Self:
        if self.estrato is not None and self.destino != "residencial":
            raise ValueError("El estrato solo aplica al destino residencial")
        return self


class CalculoImpuestoResponse(BaseModel):
    """Respuesta de cálculo del impuesto.

    Args:
        impuesto_calculado: Impuesto en pesos enteros.
        tarifa: Tarifa entera por mil utilizada.
        estrato_aplicado: Estrato residencial aplicado, o ninguno.
    """

    impuesto_calculado: int = Field(strict=True)
    tarifa: int = Field(strict=True)
    estrato_aplicado: int | None = Field(default=None, strict=True, ge=1, le=6)

    def __init__(
        self, impuesto_calculado: int, tarifa: int, estrato_aplicado: int | None = None
    ) -> None:
        """Construye la respuesta validando sus tipos.

        Args:
            impuesto_calculado: Impuesto en pesos enteros.
            tarifa: Tarifa entera por mil utilizada.
            estrato_aplicado: Estrato residencial aplicado, o ninguno.

        Raises:
            pydantic.ValidationError: Si los datos no cumplen el esquema.
        """
        super().__init__(
            impuesto_calculado=impuesto_calculado,
            tarifa=tarifa,
            estrato_aplicado=estrato_aplicado,
        )
