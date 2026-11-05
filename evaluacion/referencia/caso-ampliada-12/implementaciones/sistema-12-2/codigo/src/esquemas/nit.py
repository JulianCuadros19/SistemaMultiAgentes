"""Esquemas de intercambio para el cálculo y la validación de NIT."""

from pydantic import BaseModel, Field


class CalculoDigitoRequest(BaseModel):
    """Petición de cálculo de un dígito de verificación.

    Attributes:
        numero: Número recibido, incluidos sus separadores.
    """

    numero: str = Field(strict=True)

    def __init__(self, numero: str) -> None:
        """Construye la petición.

        Args:
            numero: Texto del número que se calculará.

        Raises:
            ValueError: Si el valor no es texto.
        """
        super().__init__(numero=numero)


class CalculoDigitoResponse(BaseModel):
    """Respuesta del cálculo del dígito de verificación.

    Attributes:
        digito_esperado: Dígito entero de cero a nueve.
    """

    digito_esperado: int = Field(strict=True, ge=0, le=9)

    def __init__(self, digito_esperado: int) -> None:
        """Construye la respuesta.

        Args:
            digito_esperado: Dígito calculado.

        Raises:
            ValueError: Si el valor no es un entero de cero a nueve.
        """
        super().__init__(digito_esperado=digito_esperado)


class ValidarNitRequest(BaseModel):
    """Petición de validación de un NIT completo.

    Attributes:
        nit: Número y dígito de verificación recibidos.
    """

    nit: str = Field(strict=True)

    def __init__(self, nit: str) -> None:
        """Construye la petición.

        Args:
            nit: Texto del NIT completo.

        Raises:
            ValueError: Si el valor no es texto.
        """
        super().__init__(nit=nit)


class ValidarNitResponse(BaseModel):
    """Respuesta de la validación de un NIT completo.

    Attributes:
        valido: Indica si coincide el dígito recibido.
        digito_esperado: Dígito entero de cero a nueve.
    """

    valido: bool = Field(strict=True)
    digito_esperado: int = Field(strict=True, ge=0, le=9)

    def __init__(self, valido: bool, digito_esperado: int) -> None:
        """Construye la respuesta.

        Args:
            valido: Resultado de la comparación.
            digito_esperado: Dígito calculado.

        Raises:
            ValueError: Si la validez no es booleana o el dígito está fuera de rango.
        """
        super().__init__(valido=valido, digito_esperado=digito_esperado)
