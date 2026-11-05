"""Adaptadores de las operaciones de NIT con traducción de errores a HTTP."""

from fastapi import HTTPException

from esquemas.nit import DigitoRespuesta, NumeroEntrada, ValidacionEntrada, ValidacionRespuesta
from servicios.nit import InvalidCharactersError, MaxLengthExceededError
from servicios.nit import calcular_digito as calcular_digito_servicio
from servicios.nit import validar_nit as validar_nit_servicio


def calcular_digito(numero_entrada: NumeroEntrada) -> DigitoRespuesta:
    """Calcula el dígito y convierte los errores del dominio en errores HTTP.

    Args:
        numero_entrada: Petición con el número cuyo dígito se desea calcular.

    Returns:
        Respuesta con el dígito calculado.

    Raises:
        HTTPException: Con estado 400 si el contenido o la longitud son inválidos.
    """
    try:
        digito = calcular_digito_servicio(numero_entrada.numero)
    except (InvalidCharactersError, MaxLengthExceededError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return DigitoRespuesta(digito_calculado=digito)


def validar_nit(validacion_entrada: ValidacionEntrada) -> ValidacionRespuesta:
    """Valida el NIT y convierte los errores del dominio en errores HTTP.

    Args:
        validacion_entrada: Petición con el NIT que incluye el dígito de verificación.

    Returns:
        Validez del NIT y los dígitos esperado y calculado.

    Raises:
        HTTPException: Con estado 400 y el mensaje del dominio para entradas inválidas.
    """
    try:
        valido, esperado, calculado = validar_nit_servicio(validacion_entrada.nit)
    except (InvalidCharactersError, MaxLengthExceededError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ValidacionRespuesta(
        validez_del_nit=valido,
        digito_esperado=esperado,
        digito_calculado=calculado,
    )
