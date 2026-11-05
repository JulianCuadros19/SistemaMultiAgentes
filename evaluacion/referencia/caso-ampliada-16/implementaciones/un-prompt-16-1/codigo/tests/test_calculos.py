"""Pruebas de reglas financieras, límites y decisiones de redondeo."""

import csv
from decimal import Decimal, ROUND_HALF_UP, localcontext

import pytest

from credito_vivienda import (
    Credito,
    Fila,
    calcular_cuota,
    calcular_resumen,
    crear_credito,
    generar_tabla,
    guardar_csv,
)


def test_cuota_del_ejemplo():
    credito = crear_credito(100_000_000, 120, "12")
    assert calcular_cuota(credito) == 1_399_472


def test_primer_mes_del_ejemplo():
    credito = crear_credito(100_000_000, 120, "12")
    assert generar_tabla(credito)[0] == Fila(1, 1_399_472, 948_879, 450_593, 99_549_407)


@pytest.mark.parametrize(
    ("monto", "plazo", "tasa"),
    [(10_000_000, 12, "1"), (500_000_000, 240, "30"), (100_000_000, 120, "12.34")],
)
def test_limites_inclusivos_y_dos_decimales(monto, plazo, tasa):
    credito = crear_credito(monto, plazo, tasa)
    assert credito.monto == Decimal(monto)
    assert credito.plazo == plazo
    assert credito.tasa_anual == Decimal(tasa)


@pytest.mark.parametrize(
    ("monto", "plazo", "tasa", "mensaje"),
    [
        (9_999_999, 120, "12", "Monto"),
        (500_000_001, 120, "12", "Monto"),
        (100_000_000, 11, "12", "Plazo"),
        (100_000_000, 241, "12", "Plazo"),
        (100_000_000, 120, "0.99", "Tasa efectiva anual"),
        (100_000_000, 120, "30.01", "Tasa efectiva anual"),
        (100_000_000, 120, "12.345", "dos decimales"),
        (100_000_000, 120, "12.000", "dos decimales"),
        ("abc", 120, "12", "Monto"),
        ("NaN", 120, "12", "finito"),
        ("Infinity", 120, "12", "finito"),
        (100_000_000, 120, "abc", "Tasa efectiva anual"),
        (100_000_000, 120, "NaN", "finito"),
        (100_000_000, 120, "Infinity", "finito"),
        (100_000_000, 12.5, "12", "Plazo"),
        (100_000_000, True, "12", "Plazo"),
    ],
)
def test_datos_invalidos(monto, plazo, tasa, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        crear_credito(monto, plazo, tasa)


def test_constructor_directo_tambien_valida():
    with pytest.raises(ValueError, match="Monto"):
        Credito(Decimal(1), 120, Decimal(12))


def test_monto_decimal_se_redondea_al_peso_con_mitad_hacia_arriba():
    assert crear_credito("10000000.49", 12, "1").monto == Decimal(10_000_000)
    assert crear_credito("10000000.50", 12, "1").monto == Decimal(10_000_001)


@pytest.mark.parametrize("tasa_anual", ["1", "12", "12.34", "30"])
def test_formula_de_tasa_mensual_y_cuota(tasa_anual):
    credito = crear_credito(100_000_000, 120, tasa_anual)
    with localcontext() as contexto:
        contexto.prec = 80
        tasa = (Decimal(1) + Decimal(tasa_anual) / 100) ** (Decimal(1) / 12) - 1
        cuota = Decimal(100_000_000) * tasa / (1 - (1 + tasa) ** -120)
        esperado = int(cuota.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    assert calcular_cuota(credito) == esperado


@pytest.mark.parametrize(
    ("monto", "plazo", "tasa_anual"),
    [
        (10_000_000, 12, "1"),
        (10_000_000, 240, "30"),
        (500_000_000, 240, "1"),
        (500_000_000, 12, "30"),
        (100_000_000, 120, "12"),
    ],
)
def test_tabla_completa_interes_capital_saldo_y_ultima_cuota(monto, plazo, tasa_anual):
    credito = crear_credito(monto, plazo, tasa_anual)
    filas = generar_tabla(credito)
    assert len(filas) == plazo
    saldo = monto
    cuota_fija = calcular_cuota(credito)
    with localcontext() as contexto:
        contexto.prec = 80
        tasa = (1 + Decimal(tasa_anual) / 100) ** (Decimal(1) / 12) - 1
        for mes, fila in enumerate(filas, start=1):
            interes = int((Decimal(saldo) * tasa).quantize(Decimal(1), rounding=ROUND_HALF_UP))
            assert fila.mes == mes
            assert fila.interes == interes
            assert fila.cuota == (saldo + interes if mes == plazo else cuota_fija)
            assert fila.abono_capital == fila.cuota - interes
            saldo -= fila.abono_capital
            assert fila.saldo == saldo
            assert all(
                type(valor) is int
                for valor in (fila.cuota, fila.interes, fila.abono_capital, fila.saldo)
            )
    assert filas[-1].saldo == 0
    assert sum(fila.abono_capital for fila in filas) == monto


def test_resumen_incluye_ajuste_final():
    credito = crear_credito(100_000_000, 120, "12")
    filas = generar_tabla(credito)
    resumen = calcular_resumen(credito)
    assert resumen.total_pagado == sum(fila.cuota for fila in filas)
    assert resumen.total_intereses == sum(fila.interes for fila in filas)
    assert resumen.total_pagado - resumen.total_intereses == 100_000_000


def test_calculos_independientes_de_precision_decimal_del_entorno():
    credito = crear_credito(100_000_000, 120, "12")
    esperado = generar_tabla(credito)
    with localcontext() as contexto:
        contexto.prec = 6
        contexto.rounding = "ROUND_DOWN"
        otro = crear_credito("100000000.50", 120, "12")
        assert otro.monto == Decimal(100_000_001)
        assert calcular_cuota(credito) == 1_399_472
        assert generar_tabla(credito) == esperado
        assert contexto.prec == 6


def test_csv_contiene_toda_la_tabla_y_sobrescribe(tmp_path):
    filas = generar_tabla(crear_credito(100_000_000, 120, "12"))
    ruta = tmp_path / "tabla.csv"
    ruta.write_text("anterior", encoding="utf-8")
    guardar_csv(filas, ruta)
    with ruta.open(encoding="utf-8", newline="") as archivo:
        registros = list(csv.reader(archivo))
    assert registros[0] == ["mes", "cuota", "interes", "abono_capital", "saldo"]
    assert len(registros) == 121
    for registro, fila in zip(registros[1:], filas, strict=True):
        assert list(map(int, registro)) == [
            fila.mes, fila.cuota, fila.interes, fila.abono_capital, fila.saldo
        ]


def test_csv_propaga_error_de_escritura(tmp_path):
    with pytest.raises(OSError):
        guardar_csv([], tmp_path / "inexistente" / "tabla.csv")
