"""Pruebas de reglas, ejemplos, validaciones y exportación."""

import csv
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

import pytest

from vivienda import calcular, guardar_csv


def test_ejemplo_cliente():
    resultado = calcular("100000000", "120", "12")
    primera = resultado.tabla[0]
    assert resultado.cuota_mensual == 1_399_472
    assert primera.mes == 1
    assert primera.cuota == 1_399_472
    assert primera.interes == 948_879
    assert primera.abono_capital == 450_593
    assert primera.saldo == 99_549_407


def test_conversion_tasa_efectiva_anual():
    resultado = calcular("100000000", "120", "12")
    with localcontext() as contexto:
        contexto.prec = 50
        reconstruida = (Decimal(1) + resultado.tasa_mensual) ** 12 - Decimal(1)
        assert abs(reconstruida - Decimal("0.12")) < Decimal("1e-45")


def test_formula_cuota_fija():
    resultado = calcular("100000000", "120", "12")
    with localcontext() as contexto:
        contexto.prec = 50
        tasa = resultado.tasa_mensual
        esperada = Decimal(100000000) * tasa / (1 - (1 + tasa) ** -120)
        assert resultado.cuota_mensual == int(
            esperada.quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
        )


@pytest.mark.parametrize("monto", ["10000000", "500000000"])
@pytest.mark.parametrize("plazo", ["12", "240"])
@pytest.mark.parametrize("tasa", ["1", "30", "12.50", "1.01", "29.99"])
def test_limites_y_consistencia(monto, plazo, tasa):
    resultado = calcular(monto, plazo, tasa)
    saldo = int(monto)
    assert len(resultado.tabla) == int(plazo)
    with localcontext() as contexto:
        contexto.prec = 50
        for mes, fila in enumerate(resultado.tabla, start=1):
            assert fila.mes == mes
            assert fila.interes == int(
                (Decimal(saldo) * resultado.tasa_mensual).quantize(
                    Decimal(1), rounding=ROUND_HALF_EVEN
                )
            )
            assert fila.abono_capital == fila.cuota - fila.interes
            assert fila.saldo == saldo - fila.abono_capital
            assert fila.saldo >= 0
            for valor in (fila.cuota, fila.interes, fila.abono_capital, fila.saldo):
                assert isinstance(valor, int)
            if mes < int(plazo):
                assert fila.cuota == resultado.cuota_mensual
            else:
                assert fila.cuota == saldo + fila.interes
            saldo = fila.saldo
    assert saldo == 0
    assert sum(fila.abono_capital for fila in resultado.tabla) == int(monto)
    assert resultado.total_pagado == sum(fila.cuota for fila in resultado.tabla)
    assert resultado.total_intereses == sum(fila.interes for fila in resultado.tabla)
    assert resultado.total_pagado == int(monto) + resultado.total_intereses


@pytest.mark.parametrize(
    ("monto", "plazo", "tasa", "mensaje"),
    [
        ("9999999", "120", "12", "Monto fuera de rango"),
        ("500000001", "120", "12", "Monto fuera de rango"),
        ("100000000", "11", "12", "Plazo fuera de rango"),
        ("100000000", "241", "12", "Plazo fuera de rango"),
        ("100000000", "120", "0.99", "Tasa fuera de rango"),
        ("100000000", "120", "30.01", "Tasa fuera de rango"),
        ("100.000.000", "120", "12", "Monto inválido"),
        ("100,000,000", "120", "12", "Monto inválido"),
        ("100000000.0", "120", "12", "Monto inválido"),
        ("-10000000", "120", "12", "Monto inválido"),
        ("", "120", "12", "Monto inválido"),
        ("abc", "120", "12", "Monto inválido"),
        ("100000000", "12.0", "12", "Plazo inválido"),
        ("100000000", "abc", "12", "Plazo inválido"),
        ("100000000", "", "12", "Plazo inválido"),
        ("100000000", "120", "12.123", "Tasa inválida"),
        ("100000000", "120", "12%", "Tasa inválida"),
        ("100000000", "120", "12,50", "Tasa inválida"),
        ("100000000", "120", "NaN", "Tasa inválida"),
        ("100000000", "120", "Infinity", "Tasa inválida"),
        ("100000000", "120", "1e1", "Tasa inválida"),
        ("100000000", "120", "", "Tasa inválida"),
    ],
)
def test_errores_de_entrada(monto, plazo, tasa, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        calcular(monto, plazo, tasa)


def test_espacios_exteriores():
    assert calcular(" 100000000 ", " 120 ", " 12 ") == calcular(
        "100000000", "120", "12"
    )


def test_csv_completo(tmp_path):
    resultado = calcular("100000000", "120", "12")
    ruta = tmp_path / "tabla.csv"
    guardar_csv(resultado, ruta)
    with ruta.open(encoding="utf-8", newline="") as archivo:
        filas = list(csv.reader(archivo))
    assert filas[0] == ["mes", "cuota", "interes", "abono_capital", "saldo"]
    assert len(filas) == 121
    for fila_csv, fila in zip(filas[1:], resultado.tabla, strict=True):
        assert fila_csv == [
            str(fila.mes), str(fila.cuota), str(fila.interes),
            str(fila.abono_capital), str(fila.saldo),
        ]


def test_csv_reemplaza_archivo(tmp_path):
    ruta = tmp_path / "tabla.csv"
    ruta.write_text("contenido anterior", encoding="utf-8")
    guardar_csv(calcular("10000000", "12", "1"), ruta)
    assert "contenido anterior" not in ruta.read_text(encoding="utf-8")


def test_csv_no_crea_directorios(tmp_path):
    with pytest.raises(OSError):
        guardar_csv(calcular("10000000", "12", "1"), tmp_path / "ausente" / "tabla.csv")
