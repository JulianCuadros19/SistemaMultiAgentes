import pytest

from esquemas.nit import (
    CalculoDigitoRequest,
    CalculoDigitoResponse,
    ValidarNitRequest,
    ValidarNitResponse,
)


def test_construccion_de_peticiones():
    assert CalculoDigitoRequest("900123456").numero == "900123456"
    assert ValidarNitRequest("900123456-8").nit == "900123456-8"


@pytest.mark.parametrize("digito", [0, 9])
def test_respuestas_admiten_limites(digito):
    assert CalculoDigitoResponse(digito).digito_esperado == digito
    respuesta = ValidarNitResponse(False, digito)
    assert respuesta.valido is False
    assert respuesta.digito_esperado == digito


@pytest.mark.parametrize("digito", [-1, 10, "8", True])
def test_respuestas_rechazan_digitos_invalidos(digito):
    with pytest.raises(ValueError):
        CalculoDigitoResponse(digito)
    with pytest.raises(ValueError):
        ValidarNitResponse(True, digito)


@pytest.mark.parametrize("entrada", [123, None, True])
def test_peticiones_rechazan_valores_no_textuales(entrada):
    with pytest.raises(ValueError):
        CalculoDigitoRequest(entrada)
    with pytest.raises(ValueError):
        ValidarNitRequest(entrada)


def test_respuesta_rechaza_validez_no_booleana():
    with pytest.raises(ValueError):
        ValidarNitResponse(1, 8)
