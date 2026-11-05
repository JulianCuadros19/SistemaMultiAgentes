"""Pruebas de reglas, límites, errores y ejemplo del cliente."""

from decimal import ROUND_HALF_UP, Decimal, localcontext
from itertools import product

import pytest

from vivienda import (
    Credito,
    EntradaInvalida,
    FilaAmortizacion,
    amortizacion,
    crear_credito,
    cuota_mensual,
    resumen,
    tasa_mensual,
)
from vivienda.calculo import _pesos


@pytest.fixture
def credito() -> Credito:
    return crear_credito("100000000", "120", "12")


def test_cuota_del_ejemplo(credito: Credito) -> None:
    assert cuota_mensual(credito) == 1_399_472


def test_primer_mes_del_ejemplo(credito: Credito) -> None:
    assert amortizacion(credito)[0] == FilaAmortizacion(
        mes=1,
        cuota=1_399_472,
        interes=948_879,
        capital=450_593,
        saldo=99_549_407,
    )


def test_conversion_tasa_efectiva(credito: Credito) -> None:
    mensual = tasa_mensual(credito)
    assert isinstance(mensual, Decimal)
    with localcontext() as contexto:
        contexto.prec = 60
        assert abs((1 + mensual) ** 12 - Decimal("1.12")) < Decimal("1e-55")


def test_formula_cuota(credito: Credito) -> None:
    with localcontext() as contexto:
        contexto.prec = 60
        mensual = tasa_mensual(credito)
        exacta = Decimal(credito.monto) * mensual / (1 - (1 + mensual) ** -credito.plazo)
        esperada = int(exacta.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    assert cuota_mensual(credito) == esperada


def test_amortizacion_completa_y_reglas_mensuales(credito: Credito) -> None:
    filas = amortizacion(credito)
    assert len(filas) == 120
    saldo = credito.monto
    with localcontext() as contexto:
        contexto.prec = 60
        mensual = tasa_mensual(credito)
        for mes, fila in enumerate(filas, start=1):
            interes = int((Decimal(saldo) * mensual).quantize(Decimal(1), rounding=ROUND_HALF_UP))
            assert fila.mes == mes
            assert fila.interes == interes
            assert fila.capital == fila.cuota - fila.interes
            assert fila.saldo == saldo - fila.capital
            if mes < credito.plazo:
                assert fila.cuota == cuota_mensual(credito)
            saldo = fila.saldo


def test_ultima_cuota_ajustada(credito: Credito) -> None:
    filas = amortizacion(credito)
    ultima = filas[-1]
    assert ultima.capital == filas[-2].saldo
    assert ultima.cuota == filas[-2].saldo + ultima.interes
    assert ultima.saldo == 0
    assert sum(fila.capital for fila in filas) == credito.monto


def test_resumen_incluye_ultima_cuota(credito: Credito) -> None:
    filas = amortizacion(credito)
    totales = resumen(credito)
    assert totales.total_pagado == sum(fila.cuota for fila in filas)
    assert totales.total_intereses == sum(fila.interes for fila in filas)
    assert totales.total_pagado == credito.monto + totales.total_intereses


@pytest.mark.parametrize(
    ("monto", "plazo", "tasa"),
    list(product((10_000_000, 500_000_000), (12, 240), ("1", "30"))),
)
def test_limites_inclusivos_y_saldos(monto: int, plazo: int, tasa: str) -> None:
    credito = crear_credito(monto, plazo, tasa)
    filas = amortizacion(credito)
    assert len(filas) == plazo
    assert filas[-1].saldo == 0
    assert all(fila.saldo >= 0 and fila.capital > 0 for fila in filas)
    assert sum(fila.capital for fila in filas) == monto


@pytest.mark.parametrize("tasa", ["1.01", "12.50", "29.99", "30.00"])
def test_tasa_con_dos_decimales(tasa: str) -> None:
    assert crear_credito(100_000_000, 120, tasa).tasa_anual == Decimal(tasa)


@pytest.mark.parametrize(
    "monto",
    ["0", "-1", "9999999", "500000001", "100000000.50", "100000000.00", "abc", ""],
)
def test_monto_invalido(monto: str) -> None:
    with pytest.raises(EntradaInvalida, match="Monto: ingrese un entero"):
        crear_credito(monto, 120, "12")


@pytest.mark.parametrize("plazo", ["0", "-12", "11", "241", "120.5", "120.0", "abc", ""])
def test_plazo_invalido(plazo: str) -> None:
    with pytest.raises(EntradaInvalida, match="Plazo: ingrese un entero"):
        crear_credito(100_000_000, plazo, "12")


@pytest.mark.parametrize(
    "tasa",
    ["0", "-1", "0.99", "30.01", "12.001", "12.000", "abc", "", "NaN", "Infinity"],
)
def test_tasa_invalida(tasa: str) -> None:
    with pytest.raises(EntradaInvalida, match="Tasa efectiva anual:"):
        crear_credito(100_000_000, 120, tasa)


@pytest.mark.parametrize("tasa", ["12,50", "12%", "1e1"])
def test_formato_porcentual_elegido(tasa: str) -> None:
    with pytest.raises(EntradaInvalida):
        crear_credito(100_000_000, 120, tasa)


@pytest.mark.parametrize("monto", ["100.000.000", "100,000,000", "1e8"])
def test_monto_sin_separadores(monto: str) -> None:
    with pytest.raises(EntradaInvalida):
        crear_credito(monto, 120, "12")


def test_no_acepta_float_ni_booleanos() -> None:
    with pytest.raises(EntradaInvalida):
        crear_credito(True, 120, "12")
    with pytest.raises(EntradaInvalida):
        crear_credito(100_000_000, True, "12")
    with pytest.raises(EntradaInvalida):
        crear_credito(100_000_000, 120, True)
    with pytest.raises(EntradaInvalida):
        crear_credito(100_000_000, 120, 12.5)  # type: ignore[arg-type]


def test_construccion_directa_tambien_valida() -> None:
    with pytest.raises(EntradaInvalida, match="Monto:"):
        Credito(0, 120, Decimal("12"))
    with pytest.raises(EntradaInvalida, match="Plazo:"):
        Credito(100_000_000, 241, Decimal("12"))
    with pytest.raises(EntradaInvalida, match="Tasa efectiva anual:"):
        Credito(100_000_000, 120, Decimal("NaN"))


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [("10.49", 10), ("10.50", 11), ("10.51", 11)],
)
def test_redondeo_al_peso_y_medios_pesos(valor: str, esperado: int) -> None:
    assert _pesos(Decimal(valor)) == esperado


def test_precision_independiente_del_contexto_externo(credito: Credito) -> None:
    esperadas = amortizacion(credito)
    with localcontext() as contexto:
        contexto.prec = 6
        assert cuota_mensual(credito) == 1_399_472
        assert amortizacion(credito) == esperadas


def test_importes_sin_centavos(credito: Credito) -> None:
    for fila in amortizacion(credito):
        assert all(
            isinstance(valor, int)
            for valor in (fila.cuota, fila.interes, fila.capital, fila.saldo)
        )
