import pytest

from servicios.nit_validacion import (
    NITMaximoDigitosError,
    NITSoloDigitosError,
    calcular_digito,
    validar_nit,
)


def test_rf_01_esc_01_calcula_digito_esperado():
    assert calcular_digito("900123456") == 8


def test_rf_01_esc_02_acepta_separadores():
    assert calcular_digito("900123456-7") == 8
    assert calcular_digito("900.123.456-7") == 8


def test_rf_01_esc_03_rechaza_letras():
    with pytest.raises(NITSoloDigitosError, match="^El NIT solo admite dígitos$"):
        calcular_digito("90012A456")


def test_rf_02_esc_01_valida_nit_correcto():
    assert validar_nit("900123456-8") == (True, 8)


def test_rf_02_esc_02_informa_digito_incorrecto():
    assert validar_nit("900123456-7") == (False, 8)


def test_rf_02_esc_03_rechaza_mas_de_quince_digitos():
    with pytest.raises(NITMaximoDigitosError, match="^El NIT admite como máximo 15 dígitos$"):
        validar_nit("1234567890123456")


@pytest.mark.parametrize("numero", ["0", "1", "000000000000000", "123456789012345"])
def test_calculo_admite_limites(numero):
    resultado = calcular_digito(numero)
    assert type(resultado) is int
    assert 0 <= resultado <= 9


def test_calculo_rechaza_limite_superior():
    with pytest.raises(NITMaximoDigitosError, match="máximo 15 dígitos"):
        calcular_digito("1234567890123456")


@pytest.mark.parametrize("numero", ["", ".-", " 123", "123 ", "12+3", "１２３", None, 123])
def test_calculo_rechaza_entrada_no_digital(numero):
    with pytest.raises(NITSoloDigitosError, match="solo admite dígitos"):
        calcular_digito(numero)


@pytest.mark.parametrize("nit", ["", "0", "12A-3", "12/3", "١٢٣", None, 123])
def test_validacion_rechaza_entrada_incompleta_o_no_digital(nit):
    with pytest.raises(NITSoloDigitosError, match="solo admite dígitos"):
        validar_nit(nit)


@pytest.mark.parametrize("nit", ["00", "000000000000000"])
def test_validacion_admite_limites(nit):
    assert validar_nit(nit) == (True, 0)


def test_validacion_acepta_puntos():
    assert validar_nit("900.123.456-8") == (True, 8)
