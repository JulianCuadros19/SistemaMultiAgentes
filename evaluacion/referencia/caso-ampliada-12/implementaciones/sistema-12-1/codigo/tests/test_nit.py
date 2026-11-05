import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from esquemas.nit import DigitoRespuesta, NumeroEntrada, ValidacionEntrada, ValidacionRespuesta
from rutas.nit import calcular_digito, validar_nit
from servicios.nit import InvalidCharactersError, MaxLengthExceededError
from servicios.nit import calcular_digito as calcular_digito_servicio
from servicios.nit import validar_nit as validar_nit_servicio


def test_rf_01_esc_01_calcular_numero_valido():
    entrada = NumeroEntrada(numero="900123456")
    respuesta = calcular_digito(entrada)
    assert isinstance(respuesta, DigitoRespuesta)
    assert respuesta.digito_calculado == 8


def test_rf_01_esc_02_calcular_con_separadores():
    entrada = NumeroEntrada(numero="900.123.456")
    respuesta = calcular_digito(entrada)
    assert respuesta.digito_calculado == 8


def test_rf_01_esc_03_rechazar_longitud_excesiva():
    entrada = NumeroEntrada(numero="1234567890123456")
    with pytest.raises(HTTPException) as capturada:
        calcular_digito(entrada)
    assert capturada.value.status_code == 400
    assert capturada.value.detail == "El NIT admite como máximo 15 dígitos"


def test_rf_02_esc_01_validar_digito_correcto():
    entrada = ValidacionEntrada(nit="900.123.456-8")
    respuesta = validar_nit(entrada)
    assert isinstance(respuesta, ValidacionRespuesta)
    assert respuesta.validez_del_nit is True
    assert respuesta.digito_esperado == 8
    assert respuesta.digito_calculado == 8


def test_rf_02_esc_02_validar_digito_incorrecto():
    entrada = ValidacionEntrada(nit="900123456-7")
    respuesta = validar_nit(entrada)
    assert respuesta.validez_del_nit is False
    assert respuesta.digito_esperado == 8
    assert respuesta.digito_calculado == 8


def test_rf_02_esc_03_rechazar_letras():
    entrada = ValidacionEntrada(nit="90012A456")
    with pytest.raises(HTTPException) as capturada:
        validar_nit(entrada)
    assert capturada.value.status_code == 400
    assert capturada.value.detail == "El NIT solo admite dígitos"


def test_rf_02_esc_04_rechazar_longitud_excesiva():
    entrada = ValidacionEntrada(nit="1234567890123456")
    with pytest.raises(HTTPException) as capturada:
        validar_nit(entrada)
    assert capturada.value.status_code == 400
    assert capturada.value.detail == "El NIT admite como máximo 15 dígitos"


@pytest.mark.parametrize(
    ("numero", "esperado"),
    [
        ("0", 0),
        ("4", 1),
        ("1", 8),
        ("8", 9),
        ("000000000000001", 8),
        ("100000000000000", 6),
        ("123456789012345", 2),
        ("900-123.456", 8),
    ],
)
def test_calculo_limites_y_pesos(numero, esperado):
    respuesta = calcular_digito(NumeroEntrada(numero=numero))
    assert respuesta.digito_calculado == esperado
    assert calcular_digito_servicio(numero) == esperado


@pytest.mark.parametrize(
    ("nit", "valido", "esperado"),
    [
        ("0", True, 0),
        ("1", False, 0),
        ("000000000000000", True, 0),
        ("000000000000018", True, 8),
        ("000.000.000.000.018", True, 8),
    ],
)
def test_validacion_limites(nit, valido, esperado):
    respuesta = validar_nit(ValidacionEntrada(nit=nit))
    assert respuesta.validez_del_nit is valido
    assert respuesta.digito_esperado == esperado
    assert respuesta.digito_calculado == esperado
    assert validar_nit_servicio(nit) == (valido, esperado, esperado)


@pytest.mark.parametrize("texto", ["", ".--", "12A", "12 3", "12/3", "１２３", "²"])
def test_contenido_invalido_en_ambas_operaciones(texto):
    with pytest.raises(InvalidCharactersError):
        calcular_digito_servicio(texto)
    with pytest.raises(InvalidCharactersError):
        validar_nit_servicio(texto)
    with pytest.raises(HTTPException) as calculo:
        calcular_digito(NumeroEntrada(numero=texto))
    with pytest.raises(HTTPException) as validacion:
        validar_nit(ValidacionEntrada(nit=texto))
    assert calculo.value.status_code == 400
    assert validacion.value.status_code == 400
    assert validacion.value.detail == "El NIT solo admite dígitos"


@pytest.mark.parametrize("texto", ["1234567890123456", "123.456.789.012.345-6"])
def test_servicios_rechazan_mas_de_quince_digitos(texto):
    with pytest.raises(MaxLengthExceededError, match="El NIT admite como máximo 15 dígitos"):
        calcular_digito_servicio(texto)
    with pytest.raises(MaxLengthExceededError, match="El NIT admite como máximo 15 dígitos"):
        validar_nit_servicio(texto)


@pytest.mark.parametrize("valor", [None, 123, True])
def test_esquemas_rechazan_entrada_no_textual(valor):
    with pytest.raises(ValidationError):
        NumeroEntrada(numero=valor)
    with pytest.raises(ValidationError):
        ValidacionEntrada(nit=valor)
    with pytest.raises(InvalidCharactersError):
        calcular_digito_servicio(valor)
    with pytest.raises(InvalidCharactersError):
        validar_nit_servicio(valor)


@pytest.mark.parametrize("digito", [0, 9])
def test_esquemas_salida_aceptan_limites(digito):
    assert DigitoRespuesta(digito_calculado=digito).digito_calculado == digito
    respuesta = ValidacionRespuesta(True, digito, digito)
    assert respuesta.validez_del_nit is True
    assert respuesta.digito_esperado == digito
    assert respuesta.digito_calculado == digito


@pytest.mark.parametrize("digito", [-1, 10, "8", True])
def test_esquemas_salida_rechazan_digitos_invalidos(digito):
    with pytest.raises(ValidationError):
        DigitoRespuesta(digito_calculado=digito)
    with pytest.raises(ValidationError):
        ValidacionRespuesta(True, digito, 8)
    with pytest.raises(ValidationError):
        ValidacionRespuesta(True, 8, digito)


def test_esquema_salida_rechaza_validez_no_booleana():
    with pytest.raises(ValidationError):
        ValidacionRespuesta("sí", 8, 8)
