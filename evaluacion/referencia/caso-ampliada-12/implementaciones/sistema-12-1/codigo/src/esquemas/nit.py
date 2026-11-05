"""Modelos de entrada y salida para las operaciones de NIT."""

from pydantic import BaseModel, Field


class NumeroEntrada(BaseModel):
    """Entrada del cálculo; las restricciones del contenido se validan en el servicio.

    Args:
        numero: Texto del número, con posibles puntos y guiones.
    """

    numero: str = Field(strict=True)

    def __init__(self, numero: str) -> None:
        """Construye la entrada del cálculo.

        Args:
            numero: Texto que se enviará al servicio.

        Raises:
            pydantic.ValidationError: Si el valor no es texto.
        """
        super().__init__(numero=numero)


class DigitoRespuesta(BaseModel):
    """Respuesta del cálculo del dígito de verificación.

    Args:
        digito_calculado: Dígito entero entre cero y nueve.
    """

    digito_calculado: int = Field(strict=True, ge=0, le=9)

    def __init__(self, digito_calculado: int) -> None:
        """Construye y valida la respuesta del cálculo.

        Args:
            digito_calculado: Dígito obtenido por el servicio.

        Raises:
            pydantic.ValidationError: Si el valor no es un entero entre cero y nueve.
        """
        super().__init__(digito_calculado=digito_calculado)


class ValidacionEntrada(BaseModel):
    """Entrada de validación; el servicio comprueba el contenido del NIT.

    Args:
        nit: Texto del NIT que incluye su dígito de verificación.
    """

    nit: str = Field(strict=True)

    def __init__(self, nit: str) -> None:
        """Construye la entrada de validación.

        Args:
            nit: Texto que se enviará al servicio.

        Raises:
            pydantic.ValidationError: Si el valor no es texto.
        """
        super().__init__(nit=nit)


class ValidacionRespuesta(BaseModel):
    """Resultado de comparar el dígito recibido con el obtenido por el servicio.

    Args:
        validez_del_nit: Indica si coincide el dígito recibido.
        digito_esperado: Dígito correcto para el número base.
        digito_calculado: Resultado del algoritmo aplicado al número base.
    """

    validez_del_nit: bool = Field(strict=True)
    digito_esperado: int = Field(strict=True, ge=0, le=9)
    digito_calculado: int = Field(strict=True, ge=0, le=9)

    def __init__(
        self, validez_del_nit: bool, digito_esperado: int, digito_calculado: int
    ) -> None:
        """Construye y valida la respuesta de validación.

        Args:
            validez_del_nit: Resultado de la comparación.
            digito_esperado: Dígito correcto para el número base.
            digito_calculado: Dígito obtenido por el algoritmo.

        Raises:
            pydantic.ValidationError: Si un campo incumple su tipo o rango.
        """
        super().__init__(
            validez_del_nit=validez_del_nit,
            digito_esperado=digito_esperado,
            digito_calculado=digito_calculado,
        )
