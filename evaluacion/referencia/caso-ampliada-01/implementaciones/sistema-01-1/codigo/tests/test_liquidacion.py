"""Pruebas de aceptación y restricciones de la liquidación."""

from decimal import Decimal

import pytest

from aplicacion.liquidacion import (
    NegocioAbiertoError,
    ReglaNegocioError,
    ValorNoPermitidoError,
    calcular_comision,
)
from dominio.comisiones import Negocio, ResultadoComision, calcular_para_negocio


def test_rf_01_esc_01_venta_con_un_asesor():
    resultado = calcular_comision("venta", 1, "cerrado", Decimal(1000000))

    assert resultado.comision_de_la_inmobiliaria == Decimal(30000)
    assert resultado.comision_de_cada_asesor == Decimal(300000)


def test_rf_01_esc_02_arriendo_con_dos_asesores():
    resultado = calcular_comision("arriendo", 2, "cerrado", Decimal(1000000))

    assert resultado.comision_de_la_inmobiliaria == Decimal(1000000)
    assert resultado.comision_de_cada_asesor == Decimal(300000)


def test_rf_01_esc_03_rechazar_negocio_abierto():
    with pytest.raises(NegocioAbiertoError, match="^El negocio aún no está cerrado$"):
        calcular_comision("venta", 1, "abierto", Decimal(1000000))


def test_rf_01_esc_04_minimo_por_asesor():
    resultado = calcular_comision("venta", 2, "cerrado", Decimal(5000000))

    assert resultado.comision_de_cada_asesor == Decimal(300000)


def test_rf_01_esc_05_rechazar_valor_cero():
    with pytest.raises(ValorNoPermitidoError):
        calcular_comision("arriendo", 1, "cerrado", Decimal(0))


@pytest.mark.parametrize(
    "valor",
    [Decimal("-0.01"), Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), 1, "1", None],
)
def test_valor_no_permitido(valor):
    with pytest.raises(ValorNoPermitidoError):
        calcular_comision("arriendo", 1, "cerrado", valor)


@pytest.mark.parametrize("tipo", ["", "Venta", "otro", None, 1])
def test_tipo_no_permitido(tipo):
    with pytest.raises(ReglaNegocioError):
        calcular_comision(tipo, 1, "cerrado", Decimal(1))


@pytest.mark.parametrize("asesores", [0, 3, -1, True, Decimal(1), "1", None])
def test_numero_de_asesores_no_permitido(asesores):
    with pytest.raises(ReglaNegocioError):
        calcular_comision("venta", asesores, "cerrado", Decimal(1))


@pytest.mark.parametrize("estado", ["", "Cerrado", "pendiente", None, 1])
def test_estado_no_permitido(estado):
    with pytest.raises(ReglaNegocioError):
        calcular_comision("venta", 1, estado, Decimal(1))


def test_importe_positivo_menor_que_un_peso():
    resultado = calcular_comision("arriendo", 1, "cerrado", Decimal("0.01"))

    assert resultado == ResultadoComision(Decimal(0), Decimal(300000))


@pytest.mark.parametrize(
    ("asesores", "valor", "esperado"),
    [
        (1, "749999.99", "300000"),
        (1, "750000", "300000"),
        (1, "1000000", "400000"),
        (2, "1500000", "300000"),
        (2, "2000000", "400000"),
    ],
)
def test_limite_minimo_y_reparto(asesores, valor, esperado):
    resultado = calcular_comision("arriendo", asesores, "cerrado", Decimal(valor))

    assert resultado.comision_de_cada_asesor == Decimal(esperado)


@pytest.mark.parametrize(
    ("valor", "inmobiliaria", "asesor"),
    [
        ("1000001.49", "1000001", "400001"),
        ("1000001.50", "1000002", "400001"),
        ("1000001.25", "1000001", "400001"),
    ],
)
def test_redondeo_al_peso(valor, inmobiliaria, asesor):
    resultado = calcular_comision("arriendo", 1, "cerrado", Decimal(valor))

    assert resultado == ResultadoComision(Decimal(inmobiliaria), Decimal(asesor))
    assert resultado.comision_de_la_inmobiliaria.as_tuple().exponent == 0
    assert resultado.comision_de_cada_asesor.as_tuple().exponent == 0


def test_dominio_calcula_venta_sin_minimo():
    negocio = Negocio("venta", 2, "cerrado", Decimal(100000000))

    resultado = calcular_para_negocio(negocio)

    assert resultado == ResultadoComision(Decimal(3000000), Decimal(600000))


def test_dominio_rechaza_negocio_abierto():
    negocio = Negocio("venta", 1, "abierto", Decimal(1000000))

    with pytest.raises(NegocioAbiertoError, match="^El negocio aún no está cerrado$"):
        calcular_para_negocio(negocio)


def test_dominio_valida_importe():
    negocio = Negocio("venta", 1, "cerrado", Decimal(-1))

    with pytest.raises(ValorNoPermitidoError):
        calcular_para_negocio(negocio)


def test_dominio_rechaza_objeto_distinto_de_negocio():
    with pytest.raises(ReglaNegocioError):
        calcular_para_negocio(None)
