import pytest

from nit_service import (
    NitError,
    calcular_digito,
    normalizar_numero,
    validar_nit,
    validar_nit_completo,
)


@pytest.mark.parametrize(
    ("numero", "esperado"),
    [
        ("0", 0),
        ("4", 1),
        ("1", 8),
        ("10", 4),
        ("123456789", 6),
        ("123456789012345", 2),
    ],
)
def test_calculo_pesos_y_ramas_del_residuo(numero, esperado):
    assert calcular_digito(numero) == esperado


def test_ejemplo_123456789():
    assert calcular_digito("123456789") == 6
    assert validar_nit("123456789", "6").valido


def test_ejemplo_900123456_discrepa_con_la_formula():
    productos = (18, 35, 52, 51, 38, 23, 0, 0, 369)
    assert sum(productos) == 686
    assert sum(productos) % 11 == 4
    assert calcular_digito("900123456") == 7


def test_ejemplo_completo_con_8_informa_el_resultado_de_la_formula():
    resultado = validar_nit_completo("900.123.456-8")
    assert not resultado.valido
    assert resultado.digito_esperado == 7


def test_ejemplo_completo_con_7_informa_el_resultado_de_la_formula():
    resultado = validar_nit_completo("900123456-7")
    assert resultado.valido
    assert resultado.digito_esperado == 7


@pytest.mark.parametrize("numero", ["123.456.789", "123-456-789", "123.456-789"])
def test_se_quitan_puntos_y_guiones(numero):
    assert normalizar_numero(numero) == "123456789"
    assert calcular_digito(numero) == 6


def test_ceros_iniciales_se_conservan():
    resultado = validar_nit("0001", "8")
    assert resultado.numero == "0001"
    assert resultado.valido


def test_limite_de_quince_digitos_despues_de_normalizar():
    assert calcular_digito("123.456.789.012.345") == 2


def test_numero_con_letras():
    with pytest.raises(NitError, match="^El NIT solo admite dígitos$"):
        calcular_digito("123A")


def test_numero_con_mas_de_quince_digitos():
    with pytest.raises(NitError, match="^El NIT admite como máximo 15 dígitos$"):
        calcular_digito("123.456.789.012.345.6")


@pytest.mark.parametrize("numero", ["", ".--"])
def test_numero_vacio(numero):
    with pytest.raises(NitError, match="^El NIT debe contener al menos 1 dígito$"):
        calcular_digito(numero)


@pytest.mark.parametrize("numero", [" 123", "123 ", "12/3", "１２３", "١٢٣", "+123"])
def test_solo_se_aceptan_digitos_ascii_y_separadores_documentados(numero):
    with pytest.raises(NitError, match="^El NIT solo admite dígitos$"):
        calcular_digito(numero)


@pytest.mark.parametrize("digito", ["", "10", "-1", "a", " 6", "６", None, 6])
def test_digito_invalido(digito):
    with pytest.raises(
        NitError, match="^El dígito de verificación debe ser un dígito de 0 a 9$"
    ):
        validar_nit("123456789", digito)


@pytest.mark.parametrize("digito", [str(valor) for valor in range(10)])
def test_cualquier_digito_de_cero_a_nueve_tiene_formato_valido(digito):
    resultado = validar_nit("123456789", digito)
    assert resultado.valido == (digito == "6")
    assert resultado.digito_esperado == 6


def test_digito_incorrecto_no_es_error_de_entrada():
    resultado = validar_nit("123456789", "5")
    assert not resultado.valido
    assert resultado.digito == 5
    assert resultado.digito_esperado == 6


def test_completo_separa_por_el_ultimo_guion():
    assert validar_nit_completo("123-456.789-6").valido


def test_completo_sin_guion():
    with pytest.raises(NitError, match="^El NIT completo debe separar el dígito con un guion$"):
        validar_nit_completo("1234567896")


@pytest.mark.parametrize("nit", ["-6", "123456789-", "123456789-66"])
def test_completo_con_una_parte_invalida(nit):
    with pytest.raises(NitError):
        validar_nit_completo(nit)


def test_numero_no_textual():
    with pytest.raises(NitError, match="^El número del NIT debe ser una cadena$"):
        normalizar_numero(123)


def test_completo_no_textual():
    with pytest.raises(NitError, match="^El NIT completo debe ser una cadena$"):
        validar_nit_completo(None)
