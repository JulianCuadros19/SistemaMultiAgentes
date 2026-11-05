"""Pruebas de las reglas y ejemplos del cálculo del NIT."""

import pytest

from nit_service import NitInvalido, calcular_digito, normalizar_nit, validar_nit


@pytest.mark.parametrize("nit, esperado", [("900123456", 8), ("123456789", 6)])
def test_ejemplos_confirmados(nit: str, esperado: int) -> None:
    assert calcular_digito(nit) == esperado
    assert validar_nit(nit, str(esperado)) == (True, esperado)


@pytest.mark.parametrize(
    "posicion, peso",
    list(enumerate((3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71))),
)
def test_cada_peso_desde_la_derecha(posicion: int, peso: int) -> None:
    residuo = peso % 11
    esperado = residuo if residuo in (0, 1) else 11 - residuo
    assert calcular_digito("1" + "0" * posicion) == esperado


@pytest.mark.parametrize("nit, esperado", [("0", 0), ("4", 1), ("1", 8)])
def test_ramas_del_residuo(nit: str, esperado: int) -> None:
    assert calcular_digito(nit) == esperado


@pytest.mark.parametrize("nit", ["900.123.456", "900-123-456", "9.00-123.456-", ".900123456-"])
def test_elimina_puntos_y_guiones(nit: str) -> None:
    assert normalizar_nit(nit) == "900123456"
    assert calcular_digito(nit) == 8
    assert validar_nit(nit, "8") == (True, 8)


def test_conserva_ceros_iniciales() -> None:
    assert normalizar_nit("000.123-456") == "000123456"
    assert calcular_digito("000123456") == calcular_digito("123456")


def test_admite_quince_digitos() -> None:
    assert calcular_digito("000000000000001") == 8
    assert calcular_digito("0" * 15) == 0


def test_validacion_negativa_devuelve_esperado() -> None:
    assert validar_nit("900123456", "7") == (False, 8)


@pytest.mark.parametrize(
    "nit, mensaje",
    [
        ("", "El NIT debe contener al menos un dígito"),
        (".-.-", "El NIT debe contener al menos un dígito"),
        ("ABC", "El NIT solo admite dígitos"),
        ("123A", "El NIT solo admite dígitos"),
        (" 123", "El NIT solo admite dígitos"),
        ("123 ", "El NIT solo admite dígitos"),
        ("12 3", "El NIT solo admite dígitos"),
        ("12\t3", "El NIT solo admite dígitos"),
        ("12\n3", "El NIT solo admite dígitos"),
        ("１２３", "El NIT solo admite dígitos"),
        ("123/456", "El NIT solo admite dígitos"),
        ("1234567890123456", "El NIT admite como máximo 15 dígitos"),
        ("0000000000000001", "El NIT admite como máximo 15 dígitos"),
        ("123.456.789.012.345-6", "El NIT admite como máximo 15 dígitos"),
    ],
)
def test_errores_del_nit_en_ambas_operaciones(nit: str, mensaje: str) -> None:
    with pytest.raises(NitInvalido) as calculo:
        calcular_digito(nit)
    assert str(calculo.value) == mensaje
    with pytest.raises(NitInvalido) as validacion:
        validar_nit(nit, "8")
    assert str(validacion.value) == mensaje


@pytest.mark.parametrize("digito", ["", "88", "A", " 8", "8 ", "-8", "８"])
def test_formato_del_digito(digito: str) -> None:
    with pytest.raises(NitInvalido) as error:
        validar_nit("900123456", digito)
    assert str(error.value) == "El dígito de verificación debe ser un único dígito de texto"
