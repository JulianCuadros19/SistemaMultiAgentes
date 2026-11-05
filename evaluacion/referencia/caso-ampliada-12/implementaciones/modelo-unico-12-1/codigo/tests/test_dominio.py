"""Pruebas de las reglas, ejemplos y decisiones de entrada."""

import pytest

from servicio_nit import ErrorNit, calcular_digito, normalizar_nit, validar_nit


@pytest.mark.parametrize(
    ("numero", "esperado"),
    [("0", "0"), ("4", "1"), ("1", "8"), ("2", "5")],
)
def test_ramas_del_residuo(numero: str, esperado: str) -> None:
    assert calcular_digito(numero) == esperado


@pytest.mark.parametrize(
    ("posicion", "peso"),
    list(enumerate((3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71))),
)
def test_cada_peso_se_aplica_desde_la_derecha(posicion: int, peso: int) -> None:
    residuo = peso % 11
    esperado = str(residuo if residuo < 2 else 11 - residuo)
    assert calcular_digito("1" + "0" * posicion) == esperado


def test_ejemplo_confirmado_por_formula() -> None:
    assert calcular_digito("123456789") == "6"
    resultado = validar_nit("123456789", "6")
    assert resultado.valido
    assert resultado.digito_esperado == "6"


def test_formula_para_ejemplo_en_disputa() -> None:
    assert calcular_digito("900123456") == "7"
    assert validar_nit("900123456", "7").valido


def test_ejemplo_del_cliente_con_ocho_sigue_en_disputa() -> None:
    # No se inventa una excepción: esta prueba evidencia la discrepancia pendiente.
    resultado = validar_nit("900123456", "8")
    assert not resultado.valido
    assert resultado.digito_esperado == "7"


def test_digito_incorrecto_informa_el_esperado() -> None:
    resultado = validar_nit("123456789", "5")
    assert not resultado.valido
    assert resultado.nit == "123456789"
    assert resultado.digito_esperado == "6"


@pytest.mark.parametrize("numero", ["123.456.789", "123-456-789", "123.456.789-"])
def test_quita_puntos_y_guiones(numero: str) -> None:
    assert normalizar_nit(numero) == "123456789"
    assert calcular_digito(numero) == "6"
    assert validar_nit(numero, "6").valido


def test_conserva_ceros_iniciales() -> None:
    resultado = validar_nit("000.123.456.789", "6")
    assert resultado.nit == "000123456789"
    assert resultado.valido


def test_acepta_quince_cifras() -> None:
    assert calcular_digito("0" * 15) == "0"


def test_limite_se_aplica_despues_de_quitar_separadores() -> None:
    assert calcular_digito("000.000.000.000.000-") == "0"


@pytest.mark.parametrize("numero", ["ABC", "123A", "123.45B-", "A" * 16])
def test_letras_producen_el_mensaje_acordado(numero: str) -> None:
    with pytest.raises(ErrorNit) as capturado:
        calcular_digito(numero)
    assert str(capturado.value) == "El NIT solo admite dígitos"


@pytest.mark.parametrize("numero", ["1" * 16, "000.000.000.000.000.0"])
def test_exceso_de_longitud_produce_el_mensaje_acordado(numero: str) -> None:
    with pytest.raises(ErrorNit) as capturado:
        calcular_digito(numero)
    assert str(capturado.value) == "El NIT admite como máximo 15 dígitos"


@pytest.mark.parametrize("numero", ["", ".", "--", ".-."])
def test_numero_vacio(numero: str) -> None:
    with pytest.raises(ErrorNit) as capturado:
        calcular_digito(numero)
    assert str(capturado.value) == "El NIT no puede estar vacío"


@pytest.mark.parametrize("numero", [" 123", "123 ", "12 3", "１２３", "١٢٣", "+123"])
def test_rechaza_espacios_y_caracteres_no_ascii(numero: str) -> None:
    with pytest.raises(ErrorNit) as capturado:
        calcular_digito(numero)
    assert str(capturado.value) == "El NIT solo admite dígitos"


@pytest.mark.parametrize("digito", ["", "A", "12", " 6", "6 ", "６", "-6", "6."])
def test_digito_debe_ser_una_sola_cifra(digito: str) -> None:
    with pytest.raises(ErrorNit) as capturado:
        validar_nit("123456789", digito)
    assert str(capturado.value) == "El dígito de verificación debe ser una sola cifra"
