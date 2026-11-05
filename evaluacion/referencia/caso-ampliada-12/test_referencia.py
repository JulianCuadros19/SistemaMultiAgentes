"""Pruebas de aceptación de referencia del caso 12, dígito de verificación del NIT (ADR-0019).

Verifican solo lo que la ficha del caso dice sin ambigüedad, a través de la interfaz de
`interfaz.md`. Las mismas pruebas evalúan al sistema, al modelo único y a la implementación manual.
"""

from adaptador_referencia import calcular_digito, validar_nit
from referencia_comun import rechaza


def test_digito_del_primer_ejemplo():
    assert calcular_digito("900123456") == 8


def test_digito_del_segundo_ejemplo():
    assert calcular_digito("123456789") == 6


def test_valida_un_nit_correcto_con_puntos_y_guion():
    assert validar_nit("900.123.456-8") == (True, 8)


def test_informa_el_digito_esperado_de_un_nit_incorrecto():
    assert validar_nit("900123456-7") == (False, 8)


def test_quita_puntos_y_guiones_antes_de_calcular():
    assert calcular_digito("900.123.456") == 8
    assert calcular_digito("900-123-456") == 8


def test_residuo_cero_o_uno_es_el_digito():
    assert calcular_digito("100000001") == 0
    assert calcular_digito("100000005") == 1


def test_numeros_de_uno_y_de_quince_digitos():
    assert calcular_digito("7") == 1
    assert calcular_digito("123456789012345") == 2


def test_muestra_de_numeros():
    muestra = {"860001022": 7, "830114921": 1, "999999999999999": 2, "800197268": 4}
    assert {numero: calcular_digito(numero) for numero in muestra} == muestra


def test_rechaza_letras():
    rechaza(calcular_digito, "90A123456", mensaje="El NIT solo admite dígitos")
    rechaza(validar_nit, "90A123456-8", mensaje="El NIT solo admite dígitos")


def test_rechaza_mas_de_quince_digitos():
    rechaza(calcular_digito, "1234567890123456", mensaje="El NIT admite como máximo 15 dígitos")
